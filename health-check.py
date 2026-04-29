#!/usr/bin/env python3
"""Health check del ecosistema Yggdrasil."""
import subprocess
import sys
from pathlib import Path

YGGDRASIL = Path(__file__).parent.resolve()
CHECKS = []


def check(name):
    def decorator(func):
        CHECKS.append((name, func))
        return func
    return decorator


@check("Git repository")
def check_git():
    return (YGGDRASIL / ".git").exists()


@check("Tests pasando")
def check_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=YGGDRASIL,
        capture_output=True,
        timeout=120,
    )
    return result.returncode == 0


@check("Paquetes instalados")
def check_packages():
    try:
        import lilith_core, lilith_tools, lilith_memory, lilith_orchestrator, lilith_api, lilith_cli, vanaheim
        return True
    except ImportError:
        return False


@check("Pre-commit hooks")
def check_precommit():
    return (YGGDRASIL / ".git" / "hooks" / "pre-commit").exists()


def main():
    print("=" * 50)
    print("Yggdrasil Health Check v2.0")
    print("=" * 50)
    all_ok = True
    for name, func in CHECKS:
        try:
            ok = func()
            status = "OK" if ok else "FAIL"
        except Exception as e:
            status = f"ERROR: {e}"
            ok = False
        print(f"  [{status:<6}] {name}")
        if not ok:
            all_ok = False
    print("=" * 50)
    print("Estado: HEALTHY" if all_ok else "Estado: DEGRADED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
