"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Lilith v2.1 - AUTO DOCUMENTER MODULE                                       ║
║  FASE B: Autonomía Predictiva - Auto-Documentation Engine                    ║
║                                                                              ║
║  Features:                                                                   ║
║  • Auto-generate docstrings from function signatures                         ║
║  • Detect API changes and suggest README updates                             ║
║  • Auto-generate CHANGELOG from git commits                                  ║
║  • Keep API documentation in sync                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ast
import asyncio
import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import config
from .logger import get_logger

logger = get_logger(__name__)

# ───────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ───────────────────────────────────────────────────────────────────────────────


@dataclass
class DocstringTemplate:
    """Template for generating docstrings."""

    style: str  # google, numpy, sphinx
    sections: Dict[str, str] = field(default_factory=dict)

    def format_param(
        self, name: str, type_hint: str = "", description: str = ""
    ) -> str:
        if self.style == "google":
            type_str = f" ({type_hint})" if type_hint else ""
            return f"    {name}{type_str}: {description}"
        elif self.style == "numpy":
            type_str = f" : {type_hint}" if type_hint else ""
            return f"    {name}{type_str}\n        {description}"
        else:  # sphinx
            type_str = f" :type {name}: {type_hint}\n" if type_hint else ""
            return f"    :param {name}: {description}\n{type_str}"

    def format_return(self, type_hint: str = "", description: str = "") -> str:
        if self.style == "google":
            type_str = f" ({type_hint})" if type_hint else ""
            return (
                f"    {type_str}: {description}" if type_str else f"    {description}"
            )
        elif self.style == "numpy":
            type_str = f" : {type_hint}" if type_hint else ""
            return f"Returns{type_str}\n    {description}"
        else:  # sphinx
            type_str = f" :rtype: {type_hint}\n" if type_hint else ""
            return f"    :return: {description}\n{type_str}"


@dataclass
class FunctionInfo:
    """Information extracted from a function."""

    name: str
    line_start: int
    line_end: int
    col_offset: int
    args: List[Dict[str, str]] = field(default_factory=list)
    returns: Optional[str] = None
    has_docstring: bool = False
    existing_docstring: str = ""
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    complexity_score: int = 0  # Cyclomatic complexity


@dataclass
class APIDiff:
    """Represents a change in the API."""

    type: str  # added, removed, modified
    category: str  # function, class, parameter, return_type
    name: str
    file_path: str
    line_number: int
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    description: str = ""


@dataclass
class DocumentationTask:
    """Task for documentation maintenance."""

    id: str
    type: str  # generate_docstring, update_readme, update_changelog, sync_api_docs
    file_path: str
    priority: str  # high, medium, low
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Dict = field(default_factory=dict)
    error: Optional[str] = None


# ───────────────────────────────────────────────────────────────────────────────
# AST ANALYZER
# ───────────────────────────────────────────────────────────────────────────────


class ASTAnalyzer(ast.NodeVisitor):
    """Analyzes Python source code using AST."""

    def __init__(self, source: str, file_path: str = ""):
        self.source = source
        self.file_path = file_path
        self.functions: List[FunctionInfo] = []
        self.classes: List[Dict] = []
        self.current_class: Optional[str] = None
        self.imports: List[Dict] = []
        self.lines = source.split("\n")

    def analyze(self) -> Dict:
        """Run full analysis."""
        try:
            tree = ast.parse(self.source)
            self.visit(tree)
            return {
                "functions": [asdict(f) for f in self.functions],
                "classes": self.classes,
                "imports": self.imports,
                "file_path": self.file_path,
            }
        except SyntaxError as e:
            logger.warning(f"Syntax error in {self.file_path}: {e}")
            return {"functions": [], "classes": [], "imports": [], "error": str(e)}

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(
                {
                    "type": "import",
                    "name": alias.name,
                    "asname": alias.asname,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports.append(
                {
                    "type": "from",
                    "module": node.module,
                    "name": alias.name,
                    "asname": alias.asname,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        self.current_class = node.name

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item, is_method=True)
                methods.append(asdict(method_info))

        self.classes.append(
            {
                "name": node.name,
                "line_start": node.lineno,
                "line_end": node.end_lineno
                if hasattr(node, "end_lineno")
                else node.lineno,
                "bases": [ast.unparse(base) for base in node.bases]
                if hasattr(ast, "unparse")
                else [],
                "methods": methods,
                "docstring": ast.get_docstring(node) or "",
            }
        )

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        self._process_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._process_function(node, is_async=True)
        self.generic_visit(node)

    def _process_function(self, node, is_async: bool):
        func_info = self._extract_function_info(node, is_async=is_async)
        self.functions.append(func_info)

    def _extract_function_info(
        self, node, is_async: bool = False, is_method: bool = False
    ) -> FunctionInfo:
        """Extract detailed function information."""
        # Get docstring
        docstring = ast.get_docstring(node)
        has_docstring = docstring is not None and len(docstring.strip()) > 0

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                if hasattr(ast, "unparse"):
                    decorators.append(ast.unparse(decorator))
                elif isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Attribute):
                    decorators.append(
                        f"{ast.unparse(decorator.value)}.{decorator.attr}"
                        if hasattr(ast, "unparse")
                        else decorator.attr
                    )
            except:
                pass

        # Extract arguments with type hints
        args = []
        arg_list = node.args

        # Handle different Python versions
        all_args = []
        if arg_list.posonlyargs:
            all_args.extend([(a, True) for a in arg_list.posonlyargs])
        all_args.extend([(a, False) for a in arg_list.args])
        if arg_list.kwonlyargs:
            all_args.extend([(a, False) for a in arg_list.kwonlyargs])

        for arg, is_posonly in all_args:
            arg_info = {
                "name": arg.arg,
                "type_hint": "",
                "default": None,
                "is_posonly": is_posonly,
                "is_kwonly": arg in arg_list.kwonlyargs,
            }

            if arg.annotation:
                try:
                    arg_info["type_hint"] = (
                        ast.unparse(arg.annotation)
                        if hasattr(ast, "unparse")
                        else str(arg.annotation)
                    )
                except:
                    pass

            # Try to find default value
            defaults = list(arg_list.defaults)
            kw_defaults = list(arg_list.kw_defaults)

            # This is a simplified approach - in real code we'd match defaults to args
            args.append(arg_info)

        # Special handling for 'self' and 'cls' in methods
        if is_method and args and args[0]["name"] in ("self", "cls"):
            args[0]["is_special"] = True

        # Extract return type
        returns = None
        if node.returns:
            try:
                returns = (
                    ast.unparse(node.returns)
                    if hasattr(ast, "unparse")
                    else str(node.returns)
                )
            except:
                pass

        # Calculate complexity (simplified)
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.comprehension,
                ),
            ):
                complexity += 1

        return FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
            col_offset=node.col_offset,
            args=args,
            returns=returns,
            has_docstring=has_docstring,
            existing_docstring=docstring or "",
            decorators=decorators,
            is_async=is_async,
            is_method=is_method,
            class_name=self.current_class,
            complexity_score=complexity,
        )


# ───────────────────────────────────────────────────────────────────────────────
# DOCSTRING GENERATOR
# ───────────────────────────────────────────────────────────────────────────────


class DocstringGenerator:
    """Generates docstrings based on function analysis."""

    TEMPLATES = {
        "google": """{summary}

{args_section}
{returns_section}
{raises_section}
{example_section}""",
        "numpy": """{summary}

{args_section}
{returns_section}
{raises_section}
{example_section}""",
        "sphinx": """{summary}

{args_section}
{returns_section}
{raises_section}
{example_section}""",
    }

    def __init__(self, style: str = "google", include_types: bool = True):
        self.style = style if style in self.TEMPLATES else "google"
        self.include_types = include_types
        self.template = DocstringTemplate(style=style)

    def generate(self, func_info: FunctionInfo, context: Dict = None) -> str:
        """Generate docstring for a function."""
        context = context or {}

        # Generate summary based on function name
        summary = self._generate_summary(func_info)

        # Generate Args section
        args_section = self._generate_args_section(func_info)

        # Generate Returns section
        returns_section = self._generate_returns_section(func_info)

        # Generate Raises section (if applicable)
        raises_section = self._generate_raises_section(func_info, context)

        # Generate Example section
        example_section = self._generate_example_section(func_info)

        # Combine based on style
        docstring = self.TEMPLATES[self.style].format(
            summary=summary,
            args_section=args_section,
            returns_section=returns_section,
            raises_section=raises_section,
            example_section=example_section,
        )

        # Clean up extra whitespace
        lines = docstring.strip().split("\n")
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned_lines)

    def _generate_summary(self, func_info: FunctionInfo) -> str:
        """Generate function summary from name."""
        name = func_info.name

        # Common naming patterns
        patterns = {
            r"^get_(.+)": lambda m: f"Retrieve the {m.group(1).replace('_', ' ')}.",
            r"^set_(.+)": lambda m: f"Set the {m.group(1).replace('_', ' ')}.",
            r"^is_(.+)": lambda m: f"Check if {m.group(1).replace('_', ' ')}.",
            r"^has_(.+)": lambda m: f"Check if has {m.group(1).replace('_', ' ')}.",
            r"^create_(.+)": lambda m: f"Create a new {m.group(1).replace('_', ' ')}.",
            r"^delete_(.+)": lambda m: f"Delete the {m.group(1).replace('_', ' ')}.",
            r"^update_(.+)": lambda m: f"Update the {m.group(1).replace('_', ' ')}.",
            r"^load_(.+)": lambda m: f"Load {m.group(1).replace('_', ' ')} from source.",
            r"^save_(.+)": lambda m: f"Save {m.group(1).replace('_', ' ')} to destination.",
            r"^parse_(.+)": lambda m: f"Parse {m.group(1).replace('_', ' ')} from input.",
            r"^format_(.+)": lambda m: f"Format {m.group(1).replace('_', ' ')} for output.",
            r"^validate_(.+)": lambda m: f"Validate {m.group(1).replace('_', ' ')}.",
            r"^calc(?:ulate)?_(.+)": lambda m: f"Calculate {m.group(1).replace('_', ' ')}.",
            r"^convert_(.+)_to_(.+)": lambda m: f"Convert {m.group(1).replace('_', ' ')} to {m.group(2).replace('_', ' ')}.",
            r"^handle_(.+)": lambda m: f"Handle {m.group(1).replace('_', ' ')} event/action.",
            r"^on_(.+)": lambda m: f"Callback for {m.group(1).replace('_', ' ')} event.",
            r"^build_(.+)": lambda m: f"Build and return {m.group(1).replace('_', ' ')}.",
            r"^init(?:ialize)?": lambda m: "Initialize the instance.",
            r"^__init__": lambda m: "Initialize the instance.",
            r"^__str__": lambda m: "Return string representation.",
            r"^__repr__": lambda m: "Return detailed string representation.",
            r"^__call__": lambda m: "Make instance callable.",
        }

        for pattern, formatter in patterns.items():
            if re.match(pattern, name):
                return formatter(re.match(pattern, name))

        # Default: convert snake_case to sentence
        words = name.replace("_", " ").split()
        if words:
            return f"{words[0].capitalize()} {' '.join(words[1:])}."

        return f"Execute {name}."

    def _generate_args_section(self, func_info: FunctionInfo) -> str:
        """Generate Args/Parameters section."""
        if not func_info.args:
            return ""

        # Filter out 'self' and 'cls' for methods
        args = [a for a in func_info.args if not a.get("is_special", False)]

        if not args:
            return ""

        if self.style == "google":
            lines = ["Args:"]
            for arg in args:
                name = arg["name"]
                type_hint = arg.get("type_hint", "")
                if type_hint and self.include_types:
                    lines.append(f"    {name} ({type_hint}): Description.")
                else:
                    lines.append(f"    {name}: Description.")
            return "\n".join(lines)

        elif self.style == "numpy":
            lines = ["Parameters", "----------"]
            for arg in args:
                name = arg["name"]
                type_hint = arg.get("type_hint", "")
                if type_hint and self.include_types:
                    lines.append(f"{name} : {type_hint}")
                else:
                    lines.append(f"{name}")
                lines.append("    Description.")
            return "\n".join(lines)

        else:  # sphinx
            lines = []
            for arg in args:
                name = arg["name"]
                type_hint = arg.get("type_hint", "")
                if type_hint and self.include_types:
                    lines.append(f":param {name}: Description.")
                    lines.append(f":type {name}: {type_hint}")
                else:
                    lines.append(f":param {name}: Description.")
            return "\n".join(lines)

    def _generate_returns_section(self, func_info: FunctionInfo) -> str:
        """Generate Returns section."""
        returns = func_info.returns

        if self.style == "google":
            if returns and self.include_types:
                return f"Returns:\n    {returns}: Description of return value."
            else:
                return "Returns:\n    Description of return value."

        elif self.style == "numpy":
            if returns and self.include_types:
                return f"Returns\n-------\n{returns}\n    Description of return value."
            else:
                return "Returns\n-------\n    Description of return value."

        else:  # sphinx
            if returns and self.include_types:
                return f":return: Description of return value.\n:rtype: {returns}"
            else:
                return ":return: Description of return value."

    def _generate_raises_section(self, func_info: FunctionInfo, context: Dict) -> str:
        """Generate Raises section based on context."""
        # This would ideally analyze the function body for raise statements
        # For now, return empty or check context
        exceptions = context.get("common_exceptions", [])

        if not exceptions:
            return ""

        if self.style == "google":
            lines = ["Raises:"]
            for exc in exceptions:
                lines.append(f"    {exc}: When {exc.lower()} occurs.")
            return "\n".join(lines)

        elif self.style == "numpy":
            lines = ["Raises", "------"]
            for exc in exceptions:
                lines.append(f"{exc}")
                lines.append(f"    When {exc.lower()} occurs.")
            return "\n".join(lines)

        else:  # sphinx
            lines = []
            for exc in exceptions:
                lines.append(f":raises {exc}: When {exc.lower()} occurs.")
            return "\n".join(lines)

    def _generate_example_section(self, func_info: FunctionInfo) -> str:
        """Generate Example section."""
        # Only add examples for public methods/functions
        if func_info.name.startswith("_"):
            return ""

        if self.style == "google":
            return "\nExample:\n    >>> result = {}()\n    >>> print(result)".format(
                func_info.name
            )

        elif self.style == "numpy":
            return "\nExamples\n--------\n>>> result = {}()\n>>> print(result)".format(
                func_info.name
            )

        else:  # sphinx
            return "\n.. code-block:: python\n\n    >>> result = {}()\n    >>> print(result)".format(
                func_info.name
            )

    def insert_docstring(
        self, source: str, func_info: FunctionInfo, new_docstring: str
    ) -> str:
        """Insert docstring into source code."""
        lines = source.split("\n")

        # Find the line with function definition
        func_line_idx = func_info.line_start - 1

        # Find insertion point (after function definition line)
        insert_idx = func_line_idx + 1

        # Get base indentation
        func_line = lines[func_line_idx]
        base_indent = len(func_line) - len(func_line.lstrip())
        body_indent = base_indent + 4

        # Format docstring with proper indentation
        docstring_lines = new_docstring.split("\n")
        formatted_docstring = ['"""']

        for i, line in enumerate(docstring_lines):
            if i == 0:
                # First line of docstring
                formatted_docstring.append(" " * body_indent + line)
            elif line.strip():
                formatted_docstring.append(" " * body_indent + line)
            else:
                formatted_docstring.append("")  # Empty line

        formatted_docstring.append(" " * body_indent + '"""')

        # Insert into source
        new_lines = lines[:insert_idx] + formatted_docstring + [""] + lines[insert_idx:]

        return "\n".join(new_lines)


# ───────────────────────────────────────────────────────────────────────────────
# API CHANGE DETECTOR
# ───────────────────────────────────────────────────────────────────────────────


class APIChangeDetector:
    """Detects changes in public API."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".Lilith" / "api_snapshots"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, project_path: Path, api_state: Dict):
        """Save current API state."""
        project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:12]
        snapshot_file = self.storage_path / f"{project_hash}.json"

        snapshot = {
            "project_path": str(project_path),
            "timestamp": datetime.now().isoformat(),
            "api_state": api_state,
        }

        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        logger.debug(f"API snapshot saved: {snapshot_file}")

    def load_snapshot(self, project_path: Path) -> Optional[Dict]:
        """Load previous API state."""
        project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:12]
        snapshot_file = self.storage_path / f"{project_hash}.json"

        if not snapshot_file.exists():
            return None

        with open(snapshot_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def detect_changes(self, project_path: Path, current_api: Dict) -> List[APIDiff]:
        """Detect changes between current and previous API state."""
        previous = self.load_snapshot(project_path)

        if previous is None:
            # First run - save and return empty
            self.save_snapshot(project_path, current_api)
            return []

        previous_api = previous.get("api_state", {})
        changes = []

        # Compare functions
        prev_funcs = {
            f"{f['file_path']}::{f['name']}": f
            for f in previous_api.get("functions", [])
        }
        curr_funcs = {
            f"{f['file_path']}::{f['name']}": f
            for f in current_api.get("functions", [])
        }

        # Detect added functions
        for key, func in curr_funcs.items():
            if key not in prev_funcs:
                changes.append(
                    APIDiff(
                        type="added",
                        category="function",
                        name=func["name"],
                        file_path=func["file_path"],
                        line_number=func["line_start"],
                        new_signature=self._get_signature(func),
                        description=f"New function added: {func['name']}",
                    )
                )

        # Detect removed functions
        for key, func in prev_funcs.items():
            if key not in curr_funcs:
                changes.append(
                    APIDiff(
                        type="removed",
                        category="function",
                        name=func["name"],
                        file_path=func["file_path"],
                        line_number=func["line_start"],
                        old_signature=self._get_signature(func),
                        description=f"Function removed: {func['name']}",
                    )
                )

        # Detect modified functions
        for key in curr_funcs:
            if key in prev_funcs:
                prev_sig = self._get_signature(prev_funcs[key])
                curr_sig = self._get_signature(curr_funcs[key])

                if prev_sig != curr_sig:
                    changes.append(
                        APIDiff(
                            type="modified",
                            category="function",
                            name=curr_funcs[key]["name"],
                            file_path=curr_funcs[key]["file_path"],
                            line_number=curr_funcs[key]["line_start"],
                            old_signature=prev_sig,
                            new_signature=curr_sig,
                            description=f"Function signature changed: {curr_funcs[key]['name']}",
                        )
                    )

        # Save current state
        self.save_snapshot(project_path, current_api)

        return changes

    def _get_signature(self, func: Dict) -> str:
        """Generate function signature string."""
        args_str = ", ".join(
            [
                f"{a['name']}: {a.get('type_hint', 'Any')}"
                if a.get("type_hint")
                else a["name"]
                for a in func.get("args", [])
            ]
        )

        ret = func.get("returns", "")
        if ret:
            return f"{func['name']}({args_str}) -> {ret}"
        return f"{func['name']}({args_str})"


# ───────────────────────────────────────────────────────────────────────────────
# CHANGELOG GENERATOR
# ───────────────────────────────────────────────────────────────────────────────


class ChangelogGenerator:
    """Generates CHANGELOG from git commits."""

    CONVENTIONAL_TYPES = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "docs": "Documentation",
        "style": "Styles",
        "refactor": "Code Refactoring",
        "perf": "Performance Improvements",
        "test": "Tests",
        "chore": "Chores",
        "ci": "CI/CD",
        "build": "Build System",
        "revert": "Reverts",
    }

    def __init__(self):
        pass

    async def generate_from_git(
        self, project_path: Path, since: Optional[str] = None
    ) -> str:
        """Generate changelog from git log."""
        import subprocess

        cmd = ["git", "log", "--pretty=format:%H|%s|%b|%an|%ad", "--date=short"]
        if since:
            cmd.extend(["--since", since])

        try:
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, encoding="utf-8"
            )

            if result.returncode != 0:
                logger.warning(f"Git log failed: {result.stderr}")
                return ""

            commits = self._parse_commits(result.stdout)
            return self._format_changelog(commits)

        except Exception as e:
            logger.error(f"Error generating changelog: {e}")
            return ""

    def _parse_commits(self, git_output: str) -> List[Dict]:
        """Parse git log output."""
        commits = []

        for line in git_output.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            hash_val, subject, body, author, date = parts

            # Parse conventional commit
            commit_type, scope, message = self._parse_conventional(subject)

            commits.append(
                {
                    "hash": hash_val[:7],
                    "type": commit_type,
                    "scope": scope,
                    "message": message,
                    "body": body,
                    "author": author,
                    "date": date,
                }
            )

        return commits

    def _parse_conventional(self, subject: str) -> Tuple[str, Optional[str], str]:
        """Parse conventional commit format."""
        pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$"
        match = re.match(pattern, subject)

        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2)
            breaking = match.group(3) == "!"
            message = match.group(4)

            if breaking:
                message = f"{message} [BREAKING CHANGE]"

            return commit_type, scope, message

        return "other", None, subject

    def _format_changelog(self, commits: List[Dict]) -> str:
        """Format commits into changelog."""
        if not commits:
            return "# Changelog\n\nNo changes found.\n"

        # Group by type
        groups = defaultdict(list)
        for commit in commits:
            commit_type = commit["type"]
            category = self.CONVENTIONAL_TYPES.get(commit_type, "Other Changes")
            groups[category].append(commit)

        # Build changelog
        lines = ["# Changelog\n"]

        # Order by importance
        order = [
            "Features",
            "Bug Fixes",
            "Performance Improvements",
            "Code Refactoring",
            "Documentation",
            "Tests",
            "Build System",
            "CI/CD",
            "Styles",
            "Chores",
            "Reverts",
            "Other Changes",
        ]

        for category in order:
            if category not in groups:
                continue

            lines.append(f"\n## {category}\n")

            for commit in groups[category]:
                scope = f"**{commit['scope']}**: " if commit["scope"] else ""
                lines.append(f"- {scope}{commit['message']} ({commit['hash']})")

        return "\n".join(lines)

    async def update_changelog_file(
        self, project_path: Path, changelog_path: Optional[Path] = None
    ) -> bool:
        """Update CHANGELOG.md file."""
        if changelog_path is None:
            changelog_path = project_path / "CHANGELOG.md"

        # Generate new changelog content
        new_content = await self.generate_from_git(project_path)

        if not new_content:
            return False

        # Read existing if present
        existing_content = ""
        if changelog_path.exists():
            with open(changelog_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

        # Merge or replace
        if existing_content:
            # Keep header, replace body
            final_content = self._merge_changelogs(existing_content, new_content)
        else:
            final_content = new_content

        # Write
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        return True

    def _merge_changelogs(self, existing: str, new: str) -> str:
        """Merge existing and new changelog content."""
        # Simple merge: prepend new entries
        # In a real implementation, this would be more sophisticated

        # Extract date from new changelog for version
        today = datetime.now().strftime("%Y-%m-%d")

        merged = f"# Changelog\n\n## [Unreleased] - {today}\n"

        # Add new content (skip header)
        new_lines = new.split("\n")[2:]  # Skip "# Changelog\n"
        merged += "\n".join(new_lines)

        # Add separator and existing content (skip header)
        existing_lines = existing.split("\n")[2:]
        if existing_lines:
            merged += "\n\n---\n\n"
            merged += "\n".join(existing_lines)

        return merged


# ───────────────────────────────────────────────────────────────────────────────
# README SYNC DETECTOR
# ───────────────────────────────────────────────────────────────────────────────


class ReadmeSyncDetector:
    """Detects when README needs updates."""

    def __init__(self):
        self.checks = [
            self._check_installation,
            self._check_usage_examples,
            self._check_api_reference,
            self._check_contributing_section,
        ]

    def analyze_readme(self, readme_path: Path) -> Dict:
        """Analyze README for completeness."""
        if not readme_path.exists():
            return {
                "exists": False,
                "completeness": 0,
                "issues": ["README.md does not exist"],
                "sections_present": [],
                "sections_missing": ["all"],
            }

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        sections = {
            "title": bool(re.search(r"^#\s+\w", content, re.MULTILINE)),
            "description": len(content) > 200,
            "installation": bool(
                re.search(r"##?\s*(?:install|setup|getting started)", content)
            ),
            "usage": bool(re.search(r"##?\s*(?:usage|examples|quick start)", content)),
            "api_reference": bool(
                re.search(r"##?\s*(?:api|reference|documentation)", content)
            ),
            "contributing": bool(
                re.search(r"##?\s*(?:contributing|development)", content)
            ),
            "license": bool(re.search(r"##?\s*(?:license|licence)", content)),
            "badges": bool(re.search(r"!\[.*?\]\(.*?\)", content)),
        }

        issues = []
        if not sections["installation"]:
            issues.append("Missing 'Installation' section")
        if not sections["usage"]:
            issues.append("Missing 'Usage' section")
        if not sections["api_reference"]:
            issues.append("Missing 'API Reference' section")

        completeness = sum(sections.values()) / len(sections) * 100

        return {
            "exists": True,
            "completeness": round(completeness, 1),
            "issues": issues,
            "sections_present": [k for k, v in sections.items() if v],
            "sections_missing": [k for k, v in sections.items() if not v],
        }

    def detect_api_doc_mismatch(
        self, readme_path: Path, api_functions: List[Dict]
    ) -> List[Dict]:
        """Detect if README API docs are outdated."""
        if not readme_path.exists():
            return []

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        mismatches = []

        for func in api_functions:
            func_name = func["name"]
            # Skip private functions
            if func_name.startswith("_"):
                continue

            # Check if function is documented
            pattern = rf"`{func_name}`|##?\s*`?{func_name}`?\(|{func_name}\("
            if not re.search(pattern, content):
                mismatches.append(
                    {
                        "type": "missing_documentation",
                        "function": func_name,
                        "file": func.get("file_path", ""),
                        "line": func.get("line_start", 0),
                        "suggestion": f"Add documentation for `{func_name}`",
                    }
                )

        return mismatches

    def _check_installation(self, content: str) -> List[str]:
        """Check if installation section is complete."""
        issues = []
        if "pip install" not in content and "npm install" not in content:
            issues.append("Missing package manager installation command")
        return issues

    def _check_usage_examples(self, content: str) -> List[str]:
        """Check if usage examples are present."""
        issues = []
        if "```" not in content:
            issues.append("No code examples found")
        return issues

    def _check_api_reference(self, content: str) -> List[str]:
        """Check if API reference is present."""
        issues = []
        if not re.search(r"##?\s*(?:api|reference)", content):
            issues.append("Missing API reference section")
        return issues

    def _check_contributing_section(self, content: str) -> List[str]:
        """Check if contributing section is present."""
        issues = []
        if not re.search(r"##?\s*(?:contributing|development)", content):
            issues.append("Missing contributing section")
        return issues


# ───────────────────────────────────────────────────────────────────────────────
# AUTO DOCUMENTER ENGINE
# ───────────────────────────────────────────────────────────────────────────────


class AutoDocumenter:
    """
    Main engine for automatic documentation maintenance.

    Features:
    - Auto-generate docstrings from function signatures
    - Detect API changes and suggest README updates
    - Auto-generate CHANGELOG from git commits
    - Keep API documentation synchronized
    """

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.docstring_generator = DocstringGenerator(style="google")
        self.api_detector = APIChangeDetector()
        self.changelog_generator = ChangelogGenerator()
        self.readme_detector = ReadmeSyncDetector()

        self.tasks: List[DocumentationTask] = []
        self._lock = asyncio.Lock()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    async def scan_for_missing_docstrings(
        self, file_path: Optional[Path] = None
    ) -> List[FunctionInfo]:
        """Scan Python files for functions missing docstrings."""
        missing = []

        if file_path:
            files = [file_path] if file_path.suffix == ".py" else []
        else:
            files = list(self.project_path.rglob("*.py"))
            # Exclude common directories
            files = [
                f
                for f in files
                if not any(
                    part.startswith(".")
                    or part
                    in {
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "env",
                        "build",
                        "dist",
                    }
                    for part in f.parts
                )
            ]

        for py_file in files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()

                analyzer = ASTAnalyzer(
                    source, str(py_file.relative_to(self.project_path))
                )
                analysis = analyzer.analyze()

                for func in analysis.get("functions", []):
                    if not func.get("has_docstring"):
                        # Convert dict back to FunctionInfo
                        func_info = FunctionInfo(**func)
                        # Skip simple getters/setters and private functions (optional)
                        if not func_info.name.startswith("_"):
                            missing.append(func_info)

            except Exception as e:
                logger.warning(f"Error scanning {py_file}: {e}")

        return missing

    async def generate_docstring_for_function(
        self, func_info: FunctionInfo, context: Dict = None
    ) -> str:
        """Generate docstring for a specific function."""
        return self.docstring_generator.generate(func_info, context)

    async def apply_docstring(
        self, file_path: Path, func_info: FunctionInfo, docstring: str
    ) -> bool:
        """Apply generated docstring to source file."""
        try:
            full_path = (
                self.project_path / file_path
                if not file_path.is_absolute()
                else file_path
            )

            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()

            new_source = self.docstring_generator.insert_docstring(
                source, func_info, docstring
            )

            # Backup original
            backup_path = full_path.with_suffix(".py.bak")
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(source)

            # Write new source
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_source)

            logger.info(f"Docstring applied to {func_info.name} in {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error applying docstring: {e}")
            return False

    async def analyze_api_changes(self) -> List[APIDiff]:
        """Analyze and detect API changes."""
        # Collect current API state
        current_api = {"functions": [], "classes": []}

        py_files = list(self.project_path.rglob("*.py"))
        py_files = [
            f
            for f in py_files
            if not any(
                part.startswith(".")
                or part in {"node_modules", "__pycache__", "venv", ".venv"}
                for part in f.parts
            )
        ]

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()

                analyzer = ASTAnalyzer(
                    source, str(py_file.relative_to(self.project_path))
                )
                analysis = analyzer.analyze()

                # Only include public functions
                for func in analysis.get("functions", []):
                    if not func["name"].startswith("_"):
                        current_api["functions"].append(func)

                current_api["classes"].extend(analysis.get("classes", []))

            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")

        # Detect changes
        changes = self.api_detector.detect_changes(self.project_path, current_api)

        return changes

    async def update_changelog(self) -> bool:
        """Update CHANGELOG.md with recent commits."""
        changelog_path = self.project_path / "CHANGELOG.md"
        return await self.changelog_generator.update_changelog_file(
            self.project_path, changelog_path
        )

    async def check_readme_completeness(self) -> Dict:
        """Check README.md for completeness."""
        readme_path = self.project_path / "README.md"
        return self.readme_detector.analyze_readme(readme_path)

    async def get_readme_api_mismatches(self) -> List[Dict]:
        """Get list of API functions not documented in README."""
        readme_path = self.project_path / "README.md"

        # Collect public API
        public_api = []
        py_files = list(self.project_path.rglob("*.py"))
        py_files = [
            f for f in py_files if not any(part.startswith(".") for part in f.parts)
        ]

        for py_file in py_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()

                analyzer = ASTAnalyzer(
                    source, str(py_file.relative_to(self.project_path))
                )
                analysis = analyzer.analyze()
                public_api.extend(analysis.get("functions", []))
            except:
                pass

        return self.readme_detector.detect_api_doc_mismatch(readme_path, public_api)

    # ═══════════════════════════════════════════════════════════════════════════
    # TASK MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_task(
        self, task_type: str, file_path: str, priority: str = "medium"
    ) -> DocumentationTask:
        """Create a new documentation task."""
        task_id = hashlib.md5(
            f"{task_type}:{file_path}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        task = DocumentationTask(
            id=task_id, type=task_type, file_path=file_path, priority=priority
        )

        async with self._lock:
            self.tasks.append(task)

        return task

    async def get_pending_tasks(self) -> List[DocumentationTask]:
        """Get list of pending tasks."""
        async with self._lock:
            return [t for t in self.tasks if t.status == "pending"]

    async def execute_task(self, task: DocumentationTask) -> bool:
        """Execute a documentation task."""
        task.status = "in_progress"

        try:
            if task.type == "generate_docstring":
                # Parse file and find function
                file_path = Path(task.file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                analyzer = ASTAnalyzer(source, str(file_path))
                analysis = analyzer.analyze()

                # Find first function without docstring
                for func_dict in analysis.get("functions", []):
                    if not func_dict.get("has_docstring"):
                        func_info = FunctionInfo(**func_dict)
                        docstring = await self.generate_docstring_for_function(
                            func_info
                        )
                        success = await self.apply_docstring(
                            file_path, func_info, docstring
                        )

                        task.result = {
                            "function": func_info.name,
                            "docstring": docstring,
                            "success": success,
                        }
                        task.status = "completed" if success else "failed"
                        return success

            elif task.type == "update_changelog":
                success = await self.update_changelog()
                task.result = {"success": success}
                task.status = "completed" if success else "failed"
                return success

            elif task.type == "update_readme":
                mismatches = await self.get_readme_api_mismatches()
                task.result = {"mismatches": mismatches}
                task.status = "completed"
                return True

            task.status = "completed"
            return True

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Task {task.id} failed: {e}")
            return False

    async def auto_document_project(self) -> Dict:
        """Run full auto-documentation on project."""
        results = {
            "docstrings_added": 0,
            "api_changes": [],
            "changelog_updated": False,
            "readme_issues": [],
            "tasks_created": [],
        }

        # 1. Find and document missing docstrings
        missing = await self.scan_for_missing_docstrings()
        for func_info in missing[:10]:  # Limit to 10 per run
            task = await self.create_task(
                "generate_docstring",
                str(self.project_path / func_info.file_path),
                priority="medium",
            )
            await self.execute_task(task)
            if task.status == "completed":
                results["docstrings_added"] += 1
            results["tasks_created"].append(asdict(task))

        # 2. Detect API changes
        changes = await self.analyze_api_changes()
        results["api_changes"] = [asdict(c) for c in changes]

        # 3. Update changelog
        results["changelog_updated"] = await self.update_changelog()

        # 4. Check README
        readme_check = await self.check_readme_completeness()
        results["readme_issues"] = readme_check.get("issues", [])

        return results


# ───────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ───────────────────────────────────────────────────────────────────────────────

_auto_documenter: Optional[AutoDocumenter] = None


def get_auto_documenter(project_path: Optional[Path] = None) -> AutoDocumenter:
    """Get or create AutoDocumenter instance."""
    global _auto_documenter
    if _auto_documenter is None:
        _auto_documenter = AutoDocumenter(project_path)
    return _auto_documenter


async def initialize_documenter(project_path: Optional[str] = None):
    """Initialize the auto documenter."""
    path = Path(project_path) if project_path else Path.cwd()
    documenter = get_auto_documenter(path)
    logger.info(f"AutoDocumenter initialized for {path}")
    return documenter


# Export public API
__all__ = [
    "AutoDocumenter",
    "DocstringGenerator",
    "ASTAnalyzer",
    "APIChangeDetector",
    "ChangelogGenerator",
    "ReadmeSyncDetector",
    "FunctionInfo",
    "APIDiff",
    "DocumentationTask",
    "get_auto_documenter",
    "initialize_documenter",
]
