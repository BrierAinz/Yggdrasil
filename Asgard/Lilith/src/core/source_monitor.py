"""
Lilith 4.2 — SourceMonitor: monitorea fuentes web y ejecuta pipeline de minería.

Detecta cambios en fuentes configuradas y automáticamente ejecuta el pipeline
de minería web para extraer, limpiar y almacenar nuevo contenido.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .web_mining_models import ScrapingStrategy, classify_source_quality
from .web_mining_orchestrator import WebMiningOrchestrator

logger = logging.getLogger("SourceMonitor")


@dataclass
class MonitorSnapshot:
    url: str
    timestamp: float
    content_hash: str
    extracted: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitorResult:
    """Resultado del monitoreo de una fuente."""

    url: str
    changed: bool
    facts_generated: int = 0
    error: Optional[str] = None
    processing_time: float = 0.0


class SourceMonitorStore:
    """Persiste el último snapshot por URL en Data/monitor_snapshots.json."""

    def __init__(self, base_path: Path):
        self.path = Path(base_path) / "Data" / "monitor_snapshots.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, url: str) -> Optional[MonitorSnapshot]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            entry = data.get(url)
            if not entry:
                return None
            return MonitorSnapshot(**entry)
        except Exception:
            return None

    def save(self, snapshot: MonitorSnapshot) -> None:
        try:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            data[snapshot.url] = snapshot.__dict__
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def load_seen_items(self, monitor_id: str) -> set:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return set(data.get(f"seen_{monitor_id}", []))
        except Exception:
            return set()

    def save_seen_items(self, monitor_id: str, items: set) -> None:
        try:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            data[f"seen_{monitor_id}"] = list(items)
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def get_last_check(self, monitor_id: str) -> float:
        """Obtiene el timestamp del último check."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get(f"last_check_{monitor_id}", 0)
        except Exception:
            return 0

    def set_last_check(self, monitor_id: str, timestamp: float) -> None:
        """Guarda el timestamp del último check."""
        try:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            data[f"last_check_{monitor_id}"] = timestamp
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass


class SourceMonitorChecker:
    """Hace fetch, extrae snapshot y compara contra el anterior."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.store = SourceMonitorStore(base_path)

    def _fetch(self, url: str, timeout: int = 15) -> str:
        import requests

        r = requests.get(
            url, timeout=timeout, headers={"User-Agent": "Lilith-Monitor/1.0"}
        )
        r.raise_for_status()
        return r.text

    def _clean(self, html: str) -> str:
        """Elimina scripts/styles para comparación estable."""
        import re

        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.I)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s+", " ", html)
        return html.strip()

    def _extract(self, html: str, fields: List[str]) -> Dict[str, Any]:
        """Extrae valores heurísticos por campo."""
        import re

        result: Dict[str, Any] = {}
        lower = (html or "").lower()
        for field in fields:
            # Buscar el campo y capturar texto cercano
            pattern = rf"{re.escape(field)}[:\s]*([A-Z0-9\s\-/]+?)[\s<]"
            m = re.search(pattern, html or "", re.I)
            result[field] = m.group(1).strip()[:80] if m else None
        # DEFCON específico
        if "defcon" in fields:
            m = re.search(r"defcon\s*[:\-]?\s*(\d)", lower)
            result["defcon"] = m.group(1) if m else result.get("defcon")
        return result

    def _hash(self, text: str) -> str:
        return hashlib.sha256(
            (text or "").encode("utf-8", errors="ignore")
        ).hexdigest()[:16]

    def _extract_items(self, html: str, monitor: dict) -> List[dict]:
        """
        Extrae ítems individuales (titulares, señales) para dedup.
        Cada ítem: {"id": str, "text": str}
        """
        import re

        items: List[dict] = []
        selector = monitor.get("item_selector", "headlines")

        if selector == "headlines":
            matches = re.findall(
                r"<(?:h[23]|li|strong)[^>]*>\\s*([^<]{20,150})\\s*</", html or "", re.I
            )
            for m in matches:
                text = re.sub(r"\\s+", " ", m).strip()
                if not text:
                    continue
                item_id = hashlib.md5(
                    text.encode("utf-8", errors="ignore")
                ).hexdigest()[:12]
                items.append({"id": item_id, "text": text})

        return items[:50]

    def _change_ratio(self, a: str, b: str) -> float:
        """0.0 = igual, 1.0 = totalmente distinto (aprox)."""
        try:
            import difflib

            r = difflib.SequenceMatcher(a=a or "", b=b or "").ratio()
            return 1.0 - float(r)
        except Exception:
            return 1.0

    def check(self, monitor: dict) -> Optional[dict]:
        """
        Retorna dict con cambio detectado o None si no hay cambio.
        """
        url = monitor["url"]
        fields = monitor.get("extract", [])
        threshold = float(monitor.get("change_threshold", 0.3))

        try:
            html = self._fetch(url)
        except Exception as e:
            return {"error": str(e), "url": url}

        clean = self._clean(html)
        new_hash = self._hash(clean)
        extracted = self._extract(html, fields)
        now = time.time()

        prev = self.store.load(url)
        new_snapshot = MonitorSnapshot(
            url=url,
            timestamp=now,
            content_hash=new_hash,
            extracted=extracted,
        )

        if prev is None:
            # Primera vez — guardar sin alertar
            self.store.save(new_snapshot)
            return None

        if prev.content_hash == new_hash:
            return None  # Sin cambio

        # Detectar qué cambió en extracted
        changes: Dict[str, Any] = {}
        for k, v in extracted.items():
            prev_v = (prev.extracted or {}).get(k)
            if prev_v != v:
                changes[k] = {"before": prev_v, "after": v}

        # Si no cambió nada de lo extraído, solo alertar si el cambio global supera el umbral
        if not changes:
            # Como no persistimos el texto limpio anterior, aproximamos con hash: si cambió pero no hay cambios
            # en extracted, tratamos esto como "ruido" y lo ignoramos salvo que el umbral lo permita.
            # Para aproximar ratio, usamos el tamaño relativo del clean vs un placeholder (degrada a 1.0 si falla).
            # Mejor: en V2, persistir clean o un sketch; en V1 evitamos spam.
            # Aquí: si threshold >= 1, nunca; si threshold <= 0, siempre.
            if threshold > 0:
                # fallback conservador: NO notificar por ruido si threshold > 0
                self.store.save(new_snapshot)
                return None

        self.store.save(new_snapshot)
        return {
            "url": url,
            "monitor_id": monitor.get("id"),
            "description": monitor.get("description", ""),
            "changes": changes,
            "tags": monitor.get("tags", []),
        }

    def check_v2(self, monitor: dict) -> Optional[dict]:
        """
        V1.1: detecta ítems nuevos por dedup, además del diff de campos.
        Retorna dict con new_items y/o changes, o None si no hay nada nuevo.
        """
        url = monitor["url"]
        monitor_id = monitor["id"]

        try:
            html = self._fetch(url)
        except Exception as e:
            return {"error": str(e), "url": url}

        current_items = self._extract_items(html, monitor)
        seen = self.store.load_seen_items(monitor_id)
        new_items = [i for i in current_items if i.get("id") not in seen]

        all_ids = seen | {i.get("id") for i in current_items if i.get("id")}
        self.store.save_seen_items(monitor_id, all_ids)

        clean = self._clean(html)
        new_hash = self._hash(clean)
        extracted = self._extract(html, monitor.get("extract", []))
        prev = self.store.load(url)
        new_snapshot = MonitorSnapshot(
            url=url,
            timestamp=time.time(),
            content_hash=new_hash,
            extracted=extracted,
        )

        field_changes: Dict[str, Any] = {}
        if prev:
            for k, v in extracted.items():
                prev_v = (prev.extracted or {}).get(k)
                if prev_v != v:
                    field_changes[k] = {"before": prev_v, "after": v}

        self.store.save(new_snapshot)

        if not new_items and not field_changes:
            return None

        return {
            "url": url,
            "monitor_id": monitor_id,
            "description": monitor.get("description", ""),
            "new_items": new_items[:10],
            "changes": field_changes,
            "tags": monitor.get("tags", []),
        }


class SourceMonitorPipeline:
    """
    Integra SourceMonitor con el pipeline de minería web.

    Cuando detecta cambios, ejecuta automáticamente el pipeline completo
    para extraer y almacenar el nuevo contenido.
    """

    def __init__(
        self,
        base_path: Path,
        orchestrator: Optional[WebMiningOrchestrator] = None,
    ):
        self.base_path = Path(base_path)
        self.checker = SourceMonitorChecker(base_path)
        self.store = SourceMonitorStore(base_path)

        # Orquestador de minería
        self.orchestrator = orchestrator or WebMiningOrchestrator(base_path)

        # Configuración
        self._config = self._load_config()

        # Callbacks
        self._on_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_mining_complete: Optional[Callable[[MonitorResult], None]] = None

    def _load_config(self) -> List[Dict[str, Any]]:
        """Carga configuración de monitores."""
        try:
            config_path = self.base_path / "Config" / "source_monitors.json"
            if not config_path.exists():
                return []
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Error loading source monitors config: %s", e)
            return []

    def set_callbacks(
        self,
        on_change: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_mining_complete: Optional[Callable[[MonitorResult], None]] = None,
    ) -> None:
        """Configura callbacks para eventos."""
        self._on_change = on_change
        self._on_mining_complete = on_mining_complete

    async def check_source(self, monitor_config: Dict[str, Any]) -> MonitorResult:
        """
        Verifica una fuente y ejecuta el pipeline si hay cambios.

        Args:
            monitor_config: Configuración del monitor

        Returns:
            MonitorResult con el resultado
        """
        url = monitor_config["url"]
        monitor_id = monitor_config.get("id", "unknown")

        start_time = time.time()

        # Verificar si es tiempo de chequear
        last_check = self.store.get_last_check(monitor_id)
        interval_hours = monitor_config.get("interval_hours", 24)
        interval_seconds = interval_hours * 3600

        if time.time() - last_check < interval_seconds:
            logger.debug("[SourceMonitor] Skipping %s (interval not reached)", url)
            return MonitorResult(
                url=url,
                changed=False,
                processing_time=time.time() - start_time,
            )

        logger.info("[SourceMonitor] Checking source: %s", url)

        # Detectar cambios
        change_result = self.checker.check_v2(monitor_config)
        self.store.set_last_check(monitor_id, time.time())

        if not change_result:
            logger.debug("[SourceMonitor] No changes detected: %s", url)
            return MonitorResult(
                url=url,
                changed=False,
                processing_time=time.time() - start_time,
            )

        # Hay cambios - notificar
        logger.info("[SourceMonitor] Changes detected: %s", url)
        if self._on_change:
            try:
                self._on_change(change_result)
            except Exception as e:
                logger.warning("Error in on_change callback: %s", e)

        # Ejecutar pipeline de minería si está configurado
        if monitor_config.get("auto_mine", True):
            # Determinar estrategia según calidad de fuente
            strategy_str = monitor_config.get("strategy")
            if strategy_str:
                strategy = ScrapingStrategy(strategy_str)
            else:
                quality = classify_source_quality(url)
                if quality == "high":
                    strategy = ScrapingStrategy.ARTICLE_ONLY
                else:
                    strategy = ScrapingStrategy.FULL_PAGE

            # Ejecutar minería
            try:
                mining_result = await self.orchestrator.mine(
                    url,
                    strategy=strategy,
                    store_in_memory=monitor_config.get("store_fact", True),
                )

                monitor_result = MonitorResult(
                    url=url,
                    changed=True,
                    facts_generated=len(mining_result.facts),
                    processing_time=time.time() - start_time,
                )

                if self._on_mining_complete:
                    try:
                        self._on_mining_complete(monitor_result)
                    except Exception as e:
                        logger.warning("Error in on_mining_complete callback: %s", e)

                return monitor_result

            except Exception as e:
                logger.exception("[SourceMonitor] Mining failed for %s: %s", url, e)
                return MonitorResult(
                    url=url,
                    changed=True,
                    error=str(e),
                    processing_time=time.time() - start_time,
                )

        return MonitorResult(
            url=url,
            changed=True,
            processing_time=time.time() - start_time,
        )

    async def check_all(self) -> List[MonitorResult]:
        """
        Verifica todas las fuentes configuradas.

        Returns:
            Lista de resultados
        """
        results = []

        for monitor in self._config:
            if not monitor.get("enabled", True):
                continue

            try:
                result = await self.check_source(monitor)
                results.append(result)

                # Rate limiting entre fuentes
                delay = monitor.get("delay_seconds", 2)
                if delay > 0:
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.exception(
                    "[SourceMonitor] Error checking %s: %s", monitor.get("url"), e
                )
                results.append(
                    MonitorResult(
                        url=monitor.get("url", "unknown"),
                        changed=False,
                        error=str(e),
                    )
                )

        return results

    async def run_scheduled(self, max_iterations: Optional[int] = None) -> None:
        """
        Ejecuta el monitoreo en loop continuo.

        Args:
            max_iterations: Número máximo de iteraciones (None = infinito)
        """
        iteration = 0

        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            logger.info("[SourceMonitor] Scheduled check iteration %d", iteration)

            try:
                results = await self.check_all()

                # Log resumen
                changed = sum(1 for r in results if r.changed)
                errors = sum(1 for r in results if r.error)
                total_facts = sum(r.facts_generated for r in results)

                logger.info(
                    "[SourceMonitor] Iteration %d complete: %d sources, %d changed, %d errors, %d facts",
                    iteration,
                    len(results),
                    changed,
                    errors,
                    total_facts,
                )

            except Exception as e:
                logger.exception("[SourceMonitor] Error in scheduled run: %s", e)

            # Esperar antes de la siguiente iteración
            # Usar el intervalo mínimo de todos los monitores
            min_interval = min(
                (m.get("interval_hours", 24) for m in self._config if m.get("enabled")),
                default=1,
            )
            wait_seconds = min_interval * 3600

            logger.info("[SourceMonitor] Sleeping for %.0f seconds", wait_seconds)
            await asyncio.sleep(wait_seconds)

    def add_monitor(self, monitor_config: Dict[str, Any]) -> None:
        """Agrega un nuevo monitor a la configuración."""
        self._config.append(monitor_config)
        self._save_config()

    def remove_monitor(self, monitor_id: str) -> bool:
        """Remueve un monitor por ID."""
        original_len = len(self._config)
        self._config = [m for m in self._config if m.get("id") != monitor_id]
        if len(self._config) < original_len:
            self._save_config()
            return True
        return False

    def _save_config(self) -> None:
        """Guarda la configuración actual."""
        try:
            config_path = self.base_path / "Config" / "source_monitors.json"
            config_path.write_text(
                json.dumps(self._config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Error saving source monitors config: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del orquestador."""
        return {
            "monitors_configured": len(self._config),
            "monitors_enabled": sum(1 for m in self._config if m.get("enabled")),
            "orchestrator_stats": self.orchestrator.get_stats(),
        }


# Instancia global
_pipeline_instance: Optional[SourceMonitorPipeline] = None


def get_monitor_pipeline(base_path: Optional[Path] = None) -> SourceMonitorPipeline:
    """Obtiene o crea la instancia global del pipeline de monitoreo."""
    global _pipeline_instance
    if _pipeline_instance is None:
        if base_path is None:
            raise ValueError("base_path required for first initialization")
        _pipeline_instance = SourceMonitorPipeline(base_path)
    return _pipeline_instance


# Compatibilidad hacia atrás - mantener clases originales
__all__ = [
    "MonitorSnapshot",
    "MonitorResult",
    "SourceMonitorStore",
    "SourceMonitorChecker",
    "SourceMonitorPipeline",
    "get_monitor_pipeline",
]
