"""
Skill: recordatorio
Sistema de notas y recordatorios persistentes con timestamp
"""
import json
import os
import time
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent
_YGGDRASIL_ROOT = Path(os.environ.get("YGGDRASIL_ROOT", str(_MODULE_DIR.parents[5])))
REMINDERS_FILE = _YGGDRASIL_ROOT / "Asgard" / "Lilith" / "Core" / "Workspace" / "Mente" / "recordatorios.json"


def _cargar():
    """Carga recordatorios del archivo JSON."""
    if REMINDERS_FILE.exists():
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _guardar(recordatorios):
    """Guarda recordatorios al archivo JSON."""
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(recordatorios, f, indent=2, ensure_ascii=False)


def ejecutar(accion: str = "listar", nota: str = "") -> str:
    """Ejecuta la skill de recordatorios."""
    recordatorios = _cargar()

    if accion == "agregar":
        if not nota:
            return (
                "ERROR: Se necesita el parametro 'nota' para agregar un recordatorio."
            )
        entrada = {
            "id": len(recordatorios) + 1,
            "nota": nota,
            "creado": time.strftime("%Y-%m-%d %H:%M"),
            "timestamp": time.time(),
            "completado": False,
        }
        recordatorios.append(entrada)
        _guardar(recordatorios)
        return f"SUCCESS: Recordatorio #{entrada['id']} agregado: '{nota}'"

    elif accion == "listar":
        if not recordatorios:
            return "No hay recordatorios pendientes."
        lineas = ["--- Recordatorios ---"]
        for r in recordatorios:
            estado = "[X]" if r.get("completado") else "[ ]"
            lineas.append(f"{r['id']}. {estado} {r['nota']} (creado: {r['creado']})")
        lineas.append(f"\nTotal: {len(recordatorios)} recordatorios")
        return "\n".join(lineas)

    else:
        return f"ERROR: Accion desconocida '{accion}'. Usa 'agregar' o 'listar'."


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 2:
        print(ejecutar(sys.argv[1], " ".join(sys.argv[2:])))
    elif len(sys.argv) > 1:
        print(ejecutar(sys.argv[1]))
    else:
        print(ejecutar("listar"))
