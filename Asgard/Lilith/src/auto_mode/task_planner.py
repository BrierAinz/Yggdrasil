"""
Lilith v2.3 — Fase C: Planificador de tareas (Kimi).
Genera un plan con subtareas y agente por subtarea.
Cuando el objetivo menciona archivos (ej. main.py o Backend/main.py), lee su contenido
y lo incluye como contexto para que el plan tenga en cuenta el código real.
"""
import glob
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TaskPlanner")


class TaskPlanner:
    def __init__(self, kimi_client=None):
        self._kimi = kimi_client

    def _get_kimi(self):
        if self._kimi is None:
            from src.llm.kimi_client import KimiClient

            self._kimi = KimiClient()
        return self._kimi

    def _resolve_and_read_files(self, objetivo: str) -> Dict[str, str]:
        """
        Busca patrones tipo *.py en el objetivo (ej. "main.py" o "Backend/main.py"),
        resuelve dentro de la raíz del proyecto y devuelve {ruta_relativa: contenido_recortado}.
        """
        # Detectar referencias a archivos .py: nombre solo o ruta (con / o \)
        candidates = re.findall(r"[\w./\\-]+\.py", objetivo)
        if not candidates:
            return {}

        project_root = Path(__file__).resolve().parent.parent.parent
        file_context: Dict[str, str] = {}
        seen_rel: set = set()

        for name in candidates:
            name_clean = name.strip().replace("\\", "/")
            filename_only = Path(name_clean).name

            # 1) Intentar ruta completa respecto a project_root (ej. Backend/main.py)
            path_from_root = project_root / name_clean
            if path_from_root.is_file():
                _add_file(project_root, path_from_root, file_context, seen_rel)
                logger.info(
                    "[Planner] Resuelto por ruta completa: %s → %s",
                    name_clean,
                    path_from_root,
                )
                continue

            # 2) Glob recursivo **/filename desde project_root
            pattern = str(project_root / "**" / filename_only)
            raw_matches = glob.glob(pattern, recursive=True)
            matches = [Path(p) for p in raw_matches]
            logger.info("[Planner] Buscando %s → %s", filename_only, raw_matches[:5])
            for path in matches[:5]:
                if not path.is_file():
                    continue
                _add_file(project_root, path, file_context, seen_rel)

        return file_context

    async def plan(self, objetivo: str) -> Dict[str, Any]:
        """
        Llama a Kimi con el objetivo y genera un plan JSON.
        Retorna dict con objetivo, subtareas (id, descripcion, agente), estimacion.
        """
        system = """Eres un planificador de tareas para un asistente AI con varios agentes.
Debes responder ÚNICAMENTE con un JSON válido, sin markdown ni texto extra.
Agentes disponibles: eva (análisis, documentación), adan (código, refactor, tests), kimi (orquestación, razonamiento).
Estructura requerida:
{
  "objetivo": "resumen del objetivo",
  "subtareas": [
    {"id": 1, "descripcion": "texto breve", "agente": "eva|adan|kimi"},
    ...
  ],
  "estimacion": "ej. 2-4 minutos"
}
Genera entre 2 y 5 subtareas. Usa "kimi" para pasos de síntesis o decisión."""

        file_context = self._resolve_and_read_files(objetivo)
        if file_context:
            bloques = []
            for fname, snippet in file_context.items():
                bloques.append(f"[{fname}]\n```python\n{snippet}\n```")
            archivos_ctx = "Contexto de archivos relevantes:\n" + "\n\n".join(bloques)
            prompt = (
                f"Objetivo del usuario: {objetivo}\n\n"
                f"{archivos_ctx}\n\n"
                "Genera el plan en JSON (solo JSON, sin ```)."
            )
        else:
            prompt = f"Objetivo del usuario: {objetivo}\n\nGenera el plan en JSON (solo JSON, sin ```)."

        kimi = self._get_kimi()
        try:
            raw = kimi.generate_text(prompt, system_prompt=system, max_tokens=1024)
        except Exception as e:
            logger.warning("TaskPlanner Kimi error: %s", e)
            return self._fallback_plan(objetivo)

        plan = self._parse_plan(raw, objetivo)
        if file_context:
            plan["file_context"] = file_context
        return plan

    def _parse_plan(self, raw: str, objetivo: str) -> Dict[str, Any]:
        """Extrae JSON del texto de Kimi."""
        if not raw or not raw.strip():
            return self._fallback_plan(objetivo)
        text = raw.strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            text = m.group(0)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("TaskPlanner: JSON inválido en respuesta")
            return self._fallback_plan(objetivo)
        subtareas = data.get("subtareas") or []
        if not isinstance(subtareas, list):
            subtareas = []
        for i, s in enumerate(subtareas):
            if not isinstance(s, dict):
                subtareas[i] = {"id": i + 1, "descripcion": str(s), "agente": "kimi"}
            else:
                s["id"] = s.get("id", i + 1)
                s["descripcion"] = s.get("descripcion", "")
                ag = (s.get("agente") or "kimi").lower()
                if ag not in ("eva", "adan", "kimi", "lucifer"):
                    s["agente"] = "kimi"
        plan: Dict[str, Any] = {
            "objetivo": data.get("objetivo") or objetivo[:200],
            "subtareas": subtareas,
            "estimacion": data.get("estimacion") or "—",
        }
        return plan

    def _fallback_plan(self, objetivo: str) -> Dict[str, Any]:
        return {
            "objetivo": objetivo[:200],
            "subtareas": [
                {
                    "id": 1,
                    "descripcion": f"Analizar y abordar: {objetivo[:80]}",
                    "agente": "kimi",
                },
            ],
            "estimacion": "1-2 minutos",
        }


def _add_file(
    project_root: Path,
    path: Path,
    file_context: Dict[str, str],
    seen_rel: set,
) -> None:
    try:
        rel = path.relative_to(project_root)
        rel_str = rel.as_posix()
        if rel_str in seen_rel:
            return
        seen_rel.add(rel_str)
        text = path.read_text(encoding="utf-8", errors="ignore")
        snippet = text[:4000]
        file_context[rel_str] = snippet
    except Exception as e:
        logger.debug("TaskPlanner: no se pudo leer %s: %s", path, e)
