"""
Lilith v2.2 — Fase C: Memoria Procedimental
Historial de errores + soluciones y patrones de trabajo.
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ProceduralMemory")

ERROR_HISTORY_FILE = "error_history.json"
PATTERNS_FILE = "patterns.json"

# Palabras en el mensaje del usuario que sugieren un error
ERROR_KEYWORDS = re.compile(
    r"\b(error|exception|traceback|falla|no funciona|failed|break|bug|crash)\b", re.I
)


# Normalizar: extraer términos clave del texto de error (primeras palabras significativas)
def _normalize_error(text: str, max_words: int = 12) -> str:
    t = (text or "").strip()
    # Quitar rutas y números de línea
    t = re.sub(r"[A-Za-z]:\\[^\s]+", "", t)
    t = re.sub(r"/[^\s]+", "", t)
    t = re.sub(r"line \d+", "", t, flags=re.I)
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", t)
    return " ".join(words[:max_words]).lower()


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


class ProceduralMemory:
    """
    Memoria procedimental: errores vistos + soluciones y patrones de trabajo.
    Archivos en memory/procedural/.
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        self.procedural_dir = self.base_path / "memory" / "procedural"
        self.procedural_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        return self.procedural_dir / filename

    def load_error_history(self) -> List[Dict[str, Any]]:
        p = self._path(ERROR_HISTORY_FILE)
        if not p.exists():
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                out = json.load(f)
                return out if isinstance(out, list) else []
        except Exception as e:
            logger.warning("Failed to load error_history.json: %s", e)
            return []

    def save_error_history(self, data: List[Dict[str, Any]]) -> None:
        p = self._path(ERROR_HISTORY_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_patterns(self) -> Dict[str, Any]:
        p = self._path(PATTERNS_FILE)
        if not p.exists():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                out = json.load(f)
                return out if isinstance(out, dict) else {}
        except Exception as e:
            logger.warning("Failed to load patterns.json: %s", e)
            return {}

    def save_patterns(self, data: Dict[str, Any]) -> None:
        p = self._path(PATTERNS_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def record_error(self, error: str, file: str, solution: str) -> None:
        """
        Registra un error y su solución. Si ya existe (fuzzy match), incrementa
        recurrencias y añade la solución; si no, crea entrada nueva.
        """
        error = (error or "").strip()[:500]
        file = (file or "").strip()[:200]
        solution = (solution or "").strip()[:2000]
        if not error:
            return
        key_norm = _normalize_error(error)
        today = _today()
        history = self.load_error_history()
        for entry in history:
            existing_norm = _normalize_error(entry.get("error", ""))
            # Match si comparten suficientes palabras (fuzzy)
            kw_new = set(key_norm.split())
            kw_old = set(existing_norm.split())
            if len(kw_new & kw_old) >= min(3, len(kw_new), len(kw_old)):
                entry["recurrencias"] = entry.get("recurrencias", 1) + 1
                entry["ultima_vez"] = today
                soluciones = entry.get("soluciones") or []
                if solution and solution not in soluciones:
                    soluciones.append(solution)
                    entry["soluciones"] = soluciones[-10:]
                if file and file != entry.get("archivo"):
                    entry["archivo"] = file
                self.save_error_history(history)
                logger.info(
                    "ProceduralMemory: updated existing error (recurrencias=%s)",
                    entry["recurrencias"],
                )
                return
        history.append(
            {
                "error": error,
                "archivo": file or "",
                "soluciones": [solution] if solution else [],
                "primera_vez": today,
                "ultima_vez": today,
                "recurrencias": 1,
            }
        )
        self.save_error_history(history)
        logger.info("ProceduralMemory: new error recorded")

    async def check_recurring_error(self, user_msg: str) -> Optional[Dict[str, Any]]:
        """
        Si el mensaje sugiere un error y hay uno similar en el historial con
        recurrencias >= 2, retorna el entry para mostrar alerta. Si no, None.
        """
        if not user_msg or not ERROR_KEYWORDS.search(user_msg):
            return None
        key_norm = _normalize_error(user_msg)
        if len(key_norm.split()) < 2:
            return None
        history = self.load_error_history()
        for entry in history:
            if entry.get("recurrencias", 0) < 2:
                continue
            existing_norm = _normalize_error(entry.get("error", ""))
            kw_new = set(key_norm.split())
            kw_old = set(existing_norm.split())
            if len(kw_new & kw_old) >= min(2, len(kw_new), len(kw_old)):
                return {
                    "error": entry.get("error", ""),
                    "archivo": entry.get("archivo", ""),
                    "soluciones": entry.get("soluciones", []),
                    "ultima_vez": entry.get("ultima_vez", ""),
                    "recurrencias": entry.get("recurrencias", 0),
                }
        return None

    async def learn_workflow(self, task_type: str, steps: List[str]) -> None:
        """Guarda una secuencia de pasos recurrentes en patterns.json."""
        if not task_type or not steps:
            return
        task_type = (task_type or "").strip()[:100]
        steps = [str(s).strip()[:500] for s in steps if str(s).strip()][:50]
        patterns = self.load_patterns()
        if task_type not in patterns:
            patterns[task_type] = []
        patterns[task_type].append(
            {
                "steps": steps,
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        # Mantener últimas N secuencias por tipo
        patterns[task_type] = patterns[task_type][-20:]
        self.save_patterns(patterns)
        logger.info("ProceduralMemory: workflow learned for %s", task_type)
