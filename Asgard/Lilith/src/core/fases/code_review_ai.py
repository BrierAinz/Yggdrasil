"""
Lilith v2.1 - CODE REVIEW AI MODULE
FASE C: Intelligence Amplification - Automated Code Review

Features:
- Static code analysis
- Best practices enforcement
- Performance suggestions
- Style guide compliance
- Complexity metrics
- Duplicate code detection
"""

import ast
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class ReviewCategory(Enum):
    STYLE = "style"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    BEST_PRACTICE = "best_practice"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"


class ReviewSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class CodeReview:
    """Represents a code review comment."""

    id: str
    title: str
    description: str
    category: ReviewCategory
    severity: ReviewSeverity
    file_path: str
    line_number: int
    column: int = 0
    code_snippet: str = ""
    suggested_fix: str = ""
    fix_applicable: bool = False
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "suggested_fix": self.suggested_fix,
            "fix_applicable": self.fix_applicable,
            "references": self.references,
        }


@dataclass
class CodeMetrics:
    """Code quality metrics."""

    file_path: str
    lines_of_code: int
    blank_lines: int
    comment_lines: int
    complexity_score: int
    function_count: int
    class_count: int
    average_function_length: float
    max_function_length: int
    issues_by_category: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "lines_of_code": self.lines_of_code,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "complexity_score": self.complexity_score,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "average_function_length": self.average_function_length,
            "max_function_length": self.max_function_length,
            "issues_by_category": self.issues_by_category,
        }


@dataclass
class ReviewResult:
    """Result of code review."""

    reviews: List[CodeReview]
    metrics: List[CodeMetrics]
    summary: Dict[str, Any]
    overall_score: float  # 0-100

    def to_dict(self) -> Dict:
        return {
            "reviews": [r.to_dict() for r in self.reviews],
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
            "overall_score": self.overall_score,
        }


# Best practices database
BEST_PRACTICES = {
    "mutable_default": {
        "pattern": r"def\s+\w+\s*\([^)]*=\s*(\[|\{)",
        "title": "Mutable Default Argument",
        "description": "Using mutable default arguments can lead to unexpected behavior.",
        "category": ReviewCategory.BEST_PRACTICE,
        "severity": ReviewSeverity.WARNING,
        "fix": "Use None as default and initialize inside function.",
    },
    "bare_except": {
        "pattern": r"except\s*:",
        "title": "Bare Except Clause",
        "description": "Bare except catches SystemExit and KeyboardInterrupt.",
        "category": ReviewCategory.BEST_PRACTICE,
        "severity": ReviewSeverity.WARNING,
        "fix": "Use 'except Exception:' instead.",
    },
    "variable_naming": {
        "check": lambda name: name in ["x", "y", "z", "i", "j", "k", "tmp", "temp"],
        "title": "Non-descriptive Variable Name",
        "description": "Variable name is not descriptive.",
        "category": ReviewCategory.MAINTAINABILITY,
        "severity": ReviewSeverity.SUGGESTION,
        "fix": "Use descriptive variable names.",
    },
    "long_function": {
        "threshold": 50,
        "title": "Function Too Long",
        "description": "Function exceeds recommended length.",
        "category": ReviewCategory.MAINTAINABILITY,
        "severity": ReviewSeverity.WARNING,
        "fix": "Refactor into smaller functions.",
    },
    "complex_function": {
        "threshold": 10,
        "title": "High Cyclomatic Complexity",
        "description": "Function has high cyclomatic complexity.",
        "category": ReviewCategory.COMPLEXITY,
        "severity": ReviewSeverity.WARNING,
        "fix": "Simplify logic or split into smaller functions.",
    },
    "unused_import": {
        "title": "Unused Import",
        "description": "Import is not used in the file.",
        "category": ReviewCategory.MAINTAINABILITY,
        "severity": ReviewSeverity.SUGGESTION,
        "fix": "Remove unused import.",
    },
    "line_too_long": {
        "threshold": 100,
        "title": "Line Too Long",
        "description": "Line exceeds recommended length.",
        "category": ReviewCategory.STYLE,
        "severity": ReviewSeverity.SUGGESTION,
        "fix": "Break line into multiple lines.",
    },
    "too_many_arguments": {
        "threshold": 5,
        "title": "Too Many Function Arguments",
        "description": "Function has too many arguments.",
        "category": ReviewCategory.MAINTAINABILITY,
        "severity": ReviewSeverity.SUGGESTION,
        "fix": "Use a configuration object or kwargs.",
    },
    "missing_type_hint": {
        "check": lambda args: any(
            a
            for a in args
            if not a.get("annotation") and a["arg"] not in ["self", "cls"]
        ),
        "title": "Missing Type Hint",
        "description": "Function argument lacks type hint.",
        "category": ReviewCategory.BEST_PRACTICE,
        "severity": ReviewSeverity.SUGGESTION,
        "fix": "Add type hints to function arguments.",
    },
}


class CodeAnalyzer(ast.NodeVisitor):
    """AST-based code analyzer."""

    def __init__(self, source: str, file_path: str):
        self.source = source
        self.file_path = file_path
        self.lines = source.split("\n")
        self.reviews: List[CodeReview] = []
        self.metrics = {
            "lines": len(self.lines),
            "blank": sum(1 for l in self.lines if not l.strip()),
            "comments": sum(1 for l in self.lines if l.strip().startswith("#")),
            "complexity": 0,
            "functions": [],
            "classes": 0,
            "imports": set(),
            "used_names": set(),
        }

    def analyze(self) -> Tuple[List[CodeReview], CodeMetrics]:
        """Run code analysis."""
        try:
            tree = ast.parse(self.source)
            self.visit(tree)

            # Check for unused imports
            self._check_unused_imports()

            # Check line lengths
            self._check_line_lengths()

            # Check regex patterns
            self._check_patterns()

        except SyntaxError as e:
            logger.warning(f"Syntax error in {self.file_path}: {e}")

        # Calculate metrics
        avg_func_len = 0
        max_func_len = 0
        if self.metrics["functions"]:
            lengths = [f["length"] for f in self.metrics["functions"]]
            avg_func_len = sum(lengths) / len(lengths)
            max_func_len = max(lengths)

        code_metrics = CodeMetrics(
            file_path=self.file_path,
            lines_of_code=self.metrics["lines"],
            blank_lines=self.metrics["blank"],
            comment_lines=self.metrics["comments"],
            complexity_score=self.metrics["complexity"],
            function_count=len(self.metrics["functions"]),
            class_count=self.metrics["classes"],
            average_function_length=avg_func_len,
            max_function_length=max_func_len,
        )

        return self.reviews, code_metrics

    def visit_Import(self, node):
        for alias in node.names:
            self.metrics["imports"].add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.metrics["imports"].add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        self.metrics["used_names"].add(node.id)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.metrics["classes"] += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._analyze_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node):
        self._analyze_function(node, is_async=True)

    def _analyze_function(self, node, is_async: bool):
        """Analyze a function definition."""
        # Calculate function length
        func_length = (
            node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 10
        )
        self.metrics["functions"].append(
            {
                "name": node.name,
                "length": func_length,
                "line": node.lineno,
            }
        )

        # Check function length
        if func_length > BEST_PRACTICES["long_function"]["threshold"]:
            self._add_review(
                title=BEST_PRACTICES["long_function"]["title"],
                description=f"Function '{node.name}' is {func_length} lines long.",
                category=BEST_PRACTICES["long_function"]["category"],
                severity=BEST_PRACTICES["long_function"]["severity"],
                node=node,
                fix=BEST_PRACTICES["long_function"]["fix"],
            )

        # Calculate complexity
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)
            ):
                complexity += 1

        self.metrics["complexity"] += complexity

        # Check complexity
        if complexity > BEST_PRACTICES["complex_function"]["threshold"]:
            self._add_review(
                title=BEST_PRACTICES["complex_function"]["title"],
                description=f"Function '{node.name}' has complexity of {complexity}.",
                category=BEST_PRACTICES["complex_function"]["category"],
                severity=BEST_PRACTICES["complex_function"]["severity"],
                node=node,
                fix=BEST_PRACTICES["complex_function"]["fix"],
            )

        # Check argument count
        arg_count = len(node.args.args) + len(node.args.kwonlyargs)
        if arg_count > BEST_PRACTICES["too_many_arguments"]["threshold"]:
            self._add_review(
                title=BEST_PRACTICES["too_many_arguments"]["title"],
                description=f"Function '{node.name}' has {arg_count} arguments.",
                category=BEST_PRACTICES["too_many_arguments"]["category"],
                severity=BEST_PRACTICES["too_many_arguments"]["severity"],
                node=node,
                fix=BEST_PRACTICES["too_many_arguments"]["fix"],
            )

        # Check for mutable defaults
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self._add_review(
                    title=BEST_PRACTICES["mutable_default"]["title"],
                    description=f"Function '{node.name}' has mutable default argument.",
                    category=BEST_PRACTICES["mutable_default"]["category"],
                    severity=BEST_PRACTICES["mutable_default"]["severity"],
                    node=node,
                    fix=BEST_PRACTICES["mutable_default"]["fix"],
                )

        # Check for type hints
        for arg in node.args.args:
            if arg.arg not in ["self", "cls"] and not arg.annotation:
                pass  # Type hint suggestion (optional)

        self.generic_visit(node)

    def _check_unused_imports(self):
        """Check for unused imports."""
        for imp in self.metrics["imports"]:
            if imp not in self.metrics["used_names"] and not imp.startswith("_"):
                # Find line number (simplified)
                for i, line in enumerate(self.lines, 1):
                    if imp in line and ("import" in line or "from" in line):
                        self._add_review(
                            title=BEST_PRACTICES["unused_import"]["title"],
                            description=f"Import '{imp}' is not used.",
                            category=BEST_PRACTICES["unused_import"]["category"],
                            severity=BEST_PRACTICES["unused_import"]["severity"],
                            line=i,
                            fix=BEST_PRACTICES["unused_import"]["fix"],
                        )
                        break

    def _check_line_lengths(self):
        """Check for lines that are too long."""
        threshold = BEST_PRACTICES["line_too_long"]["threshold"]
        for i, line in enumerate(self.lines, 1):
            if len(line) > threshold:
                self._add_review(
                    title=BEST_PRACTICES["line_too_long"]["title"],
                    description=f"Line is {len(line)} characters long.",
                    category=BEST_PRACTICES["line_too_long"]["category"],
                    severity=BEST_PRACTICES["line_too_long"]["severity"],
                    line=i,
                    fix=BEST_PRACTICES["line_too_long"]["fix"],
                )

    def _check_patterns(self):
        """Check regex patterns."""
        for practice_name, practice in BEST_PRACTICES.items():
            if "pattern" not in practice:
                continue

            for i, line in enumerate(self.lines, 1):
                if re.search(practice["pattern"], line):
                    self._add_review(
                        title=practice["title"],
                        description=practice["description"],
                        category=practice["category"],
                        severity=practice["severity"],
                        line=i,
                        fix=practice.get("fix", ""),
                    )

    def _add_review(
        self,
        title: str,
        description: str,
        category: ReviewCategory,
        severity: ReviewSeverity,
        node: Optional[ast.AST] = None,
        line: Optional[int] = None,
        fix: str = "",
    ):
        """Add a code review comment."""
        line_num = line or (node.lineno if node else 1)
        col_num = node.col_offset if node else 0

        review_id = hashlib.md5(
            f"{self.file_path}:{title}:{line_num}".encode()
        ).hexdigest()[:12]

        code_snippet = ""
        if 0 < line_num <= len(self.lines):
            code_snippet = self.lines[line_num - 1].strip()

        review = CodeReview(
            id=review_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            file_path=self.file_path,
            line_number=line_num,
            column=col_num,
            code_snippet=code_snippet,
            suggested_fix=fix,
        )

        self.reviews.append(review)


class DuplicateCodeDetector:
    """Detects duplicate code blocks."""

    def __init__(self, min_lines: int = 5):
        self.min_lines = min_lines

    def find_duplicates(self, files: List[Path]) -> List[CodeReview]:
        """Find duplicate code across files."""
        blocks: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8")
                lines = source.split("\n")

                for i in range(len(lines) - self.min_lines + 1):
                    block = "\n".join(lines[i : i + self.min_lines])
                    # Normalize
                    normalized = self._normalize(block)
                    if normalized:
                        blocks[normalized].append((str(file_path), i + 1))
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")

        # Find duplicates
        reviews = []
        for block, locations in blocks.items():
            if len(locations) > 1:
                review_id = hashlib.md5(block.encode()).hexdigest()[:12]

                locations_str = ", ".join([f"{f}:{l}" for f, l in locations[:3]])
                reviews.append(
                    CodeReview(
                        id=review_id,
                        title="Duplicate Code Block",
                        description=f"Similar code found in: {locations_str}",
                        category=ReviewCategory.DUPLICATION,
                        severity=ReviewSeverity.WARNING,
                        file_path=locations[0][0],
                        line_number=locations[0][1],
                        suggested_fix="Extract common code into a reusable function.",
                    )
                )

        return reviews

    def _normalize(self, block: str) -> str:
        """Normalize code block for comparison."""
        # Remove comments
        lines = [line.split("#")[0].strip() for line in block.split("\n")]
        # Remove empty lines
        lines = [l for l in lines if l]
        # Replace variable names
        result = "\n".join(lines)
        result = re.sub(r"[a-zA-Z_][a-zA-Z0-9_]*", "VAR", result)
        result = re.sub(r"[0-9]+", "NUM", result)
        return result


class CodeReviewAI:
    """Main code review engine."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.duplicate_detector = DuplicateCodeDetector()

    async def review_file(
        self, file_path: Path
    ) -> Tuple[List[CodeReview], Optional[CodeMetrics]]:
        """Review a single file."""
        try:
            full_path = (
                self.project_path / file_path
                if not file_path.is_absolute()
                else file_path
            )

            if full_path.suffix == ".py":
                source = full_path.read_text(encoding="utf-8")
                analyzer = CodeAnalyzer(source, str(file_path))
                return analyzer.analyze()

        except Exception as e:
            logger.warning(f"Error reviewing {file_path}: {e}")

        return [], None

    async def review_project(self, include_duplicates: bool = True) -> ReviewResult:
        """Review entire project."""
        all_reviews: List[CodeReview] = []
        all_metrics: List[CodeMetrics] = []

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
                reviews, metrics = await self.review_file(rel_path)
                all_reviews.extend(reviews)
                if metrics:
                    all_metrics.append(metrics)
            except Exception as e:
                logger.warning(f"Error reviewing {py_file}: {e}")

        # Check for duplicates
        if include_duplicates:
            dup_reviews = self.duplicate_detector.find_duplicates(py_files)
            all_reviews.extend(dup_reviews)

        # Calculate overall score
        overall_score = self._calculate_score(all_reviews, all_metrics)

        # Generate summary
        summary = self._generate_summary(all_reviews, all_metrics)

        return ReviewResult(
            reviews=all_reviews,
            metrics=all_metrics,
            summary=summary,
            overall_score=overall_score,
        )

    def _calculate_score(
        self, reviews: List[CodeReview], metrics: List[CodeMetrics]
    ) -> float:
        """Calculate overall code quality score."""
        base_score = 100.0

        # Deduct for issues
        deductions = {
            ReviewSeverity.ERROR: 10,
            ReviewSeverity.WARNING: 3,
            ReviewSeverity.SUGGESTION: 0.5,
            ReviewSeverity.INFO: 0,
        }

        for review in reviews:
            base_score -= deductions.get(review.severity, 0)

        # Bonus for comments
        if metrics:
            total_lines = sum(m.lines_of_code for m in metrics)
            total_comments = sum(m.comment_lines for m in metrics)
            if total_lines > 0:
                comment_ratio = total_comments / total_lines
                if comment_ratio > 0.1:
                    base_score += 5

        return max(0.0, min(100.0, base_score))

    def _generate_summary(
        self, reviews: List[CodeReview], metrics: List[CodeMetrics]
    ) -> Dict:
        """Generate review summary."""
        by_severity = defaultdict(int)
        by_category = defaultdict(int)

        for review in reviews:
            by_severity[review.severity.value] += 1
            by_category[review.category.value] += 1

        return {
            "total_reviews": len(reviews),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "files_reviewed": len(metrics),
            "total_lines": sum(m.lines_of_code for m in metrics),
        }


# Global instance
_code_review_ai = None


def get_code_review_ai(project_path: Optional[Path] = None) -> CodeReviewAI:
    global _code_review_ai
    if _code_review_ai is None:
        _code_review_ai = CodeReviewAI(project_path)
    return _code_review_ai
