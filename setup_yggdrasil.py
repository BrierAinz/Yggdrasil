#!/usr/bin/env python3
"""
Setup Yggdrasil - Instalador global del ecosistema
Ejecutar desde la raiz de Yggdrasil:  python setup_yggdrasil.py
"""

import subprocess
import sys
from pathlib import Path


YGGDRASIL_ROOT = Path(__file__).parent.resolve()
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


def print_banner():
    print(
        """
    ==========================================
           YGGDRASIL SETUP v2.0
    ==========================================
    """
    )


def check_python():
    print("[CHECK] Python...")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 9:
        print(f"  [OK] Python {v.major}.{v.minor}.{v.micro}")
        return True
    print(f"  [FAIL] Requiere Python >= 3.9, tienes {v.major}.{v.minor}")
    return False


def check_node():
    print("[CHECK] Node.js...")
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        print(f"  [OK] Node {out.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("  [WARN] Node.js no encontrado (necesario para Alfheim)")
        return False


def setup_asgard():
    print("\n[SETUP] Asgard - Hermes-Lilith...")
    lilith = YGGDRASIL_ROOT / "Asgard" / "Hermes-Lilith"
    if not lilith.exists():
        print("  [SKIP] Hermes-Lilith no encontrado")
        return

    req = lilith / "requirements.txt"
    if req.exists():
        print("  [INFO] Instalando dependencias Python...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req)],
                cwd=str(lilith),
                timeout=120,
                check=True,
            )
            print("  [OK] Dependencias instaladas")
        except subprocess.TimeoutExpired:
            print("  [WARN] Timeout instalando dependencias")
        except subprocess.CalledProcessError as e:
            print(f"  [WARN] Error instalando: {e}")
    else:
        print("  [SKIP] requirements.txt no encontrado")

    # Instalacion global
    setup = lilith / "setup.py"
    if setup.exists():
        print("  [INFO] Configurando comando global 'lilith'...")
        try:
            subprocess.run([sys.executable, str(setup)], cwd=str(lilith), timeout=30, check=True)
            print("  [OK] Comando 'lilith' configurado")
        except Exception as e:
            print(f"  [WARN] No se pudo configurar comando global: {e}")


def setup_vanaheim():
    print("\n[SETUP] Vanaheim - Bots...")
    bots_dir = YGGDRASIL_ROOT / "Vanaheim" / "Bots"
    if not bots_dir.exists():
        print("  [SKIP] Directorio Bots no encontrado")
        return

    bots = [d for d in bots_dir.iterdir() if d.is_dir() and (d / "requirements.txt").exists()]
    if not bots:
        print("  [INFO] Ningun bot con requirements.txt encontrado")
        return

    for bot in bots:
        print(f"  [INFO] Bot: {bot.name}")
        # No instalamos automaticamente para evitar conflictos de dependencias
        # Solo verificamos que exista
        print("    [OK] Listo (instalar manualmente con: pip install -r requirements.txt)")


def setup_alfheim():
    print("\n[SETUP] Alfheim - UI...")
    ui = YGGDRASIL_ROOT / "Alfheim" / "ui-seed"
    if not ui.exists():
        print("  [SKIP] ui-seed no encontrado")
        return

    pkg = ui / "package.json"
    if pkg.exists():
        print("  [INFO] UI seed detectada. Instalar con:")
        print(f"    cd {ui}")
        print("    npm install")
        print("    npm start")
    else:
        print("  [SKIP] package.json no encontrado")


def setup_niflheim():
    print("\n[SETUP] Niflheim - Resources...")
    nif = YGGDRASIL_ROOT / "Niflheim"
    models = nif / "Models"
    datasets = nif / "Datasets"
    print(f"  [INFO] Models: {models.exists()}")
    print(f"  [INFO] Datasets: {datasets.exists()}")
    print("  [OK] Reino de recursos listo")


def generate_env_template():
    print("\n[SETUP] Generando plantilla .env...")
    env_path = YGGDRASIL_ROOT / ".env.template"
    content = """# Yggdrasil - Variables de Entorno
# Copiar a .env y rellenar

# LM Studio / LLM Local
LM_STUDIO_URL=http://localhost:1234/v1
DEFAULT_MODEL=auto

# Telegram (si usas bots)
# TELEGRAM_BOT_TOKEN=

# OpenRouter (opcional)
# OPENROUTER_API_KEY=

# Obsidian (opcional)
# OBSIDIAN_VAULT_PATH=
"""
    env_path.write_text(content, encoding="utf-8")
    print(f"  [OK] Plantilla creada: {env_path}")
    print("  [INFO] Copiar a .env y rellenar tus valores")


def run_health_check():
    print("\n[CHECK] Ejecutando health check rapido...")
    total = 0
    active = 0
    empty = 0
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        files = list(rpath.rglob("*"))
        fcount = len([f for f in files if f.is_file()])
        total += fcount
        if fcount > 2:
            active += 1
        else:
            empty += 1

    print(f"  [INFO] Reinos activos: {active}/9")
    print(f"  [INFO] Reinos vacios/reservados: {empty}/9")
    print(f"  [INFO] Archivos totales: {total:,}")

    if total > 50000:
        print("  [WARN] Demasiados archivos. Considerar ejecutar limpieza.")
    elif total < 2000:
        print("  [OK] Ecosistema limpio y saludable")
    else:
        print("  [INFO] Estado normal")


def main():
    print_banner()
    print(f"Root: {YGGDRASIL_ROOT}")
    print(f"Realms: {', '.join(REALMS)}")
    print("-" * 50)

    ok = check_python()
    if not ok:
        print("\n[FAIL] Python insuficiente. Abortando.")
        sys.exit(1)

    check_node()
    setup_asgard()
    setup_vanaheim()
    setup_alfheim()
    setup_niflheim()
    generate_env_template()
    run_health_check()

    print("\n" + "=" * 50)
    print("Setup completo.")
    print("=" * 50)
    print(
        """
Proximos pasos:
  1. Copiar .env.template -> .env y configurar
  2. Instalar dependencias de bots individualmente en Vanaheim/
  3. cd Alfheim/ui-seed && npm install && npm start
  4. Ejecutar: python Asgard/Hermes-Lilith/lilith.py

Comandos utilies:
  python setup_yggdrasil.py        # Re-ejecutar setup
  python yggdrasil_cli.py status   # Ver estado del ecosistema
"""
    )


if __name__ == "__main__":
    main()
