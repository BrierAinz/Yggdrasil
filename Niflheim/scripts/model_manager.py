#!/usr/bin/env python3
"""Gestor de modelos LLM para Niflheim."""
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Optional

NIFLHEIM = Path(__file__).parent.parent
MODELS_DIR = NIFLHEIM / "Models"
REGISTRY = NIFLHEIM / "models" / "registry.json"


def load_registry() -> Dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {}


def save_registry(registry: Dict):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_model(name: str, url: str = "", size: int = 0, checksum: str = ""):
    registry = load_registry()
    registry[name] = {
        "url": url,
        "size": size,
        "checksum": checksum,
        "path": str(MODELS_DIR / name),
    }
    save_registry(registry)
    print(f"[OK] Modelo registrado: {name}")


def remove_model(name: str):
    registry = load_registry()
    if name in registry:
        del registry[name]
        save_registry(registry)
        print(f"[OK] Modelo eliminado del registro: {name}")
    else:
        print(f"[WARN] Modelo no encontrado: {name}")


def verify_model(name: str) -> bool:
    registry = load_registry()
    entry = registry.get(name)
    if not entry:
        return False
    path = Path(entry["path"])
    if not path.exists():
        return False
    if entry.get("checksum"):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        return sha == entry["checksum"]
    return True


def list_models():
    registry = load_registry()
    if not registry:
        print("No hay modelos registrados.")
        return
    print(f"{'Estado':<10} {'Nombre':<30} {'Tamano':<12}")
    print("-" * 60)
    for name, info in registry.items():
        exists = Path(info["path"]).exists()
        verified = verify_model(name) if exists else False
        status = "OK" if verified else "PRESENT" if exists else "MISSING"
        size_str = (
            f"{info.get('size', 0) / 1024**3:.1f} GB" if info.get("size") else "?"
        )
        print(f"{status:<10} {name:<30} {size_str:<12}")


def scan_models():
    if not MODELS_DIR.exists():
        print("[WARN] Directorio Models/ no existe")
        return
    registry = load_registry()
    known_paths = {Path(entry["path"]).resolve() for entry in registry.values()}
    found = 0
    for fpath in MODELS_DIR.rglob("*.gguf"):
        if fpath.resolve() not in known_paths:
            size = fpath.stat().st_size
            registry[fpath.name] = {
                "path": str(fpath),
                "size": size,
                "checksum": "",
                "url": "",
            }
            found += 1
    if found:
        save_registry(registry)
        print(f"[OK] {found} modelos nuevos registrados")
    else:
        print("[INFO] No hay modelos nuevos")


def main():
    if len(sys.argv) < 2:
        print("Uso: python model_manager.py [list|add|remove|verify|scan]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_models()
    elif cmd == "scan":
        scan_models()
    elif cmd == "verify" and len(sys.argv) > 2:
        ok = verify_model(sys.argv[2])
        print("OK" if ok else "FAIL")
    elif cmd == "add" and len(sys.argv) > 2:
        add_model(sys.argv[2])
    elif cmd == "remove" and len(sys.argv) > 2:
        remove_model(sys.argv[2])
    else:
        print(f"Comando desconocido: {cmd}")


if __name__ == "__main__":
    main()
