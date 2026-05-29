"""
Lilith 3.0 — Motor de aprendizaje (Fase 4).
Analiza la memoria episódica para detectar patrones y opcionalmente devuelve planes aprendidos
desde la memoria procedimental. Misión 3.8: umbrales desde Config/learning.json.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..memory import MemoryManager
from ..memory.procedural.models import LearnedPattern


def get_learning_config(base_path: Optional[Path] = None) -> Dict[str, Any]:
    """Carga Config/learning.json. Misión 3.8. Nunca falla; devuelve defaults si no existe."""
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    try:
        from ..json_safe import safe_load

        path = base_path / "Config" / "learning.json"
        data = safe_load(path, default={})
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _extract_path_from_message(message: str) -> str:
    """Extrae una ruta de archivo del mensaje (para sustituir <path> en plantillas)."""
    if not message:
        return ""
    text = message.strip()
    lower = text.lower()
    m = re.search(
        r"(\b(?:backend|tests|core|api|memory)/[\w./\-]+\.[a-z0-9]+)", lower, re.I
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"([\w./\-]+\.(?:py|md|txt|json|yaml|yml))\b", lower, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\b(?:backend|tests|core|api|memory)(?:/[\w.-]+)*)\b", lower, re.I)
    if m:
        return m.group(1).strip()
    return ""


class LearningEngine:
    """
    Analiza la memoria episódica para sugerir patrones y consulta la memoria procedimental
    para devolver planes aprendidos (get_plan_for_message).
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    def analyze_and_suggest_patterns(self, limit: int = 500) -> List[str]:
        """
        Analiza las últimas interacciones y devuelve sugerencias de patrones fuertes.
        Versión inicial basada en reglas: cuenta coincidencias mensaje → primer paso del plan.
        Misión 3.2 (B.2): solo se usan episodios con outcome == "success" para aprender.
        """
        logs = self.memory_manager.get_recent_episodic_logs(limit=limit)
        # B.2: filtrar por outcome para que los patrones se basen en interacciones exitosas
        logs = [
            log
            for log in logs
            if (log.get("outcome") or "").strip().lower() == "success"
        ]
        pattern_counter: Dict[str, int] = {}

        for log in logs:
            message = (log.get("message") or "").lower()
            plan = log.get("plan") or []
            if not plan or not isinstance(plan, list):
                continue
            first_step = plan[0] if plan else {}
            tool = first_step.get("tool") or first_step.get("tool_name") or ""

            if "mejora" in message or "mejorar" in message:
                if tool == "read_file":
                    key = "mejora_file -> read_file + delegate_eva"
                    pattern_counter[key] = pattern_counter.get(key, 0) + 1
            if "lee " in message or "leer " in message or "abre " in message:
                if tool == "read_file":
                    key = "lee_archivo -> read_file"
                    pattern_counter[key] = pattern_counter.get(key, 0) + 1
            if "lista " in message or "listar " in message:
                if tool == "list_directory":
                    key = "lista_directorio -> list_directory"
                    pattern_counter[key] = pattern_counter.get(key, 0) + 1

        suggestions: List[str] = []
        base_path = (
            getattr(self.memory_manager, "base_path", None)
            or Path(__file__).resolve().parent.parent.parent
        )
        cfg = get_learning_config(base_path)
        threshold = int(cfg.get("suggest_intents_threshold") or 5)
        for pattern_str, count in pattern_counter.items():
            if count >= threshold:
                suggestions.append(
                    f"Patrón fuerte detectado: '{pattern_str}' ({count} veces)"
                )

        return suggestions

    def get_plan_for_message(
        self,
        message: str,
        intent_hint: Optional[str] = None,
    ) -> Optional[Tuple[List[Dict[str, Any]], str]]:
        """
        Si existe un patrón procedimental cuyo trigger coincide con el mensaje,
        devuelve (plan, pattern_id). C.3: si intent_hint está definido, solo se consideran
        patrones con ese intent (mejor precisión de matching).
        """
        if not message or not message.strip():
            return None
        msg_lower = message.strip().lower()
        patterns = self.memory_manager.procedural_store.list_patterns(
            intent_filter=intent_hint
        )

        for p in patterns:
            trigger = (p.get("trigger") or "").strip().lower()
            if not trigger or trigger not in msg_lower:
                continue
            action = p.get("action") or {}
            steps_spec = action.get("steps")
            if not steps_spec or not isinstance(steps_spec, list):
                continue
            path = _extract_path_from_message(message)
            plan: List[Dict[str, Any]] = []
            for s in steps_spec:
                if not isinstance(s, dict):
                    continue
                tool_name = s.get("tool") or s.get("tool_name") or ""
                params = dict(s.get("params") or {})
                for k, v in params.items():
                    if v == "<path>" or v == "{{path}}":
                        params[k] = path or ""
                    elif v == "<context>" or v == "{{context}}":
                        params[k] = ""
                plan.append({"tool_name": tool_name, "params": params})
            if plan:
                pattern_id = (p.get("pattern_id") or "").strip()
                return (plan, pattern_id)
        return None

    def refine_planner_rules(self, learned_patterns: List[LearnedPattern]) -> None:
        """
        (Futuro) Aplica patrones aprendidos para modificar las reglas del Planner.
        Podría editar un archivo de reglas YAML o inyectar configuración.
        """
        pass

    def suggest_intent_patterns_from_audit(
        self, limit_entries: int = 500
    ) -> List[Dict[str, Any]]:
        """
        3.5 C.2: Analiza decision_audit.jsonl (fallback_lucifer) y sugiere nuevas intenciones
        para intent_patterns.json. Agrupa mensajes similares y devuelve candidatos.
        No aplica cambios; el usuario decide si añadirlos.
        """
        base_path = (
            getattr(self.memory_manager, "base_path", None)
            or Path(__file__).resolve().parent.parent.parent
        )
        if not base_path or not base_path.exists():
            return []
        cfg = get_learning_config(base_path)
        limit_entries = int(
            cfg.get("suggest_intent_patterns_limit_entries") or limit_entries
        )
        audit_path = base_path / "Data" / "decision_audit.jsonl"
        if not audit_path.exists():
            return []
        try:
            from ..json_safe import safe_load_lines

            lines = safe_load_lines(audit_path, default=[])
            fallback_messages: List[str] = []
            for entry in lines:
                if not isinstance(entry, dict):
                    continue
                if (entry.get("decision_source") or "").strip() != "fallback_lucifer":
                    continue
                msg = (entry.get("message") or "").strip()
                if msg and len(msg) > 5:
                    fallback_messages.append(msg)
            if not fallback_messages:
                return []
            # Agrupar por "clave" normalizada (primeras palabras, lower, max 50 chars)
            key_to_msgs: Dict[str, List[str]] = {}
            for m in fallback_messages[-limit_entries:]:
                key = m.lower().strip()[:50].strip()
                if not key:
                    continue
                key_to_msgs.setdefault(key, []).append(m)
            suggestions: List[Dict[str, Any]] = []
            for key, msgs in key_to_msgs.items():
                if len(msgs) < 3:
                    continue
                sample = msgs[0][:80]
                slug = (
                    re.sub(r"[^a-z0-9]+", "_", key[:30].lower()).strip("_")
                    or "suggested_intent"
                )
                suggestions.append(
                    {
                        "suggested_intent": slug,
                        "trigger_sample": sample,
                        "count": len(msgs),
                        "triggers": [sample],
                    }
                )
            return suggestions[:20]
        except Exception:
            return []
