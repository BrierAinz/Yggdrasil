"""
Test Runner para Lilith v5.0

Ejecuta todos los tests unitarios del sistema.

Uso:
    python run_tests.py              # Ejecutar todos los tests
    python run_tests.py --cov        # Con cobertura
    python run_tests.py -v           # Modo verbose
    python run_tests.py test_mag     # Solo tests de MAG
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(pattern: str = None, verbose: bool = False, coverage: bool = False):
    """Ejecuta los tests con pytest."""
    cmd = ["python", "-m", "pytest"]

    if pattern:
        cmd.append(f"Tests/test_{pattern}.py")
    else:
        cmd.append("Tests/")

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=core", "--cov-report=html", "--cov-report=term"])

    # Plugins útiles
    cmd.append("--tb=short")  # Tracebacks cortos
    cmd.append("-ra")  # Resumen de todos los resultados

    print(f"Ejecutando: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Test Runner para Lilith v5.0")
    parser.add_argument(
        "pattern",
        nargs="?",
        help="Patrón de tests (functions, mag, swarm, workflows, audit, cache, webhooks)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Modo verbose")
    parser.add_argument(
        "--cov", action="store_true", help="Generar reporte de cobertura"
    )
    parser.add_argument("--list", action="store_true", help="Listar tests disponibles")

    args = parser.parse_args()

    if args.list:
        print("Tests disponibles:")
        tests = ["functions", "mag", "swarm", "workflows", "audit", "cache", "webhooks"]
        for test in tests:
            print(f"  - {test}")
        print("\nUso: python run_tests.py <nombre_test>")
        return 0

    return run_tests(args.pattern, args.verbose, args.cov)


if __name__ == "__main__":
    sys.exit(main())
