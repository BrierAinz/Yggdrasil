"""
GraphManager - Graph visualization and dependency analysis for Lilith
Handles: Dependency graphs, project structure visualization, metrics charts
"""
import ast
import json
import logging
import os
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Node:
    """Represents a node in the graph"""

    id: str
    label: str
    type: str  # file, class, function, module, package
    path: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    color: Optional[str] = None
    size: int = 10


@dataclass
class Edge:
    """Represents an edge between nodes"""

    source: str
    target: str
    type: str  # import, call, inherit, dependency
    weight: int = 1
    label: Optional[str] = None


@dataclass
class GraphData:
    """Complete graph data structure"""

    nodes: List[Node]
    edges: List[Edge]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "metadata": self.metadata,
        }


class GraphManager:
    """
    Autonomous tool for graph generation and visualization.

    Capabilities:
    - generate_dependency_graph: Analyze file/module dependencies
    - generate_class_diagram: UML-like class relationships
    - generate_call_graph: Function call relationships
    - generate_project_structure: Hierarchical project view
    - generate_metrics_chart: Coverage, complexity visualizations
    - generate_plan_flow: Visualize execution plan flow
    """

    def __init__(self):
        self.cache = {}
        self.max_depth = 5
        self.supported_extensions = {".py", ".js", ".ts", ".json"}

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute graph operation

        Args:
            action: The graph operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Dict with graph data
        """
        try:
            if action == "dependency_graph":
                return await self._generate_dependency_graph(
                    kwargs.get("project_path", "."),
                    kwargs.get("depth", 3),
                    kwargs.get("include_external", False),
                )
            elif action == "class_diagram":
                return await self._generate_class_diagram(
                    kwargs.get("file_path") or kwargs.get("project_path", ".")
                )
            elif action == "call_graph":
                return await self._generate_call_graph(
                    kwargs.get("file_path"), kwargs.get("function_name")
                )
            elif action == "project_structure":
                return await self._generate_project_structure(
                    kwargs.get("project_path", "."), kwargs.get("max_depth", 4)
                )
            elif action == "metrics_chart":
                return await self._generate_metrics_chart(
                    kwargs.get("project_path", "."),
                    kwargs.get("chart_type", "complexity"),
                )
            elif action == "plan_flow":
                return await self._generate_plan_flow(
                    kwargs.get("plan_id") or kwargs.get("tasks", [])
                )
            elif action == "git_history_graph":
                return await self._generate_git_history_graph(
                    kwargs.get("repo_path", "."), kwargs.get("max_commits", 20)
                )
            elif action == "coverage_heatmap":
                return await self._generate_coverage_heatmap(
                    kwargs.get("project_path", ".")
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown graph action: {action}",
                    "action": action,
                }
        except Exception as e:
            logger.error(f"Graph operation failed: {e}")
            return {"success": False, "error": str(e), "action": action}

    async def _generate_dependency_graph(
        self, project_path: str, depth: int = 3, include_external: bool = False
    ) -> Dict[str, Any]:
        """Generate file/module dependency graph"""
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            return {"success": False, "error": f"Project not found: {project_path}"}

        nodes = []
        edges = []
        processed = set()

        # Find all Python files
        py_files = list(project_path.rglob("*.py"))

        # Create file nodes
        for py_file in py_files:
            rel_path = py_file.relative_to(project_path)
            node_id = (
                str(rel_path).replace("\\", "/").replace("/", "_").replace(".py", "")
            )

            # Calculate metrics
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = len(content.split("\n"))
            except:
                lines = 0

            nodes.append(
                Node(
                    id=node_id,
                    label=rel_path.name,
                    type="file",
                    path=str(rel_path),
                    metrics={"lines": lines},
                    size=min(30, 10 + lines / 50),
                )
            )

        # Analyze imports
        for py_file in py_files:
            rel_path = py_file.relative_to(project_path)
            source_id = (
                str(rel_path).replace("\\", "/").replace("/", "_").replace(".py", "")
            )

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._add_import_edge(
                                edges,
                                source_id,
                                alias.name,
                                nodes,
                                project_path,
                                include_external,
                            )

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._add_import_edge(
                                edges,
                                source_id,
                                node.module,
                                nodes,
                                project_path,
                                include_external,
                            )

            except Exception as e:
                logger.warning(f"Failed to parse {py_file}: {e}")

        graph = GraphData(
            nodes=nodes,
            edges=edges,
            metadata={
                "type": "dependency",
                "total_files": len(nodes),
                "total_dependencies": len(edges),
                "project": project_path.name,
            },
        )

        return {"success": True, "graph": graph.to_dict(), "chart_type": "network"}

    def _add_import_edge(
        self,
        edges: List[Edge],
        source_id: str,
        import_name: str,
        nodes: List[Node],
        project_path: Path,
        include_external: bool,
    ):
        """Add import edge if target exists in project"""
        # Convert import to file path
        parts = import_name.split(".")

        # Check if it's a local import
        possible_paths = [
            project_path / "/".join(parts) / "__init__.py",
            project_path / "/".join(parts) + ".py",
        ]

        for path in possible_paths:
            if path.exists():
                target_rel = path.relative_to(project_path)
                target_id = (
                    str(target_rel)
                    .replace("\\", "/")
                    .replace("/", "_")
                    .replace(".py", "")
                )

                # Check if target node exists
                if any(n.id == target_id for n in nodes):
                    edges.append(
                        Edge(
                            source=source_id, target=target_id, type="import", weight=1
                        )
                    )
                return

        # External dependency
        if include_external:
            ext_id = f"ext_{import_name.split('.')[0]}"
            if not any(n.id == ext_id for n in nodes):
                nodes.append(
                    Node(
                        id=ext_id,
                        label=import_name.split(".")[0],
                        type="external",
                        color="#94a3b8",
                    )
                )

            edges.append(
                Edge(
                    source=source_id,
                    target=ext_id,
                    type="external",
                    weight=1,
                    label="external",
                )
            )

    async def _generate_class_diagram(self, path: str) -> Dict[str, Any]:
        """Generate class diagram from Python file(s)"""
        target_path = Path(path).resolve()

        nodes = []
        edges = []

        files = (
            [target_path] if target_path.is_file() else list(target_path.rglob("*.py"))
        )

        for py_file in files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_id = f"{py_file.stem}_{node.name}"

                        # Get methods
                        methods = [
                            n.name
                            for n in node.body
                            if isinstance(n, ast.FunctionDef)
                            and not n.name.startswith("_")
                        ][
                            :5
                        ]  # Limit to 5 public methods

                        nodes.append(
                            Node(
                                id=class_id,
                                label=node.name,
                                type="class",
                                path=str(py_file),
                                metrics={"methods": len(methods)},
                                size=20 + len(methods) * 3,
                            )
                        )

                        # Check inheritance
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                parent_id = f"{py_file.stem}_{base.id}"
                                edges.append(
                                    Edge(
                                        source=class_id,
                                        target=parent_id,
                                        type="inherit",
                                        label="extends",
                                    )
                                )

            except Exception as e:
                logger.warning(f"Failed to parse {py_file}: {e}")

        graph = GraphData(
            nodes=nodes,
            edges=edges,
            metadata={"type": "class_diagram", "total_classes": len(nodes)},
        )

        return {"success": True, "graph": graph.to_dict(), "chart_type": "hierarchy"}

    async def _generate_call_graph(
        self, file_path: Optional[str], function_name: Optional[str]
    ) -> Dict[str, Any]:
        """Generate function call graph"""
        if not file_path:
            return {"success": False, "error": "File path required"}

        target_file = Path(file_path)

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            return {"success": False, "error": str(e)}

        nodes = []
        edges = []
        call_graph = defaultdict(list)

        # Build call graph
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name

                nodes.append(
                    Node(
                        id=func_name,
                        label=func_name,
                        type="function",
                        path=str(target_file),
                        size=15,
                    )
                )

                # Find calls within this function
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            call_graph[func_name].append(child.func.id)
                            edges.append(
                                Edge(
                                    source=func_name, target=child.func.id, type="call"
                                )
                            )

        graph = GraphData(
            nodes=nodes,
            edges=edges,
            metadata={
                "type": "call_graph",
                "total_functions": len(nodes),
                "total_calls": len(edges),
            },
        )

        return {"success": True, "graph": graph.to_dict(), "chart_type": "directed"}

    async def _generate_project_structure(
        self, project_path: str, max_depth: int = 4
    ) -> Dict[str, Any]:
        """Generate hierarchical project structure graph"""
        project_path = Path(project_path).resolve()

        nodes = []
        edges = []

        def add_directory(path: Path, parent_id: Optional[str] = None, depth: int = 0):
            if depth > max_depth:
                return

            node_id = (
                str(path.relative_to(project_path)).replace("\\", "_").replace("/", "_")
                or "root"
            )

            node_type = (
                "root"
                if depth == 0
                else ("package" if (path / "__init__.py").exists() else "directory")
            )

            nodes.append(
                Node(
                    id=node_id,
                    label=path.name or project_path.name,
                    type=node_type,
                    path=str(path.relative_to(project_path)) if depth > 0 else ".",
                    size=20 - depth * 3,
                )
            )

            if parent_id:
                edges.append(Edge(source=parent_id, target=node_id, type="contains"))

            # Add children
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith(".") or item.name == "__pycache__":
                        continue

                    if item.is_dir():
                        add_directory(item, node_id, depth + 1)
                    elif item.suffix in self.supported_extensions:
                        file_id = f"{node_id}_{item.name}"
                        nodes.append(
                            Node(
                                id=file_id,
                                label=item.name,
                                type="file",
                                path=str(item.relative_to(project_path)),
                                size=8,
                            )
                        )
                        edges.append(
                            Edge(source=node_id, target=file_id, type="contains")
                        )
            except PermissionError:
                pass

        add_directory(project_path)

        graph = GraphData(
            nodes=nodes,
            edges=edges,
            metadata={
                "type": "structure",
                "total_items": len(nodes),
                "max_depth": max_depth,
            },
        )

        return {"success": True, "graph": graph.to_dict(), "chart_type": "tree"}

    async def _generate_metrics_chart(
        self, project_path: str, chart_type: str = "complexity"
    ) -> Dict[str, Any]:
        """Generate metrics visualization data"""
        project_path = Path(project_path).resolve()

        metrics = []

        if chart_type == "complexity":
            # Calculate complexity per file
            for py_file in project_path.rglob("*.py"):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)

                    # Simple complexity: count branches
                    complexity = 1
                    for node in ast.walk(tree):
                        if isinstance(
                            node, (ast.If, ast.While, ast.For, ast.ExceptHandler)
                        ):
                            complexity += 1

                    rel_path = py_file.relative_to(project_path)
                    metrics.append(
                        {
                            "label": str(rel_path),
                            "value": complexity,
                            "color": "#ef4444"
                            if complexity > 10
                            else ("#f59e0b" if complexity > 5 else "#22c55e"),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Failed to analyze {py_file}: {e}")

        elif chart_type == "lines":
            # Lines of code per file
            for py_file in project_path.rglob("*.py"):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())

                    rel_path = py_file.relative_to(project_path)
                    metrics.append(
                        {"label": str(rel_path), "value": lines, "color": "#3b82f6"}
                    )
                except:
                    pass

        return {
            "success": True,
            "chart_type": "bar",
            "data": sorted(metrics, key=lambda x: x["value"], reverse=True)[
                :20
            ],  # Top 20
            "metadata": {"type": chart_type, "total_files": len(metrics)},
        }

    async def _generate_plan_flow(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Generate execution plan flow visualization"""
        nodes = []
        edges = []

        for i, task in enumerate(tasks):
            node_id = f"task_{i}"
            status = task.get("status", "pending")

            color_map = {
                "pending": "#94a3b8",
                "running": "#3b82f6",
                "completed": "#22c55e",
                "failed": "#ef4444",
            }

            nodes.append(
                Node(
                    id=node_id,
                    label=task.get("name", f"Task {i+1}"),
                    type="task",
                    metrics={"status": status, "tool": task.get("tool", "unknown")},
                    color=color_map.get(status, "#94a3b8"),
                    size=20,
                )
            )

            # Connect sequential tasks
            if i > 0:
                edges.append(
                    Edge(
                        source=f"task_{i-1}",
                        target=node_id,
                        type="sequence",
                        label=f"step {i}",
                    )
                )

            # Connect dependencies
            for dep in task.get("dependencies", []):
                edges.append(
                    Edge(
                        source=f"task_{dep}",
                        target=node_id,
                        type="dependency",
                        label="depends",
                    )
                )

        graph = GraphData(
            nodes=nodes,
            edges=edges,
            metadata={"type": "plan_flow", "total_tasks": len(tasks)},
        )

        return {"success": True, "graph": graph.to_dict(), "chart_type": "flow"}

    async def _generate_git_history_graph(
        self, repo_path: str, max_commits: int = 20
    ) -> Dict[str, Any]:
        """Generate git commit history visualization"""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    repo_path,
                    "log",
                    f"-n{max_commits}",
                    "--pretty=format:%H|%s|%an|%ad",
                    "--date=short",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"success": False, "error": "Git command failed"}

            nodes = []
            edges = []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 3)
                    if len(parts) >= 3:
                        commits.append(
                            {
                                "hash": parts[0][:7],
                                "message": parts[1][:50],
                                "author": parts[2],
                                "date": parts[3] if len(parts) > 3 else "",
                            }
                        )

            # Create nodes for each commit
            for i, commit in enumerate(commits):
                nodes.append(
                    Node(
                        id=commit["hash"],
                        label=commit["message"],
                        type="commit",
                        metrics={"author": commit["author"], "date": commit["date"]},
                        size=15,
                    )
                )

                # Link to parent (next in list)
                if i < len(commits) - 1:
                    edges.append(
                        Edge(
                            source=commits[i + 1]["hash"],
                            target=commit["hash"],
                            type="parent",
                        )
                    )

            graph = GraphData(
                nodes=nodes,
                edges=edges,
                metadata={"type": "git_history", "total_commits": len(commits)},
            )

            return {"success": True, "graph": graph.to_dict(), "chart_type": "timeline"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _generate_coverage_heatmap(self, project_path: str) -> Dict[str, Any]:
        """Generate coverage heatmap data"""
        # Try to find coverage data
        coverage_path = Path(project_path) / ".coverage"
        coverage_json = Path(project_path) / "coverage.json"

        coverage_data = []

        if coverage_json.exists():
            try:
                with open(coverage_json, "r") as f:
                    data = json.load(f)

                for file_path, info in data.get("files", {}).items():
                    coverage_pct = info.get("summary", {}).get("percent_covered", 0)

                    # Color based on coverage
                    if coverage_pct >= 80:
                        color = "#22c55e"  # Green
                    elif coverage_pct >= 50:
                        color = "#f59e0b"  # Yellow
                    else:
                        color = "#ef4444"  # Red

                    coverage_data.append(
                        {
                            "path": file_path,
                            "coverage": coverage_pct,
                            "color": color,
                            "lines": info.get("summary", {}).get("num_statements", 0),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to parse coverage.json: {e}")

        # If no coverage data, generate placeholder
        if not coverage_data:
            for py_file in Path(project_path).rglob("*.py"):
                if "test" not in str(py_file):
                    rel_path = py_file.relative_to(project_path)
                    coverage_data.append(
                        {
                            "path": str(rel_path),
                            "coverage": 0,
                            "color": "#94a3b8",
                            "lines": 0,
                        }
                    )

        return {
            "success": True,
            "chart_type": "heatmap",
            "data": coverage_data,
            "metadata": {"type": "coverage", "total_files": len(coverage_data)},
        }
