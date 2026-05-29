"""
Lilith - Workspace Manager Tool (Phase 4)
Allows Lilith to read, write, and manage her own 'Soul and Body' Workspace autonomously.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("WorkspaceManager")


class WorkspaceManager:
    """
    Tool for Lilith to interact with her personal workspace (Alma, Mente, Destrezas, Taller).
    Restricted to operations within the project's Workspace/ directory to prevent breaking the core.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root:
            root = Path(workspace_root).resolve()
        else:
            # Auto-detect project root from this file location: .../Lilith/Backend/tools/enhanced/workspace_manager.py
            project_root = Path(__file__).resolve().parents[3]
            root = (project_root / "Workspace").resolve()
        self.workspace_root = root

        # Ensure directories exist just in case
        for folder in ["Alma", "Mente", "Destrezas", "Taller"]:
            (self.workspace_root / folder).mkdir(parents=True, exist_ok=True)

    def _is_safe_path(self, target_path: str) -> bool:
        """Ensure the path is strictly within the workspace root"""
        try:
            resolved_target = (self.workspace_root / target_path).resolve()
            return str(resolved_target).startswith(str(self.workspace_root))
        except Exception:
            return False

    def execute(self, parameters: dict) -> str:
        """Execute a workspace management action"""
        action = parameters.get("action", "")

        actions = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "append_learning": self._append_learning,
            "list_contents": self._list_contents,
            "list_skills": self._list_skills,
            "run_skill": self._run_skill,
        }

        handler = actions.get(action)
        if not handler:
            return (
                f"ERROR: Unknown action '{action}'. Available: {list(actions.keys())}"
            )

        try:
            return handler(parameters)
        except Exception as e:
            logger.error(f"WorkspaceManager action '{action}' failed: {e}")
            return f"ERROR: Action failed: {e}"

    def _read_file(self, params: dict) -> str:
        """Reads a file from the workspace"""
        filepath = params.get("filepath", "")
        if not filepath:
            return "ERROR: 'filepath' is required."

        if not self._is_safe_path(filepath):
            return "ERROR: Access denied. You can only read files inside your Workspace/ directory."

        full_path = self.workspace_root / filepath
        if not full_path.exists() or not full_path.is_file():
            return f"ERROR: File not found: {filepath}"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"--- Contents of {filepath} ---\n{content}"
        except Exception as e:
            return f"ERROR: Could not read file: {e}"

    def _write_file(self, params: dict) -> str:
        """Writes or creates a file in the workspace"""
        filepath = params.get("filepath", "")
        content = params.get("content", "")

        if not filepath or content is None:
            return "ERROR: 'filepath' and 'content' are required."

        if not self._is_safe_path(filepath):
            return "ERROR: Access denied. You can only write files inside your Workspace/ directory."

        full_path = self.workspace_root / filepath

        # Prevent writing to core personality arbitrarily without review
        if "Alma/persona.md" in str(filepath).replace("\\", "/"):
            return "ERROR: Direct modification of 'Alma/persona.md' is restricted. Propose changes to the user instead."

        try:
            # Ensure parent folders exist (e.g., Taller/my_experiment.py)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"SUCCESS: Wrote {len(content)} characters to {filepath}"
        except Exception as e:
            return f"ERROR: Could not write file: {e}"

    def _append_learning(self, params: dict) -> str:
        """Appends a new learning or reflection to Mente/learnings.jsonl"""
        topic = params.get("topic", "")
        insight = params.get("insight", "")

        if not topic or not insight:
            return "ERROR: 'topic' and 'insight' are required to record a learning."

        learnings_path = self.workspace_root / "Mente" / "learnings.jsonl"

        import time

        entry = {"timestamp": time.time(), "topic": topic, "insight": insight}

        try:
            with open(learnings_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return f"SUCCESS: New learning about '{topic}' recorded in your Mente."
        except Exception as e:
            return f"ERROR: Could not record learning: {e}"

    def _list_contents(self, params: dict) -> str:
        """Lists contents of a specific workspace directory"""
        folder = params.get("folder", "")
        target_dir = self.workspace_root / folder if folder else self.workspace_root

        if not self._is_safe_path(str(target_dir)) and folder != "":
            return "ERROR: Access denied. Stay within Workspace/."

        if not target_dir.exists() or not target_dir.is_dir():
            return f"ERROR: Directory not found: {folder}"

        try:
            files = []
            dirs = []
            for item in target_dir.iterdir():
                if item.is_dir():
                    dirs.append(f"[DIR]  {item.name}/")
                else:
                    size_kb = item.stat().st_size / 1024
                    files.append(f"[FILE] {item.name} ({size_kb:.1f} KB)")

            output = f"--- Workspace Contents: {folder or 'Root'} ---\n"
            output += "\n".join(dirs + files)
            if not dirs and not files:
                output += "(Empty directory)"
            return output
        except Exception as e:
            return f"ERROR: Could not list directory: {e}"

    def _list_skills(self, params: dict) -> str:
        """Lists all available skills from the Destrezas registry"""
        registry_path = self.workspace_root / "Destrezas" / "skill_registry.json"

        if not registry_path.exists():
            return "No hay skills registradas aun."

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)

            skills = registry.get("skills", [])
            if not skills:
                return "El registro de skills esta vacio."

            lines = ["--- Skills Disponibles ---"]
            for skill in skills:
                name = skill.get("name", "???")
                estado = "[ACTIVA]" if skill.get("active") else "[INACTIVA]"
                desc = skill.get("description", "")
                cat = skill.get("category", "")
                # Try to load description from skill.json if not in registry
                if not desc:
                    skill_json = self.workspace_root / "Destrezas" / name / "skill.json"
                    if skill_json.exists():
                        with open(skill_json, "r", encoding="utf-8") as sf:
                            desc = json.load(sf).get("description", "Sin descripcion")
                cat_str = f" [{cat}]" if cat else ""
                lines.append(f"  {estado}{cat_str} {name}: {desc}")

            lines.append(f"\nTotal: {len(skills)} skills registradas")
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: Could not load skill registry: {e}"

    def _run_skill(self, params: dict) -> str:
        """Executes a skill from Destrezas by importing and running its ejecutar() function"""
        skill_name = params.get("skill_name", "")
        if not skill_name:
            return "ERROR: 'skill_name' is required."

        # Load registry to validate
        registry_path = self.workspace_root / "Destrezas" / "skill_registry.json"
        if not registry_path.exists():
            return "ERROR: No skill registry found."

        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        # Find skill in array
        skills = registry.get("skills", [])
        skill_info = None
        for s in skills:
            if s.get("name") == skill_name:
                skill_info = s
                break

        if not skill_info:
            available = [s.get("name", "?") for s in skills]
            return (
                f"ERROR: Skill '{skill_name}' no encontrada. Disponibles: {available}"
            )

        if not skill_info.get("active", False):
            return f"ERROR: Skill '{skill_name}' esta inactiva."

        # Locate the skill's run.py (path in registry is like "Destrezas/name")
        skill_rel_path = skill_info.get("path", f"Destrezas/{skill_name}")
        # If path already starts with "Destrezas/", resolve relative to workspace_root
        if skill_rel_path.startswith("Destrezas/"):
            skill_path = self.workspace_root / skill_rel_path / "run.py"
        else:
            skill_path = self.workspace_root / "Destrezas" / skill_rel_path / "run.py"

        if not skill_path.exists():
            # Fallback: try just the name
            skill_path = self.workspace_root / "Destrezas" / skill_name / "run.py"

        if not skill_path.exists():
            return f"ERROR: Script de skill no encontrado: {skill_path}"

        # Dynamically import and execute
        import importlib.util

        try:
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_name}", str(skill_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "ejecutar"):
                return f"ERROR: Skill '{skill_name}' no tiene funcion 'ejecutar()'."

            # Extract skill-specific parameters (everything except action and skill_name)
            skill_params = {
                k: v for k, v in params.items() if k not in ("action", "skill_name")
            }

            result = module.ejecutar(**skill_params)
            return result
        except TypeError as e:
            return f"ERROR: Parametros incorrectos para '{skill_name}': {e}"
        except Exception as e:
            logger.error(f"Skill '{skill_name}' execution failed: {e}")
            return f"ERROR: Skill '{skill_name}' fallo: {e}"


if __name__ == "__main__":
    print("Testing WorkspaceManager with Skills...")
    wm = WorkspaceManager()
    print(wm.execute({"action": "list_contents", "folder": ""}))
    print()
    print(wm.execute({"action": "list_skills"}))
    print()
    print(
        wm.execute(
            {
                "action": "run_skill",
                "skill_name": "recordatorio",
                "accion": "agregar",
                "nota": "Probar todas las skills del sistema",
            }
        )
    )
    print()
    print(
        wm.execute(
            {"action": "run_skill", "skill_name": "recordatorio", "accion": "listar"}
        )
    )
