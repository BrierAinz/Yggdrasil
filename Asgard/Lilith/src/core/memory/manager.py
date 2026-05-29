"""
Lilith 3.0 — MemoryManager: interfaz única para la memoria tri-capa.
Semántica (búsqueda), episódica (logs de interacción), procedimental (patrones).
4.0: Lock de escritura para thread-safety cuando el DAG ejecuta store_semantic_fact en paralelo.
"""
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .episodic.store import EpisodicStore
from .procedural.store import ProceduralStore
from .semantic.store import SemanticStore

logger = logging.getLogger("MemoryManager")


class MemoryManager:
    """
    Punto de acceso unificado a la memoria de Lilith 3.0.
    - search_semantic(query): consulta memoria semántica (perfil, proyectos, decisiones).
    - store_episodic(...): guarda una interacción para aprendizaje.
    - (Fase 4) procedural para patrones aprendidos.
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            # Raíz del proyecto (Core): contiene memory/semantic, memory/episodic
            base_path = Path(__file__).resolve().parent.parent.parent.parent
        self.base_path = Path(base_path)
        self._semantic: Optional[SemanticStore] = None
        self._episodic: Optional[EpisodicStore] = None
        self._procedural: Optional[ProceduralStore] = None
        self._write_lock = threading.Lock()

    @property
    def semantic_store(self) -> SemanticStore:
        if self._semantic is None:
            self._semantic = SemanticStore(self.base_path)
        return self._semantic

    @property
    def episodic_store(self) -> EpisodicStore:
        if self._episodic is None:
            self._episodic = EpisodicStore(self.base_path)
        return self._episodic

    @property
    def procedural_store(self) -> ProceduralStore:
        if self._procedural is None:
            self._procedural = ProceduralStore(self.base_path)
        return self._procedural

    def search_semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca en la memoria semántica. Retorna lista de {"text": str}."""
        return self.semantic_store.search(query, limit=limit)

    def _memory_config(self) -> Dict[str, Any]:
        """Carga Config/memory.json (json_safe)."""
        from src.core.json_safe import safe_load

        out = safe_load(self.base_path / "Config" / "memory.json", default={})
        return out if isinstance(out, dict) else {}

    def _load_recent_summaries(self, limit: int = 5) -> List[str]:
        """H.1: últimos N resúmenes de sesión desde Data/session_summaries.jsonl."""
        path = self.base_path / "Data" / "session_summaries.jsonl"
        if not path.exists():
            return []
        try:
            from src.core.json_safe import safe_load_lines

            lines = safe_load_lines(path, default=[])
            if not lines:
                return []
            # Últimas N líneas (cada línea es un JSON con el resumen)
            import json

            summaries = []
            for raw in lines[-limit:]:
                try:
                    obj = json.loads(raw) if isinstance(raw, str) else raw
                    if not isinstance(obj, dict):
                        continue
                    text = obj.get("summary") or obj.get("text") or str(obj)[:500]
                    if isinstance(text, str) and text.strip():
                        summaries.append(text.strip())
                except Exception:
                    pass
            return summaries[-limit:]
        except Exception as e:
            logger.debug("MemoryManager: load_recent_summaries %s", e)
            return []

    def search_context(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        H.1+H.2: Búsqueda unificada con pesos (perfil, hechos, resúmenes).
        Pre-4.0: si MuninnDB está habilitado (Config/muninn.json), añade bloque de memorias activadas.
        """
        cfg = self._memory_config()
        w_facts = float(cfg.get("weight_facts") or 0.6)
        w_profile = float(cfg.get("weight_profile") or 0.3)
        w_summaries = float(cfg.get("weight_summaries") or 0.1)
        try:
            from src.core.memory.semantic_memory import SemanticMemory

            sem = SemanticMemory(self.base_path)
            context = sem.get_context_for_prompt(query=query or "")
            parts = [context] if context and context.strip() else []
            summaries = self._load_recent_summaries(
                limit=max(1, int(10 * w_summaries) or 3)
            )
            if summaries:
                parts.append("[Resúmenes de sesión recientes]:")
                for s in summaries:
                    parts.append(f"  · {s[:500]}")
            # Pre-4.0: MuninnDB como complemento (memoria cognitiva)
            try:
                from src.core.memory.muninn_adapter import activate as muninn_activate
                from src.core.memory.muninn_adapter import is_enabled

                if is_enabled(self.base_path) and (query or "").strip():
                    activated = muninn_activate(self.base_path, context=[query.strip()])
                    if activated:
                        parts.append(
                            "[Memoria MuninnDB — relevante para esta consulta]:"
                        )
                        for item in activated:
                            text = (item.get("text") or "").strip()
                            if text:
                                parts.append(f"  · {text[:400]}")
            except Exception as muninn_e:
                logger.debug("MemoryManager: MuninnDB activate skip: %s", muninn_e)
            combined = "\n".join(parts).strip()
            if not combined:
                combined = "Sin contexto adicional."
            return [{"text": combined}]
        except Exception as e:
            logger.warning("MemoryManager: search_context failed: %s", e)
            return self.search_semantic(query, limit=limit)

    def get_recent_episodic_logs(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Devuelve las últimas N interacciones de la memoria episódica (para LearningEngine)."""
        return self.episodic_store.list_recent(limit=limit)

    def store_episodic(
        self,
        user_message: str,
        plan: List[Dict[str, Any]],
        final_response: str,
        outcome: str = "success",
        user_id: str = "",
    ) -> None:
        """Guarda una interacción en la memoria episódica."""
        self.episodic_store.store(
            user_message=user_message,
            plan=plan,
            final_response=final_response,
            outcome=outcome,
            user_id=user_id,
        )

    def reinforce_procedural_pattern(self, pattern_id: str) -> None:
        """Misión 3.2 (C.1): refuerza un patrón procedimental tras uso exitoso."""
        if not pattern_id:
            return
        try:
            self.procedural_store.increment_use(pattern_id)
        except Exception as e:
            logger.warning("MemoryManager: reinforce_procedural_pattern failed: %s", e)

    def add_fact(
        self, text: str, source_id: Optional[str] = None, topic: Optional[str] = None
    ) -> None:
        """Misión 3.2 (D.2): añade un hecho a la memoria semántica. 4.0: source_id y topic opcionales. Thread-safe para DAG paralelo."""
        if not (text or str(text).strip()):
            return
        try:
            with self._write_lock:
                self.semantic_store.add_fact(
                    str(text).strip(), source_id=source_id, topic=topic
                )
        except Exception as e:
            logger.warning("MemoryManager: add_fact failed: %s", e)

    def _post_store_fact(self, message: str) -> None:
        """3.2 (D.2): si el mensaje pide guardar/recordar algo, extrae el hecho y lo añade."""
        if not (message or "").strip():
            return
        lower = (message or "").strip().lower()
        for keyword in ("guarda que", "recuerda que", "anota que"):
            if keyword in lower:
                idx = lower.find(keyword)
                fact = message[idx + len(keyword) :].strip().strip(".,;:")
                if fact and len(fact) <= 2000:
                    self.add_fact(fact)
                break

    def _post_session_summary(self, registry: Any) -> None:
        """B.3: cada N interacciones genera un resumen con Lucifer y lo guarda como hecho + session_summaries.jsonl."""
        if not registry or not getattr(registry, "has", lambda _: False)(
            "delegate_lucifer"
        ):
            return
        try:
            from src.core.json_safe import safe_load

            data_dir = self.base_path / "Data"
            data_dir.mkdir(parents=True, exist_ok=True)
            state_file = data_dir / "session_summary_state.json"
            state = safe_load(state_file, default={})
            if not isinstance(state, dict):
                state = {}
            cfg = self._memory_config()
            interval = int(cfg.get("session_summary_interval") or 0) or 10
            count = int(state.get("stores_since_summary") or 0) + 1
            state["stores_since_summary"] = count
            if count < interval:
                try:
                    import json

                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, ensure_ascii=False, indent=0)
                except Exception:
                    pass
                return
            logs = self.get_recent_episodic_logs(limit=interval)
            if not logs:
                state["stores_since_summary"] = 0
                try:
                    import json

                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, ensure_ascii=False, indent=0)
                except Exception:
                    pass
                return
            lines = []
            for entry in reversed(logs):
                msg = (entry.get("message") or "").strip()[:500]
                resp = (entry.get("final_response") or "").strip()[:500]
                if msg or resp:
                    lines.append(f"Usuario: {msg}")
                    lines.append(f"Lilith: {resp}")
            blob = "\n".join(lines) if lines else "Sin actividad reciente."
            result = registry.execute(
                "delegate_lucifer",
                {
                    "task": "Resume en 2-4 frases breves qué se ha trabajado o hablado en esta sesión. Solo el resumen, sin saludos.",
                    "context": blob,
                },
            )
            if isinstance(result, dict) and result.get("response"):
                summary = str(result["response"]).strip()
            else:
                summary = str(result).strip()
            if summary and len(summary) > 10:
                self.add_fact(f"[Resumen de sesión] {summary}")
                summaries_file = data_dir / "session_summaries.jsonl"
                try:
                    import json
                    from datetime import datetime, timezone

                    with open(summaries_file, "a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                    "summary": summary,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                except Exception as e:
                    logger.warning("MemoryManager: session_summaries.jsonl: %s", e)
            state["stores_since_summary"] = 0
            try:
                import json

                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, indent=0)
            except Exception:
                pass
        except Exception as e:
            logger.warning("MemoryManager: session summary failed: %s", e)

    def post_interaction(
        self,
        user_message: str,
        plan_serialized: List[Dict[str, Any]],
        final_response: str,
        outcome: str = "success",
        user_id: str = "",
        *,
        planner: Optional[Any] = None,
        registry: Optional[Any] = None,
    ) -> None:
        """
        3.5 B.3: lógica de memoria tras una interacción (store episodic, refuerzo, hecho, resumen de sesión).
        planner: opcional, para reinforce_procedural_pattern si _last_used_pattern_id está definido.
        registry: opcional, para _post_session_summary (delegate_lucifer).
        """
        try:
            self.store_episodic(
                user_message=user_message,
                plan=plan_serialized,
                final_response=final_response,
                outcome=outcome,
                user_id=user_id,
            )
            pattern_id = (
                getattr(planner, "_last_used_pattern_id", None) if planner else None
            )
            if pattern_id:
                self.reinforce_procedural_pattern(pattern_id)
            self._post_store_fact(user_message)
            if registry:
                self._post_session_summary(registry)
        except Exception as e:
            logger.warning("MemoryManager: post_interaction failed: %s", e)
