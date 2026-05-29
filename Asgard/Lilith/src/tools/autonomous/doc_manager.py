"""
DocManager - Documentation generation for Lilith
Handles: README generation, docstring creation, API docs, code documentation
"""
import ast
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DocManager:
    """
    Autonomous tool for documentation generation.

    Capabilities:
    - generate_readme: Create README.md from project analysis
    - add_docstrings: Add missing docstrings to functions/classes
    - generate_api_docs: Generate API documentation from code
    - document_module: Document an entire module
    - update_changelog: Update CHANGELOG.md
    - check_doc_coverage: Check documentation coverage
    """

    def __init__(self):
        self.doc_templates = {
            "readme": self._get_readme_template(),
            "function": self._get_function_doc_template(),
            "class": self._get_class_doc_template(),
            "module": self._get_module_doc_template(),
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute documentation operation

        Args:
            action: The doc operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Dict with operation results
        """
        try:
            if action == "generate_readme":
                return await self._generate_readme(
                    kwargs.get("project_path", "."),
                    kwargs.get("output_path", "README.md"),
                    kwargs.get("template", None),
                )
            elif action == "add_docstrings":
                return await self._add_docstrings(
                    kwargs.get("file_path"), kwargs.get("dry_run", True)
                )
            elif action == "generate_api_docs":
                return await self._generate_api_docs(
                    kwargs.get("module_path"), kwargs.get("output_path", "API.md")
                )
            elif action == "document_module":
                return await self._document_module(
                    kwargs.get("module_path"), kwargs.get("recursive", False)
                )
            elif action == "update_changelog":
                return await self._update_changelog(
                    kwargs.get("project_path", "."),
                    kwargs.get("version"),
                    kwargs.get("changes", []),
                )
            elif action == "check_doc_coverage":
                return await self._check_doc_coverage(kwargs.get("project_path", "."))
            else:
                return {
                    "success": False,
                    "error": f"Unknown doc action: {action}",
                    "action": action,
                }
        except Exception as e:
            logger.error(f"Doc operation failed: {e}")
            return {"success": False, "error": str(e), "action": action}

    async def _generate_readme(
        self, project_path: str, output_path: str, template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate README.md from project analysis"""
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path not found: {project_path}",
            }

        try:
            # Scan project structure
            from src.tools.autonomous.project_scanner import ProjectScanner

            scanner = ProjectScanner()
            scan_result = await scanner.execute("scan", project_path=str(project_path))

            if not scan_result.get("success"):
                return scan_result

            project_info = scan_result

            # Generate README content
            readme_content = self._build_readme_content(project_info, template)

            output_file = project_path / output_path

            # Check if README already exists
            if output_file.exists():
                return {
                    "success": False,
                    "error": f"README already exists: {output_file}",
                    "suggestion": "Use overwrite=True to replace",
                    "preview": readme_content[:1000],
                }

            # Write README
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(readme_content)

            return {
                "success": True,
                "output_path": str(output_file),
                "content_length": len(readme_content),
                "sections_generated": self._count_sections(readme_content),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_readme_content(self, project_info: Dict, template: Optional[str]) -> str:
        """Build README content from project info"""
        project_name = project_info.get("project_name", "Project")
        project_type = project_info.get("project_type", "Unknown")
        description = project_info.get("description", "")

        lines = [
            f"# {project_name}",
            "",
            f"{description}",
            "",
            "## Overview",
            "",
            f"This is a {project_type} project.",
            "",
        ]

        # Add features section if detectable
        frameworks = project_info.get("frameworks", [])
        if frameworks:
            lines.extend(
                [
                    "## Features",
                    "",
                    f"- Built with {', '.join(frameworks)}",
                    "",
                ]
            )

        # Add installation section
        dependencies = project_info.get("dependencies", [])
        if dependencies:
            lines.extend(
                [
                    "## Installation",
                    "",
                    "```bash",
                ]
            )

            if "requirements.txt" in str(dependencies):
                lines.append("pip install -r requirements.txt")
            elif "package.json" in str(dependencies):
                lines.append("npm install")

            lines.extend(
                [
                    "```",
                    "",
                ]
            )

        # Add usage section
        entry_points = project_info.get("entry_points", [])
        if entry_points:
            lines.extend(
                [
                    "## Usage",
                    "",
                    "```bash",
                ]
            )
            for ep in entry_points[:3]:
                lines.append(f"python {ep}")
            lines.extend(
                [
                    "```",
                    "",
                ]
            )

        # Add project structure
        lines.extend(
            [
                "## Project Structure",
                "",
                "```",
            ]
        )

        # Add directory tree (simplified)
        structure = project_info.get("structure", {})
        lines.append(f"{project_name}/")
        for dir_name in structure.get("directories", [])[:10]:
            lines.append(f"  {dir_name}/")
        for file_name in structure.get("files", [])[:10]:
            lines.append(f"  {file_name}")

        lines.extend(
            [
                "```",
                "",
            ]
        )

        # Add contributing section
        lines.extend(
            [
                "## Contributing",
                "",
                "1. Fork the repository",
                "2. Create a feature branch",
                "3. Commit your changes",
                "4. Push to the branch",
                "5. Create a Pull Request",
                "",
            ]
        )

        # Add license placeholder
        lines.extend(
            [
                "## License",
                "",
                "[Add your license information here]",
                "",
            ]
        )

        return "\n".join(lines)

    def _count_sections(self, content: str) -> int:
        """Count number of sections in markdown"""
        return len(re.findall(r"^## ", content, re.MULTILINE))

    async def _add_docstrings(
        self, file_path: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Add missing docstrings to functions and classes"""
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Find functions and classes without docstrings
            missing_docs = []
            modifications = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        missing_docs.append(
                            {
                                "type": "function",
                                "name": node.name,
                                "line": node.lineno,
                                "args": [arg.arg for arg in node.args.args],
                            }
                        )

                        if not dry_run:
                            docstring = self._generate_function_docstring(node)
                            modifications.append(
                                {
                                    "line": node.lineno,
                                    "end_line": node.body[0].lineno
                                    if node.body
                                    else node.lineno,
                                    "docstring": docstring,
                                }
                            )

                elif isinstance(node, ast.ClassDef):
                    if not ast.get_docstring(node):
                        missing_docs.append(
                            {
                                "type": "class",
                                "name": node.name,
                                "line": node.lineno,
                                "methods": [
                                    n.name
                                    for n in node.body
                                    if isinstance(n, ast.FunctionDef)
                                ],
                            }
                        )

                        if not dry_run:
                            docstring = self._generate_class_docstring(node)
                            modifications.append(
                                {
                                    "line": node.lineno,
                                    "end_line": node.body[0].lineno
                                    if node.body
                                    else node.lineno,
                                    "docstring": docstring,
                                }
                            )

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "file": str(file_path),
                    "missing_docstrings": len(missing_docs),
                    "items": missing_docs,
                }

            # Apply modifications
            if modifications:
                new_content = self._apply_docstring_modifications(
                    content, modifications
                )

                # Backup original
                backup_path = file_path.with_suffix(".py.backup")
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Write new content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return {
                    "success": True,
                    "file": str(file_path),
                    "docstrings_added": len(modifications),
                    "backup_created": str(backup_path),
                }

            return {
                "success": True,
                "file": str(file_path),
                "docstrings_added": 0,
                "message": "No missing docstrings found",
            }

        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error in file: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_function_docstring(self, node) -> str:
        """Generate docstring for a function"""
        func_name = node.name
        args = [arg.arg for arg in node.args.args if arg.arg != "self"]

        lines = ['"""', f'{func_name.replace("_", " ").title()}.', "", "Args:"]

        for arg in args:
            lines.append(f"    {arg}: Description of {arg}")

        lines.extend(["", "Returns:", "    Description of return value", '"""'])

        return "\n".join(lines)

    def _generate_class_docstring(self, node) -> str:
        """Generate docstring for a class"""
        class_name = node.name
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]

        lines = [
            '"""',
            f'{class_name.replace("_", " ").title()}.',
            "",
            "Attributes:",
            "    None",
            "",
            "Methods:",
        ]

        for method in methods[:5]:  # List first 5 methods
            lines.append(f"    {method}(): Description")

        lines.append('"""')

        return "\n".join(lines)

    def _apply_docstring_modifications(
        self, content: str, modifications: List[Dict]
    ) -> str:
        """Apply docstring modifications to content"""
        lines = content.split("\n")

        # Sort modifications by line number (descending to avoid offset issues)
        modifications.sort(key=lambda x: x["line"], reverse=True)

        for mod in modifications:
            line_idx = mod["line"] - 1
            indent = len(lines[line_idx]) - len(lines[line_idx].lstrip())
            indent_str = " " * indent

            docstring_lines = mod["docstring"].split("\n")
            formatted_docstring = "\n".join(
                indent_str + line if line else line for line in docstring_lines
            )

            # Insert after function/class definition line
            lines.insert(line_idx + 1, formatted_docstring)

        return "\n".join(lines)

    async def _generate_api_docs(
        self, module_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Generate API documentation from module"""
        module_path = Path(module_path).resolve()

        if not module_path.exists():
            return {"success": False, "error": f"Module not found: {module_path}"}

        try:
            api_docs = []
            api_docs.append(f"# API Documentation\n")
            api_docs.append(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            )

            # Scan Python files
            py_files = (
                list(module_path.rglob("*.py"))
                if module_path.is_dir()
                else [module_path]
            )

            for py_file in py_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)

                    # Document classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_doc = self._document_class(node, py_file)
                            if class_doc:
                                api_docs.append(class_doc)

                except SyntaxError:
                    continue
                except Exception as e:
                    logger.warning(f"Failed to parse {py_file}: {e}")

            # Write API docs
            output_file = Path(output_path)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(api_docs))

            return {
                "success": True,
                "output_path": str(output_file),
                "classes_documented": len(api_docs) - 2,  # Subtract header
                "files_scanned": len(py_files),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _document_class(self, node: ast.ClassDef, file_path: Path) -> str:
        """Generate documentation for a class"""
        docstring = ast.get_docstring(node) or f"{node.name} class."

        lines = [
            f"## {node.name}",
            "",
            f"**File:** `{file_path.name}`",
            "",
            docstring,
            "",
            "### Methods",
            "",
        ]

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_doc = ast.get_docstring(item) or f"{item.name} method."
                lines.extend(
                    [
                        f"#### `{item.name}()`",
                        "",
                        method_doc[:200] + "..."
                        if len(method_doc) > 200
                        else method_doc,
                        "",
                    ]
                )

        return "\n".join(lines)

    async def _document_module(
        self, module_path: str, recursive: bool = False
    ) -> Dict[str, Any]:
        """Document an entire module"""
        module_path = Path(module_path).resolve()

        if not module_path.exists():
            return {"success": False, "error": f"Module not found: {module_path}"}

        try:
            files_processed = []

            if module_path.is_file():
                files = [module_path]
            else:
                pattern = "**/*.py" if recursive else "*.py"
                files = list(module_path.glob(pattern))

            for py_file in files:
                # Generate docstrings for each file
                result = await self._add_docstrings(str(py_file), dry_run=False)
                if result.get("success"):
                    files_processed.append(
                        {
                            "file": str(py_file),
                            "docstrings_added": result.get("docstrings_added", 0),
                        }
                    )

            return {
                "success": True,
                "module_path": str(module_path),
                "files_processed": len(files_processed),
                "details": files_processed,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _update_changelog(
        self, project_path: str, version: Optional[str], changes: List[str]
    ) -> Dict[str, Any]:
        """Update CHANGELOG.md"""
        project_path = Path(project_path).resolve()
        changelog_path = project_path / "CHANGELOG.md"

        try:
            version = version or "Unreleased"
            date_str = datetime.now().strftime("%Y-%m-%d")

            new_entry = [
                f"## [{version}] - {date_str}",
                "",
            ]

            for change in changes:
                new_entry.append(f"- {change}")

            new_entry.append("")

            new_content = "\n".join(new_entry)

            if changelog_path.exists():
                # Read existing content
                with open(changelog_path, "r", encoding="utf-8") as f:
                    existing = f.read()

                # Insert after header
                if "# Changelog" in existing:
                    parts = existing.split("# Changelog", 1)
                    updated = (
                        parts[0] + "# Changelog\n\n" + new_content + parts[1].lstrip()
                    )
                else:
                    updated = "# Changelog\n\n" + new_content + existing

                with open(changelog_path, "w", encoding="utf-8") as f:
                    f.write(updated)
            else:
                # Create new changelog
                with open(changelog_path, "w", encoding="utf-8") as f:
                    f.write("# Changelog\n\n" + new_content)

            return {
                "success": True,
                "changelog_path": str(changelog_path),
                "version": version,
                "changes_added": len(changes),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_doc_coverage(self, project_path: str) -> Dict[str, Any]:
        """Check documentation coverage of project"""
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            return {"success": False, "error": f"Project not found: {project_path}"}

        try:
            total_functions = 0
            documented_functions = 0
            total_classes = 0
            documented_classes = 0

            py_files = list(project_path.rglob("*.py"))

            for py_file in py_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name.startswith("_"):
                                continue  # Skip private
                            total_functions += 1
                            if ast.get_docstring(node):
                                documented_functions += 1

                        elif isinstance(node, ast.ClassDef):
                            total_classes += 1
                            if ast.get_docstring(node):
                                documented_classes += 1

                except SyntaxError:
                    continue

            func_coverage = (
                documented_functions / total_functions if total_functions > 0 else 0
            )
            class_coverage = (
                documented_classes / total_classes if total_classes > 0 else 0
            )

            return {
                "success": True,
                "project_path": str(project_path),
                "files_analyzed": len(py_files),
                "functions": {
                    "total": total_functions,
                    "documented": documented_functions,
                    "coverage": f"{func_coverage:.1%}",
                },
                "classes": {
                    "total": total_classes,
                    "documented": documented_classes,
                    "coverage": f"{class_coverage:.1%}",
                },
                "overall_coverage": f"{(func_coverage + class_coverage) / 2:.1%}",
                "recommendations": self._generate_coverage_recommendations(
                    func_coverage, class_coverage
                ),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_coverage_recommendations(
        self, func_coverage: float, class_coverage: float
    ) -> List[str]:
        """Generate recommendations based on coverage"""
        recommendations = []

        if func_coverage < 0.5:
            recommendations.append(
                "Add docstrings to public functions (coverage below 50%)"
            )
        elif func_coverage < 0.8:
            recommendations.append("Consider adding docstrings to remaining functions")

        if class_coverage < 0.5:
            recommendations.append("Add docstrings to classes (coverage below 50%)")

        if not recommendations:
            recommendations.append("Documentation coverage is good!")

        return recommendations

    # Templates
    def _get_readme_template(self) -> str:
        return """# {project_name}

{description}

## Overview

{overview}

## Installation

```bash
{install_command}
```

## Usage

```bash
{usage_command}
```

## License

{license}
"""

    def _get_function_doc_template(self) -> str:
        return '''"""
    {description}

    Args:
        {args}

    Returns:
        {returns}

    Raises:
        {raises}
    """'''

    def _get_class_doc_template(self) -> str:
        return '''"""
    {description}

    Attributes:
        {attributes}

    Methods:
        {methods}
    """'''

    def _get_module_doc_template(self) -> str:
        return '''"""
{module_name} module.

{description}

Classes:
    {classes}

Functions:
    {functions}
"""'''
