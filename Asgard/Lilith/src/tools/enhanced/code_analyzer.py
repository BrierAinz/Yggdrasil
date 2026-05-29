"""
Lilith Code Analyzer v1.0
Provides code analysis capabilities for Python projects
Enables planning engine to understand project structure and dependencies
"""

import ast
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging for standalone use
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("CodeAnalyzer")


@dataclass
class SymbolLocation:
    """Location of a symbol (function, class, variable)"""

    file_path: str
    line_number: int
    column: int
    name: str
    symbol_type: str  # 'function', 'class', 'variable', 'import'


@dataclass
class ImportDependency:
    """Import statement and its resolution"""

    module: str
    names: List[str]  # imported names (e.g., ["sys", "os"] from "import sys, os")
    level: int  # 0=absolute, 1+=relative
    file_path: str
    line_number: int
    resolved_to: Optional[str] = None  # Path to actual file if local import


@dataclass
class FunctionInfo:
    """Information about a function"""

    name: str
    file_path: str
    line_number: int
    args: List[str]
    docstring: Optional[str]
    decorators: List[str]
    calls: List[str]  # Functions called by this function
    complexity: int = 1  # Cyclomatic complexity (1 = baseline)


@dataclass
class ClassInfo:
    """Information about a class"""

    name: str
    file_path: str
    line_number: int
    bases: List[str]  # Parent classes
    docstring: Optional[str]
    methods: List[FunctionInfo]
    decorators: List[str]


@dataclass
class FileAnalysis:
    """Complete analysis of a Python file"""

    file_path: str
    imports: List[ImportDependency]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    global_vars: List[SymbolLocation]
    complexity: int  # Rough cyclomatic complexity
    lines_of_code: int
    has_main: bool  # Has if __name__ == "__main__"


@dataclass
class ProjectGraph:
    """Complete project structure graph"""

    root_path: str
    files: List[FileAnalysis]
    total_files: int
    total_loc: int
    entry_points: List[str]  # Files with if __name__ == "__main__"
    dependency_graph: Dict[str, List[str]]  # file -> [dependent files]


class CodeAnalyzer:
    """
    Analyzes Python projects to provide structure and dependency information
    Used by planning engine to understand codebase before generating plans
    """

    def __init__(self):
        self.project_graph: Optional[ProjectGraph] = None
        logger.info("CodeAnalyzer initialized")

    def analyze_project(self, root_path: str, max_files: int = 100) -> ProjectGraph:
        """
        Analyzes a complete Python project

        Args:
            root_path: Path to project root
            max_files: Maximum files to analyze (safety limit)

        Returns:
            Complete ProjectGraph
        """
        logger.info(f"Analyzing project: {root_path}")

        root = Path(root_path)
        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")

        files_to_analyze = []
        py_files = list(root.rglob("*.py"))

        if len(py_files) > max_files:
            logger.warning(f"Too many files ({len(py_files)}), limiting to {max_files}")
            py_files = py_files[:max_files]

        file_analyses = []
        for py_file in py_files:
            try:
                analysis = self.analyze_file(str(py_file))
                file_analyses.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze {py_file}: {e}")
                continue

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(file_analyses)

        # Find entry points
        entry_points = [f.file_path for f in file_analyses if f.has_main]

        self.project_graph = ProjectGraph(
            root_path=str(root_path),
            files=file_analyses,
            total_files=len(file_analyses),
            total_loc=sum(f.lines_of_code for f in file_analyses),
            entry_points=entry_points,
            dependency_graph=dependency_graph,
        )

        logger.info(
            f"Analysis complete: {len(file_analyses)} files, {self.project_graph.total_loc} LOC"
        )
        return self.project_graph

    def analyze_file(self, file_path: str) -> FileAnalysis:
        """
        Analyzes a single Python file

        Args:
            file_path: Path to Python file

        Returns:
            FileAnalysis object
        """
        logger.debug(f"Analyzing file: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return FileAnalysis(
                file_path=file_path,
                imports=[],
                functions=[],
                classes=[],
                global_vars=[],
                complexity=0,
                lines_of_code=len(content.splitlines()),
                has_main=False,
            )

        # Extract information using AST visitors
        import_visitor = ImportVisitor(file_path)
        function_visitor = FunctionVisitor(file_path)
        class_visitor = ClassVisitor(file_path)

        import_visitor.visit(tree)
        function_visitor.visit(tree)
        class_visitor.visit(tree)

        # Check for if __name__ == "__main__"
        has_main = self._check_has_main(tree)

        # Calculate complexity
        complexity = sum(func.complexity for func in function_visitor.functions)

        return FileAnalysis(
            file_path=file_path,
            imports=import_visitor.imports,
            functions=function_visitor.functions,
            classes=class_visitor.classes,
            global_vars=[],  # Could be implemented with another visitor
            complexity=complexity,
            lines_of_code=len(content.splitlines()),
            has_main=has_main,
        )

    def find_definition(
        self, symbol_name: str, project_path: Optional[str] = None
    ) -> List[SymbolLocation]:
        """
        Find where a symbol (function/class) is defined

        Args:
            symbol_name: Name of the symbol to find
            project_path: Project root (uses cached graph if available)

        Returns:
            List of SymbolLocation where symbol is defined
        """
        if not self.project_graph and project_path:
            self.analyze_project(project_path)

        if not self.project_graph:
            logger.warning("No project graph available for find_definition")
            return []

        locations = []

        for file_analysis in self.project_graph.files:
            # Check functions
            for func in file_analysis.functions:
                if func.name == symbol_name:
                    locations.append(
                        SymbolLocation(
                            file_path=file_analysis.file_path,
                            line_number=func.line_number,
                            column=0,  # Could be extracted
                            name=symbol_name,
                            symbol_type="function",
                        )
                    )

            # Check classes
            for cls in file_analysis.classes:
                if cls.name == symbol_name:
                    locations.append(
                        SymbolLocation(
                            file_path=file_analysis.file_path,
                            line_number=cls.line_number,
                            column=0,
                            name=symbol_name,
                            symbol_type="class",
                        )
                    )

        return locations

    def find_references(
        self, symbol_name: str, project_path: Optional[str] = None
    ) -> List[SymbolLocation]:
        """
        Find all references to a symbol in the codebase
        **Note:** This is a simplified version

        Args:
            symbol_name: Name to search for
            project_path: Project root

        Returns:
            List of SymbolLocation where symbol is referenced
        """
        if not self.project_graph and project_path:
            self.analyze_project(project_path)

        if not self.project_graph:
            raise ValueError("No project graph available")

        # Simplified: just search for the name in function call lists
        # A full implementation would need more sophisticated analysis
        locations = []

        for file_analysis in self.project_graph.files:
            for func in file_analysis.functions:
                if symbol_name in func.calls:
                    # Find line numbers where symbol is called
                    # This is simplified - would need AST visitor for actual line numbers
                    locations.append(
                        SymbolLocation(
                            file_path=file_analysis.file_path,
                            line_number=0,  # Would be actual line
                            column=0,
                            name=symbol_name,
                            symbol_type="reference",
                        )
                    )

        return locations

    def get_entry_points(self) -> List[str]:
        """Returns files with if __name__ == "__main__" blocks"""
        if not self.project_graph:
            raise ValueError("No project graph available, run analyze_project first")

        return self.project_graph.entry_points

    def get_dependency_chain(self, file_path: str) -> List[str]:
        """
        Get all files that a given file depends on (transitive)

        Args:
            file_path: Path to file

        Returns:
            List of dependent file paths
        """
        if not self.project_graph:
            raise ValueError("No project graph available")

        visited = set()
        chain = []

        def dfs(current_path: str):
            if current_path in visited:
                return
            visited.add(current_path)

            dependencies = self.project_graph.dependency_graph.get(current_path, [])
            for dep in dependencies:
                dfs(dep)

            chain.append(current_path)

        dfs(file_path)
        return chain

    def _check_has_main(self, tree: ast.AST) -> bool:
        """Check if the AST has if __name__ == "__main__" block"""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if test is comparing __name__ to "__main__"
                if self._is_main_check(node.test):
                    return True
        return False

    def _is_main_check(self, node: ast.AST) -> bool:
        """Check if a node is __name__ == "__main__" comparison"""
        if isinstance(node, ast.Compare):
            # Check if comparing __name__ to "__main__"
            has_name = False
            has_main = False

            # Check left side
            if isinstance(node.left, ast.Name) and node.left.id == "__name__":
                has_name = True

            # Check comparators
            for comp in node.comparators:
                if isinstance(comp, ast.Constant) and comp.value == "__main__":
                    has_main = True

            return has_name and has_main
        return False

    def _build_dependency_graph(
        self, file_analyses: List[FileAnalysis]
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph between files based on imports

        Args:
            file_analyses: List of file analyses

        Returns:
            Dict mapping file to list of files it depends on
        """
        # First, create a map of importable module names to file paths
        module_to_file = {}
        for analysis in file_analyses:
            rel_path = os.path.relpath(analysis.file_path)
            # Convert path to module name
            module_name = rel_path.replace(os.sep, ".").rstrip(".py")
            module_to_file[module_name] = analysis.file_path

            # Also add without .py
            if module_name.endswith(".py"):
                module_to_file[module_name[:-3]] = analysis.file_path

        # Build dependency graph
        graph = {}
        for analysis in file_analyses:
            deps = []
            for imp in analysis.imports:
                # Skip stdlib and third-party for now (would need environment detection)
                if imp.level > 0:  # Relative import
                    # Resolve relative import
                    resolved = self._resolve_relative_import(imp, analysis.file_path)
                    if resolved:
                        deps.append(resolved)
                elif imp.module and imp.module in module_to_file:
                    # Local module import
                    deps.append(module_to_file[imp.module])

            graph[analysis.file_path] = list(set(deps))  # Remove duplicates

        return graph

    def _resolve_relative_import(
        self, imp: ImportDependency, file_path: str
    ) -> Optional[str]:
        """
        Resolve a relative import to an actual file path

        Args:
            imp: ImportDependency with level > 0
            file_path: File containing the import

        Returns:
            Resolved file path or None
        """
        # This is a simplified implementation
        # In practice, you'd need to handle package structure, __init__.py, etc.

        dir_path = os.path.dirname(file_path)
        for _ in range(imp.level):
            dir_path = os.path.dirname(dir_path)

        # Try to find the module
        if imp.module:
            module_path = imp.module.replace(".", os.sep)
            candidate = os.path.join(dir_path, module_path + ".py")
            if os.path.exists(candidate):
                return candidate

            # Try as package
            candidate = os.path.join(dir_path, module_path, "__init__.py")
            if os.path.exists(candidate):
                return candidate

        return None


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract imports"""

    def __init__(self, file_path: str):
        self.imports: List[ImportDependency] = []
        self.file_path = file_path

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            imp = ImportDependency(
                module=alias.name if "." in alias.name else None,
                names=[alias.name],
                level=0,
                file_path=self.file_path,
                line_number=node.lineno,
            )
            self.imports.append(imp)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        names = [alias.name for alias in node.names]
        imp = ImportDependency(
            module=node.module,
            names=names,
            level=node.level if node.level is not None else 0,
            file_path=self.file_path,
            line_number=node.lineno,
        )
        self.imports.append(imp)
        self.generic_visit(node)


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to extract functions"""

    def __init__(self, file_path: str):
        self.functions: List[FunctionInfo] = []
        self.current_class: Optional[str] = None
        self.file_path = file_path

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node)
        decorators = [self._name_to_str(d) for d in node.decorator_list]

        # Simple complexity: count branches
        complexity = 1 + sum(
            1 for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While))
        )

        func_info = FunctionInfo(
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            args=args,
            docstring=docstring,
            decorators=decorators,
            calls=self._extract_calls(node),
        )
        self.functions.append(func_info)
        self.generic_visit(node)

    def _extract_calls(self, node: ast.AST) -> List[str]:
        """Extract function calls from AST"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # For method calls, store full path
                    names = []
                    current = child.func
                    while isinstance(current, ast.Attribute):
                        names.insert(0, current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        names.insert(0, current.id)
                    calls.append(".".join(names))
        return list(set(calls))  # Remove duplicates

    def _name_to_str(self, node: ast.AST) -> str:
        """Convert name node to string"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._name_to_str(node.value)}.{node.attr}"
        return str(node)


class ClassVisitor(ast.NodeVisitor):
    """AST visitor to extract classes"""

    def __init__(self, file_path: str):
        self.classes: List[ClassInfo] = []
        self.file_path = file_path

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = [self._base_to_str(base) for base in node.bases]
        docstring = ast.get_docstring(node)
        decorators = [self._name_to_str(d) for d in node.decorator_list]

        # Find methods using FunctionVisitor
        method_visitor = FunctionVisitor(self.file_path)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_visitor.visit(item)

        class_info = ClassInfo(
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            bases=bases,
            docstring=docstring,
            methods=method_visitor.functions,
            decorators=decorators,
        )
        self.classes.append(class_info)
        self.generic_visit(node)

    def _base_to_str(self, node: ast.AST) -> str:
        """Convert base class to string"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._base_to_str(node.value)}.{node.attr}"
        return str(node)

    def _name_to_str(self, node: ast.AST) -> str:
        """Convert name node to string"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._name_to_str(node.value)}.{node.attr}"
        return str(node)


# === Testing & Usage ===

if __name__ == "__main__":
    """Simple test of CodeAnalyzer"""
    import sys

    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "D:\\Proyectos\\Lilith\\Core"

    print(f"Analyzing project: {project_path}")
    print("=" * 60)

    analyzer = CodeAnalyzer()

    try:
        graph = analyzer.analyze_project(project_path, max_files=50)

        print(f"âœ“ Analyzed {graph.total_files} files")
        print(f"âœ“ Total LOC: {graph.total_loc}")
        print(f"âœ“ Entry points: {len(graph.entry_points)}")

        # Show some details
        print("\nFirst few files analyzed:")
        for i, file_analysis in enumerate(graph.files[:3], 1):
            print(f"\n{i}. {os.path.basename(file_analysis.file_path)}")
            print(f"   Functions: {len(file_analysis.functions)}")
            print(f"   Classes: {len(file_analysis.classes)}")
            print(f"   Imports: {len(file_analysis.imports)}")
            print(f"   LOC: {file_analysis.lines_of_code}")

            if file_analysis.functions:
                print(
                    f"   Function names: {[f.name for f in file_analysis.functions[:3]]}"
                )

        # Show entry points
        if graph.entry_points:
            print("\nEntry points (if __name__ == '__main__'):")
            for ep in graph.entry_points:
                print(f"  - {ep}")

        print("\nâœ“ Analysis complete!")

        # Test symbol lookup
        print("\nTesting symbol lookup...")
        definitions = analyzer.find_definition("PlanningEngine", project_path)
        if definitions:
            print(f"Found PlanningEngine in: {definitions[0].file_path}")
        else:
            print("PlanningEngine not found (expected if not in analyzed files)")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
