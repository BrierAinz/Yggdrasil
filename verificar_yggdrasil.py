#!/usr/bin/env python3
"""
Script de verificación completa de Yggdrasil
Testea todas las funcionalidades clave del ecosistema
"""

import os
import subprocess
import sys
from pathlib import Path


YGGDRASIL_DIR = Path("/mnt/d/Proyectos/Yggdrasil")


def print_header(text: str):
    """Print header with decorative border"""
    border = "=" * 60
    print(f"\n{border}")
    print(f"⚔ {text} ⚔")
    print(border)


def run_command(cmd: str, description: str):
    """Run command and print status"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"✅ {description} completado")
            if result.stdout.strip():
                print(f"📄 Salida:\n{result.stdout.strip()[:200]}...")
        else:
            print(f"❌ {description} falló")
            print(f"🔴 Error:\n{result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} falló: {e}")
        return False


def verify_environment():
    """Verify environment variables are set"""
    print_header("Verificación del Entorno")

    required_vars = ["BYTEPLUS_API_KEY", "ALIBABA_API_KEY", "LILITH_PROFILE", "YGGDRASIL_ROOT"]

    all_vars_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} está configurada: {'***' + value[-8:]}")
        else:
            print(f"❌ {var} NO está configurada")
            all_vars_set = False

    return all_vars_set


def verify_yggdrasil_cli():
    """Verify Yggdrasil CLI is working"""
    print_header("Verificación del CLI de Yggdrasil")

    success = True
    commands = [
        ("cd /mnt/d/Proyectos/Yggdrasil && uv run python yggdrasil_cli.py --help", "Ayuda del CLI"),
        (
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python yggdrasil_cli.py status",
            "Estado de Yggdrasil",
        ),
        (
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python yggdrasil_cli.py health",
            "Verificación de README.md",
        ),
    ]

    for cmd, desc in commands:
        if not run_command(cmd, desc):
            success = False

    return success


def verify_llm_integration():
    """Verify LLM integration"""
    print_header("Verificación de la Integración LLM")

    success = True
    commands = [
        (
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python -c \"from lilith_core.config import Config; from lilith_core.providers.registry import ProviderRegistry; config = Config(); registry = ProviderRegistry(config); print('✅ Provider registry loaded'); print(f'  Active profile: {config.active_profile}'); print(f'  Available profiles: {len(registry.list_profiles())}');\"",
            "Carga del provider registry",
        ),
        (
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python -c \"from lilith_core.providers.registry import ProviderRegistry; from lilith_core.config import Config; config = Config(); registry = ProviderRegistry(config); print('✅ BytePlus profile:'); print(f'  Model count: {len(registry.get_profile('byteplus-lite').get('models', {}).get('list', []))}'); print(f'  Description: {registry.get_profile('byteplus-lite').get('description', 'No description')}');\"",
            "BytePlus profile details",
        ),
        (
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python -c \"from lilith_core.providers.registry import ProviderRegistry; from lilith_core.config import Config; config = Config(); registry = ProviderRegistry(config); print('✅ Alibaba profile:'); print(f'  Model count: {len(registry.get_profile('alibaba-token-plan').get('models', {}).get('list', []))}'); print(f'  Description: {registry.get_profile('alibaba-token-plan').get('description', 'No description')}');\"",
            "Alibaba Cloud profile details",
        ),
    ]

    for cmd, desc in commands:
        if not run_command(cmd, desc):
            success = False

    return success


def verify_memory_system():
    """Verify memory system"""
    print_header("Verificación del Sistema de Memoria")

    success = True

    # Verificar base de datos de chat
    chat_db = YGGDRASIL_DIR / "chat_memory.db"
    if chat_db.exists():
        print(f"✅ Base de datos de chat existe: {chat_db}")
    else:
        print(f"❌ Base de datos de chat no existe: {chat_db}")
        success = False

    # Verificar directorio de memory
    memory_dir = YGGDRASIL_DIR / "chat_memory"
    if memory_dir.exists() and memory_dir.is_dir():
        print(f"✅ Directorio de memory existe: {memory_dir}")
    else:
        print(f"❌ Directorio de memory no existe: {memory_dir}")
        success = False

    return success


def run_system_health_check():
    """Run system health check"""
    print_header("Verificación de Salud del Sistema")

    health_script = YGGDRASIL_DIR / "health_check.py"
    if health_script.exists():
        return run_command(
            "cd /mnt/d/Proyectos/Yggdrasil && uv run python health_check.py",
            "Health check completo",
        )
    else:
        print("⚠️ Script de health check no encontrado")
        return False


def main():
    """Main verification function"""
    print("⚔ Iniciando verificación completa de Yggdrasil ⚔")
    print("=" * 60)

    # Cargar variables de entorno
    env_file = YGGDRASIL_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
                    except:
                        pass

    # Ejecutar verificaciones
    checks = [
        verify_environment(),
        verify_yggdrasil_cli(),
        verify_llm_integration(),
        verify_memory_system(),
        run_system_health_check(),
    ]

    # Resumen de resultados
    print_header("Resumen de la Verificación")
    passed = sum(checks)
    total = len(checks)
    print(f"✅ Verificaciones pasadas: {passed}/{total}")
    print(f"❌ Verificaciones fallidas: {total - passed}/{total}")

    if all(checks):
        print("\n🎉 Yggdrasil está completamente listo para usar!")
        print("\n📋 Pasos siguientes:")
        print("1. Inicia el chat interactivo: yggdrasil chat")
        print("2. Verifica el estado: yggdrasil status")
        print("3. Consulta la ayuda: yggdrasil --help")
        return 0
    else:
        print("\n⚠️ Yggdrasil requiere correcciones antes de usarlo")
        print("🔍 Verifica los errores anteriores para solucionar los problemas")
        return 1


if __name__ == "__main__":
    sys.exit(main())
