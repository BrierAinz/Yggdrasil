#!/usr/bin/env python3
"""Sincroniza metadatos entre reinos de Yggdrasil."""
import json
from pathlib import Path
import sys

YGGDRASIL = Path(__file__).parent.resolve()
STATE_FILE = YGGDRASIL / ".yggdrasil_state.json"


EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", "Archives", "Archives_Lilith_Monolith", "Archives_Lilith_Legacy"}

def scan_realms() -> dict:
    realms = {}
    for realm in [
        "Asgard", "Vanaheim", "Alfheim", "Svartalfheim",
        "Muspelheim", "Niflheim", "Midgard", "Jotunheim", "Helheim",
    ]:
        path = YGGDRASIL / realm
        if not path.exists():
            continue
        files = []
        for ext in ("*.py", "*.js", "*.md"):
            for f in path.rglob(ext):
                if any(part in EXCLUDE_DIRS for part in f.parts):
                    continue
                files.append(f)
        realms[realm] = {
            "path": str(path),
            "files": len(files),
            "size_kb": sum(f.stat().st_size for f in files if f.exists()) // 1024,
        }
    return realms


def main():
    print("[Yggdrasil] Escaneando reinos...")
    state = {"realms": scan_realms()}
    total_files = sum(r["files"] for r in state["realms"].values())
    total_size = sum(r["size_kb"] for r in state["realms"].values())
    state["summary"] = {
        "total_files": total_files,
        "total_size_kb": total_size,
        "realms_active": len(state["realms"]),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {len(state['realms'])} reinos escaneados")
    print(f"[OK] {total_files} archivos, {total_size} KB totales")
    print(f"[OK] Estado guardado en {STATE_FILE}")


if __name__ == "__main__":
    main()
