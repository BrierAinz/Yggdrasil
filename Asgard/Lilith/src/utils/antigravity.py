"""
Antigravity Integration - Access to this IDE and Session Context
"""
import glob
import os
from pathlib import Path
from typing import Dict, List, Optional

# Current Session Brain Path (Hardcoded for this session, usually dynamically loaded)
SESSION_PATH = (
    r"C:\Users\Game_\.gemini\antigravity\brain\28bf0e06-5ce5-4a7f-9e27-0ce8329ae55b"
)


class AntigravityCapability:
    """Integration with Antigravity IDE Session"""

    def __init__(self):
        """Initialize Antigravity capability"""
        self.session_path = Path(SESSION_PATH)
        self.available = self.session_path.exists()

    def get_info(self) -> str:
        """Get information about Antigravity connection"""
        if not self.available:
            return (
                "âŒ No puedo acceder a la sesiÃ³n de Antigravity (Ruta no encontrada)"
            )

        return f"""ðŸ¤– **ConexiÃ³n Antigravity Establecida**

**SesiÃ³n Actual:** `{self.session_path.name}`
**UbicaciÃ³n:** `{self.session_path}`

**Capacidades:**
- ðŸ“– **Leer Contexto:** Puedo leer `task.md`, `walkthrough.md` y otros artefactos de tu sesiÃ³n.
- âœï¸ **Escribir Notas:** Puedo crear archivos en el cerebro compartido.
- ðŸ§  **SincronizaciÃ³n:** Estoy al tanto de lo que tÃº y Antigravity estÃ¡is trabajando.

**Comandos:**
- `@ag context` - Leer lo que estÃ¡ pasando en la sesiÃ³n
- `@ag tasks` - Ver la lista de tareas actual
- `@ag note <texto>` - Dejar una nota para Antigravity/Usuario
"""

    def read_context(self) -> str:
        """Read key context files from the session"""
        if not self.session_path.exists():
            return "Error: Session path not found."

        context = ""

        # Read Task List
        task_file = self.session_path / "task.md"
        if task_file.exists():
            context += f"ðŸ“‹ **TAREAS ACTUALES (task.md):**\n\n{task_file.read_text(encoding='utf-8')[:1000]}\n...\n\n"

        # Read Implementation Plan
        plan_file = self.session_path / "implementation_plan.md"
        if plan_file.exists():
            context += f"ðŸ—ï¸ **PLAN DE IMPLEMENTACIÃ“N:**\n\n{plan_file.read_text(encoding='utf-8')[:1000]}\n...\n\n"

        return context

    def get_recent_artifacts(self) -> str:
        """List recently modified artifacts"""
        if not self.session_path.exists():
            return "Error: Session path not found."

        files = sorted(
            self.session_path.glob("*.md"), key=os.path.getmtime, reverse=True
        )

        output = "ðŸ“‚ **Artefactos Recientes:**\n\n"
        for f in files[:5]:
            output += f"- `{f.name}`\n"

        return output

    def write_note(self, content: str) -> str:
        """Write a note to the session"""
        try:
            note_file = self.session_path / "sebas_notes.md"

            mode = "a" if note_file.exists() else "w"
            with open(note_file, mode, encoding="utf-8") as f:
                f.write(f"\n\n---\n**Nota de SEBAS:**\n{content}")

            return f"âœ… Nota guardada en `sebas_notes.md`"
        except Exception as e:
            return f"âŒ Error escribiendo nota: {e}"


# Singleton
_antigravity = None


def get_antigravity() -> AntigravityCapability:
    """Get Antigravity singleton"""
    global _antigravity
    if _antigravity is None:
        _antigravity = AntigravityCapability()
    return _antigravity
