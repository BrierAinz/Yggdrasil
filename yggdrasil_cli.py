#!/usr/bin/env python3
"""
Yggdrasil CLI - Comando central del ecosistema
Uso: python yggdrasil_cli.py [comando]

Comandos:
  status      - Estado de salud de todos los reinos
  clean       - Limpiar basura regenerable (pycache, node_modules, etc.)
  backup      - Crear backup de Svartalfheim + configs
  migrate     - Migrar proyecto entre reinos (interactivo)
  size        - Mostrar tamano por reino
  tree        - Arbol de proyectos
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

YGGDRASIL_ROOT = Path(__file__).parent.resolve()
REALMS = ["Asgard", "Vanaheim", "Alfheim", "Svartalfheim",
          "Muspelheim", "Helheim", "Niflheim", "Jotunheim", "Midgard"]

JUNK_PATTERNS = [
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache",
    "node_modules", ".npm", ".next", "dist", "build",
    "*.map", ".turbo", ".parcel-cache", ".cache"
]


def print_banner():
    print("""
    ==========================================
           YGGDRASIL CLI v2.0
    ==========================================
    """)


def cmd_status():
    print("[STATUS] Yggdrasil Health Check")
    print("-" * 60)
    print(f"{'Reino':<15} {'Estado':<10} {'Tamano':<12} {'Archivos':<10} {'py/js'}")
    print("-" * 60)

    total_size = 0
    total_files = 0

    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            print(f"{realm:<15} {'NO EXISTE':<10}")
            continue

        try:
            du_out = subprocess.run(
                ["du", "-sb", str(rpath)],
                capture_output=True, text=True, timeout=10
            ).stdout
            size_bytes = int(du_out.split()[0])
        except Exception:
            size_bytes = 0

        try:
            find_out = subprocess.run(
                ["find", str(rpath), "-type", "f"],
                capture_output=True, text=True, timeout=10
            ).stdout
            fcount = len([l for l in find_out.splitlines() if l.strip()])
        except Exception:
            fcount = 0

        try:
            py_out = subprocess.run(
                ["find", str(rpath), "-name", "*.py"],
                capture_output=True, text=True, timeout=10
            ).stdout
            py_count = len(py_out.splitlines())
        except Exception:
            py_count = 0

        try:
            js_out = subprocess.run(
                ["find", str(rpath), "-name", "*.js"],
                capture_output=True, text=True, timeout=10
            ).stdout
            js_count = len(js_out.splitlines())
        except Exception:
            js_count = 0

        status = "ACTIVO" if fcount > 2 else "VACIO"
        if realm in ("Jotunheim", "Midgard") and fcount <= 2:
            status = "RESERVADO"
        if realm == "Helheim":
            status = "ARCHIVO"

        if size_bytes >= 1024**3:
            sstr = f"{size_bytes/1024**3:.1f} GB"
        elif size_bytes >= 1024**2:
            sstr = f"{size_bytes/1024**2:.0f} MB"
        else:
            sstr = f"{size_bytes/1024:.0f} KB"

        print(f"{realm:<15} {status:<10} {sstr:<12} {fcount:<10} {py_count}/{js_count}")
        total_size += size_bytes
        total_files += fcount

    print("-" * 60)
    tstr = f"{total_size/1024**3:.1f} GB" if total_size >= 1024**3 else f"{total_size/1024**2:.0f} MB"
    print(f"{'TOTAL':<15} {'':<10} {tstr:<12} {total_files:,}")
    print("-" * 60)

    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if q.exists():
        try:
            qs = int(subprocess.run(["du", "-sb", str(q)], capture_output=True, text=True, timeout=5).stdout.split()[0])
            qstr = f"{qs/1024**2:.0f} MB" if qs < 1024**3 else f"{qs/1024**3:.1f} GB"
            print(f"\n[CUARENTENA] {qstr} en Helheim/Quarantine_2026-04-29/")
            print("  Ejecutar: python yggdrasil_cli.py purge  # para eliminar")
        except Exception:
            pass


def cmd_size():
    print("[SIZE] Tamano por reino (du -sh)")
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        try:
            out = subprocess.run(["du", "-sh", str(rpath)], capture_output=True, text=True, timeout=10).stdout
            print(f"  {out.strip()}")
        except Exception:
            pass


def cmd_tree():
    print("[TREE] Proyectos activos")
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        print(f"\n{realm}/")
        for item in sorted(rpath.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                marker = "[DIR]"
                if (item / "README.md").exists():
                    marker = "[PROYECTO]"
                print(f"  {marker} {item.name}")


def cmd_clean():
    print("[CLEAN] Buscando basura regenerable...")
    cleaned = 0
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        for pattern in JUNK_PATTERNS:
            if pattern.startswith("*"):
                # glob pattern
                for fpath in rpath.rglob(pattern[1:]):
                    if fpath.is_file():
                        try:
                            fpath.unlink()
                            cleaned += 1
                        except Exception:
                            pass
                for dpath in rpath.rglob(pattern[1:]):
                    if dpath.is_dir() and dpath.name == pattern[1:]:
                        try:
                            shutil.rmtree(dpath)
                            cleaned += 1
                            print(f"  [DEL DIR] {dpath.relative_to(YGGDRASIL_ROOT)}")
                        except Exception:
                            pass
            else:
                # exact directory name
                for dpath in rpath.rglob(pattern):
                    if dpath.is_dir():
                        try:
                            shutil.rmtree(dpath)
                            cleaned += 1
                            print(f"  [DEL DIR] {dpath.relative_to(YGGDRASIL_ROOT)}")
                        except Exception:
                            pass
    print(f"\n[OK] {cleaned} items eliminados")


def cmd_purge():
    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if not q.exists():
        print("[INFO] No hay cuarentena para purgar")
        return
    print(f"[PURGE] Eliminando cuarentena: {q}")
    confirm = input("Confirmar eliminacion permanente? (yes/no): ")
    if confirm.lower() == "yes":
        try:
            shutil.rmtree(q)
            print("[OK] Cuarentena eliminada")
        except Exception as e:
            print(f"[ERROR] {e}")
    else:
        print("[CANCELADO]")


def cmd_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = YGGDRASIL_ROOT / f"backup_{ts}"
    backup_dir.mkdir(exist_ok=True)

    print(f"[BACKUP] Creando backup en {backup_dir}")

    # Backup Svartalfheim (docs)
    src = YGGDRASIL_ROOT / "Svartalfheim"
    dst = backup_dir / "Svartalfheim"
    if src.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
        print("  [OK] Svartalfheim")

    # Backup configs (si existen .env files)
    env = YGGDRASIL_ROOT / ".env"
    if env.exists():
        shutil.copy2(env, backup_dir / ".env")
        print("  [OK] .env")

    # Backup reglas
    for f in ["REGLAS_YGGDRASIL.md", "setup_yggdrasil.py", "yggdrasil_cli.py"]:
        srcf = YGGDRASIL_ROOT / f
        if srcf.exists():
            shutil.copy2(srcf, backup_dir / f)
            print(f"  [OK] {f}")

    print(f"\n[OK] Backup completo: {backup_dir}")


def main():
    print_banner()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "status":
        cmd_status()
    elif cmd == "size":
        cmd_size()
    elif cmd == "tree":
        cmd_tree()
    elif cmd == "clean":
        cmd_clean()
    elif cmd == "purge":
        cmd_purge()
    elif cmd == "backup":
        cmd_backup()
    elif cmd == "test":
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=YGGDRASIL_ROOT)
    elif cmd == "sync":
        subprocess.run([sys.executable, str(YGGDRASIL_ROOT / "sync.py")])
    elif cmd == "api":
        subprocess.run([sys.executable, "-m", "uvicorn", "lilith_api.main:app", "--reload", "--port", "8000"])
    else:
        print(f"[ERROR] Comando desconocido: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
