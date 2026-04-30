"""
Lilith v2.1 - SECURITY SCANNER MODULE
FASE C: Intelligence Amplification - Security Vulnerability Detection

Features:
- Static analysis for security vulnerabilities
- Python-specific security checks
- Dependency vulnerability scanning
- Secret detection (API keys, passwords)
- CWE classification
- Risk scoring
"""

import ast
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class Severity(Enum):
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Fix ASAP
    MEDIUM = "medium"  # Fix in next sprint
    LOW = "low"  # Fix when convenient
    INFO = "info"  # Informational


class VulnCategory(Enum):
    INJECTION = "injection"
    AUTH = "authentication"
    DATA_EXPOSURE = "data_exposure"
    CONFIG = "configuration"
    CRYPTO = "cryptography"
    VALIDATION = "validation"
    SECRETS = "secrets"
    DEPENDENCIES = "dependencies"


@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding."""

    id: str
    title: str
    description: str
    severity: Severity
    category: VulnCategory
    file_path: str
    line_number: int
    column: int = 0
    code_snippet: str = ""
    cwe_id: Optional[str] = None
    cwe_name: Optional[str] = None
    fix_suggestion: str = ""
    references: List[str] = field(default_factory=list)
    confidence: float = 0.8  # 0.0 - 1.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "cwe_id": self.cwe_id,
            "cwe_name": self.cwe_name,
            "fix_suggestion": self.fix_suggestion,
            "references": self.references,
            "confidence": self.confidence,
        }


@dataclass
class ScanResult:
    """Result of a security scan."""

    findings: List[SecurityFinding]
    scanned_files: int
    duration_seconds: float
    risk_score: float  # 0.0 - 100.0
    summary: Dict[str, int]  # Count by severity

    def to_dict(self) -> Dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "scanned_files": self.scanned_files,
            "duration_seconds": self.duration_seconds,
            "risk_score": self.risk_score,
            "summary": self.summary,
        }


# Security patterns database
SECURITY_PATTERNS = {
    "hardcoded_password": {
        "pattern": r"(password|passwd|pwd)\s*=\s*[\'\"][^\'\"]{3,}[\'\"]",
        "severity": Severity.CRITICAL,
        "category": VulnCategory.SECRETS,
        "title": "Hardcoded Password Detected",
        "description": "Password is hardcoded in source code.",
        "cwe_id": "CWE-798",
        "cwe_name": "Use of Hard-coded Credentials",
        "fix": "Use environment variables or a secrets manager.",
    },
    "hardcoded_api_key": {
        "pattern": r"(api_key|apikey|api-key|secret_key|token)\s*=\s*[\'\"][a-zA-Z0-9_\-]{16,}[\'\"]",
        "severity": Severity.CRITICAL,
        "category": VulnCategory.SECRETS,
        "title": "Hardcoded API Key Detected",
        "description": "API key or secret is hardcoded in source code.",
        "cwe_id": "CWE-798",
        "cwe_name": "Use of Hard-coded Credentials",
        "fix": "Use environment variables or a secrets manager.",
    },
    "sql_injection": {
        "pattern": r"(execute|raw|query)\s*\(\s*[f\"\'].*\{.*\}",
        "severity": Severity.CRITICAL,
        "category": VulnCategory.INJECTION,
        "title": "Potential SQL Injection",
        "description": "User input may be directly used in SQL query.",
        "cwe_id": "CWE-89",
        "cwe_name": "SQL Injection",
        "fix": "Use parameterized queries or ORM.",
    },
    "eval_usage": {
        "pattern": r"\beval\s*\(",
        "severity": Severity.HIGH,
        "category": VulnCategory.INJECTION,
        "title": "Dangerous eval() Usage",
        "description": "eval() can execute arbitrary code.",
        "cwe_id": "CWE-95",
        "cwe_name": "Eval Injection",
        "fix": "Use ast.literal_eval() for safe evaluation.",
    },
    "exec_usage": {
        "pattern": r"\bexec\s*\(",
        "severity": Severity.HIGH,
        "category": VulnCategory.INJECTION,
        "title": "Dangerous exec() Usage",
        "description": "exec() can execute arbitrary code.",
        "cwe_id": "CWE-95",
        "cwe_name": "Eval Injection",
        "fix": "Avoid exec(). Use safer alternatives.",
    },
    "pickle_load": {
        "pattern": r"pickle\.load|pickle\.loads",
        "severity": Severity.HIGH,
        "category": VulnCategory.VALIDATION,
        "title": "Unsafe Deserialization",
        "description": "pickle can execute arbitrary code during deserialization.",
        "cwe_id": "CWE-502",
        "cwe_name": "Deserialization of Untrusted Data",
        "fix": "Use json or safe serialization libraries.",
    },
    "yaml_load": {
        "pattern": r"yaml\.load\s*\([^)]*\)(?!.*Loader\s*=\s*yaml\.SafeLoader)",
        "severity": Severity.HIGH,
        "category": VulnCategory.VALIDATION,
        "title": "Unsafe YAML Loading",
        "description": "yaml.load without SafeLoader can execute arbitrary code.",
        "cwe_id": "CWE-502",
        "cwe_name": "Deserialization of Untrusted Data",
        "fix": "Use yaml.safe_load() instead.",
    },
    "md5_hash": {
        "pattern": r"hashlib\.md5|md5\s*\(",
        "severity": Severity.MEDIUM,
        "category": VulnCategory.CRYPTO,
        "title": "Weak Hash Algorithm",
        "description": "MD5 is cryptographically broken and should not be used.",
        "cwe_id": "CWE-328",
        "cwe_name": "Use of Weak Hash",
        "fix": "Use SHA-256 or stronger hash algorithms.",
    },
    "sha1_hash": {
        "pattern": r"hashlib\.sha1|sha1\s*\(",
        "severity": Severity.MEDIUM,
        "category": VulnCategory.CRYPTO,
        "title": "Weak Hash Algorithm",
        "description": "SHA-1 is cryptographically weak.",
        "cwe_id": "CWE-328",
        "cwe_name": "Use of Weak Hash",
        "fix": "Use SHA-256 or stronger hash algorithms.",
    },
    "debug_mode": {
        "pattern": r"debug\s*=\s*True|DEBUG\s*=\s*True",
        "severity": Severity.MEDIUM,
        "category": VulnCategory.CONFIG,
        "title": "Debug Mode Enabled",
        "description": "Debug mode should not be enabled in production.",
        "cwe_id": "CWE-489",
        "cwe_name": "Active Debug Code",
        "fix": "Set debug=False in production.",
    },
    "http_without_tls": {
        "pattern": r"http://(?!localhost|127\.0\.0\.1)",
        "severity": Severity.MEDIUM,
        "category": VulnCategory.DATA_EXPOSURE,
        "title": "Insecure HTTP Connection",
        "description": "HTTP without TLS can expose sensitive data.",
        "cwe_id": "CWE-319",
        "cwe_name": "Cleartext Transmission",
        "fix": "Use HTTPS instead of HTTP.",
    },
    "temp_file": {
        "pattern": r"mktemp\s*\(|tempfile\.mktemp",
        "severity": Severity.MEDIUM,
        "category": VulnCategory.CONFIG,
        "title": "Insecure Temporary File",
        "description": "mktemp is insecure; use mkstemp instead.",
        "cwe_id": "CWE-377",
        "cwe_name": "Insecure Temporary File",
        "fix": "Use tempfile.mkstemp() or NamedTemporaryFile.",
    },
    "wildcard_import": {
        "pattern": r"from\s+\S+\s+import\s+\*",
        "severity": Severity.LOW,
        "category": VulnCategory.CONFIG,
        "title": "Wildcard Import",
        "description": "Wildcard imports can obscure code and create conflicts.",
        "cwe_id": None,
        "cwe_name": None,
        "fix": "Import only what you need explicitly.",
    },
    " bare_except": {
        "pattern": r"except\s*:",
        "severity": Severity.LOW,
        "category": VulnCategory.VALIDATION,
        "title": "Bare Except Clause",
        "description": "Bare except catches SystemExit and KeyboardInterrupt.",
        "cwe_id": "CWE-391",
        "cwe_name": "Unchecked Error Condition",
        "fix": "Use 'except Exception:' instead.",
    },
}


class PythonSecurityAnalyzer(ast.NodeVisitor):
    """AST-based security analyzer for Python."""

    DANGEROUS_FUNCTIONS = {
        "eval": (Severity.CRITICAL, "CWE-95", "Eval Injection"),
        "exec": (Severity.CRITICAL, "CWE-95", "Eval Injection"),
        "compile": (Severity.HIGH, "CWE-95", "Eval Injection"),
        "input": (Severity.MEDIUM, "CWE-20", "Improper Input Validation"),
    }

    DANGEROUS_MODULES = {
        "pickle": (Severity.HIGH, "CWE-502", "Deserialization of Untrusted Data"),
        "marshal": (Severity.HIGH, "CWE-502", "Deserialization of Untrusted Data"),
        "subprocess": (Severity.MEDIUM, "CWE-78", "OS Command Injection"),
    }

    SQL_METHODS = ["execute", "executemany", "raw", "query"]

    def __init__(self, source: str, file_path: str):
        self.source = source
        self.file_path = file_path
        self.findings: List[SecurityFinding] = []
        self.lines = source.split("\n")

    def analyze(self) -> List[SecurityFinding]:
        """Run security analysis."""
        try:
            tree = ast.parse(self.source)
            self.visit(tree)

            # Also run regex patterns
            self._check_patterns()

        except SyntaxError as e:
            logger.warning(f"Syntax error in {self.file_path}: {e}")

        return self.findings

    def visit_Call(self, node):
        """Check for dangerous function calls."""
        func_name = self._get_func_name(node.func)

        # Check for dangerous functions
        if func_name in self.DANGEROUS_FUNCTIONS:
            severity, cwe_id, cwe_name = self.DANGEROUS_FUNCTIONS[func_name]
            self._add_finding(
                title=f"Dangerous {func_name}() Usage",
                description=f"{func_name}() can execute arbitrary code.",
                severity=severity,
                category=VulnCategory.INJECTION,
                node=node,
                cwe_id=cwe_id,
                cwe_name=cwe_name,
                fix=f"Avoid {func_name}(). Use safer alternatives.",
            )

        # Check for SQL injection patterns
        if func_name and any(sql in func_name.lower() for sql in self.SQL_METHODS):
            if self._has_user_input(node):
                self._add_finding(
                    title="Potential SQL Injection",
                    description=f"{func_name} may include user-controlled data.",
                    severity=Severity.CRITICAL,
                    category=VulnCategory.INJECTION,
                    node=node,
                    cwe_id="CWE-89",
                    cwe_name="SQL Injection",
                    fix="Use parameterized queries.",
                )

        self.generic_visit(node)

    def visit_Import(self, node):
        """Check for dangerous imports."""
        for alias in node.names:
            if alias.name in self.DANGEROUS_MODULES:
                severity, cwe_id, cwe_name = self.DANGEROUS_MODULES[alias.name]
                self._add_finding(
                    title=f"Potentially Dangerous Import: {alias.name}",
                    description=f"{alias.name} module can be dangerous if used with untrusted data.",
                    severity=severity,
                    category=VulnCategory.VALIDATION,
                    node=node,
                    cwe_id=cwe_id,
                    cwe_name=cwe_name,
                    fix=f"Ensure {alias.name} is only used with trusted data.",
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check for dangerous imports."""
        if node.module in self.DANGEROUS_MODULES:
            severity, cwe_id, cwe_name = self.DANGEROUS_MODULES[node.module]
            self._add_finding(
                title=f"Potentially Dangerous Import: {node.module}",
                description=f"{node.module} module can be dangerous.",
                severity=severity,
                category=VulnCategory.VALIDATION,
                node=node,
                cwe_id=cwe_id,
                cwe_name=cwe_name,
                fix=f"Ensure {node.module} is used safely.",
            )
        self.generic_visit(node)

    def _check_patterns(self):
        """Check regex patterns."""
        for pattern_name, pattern_info in SECURITY_PATTERNS.items():
            for i, line in enumerate(self.lines, 1):
                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                    # Skip if in comment or string
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('""'):
                        continue

                    self._add_finding_from_pattern(pattern_name, pattern_info, i, line)

    def _add_finding_from_pattern(
        self, name: str, info: Dict, line_num: int, line: str
    ):
        """Add finding from pattern match."""
        finding_id = hashlib.md5(
            f"{self.file_path}:{name}:{line_num}".encode()
        ).hexdigest()[:12]

        finding = SecurityFinding(
            id=finding_id,
            title=info["title"],
            description=info["description"],
            severity=info["severity"],
            category=info["category"],
            file_path=self.file_path,
            line_number=line_num,
            code_snippet=line.strip(),
            cwe_id=info.get("cwe_id"),
            cwe_name=info.get("cwe_name"),
            fix_suggestion=info.get("fix", ""),
            references=[
                f"https://cwe.mitre.org/data/definitions/{info['cwe_id'].split('-')[1]}.html"
            ]
            if info.get("cwe_id")
            else [],
        )

        self.findings.append(finding)

    def _add_finding(
        self,
        title: str,
        description: str,
        severity: Severity,
        category: VulnCategory,
        node: ast.AST,
        cwe_id: Optional[str] = None,
        cwe_name: Optional[str] = None,
        fix: str = "",
    ):
        """Add a security finding."""
        finding_id = hashlib.md5(
            f"{self.file_path}:{title}:{node.lineno}".encode()
        ).hexdigest()[:12]

        line_num = getattr(node, "lineno", 0)
        col_num = getattr(node, "col_offset", 0)

        code_snippet = ""
        if 0 < line_num <= len(self.lines):
            code_snippet = self.lines[line_num - 1].strip()

        finding = SecurityFinding(
            id=finding_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            file_path=self.file_path,
            line_number=line_num,
            column=col_num,
            code_snippet=code_snippet,
            cwe_id=cwe_id,
            cwe_name=cwe_name,
            fix_suggestion=fix,
            references=[
                f"https://cwe.mitre.org/data/definitions/{cwe_id.split('-')[1]}.html"
            ]
            if cwe_id
            else [],
        )

        self.findings.append(finding)

    def _get_func_name(self, node) -> Optional[str]:
        """Extract function name from call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _has_user_input(self, node: ast.Call) -> bool:
        """Check if call has user input (simplified)."""
        for arg in node.args:
            if isinstance(arg, (ast.JoinedStr, ast.BinOp)):
                return True
            if isinstance(arg, ast.Call):
                func_name = self._get_func_name(arg.func)
                if func_name in ["input", "request", "get"]:
                    return True
        return False


class DependencyScanner:
    """Scans dependencies for known vulnerabilities."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def scan_dependencies(self) -> List[SecurityFinding]:
        """Scan project dependencies."""
        findings = []

        # Check for requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            findings.extend(self._scan_requirements(req_file))

        # Check for package.json
        pkg_file = self.project_path / "package.json"
        if pkg_file.exists():
            findings.extend(self._scan_package_json(pkg_file))

        return findings

    def _scan_requirements(self, req_file: Path) -> List[SecurityFinding]:
        """Scan requirements.txt for issues."""
        findings = []

        try:
            content = req_file.read_text()

            # Check for pinned versions (good practice)
            for i, line in enumerate(content.split("\n"), 1):
                if line.strip() and not line.startswith("#"):
                    # Check if version is pinned
                    if "==" not in line and ">=" not in line and "<=" not in line:
                        finding = SecurityFinding(
                            id=hashlib.md5(f"req:{i}".encode()).hexdigest()[:12],
                            title="Unpinned Dependency",
                            description=f"Dependency '{line.strip()}' has no version specified.",
                            severity=Severity.LOW,
                            category=VulnCategory.DEPENDENCIES,
                            file_path=str(req_file.relative_to(self.project_path)),
                            line_number=i,
                            fix_suggestion="Pin dependency versions using 'package==version'",
                        )
                        findings.append(finding)

            # Try to run safety check if available
            try:
                result = subprocess.run(
                    ["safety", "check", "--file", str(req_file), "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout:
                    vulnerabilities = json.loads(result.stdout)
                    for vuln in vulnerabilities:
                        finding = SecurityFinding(
                            id=vuln.get("vulnerability_id", "unknown"),
                            title=f"Vulnerable Dependency: {vuln.get('package_name')}",
                            description=vuln.get(
                                "vulnerability_description", "Unknown vulnerability"
                            ),
                            severity=Severity.HIGH,
                            category=VulnCategory.DEPENDENCIES,
                            file_path="requirements.txt",
                            line_number=0,
                            fix_suggestion=f"Upgrade to {vuln.get('package_name')}>= {vuln.get('fixed_version', 'latest')}",
                            references=[vuln.get("more_info_url", "")]
                            if vuln.get("more_info_url")
                            else [],
                        )
                        findings.append(finding)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # safety not installed

        except Exception as e:
            logger.warning(f"Error scanning requirements: {e}")

        return findings

    def _scan_package_json(self, pkg_file: Path) -> List[SecurityFinding]:
        """Scan package.json for issues."""
        findings = []
        # Implementation similar to requirements.txt
        return findings


class SecurityScanner:
    """Main security scanner engine."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.dependency_scanner = DependencyScanner(self.project_path)

    async def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single file."""
        findings = []

        try:
            full_path = (
                self.project_path / file_path
                if not file_path.is_absolute()
                else file_path
            )

            if full_path.suffix == ".py":
                source = full_path.read_text(encoding="utf-8")
                analyzer = PythonSecurityAnalyzer(source, str(file_path))
                findings = analyzer.analyze()

        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")

        return findings

    async def scan_project(self, include_dependencies: bool = True) -> ScanResult:
        """Scan entire project."""
        import time

        start_time = time.time()

        all_findings: List[SecurityFinding] = []
        scanned_files = 0

        # Find Python files
        py_files = list(self.project_path.rglob("*.py"))
        py_files = [
            f
            for f in py_files
            if not any(
                part.startswith(".")
                or part in {"node_modules", "__pycache__", "venv", ".venv", "env"}
                for part in f.parts
            )
        ]

        for py_file in py_files:
            try:
                rel_path = py_file.relative_to(self.project_path)
                findings = await self.scan_file(rel_path)
                all_findings.extend(findings)
                scanned_files += 1
            except Exception as e:
                logger.warning(f"Error scanning {py_file}: {e}")

        # Scan dependencies
        if include_dependencies:
            dep_findings = self.dependency_scanner.scan_dependencies()
            all_findings.extend(dep_findings)

        # Calculate risk score
        risk_score = self._calculate_risk_score(all_findings)

        # Generate summary
        summary = defaultdict(int)
        for finding in all_findings:
            summary[finding.severity.value] += 1

        duration = time.time() - start_time

        return ScanResult(
            findings=all_findings,
            scanned_files=scanned_files,
            duration_seconds=duration,
            risk_score=risk_score,
            summary=dict(summary),
        )

    def _calculate_risk_score(self, findings: List[SecurityFinding]) -> float:
        """Calculate overall risk score (0-100)."""
        weights = {
            Severity.CRITICAL: 10,
            Severity.HIGH: 5,
            Severity.MEDIUM: 2,
            Severity.LOW: 0.5,
            Severity.INFO: 0,
        }

        score = sum(weights[f.severity] for f in findings)
        return min(score, 100.0)


# Global instance
_security_scanner = None


def get_security_scanner(project_path: Optional[Path] = None) -> SecurityScanner:
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = SecurityScanner(project_path)
    return _security_scanner
