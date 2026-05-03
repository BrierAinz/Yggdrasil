#!/usr/bin/env python3
"""
Yggdrasil Health Check
Escanea el ecosistema de 9 reinos y reporta estado, basura y metricas.
Uso: python health_check.py
"""

import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent.resolve()
REALMS = [
    "Asgard",
    "Vanaheim",
    "Alfheim",
    "Svartalfheim",
    "Muspelheim",
    "Helheim",
    "Niflheim",
    "Jotunheim",
    "Midgard",
]


def scan_realm(name: str) -> dict:
    path = BASE / name
    if not path.exists():
        return {
            "exists": False,
            "size": 0,
            "files": 0,
            "dirs": 0,
            "py_files": 0,
            "py_lines": 0,
            "js_files": 0,
            "manifests": [],
            "trash": [],
        }

    stats = {
        "exists": True,
        "size": 0,
        "files": 0,
        "dirs": 0,
        "py_files": 0,
        "py_lines": 0,
        "js_files": 0,
        "manifests": [],
        "trash": defaultdict(int),
    }

    for root, dirs, files in os.walk(path):
        # Skip quarantine, hidden, cache, and legacy dirs
        rel = Path(root).relative_to(path)
        if any(p.startswith(".") for p in rel.parts):
            continue
        skip_parts = {
            "Quarantine",
            "quarantine",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            ".ruff_cache",
        }
        if any(p in skip_parts for p in rel.parts):
            continue

        for d in dirs:
            if d == "node_modules":
                stats["trash"]["node_modules"] += 1
            elif d == "__pycache__":
                stats["trash"]["__pycache__"] += 1
            elif d == ".pytest_cache":
                stats["trash"][".pytest_cache"] += 1

        for f in files:
            fpath = Path(root) / f
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            stats["size"] += size
            stats["files"] += 1

            if f.endswith(".py"):
                stats["py_files"] += 1
                try:
                    with fpath.open(encoding="utf-8", errors="ignore") as fh:
                        stats["py_lines"] += sum(1 for _ in fh)
                except:
                    pass
            elif f.endswith(".js") or f.endswith(".ts"):
                stats["js_files"] += 1
            elif f.endswith(".pyc"):
                stats["trash"][".pyc"] += 1
            elif f in {"package.json", "requirements.txt", "pyproject.toml"}:
                stats["manifests"].append(str(fpath.relative_to(BASE)))

    return stats


def fmt_size(n: int) -> str:
    if n >= 1024**3:
        return f"{n / 1024**3:.1f} GB"
    elif n >= 1024**2:
        return f"{n / 1024**2:.0f} MB"
    elif n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def main():
    print("=" * 70)
    print(f"YGGDRASIL HEALTH CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    total_size = 0
    total_files = 0
    total_py = 0
    total_js = 0

    for realm in REALMS:
        s = scan_realm(realm)
        if not s["exists"]:
            print(f"\n[{realm:12}] NO EXISTE")
            continue

        total_size += s["size"]
        total_files += s["files"]
        total_py += s["py_files"]
        total_js += s["js_files"]

        status = "VACIO" if s["files"] <= 2 else "ACTIVO"
        print(
            f"\n[{realm:12}] {status:7} | {fmt_size(s['size']):>8} | {s['files']:>5} files | "
            f"{s['py_files']:>3} py | {s['js_files']:>3} js"
        )

        if s["manifests"]:
            for m in s["manifests"][:3]:
                print(f"            manifest: {m}")
            if len(s["manifests"]) > 3:
                print(f"            ... y {len(s['manifests']) - 3} mas")

        if s["trash"]:
            trash_items = ", ".join(f"{k}={v}" for k, v in s["trash"].items())
            print(f"            BASURA DETECTADA: {trash_items}")

    print("\n" + "=" * 70)
    print(
        f"TOTALES: {fmt_size(total_size)} | {total_files:,} files | {total_py:,} py | {total_js:,} js"
    )
    print("=" * 70)

    # Check quarantine
    q = BASE / "Helheim" / "Quarantine_2026-04-29"
    if q.exists():
        q_size = sum(f.stat().st_size for f in q.rglob("*") if f.is_file())
        print(f"\nCUARENTENA: {fmt_size(q_size)} en Helheim/Quarantine_2026-04-29/")
        print("  Puede purgarse con:  rmdir /s Helheim\\Quarantine_2026-04-29")

    print("\nYggdrasil crece con orden o no crece.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
