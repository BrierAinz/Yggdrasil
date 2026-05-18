"""
Skill: reporte_proyecto
Escanea el proyecto Lilith y genera un reporte de estado
"""
import json
import os
import time
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent
_YGGDRASIL_ROOT = Path(os.environ.get("YGGDRASIL_ROOT", str(_MODULE_DIR.parents[5])))


def ejecutar() -> str:
    """Genera reporte del estado del proyecto."""
    workspace = _YGGDRASIL_ROOT / "Asgard" / "Lilith" / "Core" / "Workspace"
    project = _YGGDRASIL_ROOT / "Asgard" / "Lilith" / "Core"

    reporte = []
    reporte.append(f"# Reporte de Estado - Lilith")
    reporte.append(f"*Generado el {time.strftime('%Y-%m-%d %H:%M')}*\n")

    # 1. Estructura del proyecto
    reporte.append("## Estructura del Proyecto")
    for item in sorted(project.iterdir()):
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        if item.is_dir():
            count = sum(1 for _ in item.rglob("*") if _.is_file())
            reporte.append(f"- **{item.name}/** ({count} archivos)")
        else:
            size_kb = item.stat().st_size / 1024
            reporte.append(f"- {item.name} ({size_kb:.1f} KB)")

    # 2. Estado del Workspace
    reporte.append("\n## Estado del Workspace")
    for section in ["Alma", "Mente", "Destrezas", "Taller"]:
        section_path = workspace / section
        if section_path.exists():
            files = list(section_path.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            reporte.append(f"- **{section}/**: {file_count} archivos")
        else:
            reporte.append(f"- **{section}/**: No existe")

    # 3. Ultimos aprendizajes
    learnings_path = workspace / "Mente" / "learnings.jsonl"
    if learnings_path.exists():
        reporte.append("\n## Ultimos Aprendizajes")
        with open(learnings_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-5:]:
            try:
                entry = json.loads(line.strip())
                ts = time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(entry.get("timestamp", 0))
                )
                reporte.append(
                    f"- [{ts}] **{entry.get('topic', '?')}**: {entry.get('insight', '')[:80]}"
                )
            except:
                pass

    # 4. Skills disponibles
    registry_path = workspace / "Destrezas" / "skill_registry.json"
    if registry_path.exists():
        reporte.append("\n## Skills Disponibles")
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        for name, info in registry.get("skills", {}).items():
            estado = "Activa" if info.get("active") else "Inactiva"
            reporte.append(f"- **{name}** [{estado}]: {info.get('description', '')}")

    reporte_text = "\n".join(reporte)

    # Guardar en Taller
    output_path = workspace / "Taller" / f"reporte_{time.strftime('%Y%m%d_%H%M')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reporte_text)

    return reporte_text


if __name__ == "__main__":
    print(ejecutar())
