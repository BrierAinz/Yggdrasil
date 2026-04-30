"""
Lilith v2.1 - TEST GENERATOR MODULE
FASE C: Intelligence Amplification - Automated Test Generation

Features:
- Generate unit tests from function signatures
- Detect edge cases automatically
- Create test fixtures and mocks
- Property-based test suggestions
- Coverage analysis
"""

import ast
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"
    ERROR_CASE = "error_case"
    PROPERTY = "property"


@dataclass
class TestCase:
    """Represents a generated test case."""

    id: str
    name: str
    function_name: str
    test_type: TestType
    description: str
    code: str
    fixtures: List[str] = field(default_factory=list)
    mocks: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)
    imports_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "function_name": self.function_name,
            "test_type": self.test_type.value,
            "description": self.description,
            "code": self.code,
            "fixtures": self.fixtures,
            "mocks": self.mocks,
            "assertions": self.assertions,
            "imports_needed": self.imports_needed,
        }


@dataclass
class TestSuite:
    """Generated test suite for a module."""

    file_path: str
    test_file_path: str
    test_cases: List[TestCase]
    fixtures: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)

    def generate_full_file(self) -> str:
        """Generate complete test file content."""
        lines = []

        # Imports
        lines.extend(self.imports)
        lines.append("")
        lines.append("import pytest")
        lines.append("")

        # Fixtures
        if self.fixtures:
            lines.append("# Fixtures")
            for name, code in self.fixtures.items():
                lines.append(code)
                lines.append("")

        # Test cases
        for test in self.test_cases:
            lines.append(f"# {test.description}")
            lines.append(test.code)
            lines.append("")

        return "\n".join(lines)


class TypeHintAnalyzer:
    """Analyzes type hints to generate test data."""

    DEFAULT_VALUES = {
        "str": ['"test"', '""', '"special chars: <>&"'],
        "int": ["42", "0", "-1", "999999"],
        "float": ["3.14", "0.0", "-1.5"],
        "bool": ["True", "False"],
        "list": ["[]", "[1, 2, 3]"],
        "dict": ["{}", '{"key": "value"}'],
        "Optional": ["None", "valid_value"],
        "Any": ["None", "42", '"test"'],
    }

    def get_test_values(self, type_hint: str) -> List[str]:
        """Get appropriate test values for a type."""
        # Handle Optional[X]
        if type_hint.startswith("Optional["):
            inner = type_hint[9:-1]
            values = self.get_test_values(inner)
            return ["None"] + values[:2]

        # Handle List[X], Dict[X, Y]
        if type_hint.startswith(("List[", "Sequence[")):
            return ["[]", "[item1, item2]"]

        if type_hint.startswith("Dict["):
            return ["{}", "{key: value}"]

        # Basic types
        for type_name, values in self.DEFAULT_VALUES.items():
            if type_name in type_hint:
                return values

        return ["None", "test_value"]


class TestGenerator:
    """Generates test cases from Python code."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.type_analyzer = TypeHintAnalyzer()

    def generate_tests_for_file(self, file_path: Path) -> TestSuite:
        """Generate test suite for a Python file."""
        full_path = (
            self.project_path / file_path if not file_path.is_absolute() else file_path
        )

        try:
            source = full_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            module_name = file_path.stem
            test_file_name = f"test_{module_name}.py"

            test_cases = []
            fixtures = {}
            imports = [f"from {module_name} import *"]

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private functions
                    if node.name.startswith("_"):
                        continue

                    test_cases.extend(self._generate_function_tests(node, module_name))

            return TestSuite(
                file_path=str(file_path),
                test_file_path=test_file_name,
                test_cases=test_cases,
                fixtures=fixtures,
                imports=imports,
            )

        except Exception as e:
            logger.error(f"Error generating tests for {file_path}: {e}")
            return TestSuite(
                file_path=str(file_path),
                test_file_path="",
                test_cases=[],
            )

    def _generate_function_tests(
        self, func: ast.FunctionDef, module: str
    ) -> List[TestCase]:
        """Generate test cases for a function."""
        tests = []
        func_name = func.name

        # Get function info
        args_info = []
        for arg in func.args.args:
            type_hint = ""
            if arg.annotation:
                try:
                    type_hint = (
                        ast.unparse(arg.annotation)
                        if hasattr(ast, "unparse")
                        else str(arg.annotation)
                    )
                except:
                    pass

            args_info.append(
                {
                    "name": arg.arg,
                    "type_hint": type_hint,
                }
            )

        return_type = ""
        if func.returns:
            try:
                return_type = (
                    ast.unparse(func.returns)
                    if hasattr(ast, "unparse")
                    else str(func.returns)
                )
            except:
                pass

        # Generate basic test
        test_id = hashlib.md5(f"{module}.{func_name}:basic".encode()).hexdigest()[:12]

        # Build test arguments
        test_args = []
        for arg in args_info:
            if arg["name"] in ["self", "cls"]:
                continue
            values = self.type_analyzer.get_test_values(arg["type_hint"])
            test_args.append((arg["name"], values[0] if values else "None"))

        arg_str = ", ".join([f"{name}={val}" for name, val in test_args])

        code = f"""
def test_{func_name}_basic():
    \"\"\"Test {func_name} with basic inputs.\"\"\""
    result = {func_name}({arg_str})
    assert result is not None
"""

        tests.append(
            TestCase(
                id=test_id,
                name=f"test_{func_name}_basic",
                function_name=func_name,
                test_type=TestType.UNIT,
                description=f"Basic test for {func_name}",
                code=code,
                assertions=["assert result is not None"],
            )
        )

        # Generate edge case tests for each argument
        for i, arg in enumerate(args_info):
            if arg["name"] in ["self", "cls"]:
                continue

            values = self.type_analyzer.get_test_values(arg["type_hint"])
            for j, val in enumerate(values[1:2], 1):  # Skip first (used in basic)
                test_id = hashlib.md5(
                    f"{module}.{func_name}:edge_{i}_{j}".encode()
                ).hexdigest()[:12]

                edge_args = test_args.copy()
                for k, (arg_name, _) in enumerate(edge_args):
                    if arg_name == arg["name"]:
                        edge_args[k] = (arg_name, val)
                        break

                arg_str_edge = ", ".join([f"{name}={val}" for name, val in edge_args])

                code = f"""
def test_{func_name}_edge_{arg["name"]}_{j}():
    \"\"\"Test {func_name} with edge case for {arg["name"]}.\"\"\""
    result = {func_name}({arg_str_edge})
    assert result is not None
"""

                tests.append(
                    TestCase(
                        id=test_id,
                        name=f"test_{func_name}_edge_{arg['name']}_{j}",
                        function_name=func_name,
                        test_type=TestType.EDGE_CASE,
                        description=f"Edge case test for {func_name} - {arg['name']}={val}",
                        code=code,
                        assertions=["assert result is not None"],
                    )
                )

        # Generate error case test
        test_id = hashlib.md5(f"{module}.{func_name}:error".encode()).hexdigest()[:12]

        code = f"""
def test_{func_name}_error():
    \"\"\"Test {func_name} error handling.\"\"\""
    # TODO: Add invalid inputs and test exception handling
    # with pytest.raises(ValueError):
    #     {func_name}(invalid_arg)
    pass
"""

        tests.append(
            TestCase(
                id=test_id,
                name=f"test_{func_name}_error",
                function_name=func_name,
                test_type=TestType.ERROR_CASE,
                description=f"Error handling test for {func_name}",
                code=code,
                imports_needed=["pytest"],
            )
        )

        return tests

    async def apply_tests(
        self, test_suite: TestSuite, output_dir: Optional[Path] = None
    ) -> Path:
        """Write test file to disk."""
        output = output_dir or self.project_path / "tests"
        output.mkdir(exist_ok=True)

        test_file = output / test_suite.test_file_path
        test_content = test_suite.generate_full_file()

        test_file.write_text(test_content, encoding="utf-8")
        logger.info(f"Generated test file: {test_file}")

        return test_file


class CoverageAnalyzer:
    """Analyzes test coverage."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    async def analyze_coverage(self) -> Dict:
        """Run coverage analysis."""
        try:
            result = subprocess.run(
                ["pytest", "--cov=.", "--cov-report=json", "-q"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Try to read coverage report
            coverage_file = self.project_path / "coverage.json"
            if coverage_file.exists():
                import json

                with open(coverage_file) as f:
                    data = json.load(f)

                return {
                    "total_coverage": data.get("totals", {}).get("percent_covered", 0),
                    "files": data.get("files", {}),
                }

        except Exception as e:
            logger.warning(f"Coverage analysis failed: {e}")

        return {"total_coverage": 0, "files": {}}


class TestRunner:
    """Runs tests and analyzes results."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    async def run_tests(self, test_path: Optional[Path] = None) -> Dict:
        """Run tests and return results."""
        try:
            cmd = ["pytest", "-v", "--tb=short"]
            if test_path:
                cmd.append(str(test_path))

            result = subprocess.run(
                cmd, cwd=self.project_path, capture_output=True, text=True, timeout=120
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Test execution timed out",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": str(e),
                "returncode": -1,
            }


# Global instance
_test_generator = None


def get_test_generator(project_path: Optional[Path] = None) -> TestGenerator:
    global _test_generator
    if _test_generator is None:
        _test_generator = TestGenerator(project_path)
    return _test_generator
