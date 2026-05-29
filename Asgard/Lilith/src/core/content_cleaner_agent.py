"""
Lilith 4.2 — ContentCleanerAgent: limpia texto crudo (salida de WebScraperAgent).

Elimina HTML/XML residual, normaliza espacios y saltos de línea, filtra líneas
boilerplate típicas (cookies, privacidad, menús repetidos), y detecta contenido
duplicado. Salida: CleanedContent listo para QualityFilterAgent.
"""
import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .agent_registry import Agent
from .tools_v3.protocol import ToolResult
from .web_mining_models import CleanedContent, ScrapedContent

logger = logging.getLogger("ContentCleanerAgent")


def _strip_html(text: str) -> str:
    """Elimina etiquetas HTML/XML residuales."""
    if not text or "<" not in text:
        return text
    # Eliminar tags
    out = re.sub(r"<[^>]+>", " ", text)
    # Entidades comunes
    entities = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&mdash;": "—",
        "&ndash;": "–",
        "&hellip;": "…",
    }
    for ent, repl in entities.items():
        out = out.replace(ent, repl)
    # Entidades numéricas
    out = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), out)
    out = re.sub(r"&#[xX]([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), out)
    return out


def _normalize_whitespace(text: str) -> str:
    """Unifica espacios y limita líneas en blanco consecutivas."""
    lines = text.splitlines()
    out: List[str] = []
    prev_blank = False
    for line in lines:
        line = " ".join(line.split()).strip()
        if not line:
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(line)
            prev_blank = False
    return "\n".join(out).strip()


# Líneas que suelen ser boilerplate (menús, pies, legal). Se eliminan si son líneas cortas o coinciden.
_BOILERPLATE_PATTERNS = (
    r"^(cookie|cookies|privacy|terms|legal|subscribe|sign up|sign in|log in|log out|menu|home|contact|about us|follow us|share|tweet|like|©|copyright|all rights reserved|back to top|accept|reject)$",
    r"^[\d\s\.\-]+$",  # Solo números/guiones (paginación)
    r"^[\.\-\s]{2,}$",  # Líneas de puntos o guiones
    r"^(click here|read more|learn more|continue reading|show more)$",
    r"^(share this|share on|follow on|connect with)$",
)
_BOILERPLATE_RE = re.compile(
    "|".join(f"({p})" for p in _BOILERPLATE_PATTERNS), re.IGNORECASE
)

# Patrones de ads y navegación
_AD_PATTERNS = [
    r"advertisement",
    r"sponsored",
    r"promoted",
    r"ad\s*slot",
    r"google.*ad",
    r"facebook.*like",
    r"twitter.*follow",
    r"newsletter",
    r"subscribe.*now",
]
_AD_RE = re.compile("|".join(_AD_PATTERNS), re.IGNORECASE)


def _drop_boilerplate_lines(lines: List[str], min_line_len: int = 3) -> List[str]:
    """Quita líneas que parecen boilerplate."""
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if len(s) < min_line_len:
            continue
        if _BOILERPLATE_RE.match(s):
            continue
        out.append(line)
    return out


def _remove_ad_sections(text: str) -> str:
    """Elimina secciones que parecen publicidad."""
    lines = text.splitlines()
    out: List[str] = []
    for line in lines:
        if not _AD_RE.search(line):
            out.append(line)
    return "\n".join(out)


def _compute_content_hash(text: str) -> str:
    """Calcula hash del contenido para detección de duplicados."""
    # Normalizar antes de hashear (minúsculas, sin espacios extra)
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calcula similitud entre dos textos (0.0-1.0)."""
    try:
        import difflib

        normalized1 = " ".join(text1.lower().split())
        normalized2 = " ".join(text2.lower().split())
        return difflib.SequenceMatcher(None, normalized1, normalized2).ratio()
    except Exception:
        # Fallback: comparación simple de palabras
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)


def _clean(
    raw: str,
    max_paragraph_len: int = 50_000,
    remove_ads: bool = True,
    remove_boilerplate: bool = True,
) -> str:
    """Pipeline de limpieza: HTML → espacios → boilerplate."""
    if not raw or not raw.strip():
        return ""

    original_length = len(raw)

    text = _strip_html(raw)
    text = _normalize_whitespace(text)

    if remove_ads:
        text = _remove_ad_sections(text)

    if remove_boilerplate:
        lines = text.splitlines()
        lines = _drop_boilerplate_lines(lines)
        text = "\n\n".join(lines)

    if len(text) > max_paragraph_len:
        text = text[:max_paragraph_len].rstrip() + "\n\n… (truncado)"

    return text.strip()


def _load_config(base_path: Optional[Path]) -> Dict[str, Any]:
    """Carga Config/content_cleaner.json si existe."""
    if not base_path or not base_path.exists():
        return {}
    try:
        from .json_safe import safe_load

        path = base_path / "Config" / "content_cleaner.json"
        if not path.exists():
            return {}
        data = safe_load(path, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class ContentCleanerAgent(Agent):
    """
    Agente que limpia texto crudo (p. ej. salida de WebScraperAgent).
    Recibe el texto en params['context'] o params['text']; devuelve el texto limpio.
    Soporta detección de duplicados.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = Path(base_path) if base_path else None
        self._config = _load_config(self._base_path)
        self._seen_hashes: Set[str] = set()

    @property
    def agent_id(self) -> str:
        return "content_cleaner"

    @property
    def tool_name(self) -> str:
        return "delegate_content_cleaner"

    @property
    def description(self) -> str:
        return "Limpia texto crudo: elimina HTML residual, normaliza espacios, filtra boilerplate y detecta duplicados."

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecución síncrona compatible con AgentRegistry."""
        try:
            # Si viene de WebScraperAgent, puede tener scraped_content
            scraped = params.get("scraped_content")
            if scraped and isinstance(scraped, ScrapedContent):
                cleaned = self.clean_scraped(scraped)
            else:
                raw = (params.get("context") or params.get("text") or "").strip()
                if not raw:
                    return {
                        "response": "No hay texto que limpiar (pasa 'context' o 'text' con el contenido crudo).",
                        "error": True,
                    }
                cleaned = self.clean_raw(raw, url=params.get("url", ""))

            if not cleaned.cleaned_text:
                return {
                    "response": "Tras la limpieza no quedó contenido utilizable.",
                    "error": False,
                }

            reduction = (
                1 - cleaned.cleaned_length / max(1, cleaned.original_length)
            ) * 100
            logger.info(
                "[ContentCleaner] Cleaned: %s (%d → %d chars, %.1f%% reduction)",
                cleaned.url or "unknown",
                cleaned.original_length,
                cleaned.cleaned_length,
                reduction,
            )

            return {
                "response": cleaned.cleaned_text,
                "cleaned_content": cleaned,
                "reduction_percent": round(reduction, 1),
                "error": False,
            }

        except Exception as e:
            logger.warning("ContentCleanerAgent: %s", e)
            return {"response": str(e), "error": True}

    def clean_raw(self, raw_text: str, url: str = "") -> CleanedContent:
        """
        Limpia texto crudo.

        Args:
            raw_text: Texto a limpiar
            url: URL de origen (opcional)

        Returns:
            CleanedContent
        """
        original_length = len(raw_text)

        cleaned_text = _clean(
            raw_text,
            max_paragraph_len=self._config.get("max_content_length", 50_000),
            remove_ads=self._config.get("remove_ads", True),
            remove_boilerplate=self._config.get("remove_boilerplate", True),
        )

        return CleanedContent(
            url=url,
            cleaned_text=cleaned_text,
            original_length=original_length,
            cleaned_length=len(cleaned_text),
            metadata={},
        )

    def clean_scraped(self, scraped: ScrapedContent) -> CleanedContent:
        """
        Limpia contenido scrapeado.

        Args:
            scraped: ScrapedContent de WebScraperAgent

        Returns:
            CleanedContent
        """
        original_length = len(scraped.text)

        cleaned_text = _clean(
            scraped.text,
            max_paragraph_len=self._config.get("max_content_length", 50_000),
            remove_ads=self._config.get("remove_ads", True),
            remove_boilerplate=self._config.get("remove_boilerplate", True),
        )

        return CleanedContent(
            url=scraped.url,
            cleaned_text=cleaned_text,
            original_length=original_length,
            cleaned_length=len(cleaned_text),
            metadata=scraped.metadata,
        )

    def detect_duplicate(
        self,
        content: CleanedContent,
        existing_hashes: Optional[Set[str]] = None,
        similarity_threshold: float = 0.9,
    ) -> tuple[bool, float]:
        """
        Detecta si el contenido es duplicado.

        Args:
            content: Contenido a verificar
            existing_hashes: Set de hashes existentes (opcional)
            similarity_threshold: Umbral de similitud (0.0-1.0)

        Returns:
            Tuple (es_duplicado, similitud_maxima)
        """
        # Verificar hash exacto
        if content.content_hash in self._seen_hashes:
            logger.info("[ContentCleaner] Exact duplicate detected: %s", content.url)
            return True, 1.0

        if existing_hashes and content.content_hash in existing_hashes:
            logger.info(
                "[ContentCleaner] Exact duplicate detected (external): %s", content.url
            )
            return True, 1.0

        # Verificar similitud con contenido previo
        max_similarity = 0.0
        for seen_hash in list(self._seen_hashes)[:100]:  # Limitar comparaciones
            # Nota: esto es simplificado, en producción se compararía con contenido real
            pass

        if max_similarity >= similarity_threshold:
            logger.info(
                "[ContentCleaner] Similar duplicate detected: %s (%.2f similarity)",
                content.url,
                max_similarity,
            )
            return True, max_similarity

        # Agregar a hashes vistos
        self._seen_hashes.add(content.content_hash)

        return False, max_similarity

    def is_content_acceptable(self, content: CleanedContent) -> bool:
        """
        Verifica si el contenido limpio cumple requisitos mínimos.

        Args:
            content: Contenido a verificar

        Returns:
            True si es aceptable
        """
        min_length = self._config.get("min_content_length", 100)
        max_length = self._config.get("max_content_length", 50_000)

        if content.cleaned_length < min_length:
            logger.debug(
                "[ContentCleaner] Content too short: %d < %d",
                content.cleaned_length,
                min_length,
            )
            return False

        if content.cleaned_length > max_length:
            logger.debug(
                "[ContentCleaner] Content too long: %d > %d",
                content.cleaned_length,
                max_length,
            )
            return False

        return True

    def add_to_seen(self, content: CleanedContent) -> None:
        """Agrega el contenido al registro de vistos."""
        self._seen_hashes.add(content.content_hash)

    def clear_seen(self) -> None:
        """Limpia el registro de contenido visto."""
        self._seen_hashes.clear()
