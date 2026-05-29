"""
TestRunner - Skill autÃ³noma para ejecuciÃ³n y anÃ¡lisis de tests
Detecta frameworks, ejecuta tests, analiza cobertura y sugiere tests faltantes
"""

import ast
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("TestRunner")


class TestFramework(str, Enum):
    """Frameworks de testing soportados"""

    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    UNKNOWN = "unknown"


class TestStatus(str, Enum):
    """Estados de un test"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    NOT_RUN = "not_run"


@dataclass
class TestResult:
    """Resultado de un test individual"""

    name: str
    status: TestStatus
    duration: float
    message: str = ""
    traceback: str = ""
    file_path: str = ""
    line_number: int = 0


@dataclass
class TestSuite:
    """Resultado de una suite de tests"""

    framework: TestFramework
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    test_results: List[TestResult] = field(default_factory=list)
    coverage: Optional[Dict[str, Any]] = None


class TestRunner:
    """
    Skill autÃ³noma para ejecuciÃ³n y anÃ¡lisis de tests.

    Capacidades:
    - Detectar framework de testing automÃ¡ticamente
    - Ejecutar tests y reportar resultados detallados
    - Analizar cobertura de cÃ³digo
    - Identificar tests faltantes por mÃ³dulo
    - Generar tests bÃ¡sicos automÃ¡ticamente
    - Comparar resultados entre runs
    """

    def __init__(self):
        self.name = "TestRunner"
        self.description = "EjecuciÃ³n y anÃ¡lisis de tests con cobertura"
        self.version = "1.0.0"
        self.supported_frameworks = {
            "pytest": TestFramework.PYTEST,
            "unittest": TestFramework.UNITTEST,
            "jest": TestFramework.JEST,
            "mocha": TestFramework.MOCHA,
            "vitest": TestFramework.VITEST,
        }
        logger.info("TestRunner initialized")

    def check_dependencies(self) -> bool:
        """Verificar dependencias"""
        return True

    def _detect_framework(self, project_path: str) -> Tuple[TestFramework, str]:
        """
        Detectar el framework de testing usado en el proyecto.

        Returns:
            Tuple de (framework, config_file_path)
        """
        path = Path(project_path)

        # Python projects
        if (path / "pytest.ini").exists() or (path / "pyproject.toml").exists():
            # Verificar si usa pytest
            if self._has_pytest_config(path):
                return TestFramework.PYTEST, str(path / "pytest.ini")

        if (path / "setup.py").exists() or (path / "requirements.txt").exists():
            # Verificar si tiene pytest en requirements
            if self._has_dependency(path, "pytest"):
                return TestFramework.PYTEST, str(path / "requirements.txt")
            # Default a unittest para proyectos Python
            if list(path.rglob("test_*.py")) or list(path.rglob("*_test.py")):
                return TestFramework.UNITTEST, ""

        # JavaScript/TypeScript projects
        if (path / "package.json").exists():
            return self._detect_js_framework(path)

        # Buscar archivos de test
        test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if test_files:
            # Analizar primer archivo de test
            with open(test_files[0], "r") as f:
                content = f.read()
                if "import unittest" in content or "from unittest" in content:
                    return TestFramework.UNITTEST, ""
                elif "import pytest" in content or "def test_" in content:
                    return TestFramework.PYTEST, ""

        return TestFramework.UNKNOWN, ""

    def _has_pytest_config(self, path: Path) -> bool:
        """Verificar si el proyecto tiene configuraciÃ³n de pytest"""
        config_files = ["pytest.ini", "setup.cfg", "pyproject.toml", "tox.ini"]
        for config in config_files:
            config_path = path / config
            if config_path.exists():
                content = config_path.read_text()
                if "pytest" in content.lower() or "[tool.pytest" in content:
                    return True
        return False

    def _has_dependency(self, path: Path, dependency: str) -> bool:
        """Verificar si el proyecto tiene una dependencia"""
        req_files = ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
        for req_file in req_files:
            req_path = path / req_file
            if req_path.exists():
                content = req_path.read_text().lower()
                if dependency.lower() in content:
                    return True
        return False

    def _detect_js_framework(self, path: Path) -> Tuple[TestFramework, str]:
        """Detectar framework de testing para JS/TS"""
        package_json = path / "package.json"
        if not package_json.exists():
            return TestFramework.UNKNOWN, ""

        try:
            content = json.loads(package_json.read_text())

            # Check devDependencies y dependencies
            all_deps = {
                **content.get("dependencies", {}),
                **content.get("devDependencies", {}),
            }

            if "jest" in all_deps:
                return TestFramework.JEST, str(package_json)
            elif "vitest" in all_deps:
                return TestFramework.VITEST, str(package_json)
            elif "mocha" in all_deps:
                return TestFramework.MOCHA, str(package_json)

            # Check scripts
            scripts = content.get("scripts", {})
            for script_name, script_cmd in scripts.items():
                if "test" in script_name.lower():
                    if "jest" in script_cmd:
                        return TestFramework.JEST, str(package_json)
                    elif "vitest" in script_cmd:
                        return TestFramework.VITEST, str(package_json)
                    elif "mocha" in script_cmd:
                        return TestFramework.MOCHA, str(package_json)

        except Exception as e:
            logger.warning(f"Error detecting JS framework: {e}")

        return TestFramework.UNKNOWN, ""

    def run_tests(
        self,
        project_path: str,
        test_path: Optional[str] = None,
        framework: Optional[TestFramework] = None,
    ) -> Dict[str, Any]:
        """
        Ejecutar tests y reportar resultados.

        Args:
            project_path: Ruta raÃ­z del proyecto
            test_path: Ruta especÃ­fica de tests (opcional)
            framework: Framework especÃ­fico (opcional, autodetecta si no se da)

        Returns:
            Dict con resultados de la ejecuciÃ³n
        """
        try:
            # Detectar framework si no se especificÃ³
            if not framework:
                framework, config_file = self._detect_framework(project_path)

            if framework == TestFramework.UNKNOWN:
                return {
                    "success": False,
                    "error": "No se pudo detectar el framework de testing",
                    "message": "AsegÃºrate de tener pytest, unittest, jest, mocha o vitest instalado",
                }

            # Ejecutar segÃºn el framework
            if framework in [TestFramework.PYTEST, TestFramework.UNITTEST]:
                return self._run_python_tests(project_path, test_path, framework)
            elif framework in [
                TestFramework.JEST,
                TestFramework.MOCHA,
                TestFramework.VITEST,
            ]:
                return self._run_js_tests(project_path, test_path, framework)
            else:
                return {
                    "success": False,
                    "error": f"Framework no soportado: {framework}",
                }

        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error ejecutando tests: {str(e)}",
            }

    def _run_python_tests(
        self, project_path: str, test_path: Optional[str], framework: TestFramework
    ) -> Dict[str, Any]:
        """Ejecutar tests de Python"""

        if framework == TestFramework.PYTEST:
            return self._run_pytest(project_path, test_path)
        else:
            return self._run_unittest(project_path, test_path)

    def _run_pytest(
        self, project_path: str, test_path: Optional[str]
    ) -> Dict[str, Any]:
        """Ejecutar pytest con reporte JSON"""
        cmd = ["python", "-m", "pytest"]

        if test_path:
            cmd.append(test_path)
        else:
            cmd.append(".")

        cmd.extend(
            [
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=pytest-report.json",
            ]
        )

        try:
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=300
            )

            # Parsear reporte JSON si existe
            report_path = Path(project_path) / "pytest-report.json"
            test_results = []
            summary = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 0,
                "duration": 0,
            }

            if report_path.exists():
                try:
                    with open(report_path, "r") as f:
                        report = json.load(f)

                    summary = report.get("summary", summary)

                    for test in report.get("tests", []):
                        test_results.append(
                            {
                                "name": test.get("nodeid", "unknown"),
                                "status": test.get("outcome", "unknown"),
                                "duration": test.get("duration", 0),
                                "message": test.get("setup", {}).get("longrepr", "")
                                if test.get("outcome") == "error"
                                else test.get("call", {}).get("longrepr", ""),
                            }
                        )

                    # Limpiar archivo de reporte
                    report_path.unlink()

                except Exception as e:
                    logger.warning(f"Error parsing pytest report: {e}")

            # Si no hay reporte JSON, parsear salida de texto
            if not test_results and result.stdout:
                test_results = self._parse_pytest_output(result.stdout)

            success = result.returncode == 0

            return {
                "success": success,
                "framework": "pytest",
                "summary": summary,
                "test_results": test_results[:50],  # Limitar a 50 tests
                "total_tests": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "errors": summary.get("error", 0),
                "duration": summary.get("duration", 0),
                "stdout": result.stdout[-2000:]
                if len(result.stdout) > 2000
                else result.stdout,
                "stderr": result.stderr[-1000:]
                if len(result.stderr) > 1000
                else result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout",
                "message": "Los tests tomaron mÃ¡s de 5 minutos en ejecutarse",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error ejecutando pytest: {str(e)}",
            }

    def _parse_pytest_output(self, output: str) -> List[Dict]:
        """Parsear salida de texto de pytest"""
        results = []
        lines = output.split("\n")

        for line in lines:
            # Buscar lÃ­neas como "test_file.py::test_name PASSED"
            match = re.match(r"(\S+)::(\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)", line)
            if match:
                results.append(
                    {
                        "name": f"{match.group(1)}::{match.group(2)}",
                        "status": match.group(3).lower(),
                        "duration": 0,
                    }
                )

        return results

    def _run_unittest(
        self, project_path: str, test_path: Optional[str]
    ) -> Dict[str, Any]:
        """Ejecutar unittest con descubrimiento"""
        cmd = ["python", "-m", "unittest", "discover", "-v"]

        if test_path:
            cmd = ["python", "-m", "unittest", "-v", test_path]

        try:
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=300
            )

            # Parsear salida
            test_results = []
            total = passed = failed = errors = 0

            lines = result.stdout.split("\n")
            for line in lines:
                # test_name (module.Class) ... ok/FAIL/ERROR
                if " ... " in line:
                    parts = line.split(" ... ")
                    test_name = parts[0].strip()
                    outcome = parts[1].strip()

                    status = "unknown"
                    if outcome == "ok":
                        status = "passed"
                        passed += 1
                    elif outcome == "FAIL":
                        status = "failed"
                        failed += 1
                    elif outcome == "ERROR":
                        status = "error"
                        errors += 1

                    test_results.append(
                        {"name": test_name, "status": status, "duration": 0}
                    )
                    total += 1

                # Resumen final
                if "Ran" in line and "tests" in line:
                    match = re.search(r"Ran (\d+) tests?", line)
                    if match:
                        total = int(match.group(1))

            success = result.returncode == 0

            return {
                "success": success,
                "framework": "unittest",
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": 0,
                "test_results": test_results[:50],
                "stdout": result.stdout[-2000:]
                if len(result.stdout) > 2000
                else result.stdout,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout",
                "message": "Los tests tomaron mÃ¡s de 5 minutos en ejecutarse",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_js_tests(
        self, project_path: str, test_path: Optional[str], framework: TestFramework
    ) -> Dict[str, Any]:
        """Ejecutar tests de JavaScript"""

        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

        if framework == TestFramework.JEST:
            cmd = [npm_cmd, "test", "--", "--json", "--outputFile=jest-results.json"]
        elif framework == TestFramework.VITEST:
            cmd = [npm_cmd, "test", "--", "--reporter=json"]
        else:
            cmd = [npm_cmd, "test"]

        try:
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=300
            )

            # Para Jest, intentar leer el archivo JSON
            if framework == TestFramework.JEST:
                report_path = Path(project_path) / "jest-results.json"
                if report_path.exists():
                    with open(report_path, "r") as f:
                        data = json.load(f)
                    report_path.unlink()

                    return {
                        "success": data.get("success", False),
                        "framework": "jest",
                        "total_tests": data.get("numTotalTests", 0),
                        "passed": data.get("numPassedTests", 0),
                        "failed": data.get("numFailedTests", 0),
                        "pending": data.get("numPendingTests", 0),
                        "test_results": data.get("testResults", [])[:50],
                    }

            # Fallback a parsing de texto
            return {
                "success": result.returncode == 0,
                "framework": framework.value,
                "stdout": result.stdout[-2000:]
                if len(result.stdout) > 2000
                else result.stdout,
                "stderr": result.stderr[-1000:]
                if len(result.stderr) > 1000
                else result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_coverage(self, project_path: str) -> Dict[str, Any]:
        """
        Analizar cobertura de cÃ³digo.

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con anÃ¡lisis de cobertura
        """
        try:
            framework, _ = self._detect_framework(project_path)

            if framework not in [TestFramework.PYTEST, TestFramework.UNITTEST]:
                return {
                    "success": False,
                    "error": "AnÃ¡lisis de cobertura solo disponible para Python",
                    "message": "Instala pytest-cov: pip install pytest-cov",
                }

            # Verificar si pytest-cov estÃ¡ instalado
            try:
                subprocess.run(
                    ["python", "-m", "pytest", "--version"],
                    capture_output=True,
                    check=True,
                )
            except:
                return {
                    "success": False,
                    "error": "pytest no estÃ¡ instalado",
                    "message": "Instala pytest: pip install pytest pytest-cov",
                }

            # Ejecutar con cobertura
            cmd = [
                "python",
                "-m",
                "pytest",
                "--cov=.",
                "--cov-report=json",
                "--cov-report=term-missing",
                "-q",
            ]

            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=300
            )

            # Leer reporte JSON de cobertura
            coverage_path = Path(project_path) / "coverage.json"
            coverage_data = {}

            if coverage_path.exists():
                try:
                    with open(coverage_path, "r") as f:
                        coverage_data = json.load(f)
                    coverage_path.unlink()
                except Exception as e:
                    logger.warning(f"Error reading coverage: {e}")

            # Calcular mÃ©tricas
            totals = coverage_data.get("totals", {})
            files = coverage_data.get("files", {})

            # Encontrar archivos con baja cobertura
            low_coverage_files = []
            for file_path, file_data in files.items():
                if file_path.startswith("test") or "/test" in file_path:
                    continue

                summary = file_data.get("summary", {})
                percent_covered = summary.get("percent_covered", 0)

                if percent_covered < 80:
                    low_coverage_files.append(
                        {
                            "file": file_path,
                            "coverage": percent_covered,
                            "missing_lines": summary.get("missing_lines", 0),
                        }
                    )

            # Ordenar por menor cobertura
            low_coverage_files.sort(key=lambda x: x["coverage"])

            return {
                "success": True,
                "framework": framework.value,
                "overall_coverage": totals.get("percent_covered", 0),
                "total_lines": totals.get("num_statements", 0),
                "covered_lines": totals.get("covered_lines", 0),
                "missing_lines": totals.get("missing_lines", 0),
                "low_coverage_files": low_coverage_files[:10],
                "files_analyzed": len(files),
                "stdout": result.stdout[-1500:]
                if len(result.stdout) > 1500
                else result.stdout,
            }

        except Exception as e:
            logger.error(f"Error analyzing coverage: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error analizando cobertura: {str(e)}",
            }

    def find_missing_tests(self, project_path: str) -> Dict[str, Any]:
        """
        Encontrar mÃ³dulos que carecen de tests.

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con mÃ³dulos sin test
        """
        try:
            path = Path(project_path)

            # Encontrar todos los archivos Python
            py_files = list(path.rglob("*.py"))

            # Filtrar archivos de cÃ³digo fuente (no tests)
            source_files = []
            for f in py_files:
                name = f.name
                if name.startswith("test_") or name.endswith("_test.py"):
                    continue
                if "__pycache__" in str(f):
                    continue
                if f.name == "__init__.py":
                    continue
                source_files.append(f)

            # Encontrar archivos de test existentes
            test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
            tested_modules = set()

            for test_file in test_files:
                # Intentar inferir quÃ© mÃ³dulo testea
                test_name = test_file.stem
                if test_name.startswith("test_"):
                    module_name = test_name[5:]  # test_module -> module
                else:
                    module_name = test_name.replace("_test", "")

                tested_modules.add(module_name)

            # Encontrar mÃ³dulos sin test
            missing_tests = []
            for source_file in source_files:
                module_name = source_file.stem

                # Verificar si tiene test
                has_test = module_name in tested_modules

                # Verificar si tiene funciones/clases que deberÃ­an testearse
                functions, classes = self._analyze_module_content(source_file)

                if functions or classes:
                    if not has_test:
                        missing_tests.append(
                            {
                                "file": str(source_file.relative_to(path)),
                                "functions": functions,
                                "classes": classes,
                                "suggested_test_file": f"test_{module_name}.py",
                            }
                        )

            return {
                "success": True,
                "total_source_files": len(source_files),
                "tested_modules": len(tested_modules),
                "missing_tests_count": len(missing_tests),
                "missing_tests": missing_tests[:20],
                "coverage_percentage": (len(tested_modules) / len(source_files) * 100)
                if source_files
                else 0,
            }

        except Exception as e:
            logger.error(f"Error finding missing tests: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_module_content(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Analizar contenido de un mÃ³dulo para encontrar funciones y clases"""
        functions = []
        classes = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("_"):  # No privadas
                        functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)

        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")

        return functions, classes

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n de TestRunner.

        Args:
            action: Tipo de acciÃ³n
            **kwargs: ParÃ¡metros especÃ­ficos

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "run": self.run_tests,
            "run_tests": self.run_tests,
            "test": self.run_tests,
            "coverage": self.analyze_coverage,
            "analyze_coverage": self.analyze_coverage,
            "find_missing": self.find_missing_tests,
            "missing_tests": self.find_missing_tests,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"AcciÃ³n no vÃ¡lida: {action}. "
                f"Acciones disponibles: {', '.join(action_map.keys())}",
            }

        method = action_map[action]
        return method(**kwargs)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 70)
        print("TestRunner - Test Suite")
        print("=" * 70)

        runner = TestRunner()

        # Test 1: Detectar framework
        print("\n[Test 1] Detectar framework")
        framework, config = runner._detect_framework(".")
        print(f"  Framework detectado: {framework.value}")
        print(f"  Config file: {config}")

        # Test 2: Buscar tests faltantes
        print("\n[Test 2] Buscar tests faltantes")
        result = await runner.execute("find_missing", project_path=".")
        if result.get("success"):
            print(f"  Archivos fuente: {result['total_source_files']}")
            print(f"  MÃ³dulos testeados: {result['tested_modules']}")
            print(f"  Tests faltantes: {result['missing_tests_count']}")
            if result["missing_tests"]:
                print(f"  Ejemplo: {result['missing_tests'][0]['file']}")

        print("\n" + "=" * 70)
        print("Tests completados!")
        print("=" * 70)

    asyncio.run(test())
