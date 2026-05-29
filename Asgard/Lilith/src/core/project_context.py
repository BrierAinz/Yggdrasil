"""
ProjectContext - MÃ³dulo de detecciÃ³n y gestiÃ³n de proyectos para Lilith

Proporciona:
- DetecciÃ³n automÃ¡tica de proyecto basado en directorio activo
- IdentificaciÃ³n de tipo de proyecto (Python, Node.js, etc.)
- Carga de configuraciÃ³n especÃ­fica por proyecto
- Cambio automÃ¡tico de contexto
- Historial de proyectos recientes
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ProjectContext")


@dataclass
class ProjectConfig:
    """ConfiguraciÃ³n de un proyecto"""

    name: str
    path: str
    project_type: str
    detected_types: List[str]
    entry_points: List[str]
    frameworks: List[str]
    description: str
    preferred_tools: List[str]
    last_accessed: str
    access_count: int
    custom_settings: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectContext:
    """Contexto completo del proyecto actual"""

    is_project: bool
    config: Optional[ProjectConfig]
    current_directory: str
    git_root: Optional[str]
    suggested_actions: List[Dict[str, str]]
    recent_projects: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_project": self.is_project,
            "config": self.config.to_dict() if self.config else None,
            "current_directory": self.current_directory,
            "git_root": self.git_root,
            "suggested_actions": self.suggested_actions,
            "recent_projects": self.recent_projects,
        }


class ProjectTypeDetector:
    """Detector de tipos de proyecto"""

    # Patrones de detecciÃ³n por tipo
    DETECTION_PATTERNS = {
        "python": {
            "files": [
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "Pipfile",
                "setup.cfg",
            ],
            "extensions": [".py"],
            "indicators": ["__init__.py", "manage.py", "app.py", "main.py"],
        },
        "nodejs": {
            "files": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
            ],
            "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs"],
            "indicators": [
                "node_modules",
                "next.config.js",
                "vite.config.js",
                "webpack.config.js",
            ],
        },
        "rust": {
            "files": ["Cargo.toml", "Cargo.lock"],
            "extensions": [".rs"],
            "indicators": ["src/main.rs", "src/lib.rs"],
        },
        "go": {
            "files": ["go.mod", "go.sum"],
            "extensions": [".go"],
            "indicators": ["main.go", "cmd/"],
        },
        "java": {
            "files": ["pom.xml", "build.gradle", "gradlew", "settings.gradle"],
            "extensions": [".java", ".kt"],
            "indicators": ["src/main/java", "src/test/java"],
        },
        "dotnet": {
            "files": [".csproj", ".sln", "global.json"],
            "extensions": [".cs", ".fs"],
            "indicators": ["Program.cs", "Startup.cs"],
        },
        "flutter": {
            "files": ["pubspec.yaml"],
            "extensions": [".dart"],
            "indicators": ["lib/main.dart", "android/app", "ios/Runner"],
        },
        "docker": {
            "files": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
            "extensions": [],
            "indicators": [],
        },
        "terraform": {
            "files": ["main.tf", "variables.tf", "outputs.tf", ".terraform"],
            "extensions": [".tf", ".tfvars"],
            "indicators": [],
        },
        "markdown_docs": {
            "files": ["README.md", "mkdocs.yml", "docusaurus.config.js"],
            "extensions": [".md", ".mdx"],
            "indicators": ["docs/"],
        },
    }

    FRAMEWORK_PATTERNS = {
        "fastapi": {
            "files": [],
            "indicators": ["FastAPI", "fastapi"],
            "in": ["requirements.txt", "pyproject.toml"],
        },
        "django": {
            "files": ["manage.py", "settings.py"],
            "indicators": ["django"],
            "in": ["requirements.txt"],
        },
        "flask": {
            "files": [],
            "indicators": ["Flask", "flask"],
            "in": ["requirements.txt"],
        },
        "react": {
            "files": [],
            "indicators": ["react", "react-dom"],
            "in": ["package.json"],
        },
        "vue": {
            "files": ["vue.config.js"],
            "indicators": ["vue"],
            "in": ["package.json"],
        },
        "angular": {
            "files": ["angular.json"],
            "indicators": ["@angular"],
            "in": ["package.json"],
        },
        "nextjs": {
            "files": ["next.config.js", "next.config.mjs"],
            "indicators": ["next"],
            "in": ["package.json"],
        },
        "svelte": {
            "files": ["svelte.config.js"],
            "indicators": ["svelte"],
            "in": ["package.json"],
        },
        "express": {"files": [], "indicators": ["express"], "in": ["package.json"]},
        "spring": {
            "files": [],
            "indicators": ["spring-boot", "spring"],
            "in": ["pom.xml", "build.gradle"],
        },
        "laravel": {"files": ["artisan"], "indicators": [], "in": []},
        "rails": {
            "files": ["Gemfile", "Rakefile"],
            "indicators": ["rails"],
            "in": ["Gemfile"],
        },
    }

    @classmethod
    def detect(cls, path: str) -> Dict[str, Any]:
        """Detectar tipo de proyecto en un directorio"""
        detected_types = []
        frameworks = []
        entry_points = []

        path_obj = Path(path)
        if not path_obj.exists():
            return {
                "types": [],
                "frameworks": [],
                "entry_points": [],
                "is_project": False,
            }

        # Listar archivos en el directorio (no recursivo para velocidad)
        try:
            files = [f.name for f in path_obj.iterdir() if f.is_file()]
            dirs = [d.name for d in path_obj.iterdir() if d.is_dir()]
            all_items = files + dirs
        except:
            all_items = []

        # Detectar tipos
        for project_type, patterns in cls.DETECTION_PATTERNS.items():
            score = 0

            # Verificar archivos especÃ­ficos
            for file_pattern in patterns["files"]:
                if any(file_pattern in f for f in all_items):
                    score += 3

            # Verificar directorios indicadores
            for indicator in patterns["indicators"]:
                if any(indicator in d for d in all_items):
                    score += 2

            # Si hay score, es de este tipo
            if score > 0:
                detected_types.append(
                    {
                        "type": project_type,
                        "score": score,
                        "confidence": "high"
                        if score >= 5
                        else "medium"
                        if score >= 3
                        else "low",
                    }
                )

        # Ordenar por score
        detected_types.sort(key=lambda x: x["score"], reverse=True)

        # Detectar frameworks
        if detected_types:
            primary_type = detected_types[0]["type"]

            for framework, patterns in cls.FRAMEWORK_PATTERNS.items():
                found = False

                # Verificar archivos de framework
                for file_pattern in patterns["files"]:
                    if any(file_pattern in f for f in all_items):
                        found = True
                        break

                # Verificar en contenido de archivos de config
                if not found and patterns["in"]:
                    for config_file in patterns["in"]:
                        if config_file in files:
                            try:
                                with open(
                                    path_obj / config_file, "r", encoding="utf-8"
                                ) as f:
                                    content = f.read().lower()
                                    for indicator in patterns["indicators"]:
                                        if indicator.lower() in content:
                                            found = True
                                            break
                            except:
                                pass
                        if found:
                            break

                if found:
                    frameworks.append(framework)

        # Buscar entry points
        entry_point_candidates = {
            "python": ["main.py", "app.py", "manage.py", "run.py", "server.py"],
            "nodejs": ["index.js", "server.js", "app.js", "main.js"],
            "rust": ["main.rs", "lib.rs"],
            "go": ["main.go"],
            "java": ["Main.java", "Application.java"],
        }

        for type_info in detected_types:
            proj_type = type_info["type"]
            if proj_type in entry_point_candidates:
                for candidate in entry_point_candidates[proj_type]:
                    if candidate in files:
                        entry_points.append(candidate)

        return {
            "types": detected_types,
            "frameworks": frameworks,
            "entry_points": entry_points,
            "is_project": len(detected_types) > 0,
        }


class ProjectContextManager:
    """Manager de contexto de proyectos"""

    def __init__(self):
        self.storage_path = Path.home() / ".Lilith" / "projects"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.projects_file = self.storage_path / "projects.json"
        self.projects: Dict[str, ProjectConfig] = {}
        self._load_projects()

        self._current_project: Optional[str] = None

    def _load_projects(self):
        """Cargar proyectos conocidos"""
        if self.projects_file.exists():
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for proj_data in data:
                        config = ProjectConfig(**proj_data)
                        self.projects[config.path] = config
            except Exception as e:
                logger.error(f"Error loading projects: {e}")

    def _save_projects(self):
        """Guardar proyectos"""
        try:
            data = [proj.to_dict() for proj in self.projects.values()]
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving projects: {e}")

    def detect_project(self, path: str) -> Optional[ProjectConfig]:
        """Detectar proyecto en una ruta"""
        # Primero verificar si ya conocemos este proyecto
        if path in self.projects:
            config = self.projects[path]
            config.last_accessed = datetime.now().isoformat()
            config.access_count += 1
            self._save_projects()
            return config

        # Detectar nuevo proyecto
        detection = ProjectTypeDetector.detect(path)

        if not detection["is_project"]:
            return None

        # Crear config
        primary_type = (
            detection["types"][0]["type"] if detection["types"] else "unknown"
        )
        all_types = [t["type"] for t in detection["types"]]

        # Generar nombre del proyecto
        project_name = Path(path).name or "unknown"

        # DescripciÃ³n automÃ¡tica
        frameworks_str = (
            f" ({', '.join(detection['frameworks'])})"
            if detection["frameworks"]
            else ""
        )
        description = f"Proyecto {primary_type}{frameworks_str}"

        # Herramientas preferidas segÃºn tipo
        preferred_tools = self._get_preferred_tools(
            primary_type, detection["frameworks"]
        )

        config = ProjectConfig(
            name=project_name,
            path=path,
            project_type=primary_type,
            detected_types=all_types,
            entry_points=detection["entry_points"],
            frameworks=detection["frameworks"],
            description=description,
            preferred_tools=preferred_tools,
            last_accessed=datetime.now().isoformat(),
            access_count=1,
            custom_settings={},
        )

        # Guardar proyecto
        self.projects[path] = config
        self._save_projects()

        logger.info(f"New project detected: {project_name} ({primary_type})")

        return config

    def _get_preferred_tools(
        self, project_type: str, frameworks: List[str]
    ) -> List[str]:
        """Obtener herramientas preferidas segÃºn tipo de proyecto"""
        tools_map = {
            "python": [
                "FileManager",
                "CodeAnalyzer",
                "TestRunner",
                "DocManager",
                "AutoFixer",
            ],
            "nodejs": [
                "FileManager",
                "CodeAnalyzer",
                "DependencyManager",
                "TestRunner",
            ],
            "rust": ["FileManager", "CodeAnalyzer", "TestRunner"],
            "go": ["FileManager", "CodeAnalyzer", "TestRunner"],
            "java": ["FileManager", "CodeAnalyzer", "TestRunner", "DependencyManager"],
            "docker": ["FileManager", "SystemExecutor"],
            "terraform": ["FileManager", "SystemExecutor"],
        }

        tools = tools_map.get(project_type, ["FileManager", "CodeAnalyzer"])

        # AÃ±adir tools especÃ­ficas de framework
        framework_tools = {
            "fastapi": ["DocManager"],
            "django": ["DocManager"],
            "react": ["GraphManager"],
            "nextjs": ["GraphManager"],
        }

        for framework in frameworks:
            if framework in framework_tools:
                tools.extend(framework_tools[framework])

        # Eliminar duplicados manteniendo orden
        seen = set()
        return [t for t in tools if not (t in seen or seen.add(t))]

    def get_context(self, current_path: str) -> ProjectContext:
        """Obtener contexto completo para el directorio actual"""
        # Detectar proyecto
        config = self.detect_project(current_path)

        # Encontrar git root si existe
        git_root = None
        try:
            from src.core.git_context import get_git_context_manager

            git_manager = get_git_context_manager(current_path)
            git_ctx = git_manager.get_context()
            if git_ctx.is_git_repo:
                git_root = git_ctx.repo_path
        except:
            pass

        # Proyectos recientes (ordenados por Ãºltimo acceso)
        recent = sorted(
            [p.to_dict() for p in self.projects.values()],
            key=lambda x: x["last_accessed"],
            reverse=True,
        )[:5]

        # Sugerir acciones
        suggestions = self._suggest_actions(config, current_path)

        return ProjectContext(
            is_project=config is not None,
            config=config,
            current_directory=current_path,
            git_root=git_root,
            suggested_actions=suggestions,
            recent_projects=recent,
        )

    def _suggest_actions(
        self, config: Optional[ProjectConfig], path: str
    ) -> List[Dict[str, str]]:
        """Sugerir acciones basadas en el proyecto"""
        suggestions = []

        if not config:
            return suggestions

        # Sugerencias segÃºn tipo
        type_actions = {
            "python": [
                {
                    "action": "run_tests",
                    "text": "Ejecutar tests con pytest",
                    "command": "python -m pytest",
                },
                {
                    "action": "check_lint",
                    "text": "Verificar con flake8/pylint",
                    "command": "python -m flake8 .",
                },
            ],
            "nodejs": [
                {
                    "action": "install_deps",
                    "text": "Instalar dependencias",
                    "command": "npm install",
                },
                {
                    "action": "run_tests",
                    "text": "Ejecutar tests",
                    "command": "npm test",
                },
                {
                    "action": "build",
                    "text": "Build del proyecto",
                    "command": "npm run build",
                },
            ],
            "rust": [
                {
                    "action": "build",
                    "text": "Compilar con cargo",
                    "command": "cargo build",
                },
                {
                    "action": "run_tests",
                    "text": "Ejecutar tests",
                    "command": "cargo test",
                },
            ],
            "go": [
                {"action": "build", "text": "Compilar", "command": "go build ."},
                {
                    "action": "run_tests",
                    "text": "Ejecutar tests",
                    "command": "go test ./...",
                },
            ],
        }

        if config.project_type in type_actions:
            suggestions.extend(type_actions[config.project_type])

        # Sugerencias de entry points
        for entry in config.entry_points[:2]:
            if config.project_type == "python":
                suggestions.append(
                    {
                        "action": "run",
                        "text": f"Ejecutar {entry}",
                        "command": f"python {entry}",
                    }
                )
            elif config.project_type == "nodejs":
                suggestions.append(
                    {
                        "action": "run",
                        "text": f"Ejecutar {entry}",
                        "command": f"node {entry}",
                    }
                )

        return suggestions[:5]  # Limitar a 5 sugerencias

    def update_project_settings(self, path: str, settings: Dict[str, Any]) -> bool:
        """Actualizar configuraciÃ³n de un proyecto"""
        if path not in self.projects:
            return False

        config = self.projects[path]
        config.custom_settings.update(settings)
        self._save_projects()
        return True

    def get_recent_projects(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener proyectos recientes"""
        projects = sorted(
            [p.to_dict() for p in self.projects.values()],
            key=lambda x: x["last_accessed"],
            reverse=True,
        )
        return projects[:limit]


# Singleton
_project_manager: Optional[ProjectContextManager] = None


def get_project_manager() -> ProjectContextManager:
    """Obtener instancia singleton"""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectContextManager()
    return _project_manager


# === Testing ===
if __name__ == "__main__":
    print("=" * 60)
    print("ProjectContext - Test Suite")
    print("=" * 60)

    manager = get_project_manager()

    # Test 1: Detectar proyecto actual
    import os

    current_dir = os.getcwd()

    print(f"\n[Test 1] Detectando proyecto en: {current_dir}")
    ctx = manager.get_context(current_dir)

    print(f"âœ“ Is project: {ctx.is_project}")
    if ctx.config:
        print(f"âœ“ Name: {ctx.config.name}")
        print(f"âœ“ Type: {ctx.config.project_type}")
        print(f"âœ“ Frameworks: {ctx.config.frameworks}")
        print(f"âœ“ Entry points: {ctx.config.entry_points}")
        print(f"âœ“ Preferred tools: {ctx.config.preferred_tools}")

    print(f"âœ“ Recent projects: {len(ctx.recent_projects)}")

    print("\n[Test 2] Sugerencias de acciones")
    for suggestion in ctx.suggested_actions:
        print(f"  - {suggestion['text']}: {suggestion['command']}")

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
