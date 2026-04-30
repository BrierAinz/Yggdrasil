"""
ProjectScanner - Skill autÃ³noma para anÃ¡lisis inteligente de proyectos
Detecta tipo de proyecto, estructura, dependencias y entry points
"""

import ast
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("ProjectScanner")


class ProjectType(str, Enum):
    """Tipos de proyectos soportados"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    REACT = "react"
    VUE = "vue"
    NODE = "node"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    UNKNOWN = "unknown"


@dataclass
class ProjectStructure:
    """Estructura de un proyecto"""

    root_path: str
    project_type: ProjectType
    confidence: float
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    config_files: Dict[str, str] = field(default_factory=dict)
    directories: List[str] = field(default_factory=list)
    source_files: int = 0
    test_files: int = 0
    documentation: List[str] = field(default_factory=list)
    dependencies: Dict[str, Any] = field(default_factory=dict)


class ProjectScanner:
    """
    Skill autÃ³noma para anÃ¡lisis inteligente de proyectos.

    Capacidades:
    - Detectar tipo de proyecto (Python, JS, React, etc.)
    - Identificar entry points
    - Mapear estructura de directorios
    - Encontrar archivos de configuraciÃ³n
    - Analizar dependencias
    - Detectar frameworks utilizados
    """

    # Archivos que indican tipo de proyecto
    PROJECT_INDICATORS = {
        ProjectType.PYTHON: [
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "setup.cfg",
            "Pipfile",
            "poetry.lock",
            "environment.yml",
            "conda.yml",
            "tox.ini",
            "pytest.ini",
            ".flake8",
        ],
        ProjectType.JAVASCRIPT: [
            "package.json",
            "package-lock.json",
            "yarn.lock",
            ".npmrc",
        ],
        ProjectType.TYPESCRIPT: ["tsconfig.json", "package.json"],
        ProjectType.REACT: [
            "package.json",
            "src/App.js",
            "src/App.jsx",
            "src/App.tsx",
            "public/index.html",
            "vite.config.js",
            "next.config.js",
        ],
        ProjectType.VUE: [
            "vue.config.js",
            "vite.config.js",
            "src/App.vue",
            "nuxt.config.js",
        ],
        ProjectType.NODE: ["package.json", "server.js", "app.js", "index.js"],
        ProjectType.JAVA: [
            "pom.xml",
            "build.gradle",
            "gradlew",
            "settings.gradle",
            "src/main/java",
            "src/test/java",
        ],
        ProjectType.GO: ["go.mod", "go.sum", "main.go"],
        ProjectType.RUST: ["Cargo.toml", "Cargo.lock", "src/main.rs", "src/lib.rs"],
        ProjectType.CPP: [
            "CMakeLists.txt",
            "Makefile",
            "configure.ac",
            "setup.py",
            "src/*.cpp",
            "include/*.h",
        ],
    }

    # Mapeo de extensiones a lenguajes
    LANGUAGE_EXTENSIONS = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript (React)",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".vue": "Vue",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".c": "C",
        ".h": "C/C++ Header",
        ".hpp": "C++ Header",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".scala": "Scala",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".fs": "F#",
    }

    def __init__(self):
        self.name = "ProjectScanner"
        self.description = "AnÃ¡lisis inteligente de proyectos de software"
        self.version = "1.0.0"
        logger.info("ProjectScanner initialized")

    def check_dependencies(self) -> bool:
        """Verificar dependencias"""
        return True

    def scan_project(self, project_path: str) -> Dict[str, Any]:
        """
        Escanear un proyecto completo

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con anÃ¡lisis completo del proyecto
        """
        try:
            path = Path(project_path).resolve()

            if not path.exists():
                return {
                    "success": False,
                    "error": f"Ruta no encontrada: {project_path}",
                }

            if not path.is_dir():
                return {
                    "success": False,
                    "error": f"La ruta no es un directorio: {project_path}",
                }

            logger.info(f"Scanning project at: {path}")

            # Detectar tipo de proyecto
            project_type, confidence = self._detect_project_type(path)

            # Analizar estructura
            structure = self._analyze_structure(path)

            # Encontrar entry points
            entry_points = self._find_entry_points(path, project_type)

            # Analizar dependencias
            dependencies = self._analyze_dependencies(path, project_type)

            # Detectar frameworks
            frameworks = self._detect_frameworks(path, project_type)

            # Encontrar documentaciÃ³n
            documentation = self._find_documentation(path)

            # Encontrar config files
            config_files = self._find_config_files(path)

            # Compilar resultado
            result = {
                "success": True,
                "project_path": str(path),
                "project_name": path.name,
                "project_type": project_type.value,
                "confidence": round(confidence, 2),
                "summary": {
                    "languages": structure["languages"],
                    "frameworks": frameworks,
                    "total_files": structure["total_files"],
                    "source_files": structure["source_files"],
                    "test_files": structure["test_files"],
                    "directories": structure["dir_count"],
                },
                "entry_points": entry_points,
                "config_files": config_files,
                "dependencies": dependencies,
                "documentation": documentation,
                "structure": {
                    "top_level_dirs": structure["top_dirs"],
                    "source_dirs": structure["source_dirs"],
                    "test_dirs": structure["test_dirs"],
                },
                "recommendations": self._generate_recommendations(
                    project_type, structure, entry_points
                ),
            }

            return result

        except Exception as e:
            logger.error(f"Error scanning project: {e}")
            return {"success": False, "error": f"Error escaneando proyecto: {str(e)}"}

    def _detect_project_type(self, path: Path) -> tuple:
        """Detectar el tipo de proyecto y confianza"""
        scores = {project_type: 0 for project_type in ProjectType}

        # Verificar archivos indicadores
        for project_type, indicators in self.PROJECT_INDICATORS.items():
            for indicator in indicators:
                indicator_path = path / indicator
                if indicator_path.exists():
                    scores[project_type] += 2

                # TambiÃ©n verificar con glob para patrones
                if "*" in indicator:
                    matches = list(path.glob(indicator))
                    scores[project_type] += len(matches)

        # Contar archivos por extensiÃ³n
        extensions = {}
        for file_path in path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                extensions[ext] = extensions.get(ext, 0) + 1

        # Puntuar basado en extensiones
        if extensions.get(".py", 0) > 0:
            scores[ProjectType.PYTHON] += extensions[".py"] * 0.5
        if extensions.get(".js", 0) > 0:
            scores[ProjectType.JAVASCRIPT] += extensions[".js"] * 0.3
        if extensions.get(".ts", 0) > 0:
            scores[ProjectType.TYPESCRIPT] += extensions[".ts"] * 0.5
        if extensions.get(".tsx", 0) > 0:
            scores[ProjectType.REACT] += extensions[".tsx"] * 0.7
        if extensions.get(".jsx", 0) > 0:
            scores[ProjectType.REACT] += extensions[".jsx"] * 0.7
        if extensions.get(".vue", 0) > 0:
            scores[ProjectType.VUE] += extensions[".vue"] * 2
        if extensions.get(".java", 0) > 0:
            scores[ProjectType.JAVA] += extensions[".java"] * 0.3
        if extensions.get(".go", 0) > 0:
            scores[ProjectType.GO] += extensions[".go"] * 1
        if extensions.get(".rs", 0) > 0:
            scores[ProjectType.RUST] += extensions[".rs"] * 1

        # Encontrar el tipo con mayor score
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]

        # Calcular confianza (0-1)
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0

        # Si no hay score significativo, es unknown
        if max_score < 1:
            return ProjectType.UNKNOWN, 0.0

        return max_type, min(confidence, 1.0)

    def _analyze_structure(self, path: Path) -> Dict[str, Any]:
        """Analizar estructura del proyecto"""
        languages = set()
        total_files = 0
        source_files = 0
        test_files = 0
        dir_count = 0
        top_dirs = []
        source_dirs = set()
        test_dirs = set()

        # Top-level directories
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                top_dirs.append(item.name)

        # Recorrer recursivamente
        for item in path.rglob("*"):
            if item.is_dir():
                dir_count += 1
                dir_name = item.name.lower()

                # Detectar directorios de cÃ³digo fuente
                if dir_name in ["src", "source", "lib", "app", "core"]:
                    source_dirs.add(str(item.relative_to(path)))

                # Detectar directorios de test
                if dir_name in ["test", "tests", "spec", "specs", "__tests__"]:
                    test_dirs.add(str(item.relative_to(path)))

            elif item.is_file():
                total_files += 1
                ext = item.suffix.lower()

                # Contar por tipo
                if ext in self.LANGUAGE_EXTENSIONS:
                    languages.add(self.LANGUAGE_EXTENSIONS[ext])
                    source_files += 1

                # Detectar archivos de test
                name_lower = item.name.lower()
                if "test" in name_lower or "spec" in name_lower:
                    if ext in [".py", ".js", ".ts", ".java", ".go"]:
                        test_files += 1

        return {
            "languages": list(languages),
            "total_files": total_files,
            "source_files": source_files,
            "test_files": test_files,
            "dir_count": dir_count,
            "top_dirs": top_dirs,
            "source_dirs": list(source_dirs),
            "test_dirs": list(test_dirs),
        }

    def _find_entry_points(
        self, path: Path, project_type: ProjectType
    ) -> List[Dict[str, Any]]:
        """Encontrar puntos de entrada del proyecto"""
        entry_points = []

        # Buscar segÃºn tipo de proyecto
        if project_type == ProjectType.PYTHON:
            # Buscar archivos con if __name__ == "__main__"
            for py_file in path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if "__main__" in content:
                        # Verificar si es realmente un entry point
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.If):
                                if hasattr(node.test, "left") and hasattr(
                                    node.test.left, "id"
                                ):
                                    if node.test.left.id == "__name__":
                                        entry_points.append(
                                            {
                                                "path": str(py_file.relative_to(path)),
                                                "type": "python_script",
                                                "description": f"Python script ejecutable",
                                            }
                                        )
                                        break
                except Exception:
                    continue

            # Buscar setup.py o pyproject.toml con entry points
            if (path / "setup.py").exists() or (path / "pyproject.toml").exists():
                entry_points.append(
                    {
                        "path": "setup.py / pyproject.toml",
                        "type": "package_entry",
                        "description": "Paquete Python instalable",
                    }
                )

        elif project_type in [
            ProjectType.JAVASCRIPT,
            ProjectType.NODE,
            ProjectType.REACT,
        ]:
            # Leer package.json
            package_json = path / "package.json"
            if package_json.exists():
                try:
                    data = json.loads(package_json.read_text())

                    # Main entry
                    if "main" in data:
                        entry_points.append(
                            {
                                "path": data["main"],
                                "type": "main",
                                "description": "Entry point principal",
                            }
                        )

                    # Scripts
                    if "scripts" in data:
                        for script_name, script_cmd in data["scripts"].items():
                            if script_name in ["start", "serve", "dev"]:
                                entry_points.append(
                                    {
                                        "path": f"package.json scripts.{script_name}",
                                        "type": "npm_script",
                                        "description": f"npm run {script_name}",
                                    }
                                )
                except Exception:
                    pass

            # Buscar index.js/ts
            for entry in ["index.js", "index.ts", "src/index.js", "src/index.ts"]:
                if (path / entry).exists():
                    entry_points.append(
                        {
                            "path": entry,
                            "type": "index_file",
                            "description": "Archivo Ã­ndice",
                        }
                    )
                    break

        elif project_type == ProjectType.JAVA:
            # Buscar Main.java o clases con main
            for java_file in path.rglob("*.java"):
                try:
                    content = java_file.read_text(encoding="utf-8", errors="ignore")
                    if "public static void main" in content:
                        entry_points.append(
                            {
                                "path": str(java_file.relative_to(path)),
                                "type": "java_main",
                                "description": "Clase Java con mÃ©todo main",
                            }
                        )
                except Exception:
                    continue

        elif project_type == ProjectType.GO:
            # Buscar package main
            for go_file in path.rglob("*.go"):
                try:
                    content = go_file.read_text(encoding="utf-8", errors="ignore")
                    if "package main" in content:
                        entry_points.append(
                            {
                                "path": str(go_file.relative_to(path)),
                                "type": "go_main",
                                "description": "Archivo Go ejecutable",
                            }
                        )
                        break
                except Exception:
                    continue

        elif project_type == ProjectType.RUST:
            # Buscar main.rs o lib.rs
            for entry in ["src/main.rs", "src/lib.rs"]:
                if (path / entry).exists():
                    entry_points.append(
                        {
                            "path": entry,
                            "type": "rust_entry",
                            "description": "Entry point Rust",
                        }
                    )

        return entry_points

    def _analyze_dependencies(
        self, path: Path, project_type: ProjectType
    ) -> Dict[str, Any]:
        """Analizar dependencias del proyecto"""
        deps = {"production": [], "development": [], "total_count": 0}

        try:
            if project_type == ProjectType.PYTHON:
                # requirements.txt
                req_file = path / "requirements.txt"
                if req_file.exists():
                    content = req_file.read_text()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            deps["production"].append(
                                line.split("==")[0].split(">=")[0]
                            )

                # pyproject.toml
                pyproject = path / "pyproject.toml"
                if pyproject.exists():
                    deps["production"].append("ConfiguraciÃ³n en pyproject.toml")

                # Pipfile
                pipfile = path / "Pipfile"
                if pipfile.exists():
                    deps["production"].append("Pipenv gestiona dependencias")

            elif project_type in [
                ProjectType.JAVASCRIPT,
                ProjectType.NODE,
                ProjectType.REACT,
                ProjectType.TYPESCRIPT,
            ]:
                package_json = path / "package.json"
                if package_json.exists():
                    data = json.loads(package_json.read_text())

                    if "dependencies" in data:
                        deps["production"] = list(data["dependencies"].keys())

                    if "devDependencies" in data:
                        deps["development"] = list(data["devDependencies"].keys())

            elif project_type == ProjectType.JAVA:
                # Maven
                pom = path / "pom.xml"
                if pom.exists():
                    deps["production"].append("Maven project (dependencies in pom.xml)")

                # Gradle
                gradle = path / "build.gradle"
                if gradle.exists():
                    deps["production"].append(
                        "Gradle project (dependencies in build.gradle)"
                    )

            elif project_type == ProjectType.GO:
                go_mod = path / "go.mod"
                if go_mod.exists():
                    content = go_mod.read_text()
                    for line in content.split("\n"):
                        if line.strip().startswith("require"):
                            deps["production"].append(line.strip())

            elif project_type == ProjectType.RUST:
                cargo = path / "Cargo.toml"
                if cargo.exists():
                    content = cargo.read_text()
                    in_deps = False
                    for line in content.split("\n"):
                        if "[dependencies]" in line:
                            in_deps = True
                        elif in_deps and line.startswith("["):
                            in_deps = False
                        elif in_deps and line.strip() and not line.startswith("#"):
                            dep_name = line.split("=")[0].strip()
                            deps["production"].append(dep_name)

            deps["total_count"] = len(deps["production"]) + len(deps["development"])

        except Exception as e:
            logger.warning(f"Error analyzing dependencies: {e}")

        return deps

    def _detect_frameworks(self, path: Path, project_type: ProjectType) -> List[str]:
        """Detectar frameworks utilizados"""
        frameworks = []

        try:
            # Detectar frameworks Python
            if project_type == ProjectType.PYTHON:
                # Buscar imports tÃ­picos
                for py_file in path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding="utf-8", errors="ignore")

                        framework_patterns = {
                            "django": "Django",
                            "flask": "Flask",
                            "fastapi": "FastAPI",
                            "tornado": "Tornado",
                            "bottle": "Bottle",
                            "sqlalchemy": "SQLAlchemy",
                            "pandas": "Pandas",
                            "numpy": "NumPy",
                            "torch": "PyTorch",
                            "tensorflow": "TensorFlow",
                            "pytest": "Pytest",
                            "unittest": "unittest",
                            "requests": "Requests",
                            "httpx": "HTTPX",
                            "pydantic": "Pydantic",
                            "typer": "Typer",
                            "click": "Click",
                            "jinja2": "Jinja2",
                            "asyncio": "AsyncIO",
                            "aiohttp": "AIOHTTP",
                            "tortoise": "TortoiseORM",
                            "peewee": "Peewee",
                        }

                        for pattern, name in framework_patterns.items():
                            if (
                                f"import {pattern}" in content
                                or f"from {pattern}" in content
                            ):
                                if name not in frameworks:
                                    frameworks.append(name)

                        if len(frameworks) >= 10:  # Limitar
                            break

                    except Exception:
                        continue

            # Detectar frameworks JS/TS
            elif project_type in [
                ProjectType.JAVASCRIPT,
                ProjectType.TYPESCRIPT,
                ProjectType.REACT,
                ProjectType.NODE,
            ]:
                package_json = path / "package.json"
                if package_json.exists():
                    data = json.loads(package_json.read_text())
                    all_deps = list(data.get("dependencies", {}).keys()) + list(
                        data.get("devDependencies", {}).keys()
                    )

                    framework_patterns = {
                        "react": "React",
                        "vue": "Vue.js",
                        "next": "Next.js",
                        "nuxt": "Nuxt.js",
                        "express": "Express.js",
                        "fastify": "Fastify",
                        "nestjs": "NestJS",
                        "angular": "Angular",
                        "svelte": "Svelte",
                        "vite": "Vite",
                        "webpack": "Webpack",
                        "jest": "Jest",
                        "mocha": "Mocha",
                        "cypress": "Cypress",
                        "tailwindcss": "Tailwind CSS",
                        "bootstrap": "Bootstrap",
                        "material-ui": "Material-UI",
                        "typescript": "TypeScript",
                    }

                    for dep in all_deps:
                        for pattern, name in framework_patterns.items():
                            if pattern in dep.lower():
                                if name not in frameworks:
                                    frameworks.append(name)

        except Exception as e:
            logger.warning(f"Error detecting frameworks: {e}")

        return frameworks

    def _find_documentation(self, path: Path) -> List[str]:
        """Encontrar archivos de documentaciÃ³n"""
        docs = []
        doc_files = [
            "README.md",
            "README.rst",
            "README.txt",
            "README",
            "CONTRIBUTING.md",
            "CONTRIBUTING.rst",
            "CHANGELOG.md",
            "CHANGELOG.rst",
            "HISTORY.md",
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
            "docs/",
            "doc/",
            "Documentation/",
        ]

        for doc in doc_files:
            doc_path = path / doc
            if doc_path.exists():
                docs.append(doc)

        return docs

    def _find_config_files(self, path: Path) -> Dict[str, str]:
        """Encontrar archivos de configuraciÃ³n"""
        configs = {}
        config_patterns = [
            (".gitignore", "Git ignore rules"),
            (".gitattributes", "Git attributes"),
            (".editorconfig", "Editor configuration"),
            (".env.example", "Environment variables example"),
            (".env", "Environment variables"),
            ("docker-compose.yml", "Docker Compose"),
            ("Dockerfile", "Docker image definition"),
            (".github/", "GitHub configuration"),
            (".gitlab-ci.yml", "GitLab CI/CD"),
            (".travis.yml", "Travis CI"),
            ("tox.ini", "Tox configuration"),
            ("setup.cfg", "Setup configuration"),
            ("Makefile", "Make configuration"),
            ("justfile", "Just configuration"),
        ]

        for pattern, description in config_patterns:
            config_path = path / pattern
            if config_path.exists():
                configs[pattern] = description

        return configs

    def _generate_recommendations(
        self, project_type: ProjectType, structure: Dict, entry_points: List
    ) -> List[str]:
        """Generar recomendaciones basadas en el anÃ¡lisis"""
        recommendations = []

        if project_type == ProjectType.UNKNOWN:
            recommendations.append(
                "El tipo de proyecto no pudo ser determinado con confianza"
            )

        if structure["test_files"] == 0:
            recommendations.append(
                "No se detectaron archivos de test - considera agregar tests"
            )

        if not entry_points:
            recommendations.append(
                "No se encontraron entry points claros - verifica la estructura"
            )

        if "README" not in str(structure.get("top_dirs", [])):
            readme_exists = any("README" in d for d in structure.get("top_dirs", []))
            if not readme_exists:
                recommendations.append(
                    "No se encontrÃ³ README.md - considera agregar documentaciÃ³n"
                )

        if ".gitignore" not in str(structure.get("top_dirs", [])):
            recommendations.append("No se encontrÃ³ .gitignore - considera agregar uno")

        if (
            structure["source_files"] > 50
            and structure["test_files"] < structure["source_files"] * 0.1
        ):
            recommendations.append("La cobertura de tests parece baja (< 10%)")

        return recommendations

    async def execute(self, action: str = "scan", **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del ProjectScanner

        Args:
            action: AcciÃ³n a ejecutar (scan)
            **kwargs: ParÃ¡metros

        Returns:
            Resultado de la operaciÃ³n
        """
        if action in ["scan", "analyze", "scan_project"]:
            return self.scan_project(kwargs.get("project_path", "."))

        return {"success": False, "error": f"AcciÃ³n no vÃ¡lida: {action}. Use 'scan'"}


# === Testing ===
if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 60)
        print("ProjectScanner - Test Suite")
        print("=" * 60)

        scanner = ProjectScanner()

        # Test 1: Escanear el proyecto actual (raíz detectada por ubicación del archivo)
        print("\n[Test] Escanear proyecto Lilith")
        project_root = Path(__file__).resolve().parents[3]
        result = await scanner.execute("scan", project_path=str(project_root))

        if result.get("success"):
            print(f"âœ“ Proyecto: {result['project_name']}")
            print(
                f"âœ“ Tipo: {result['project_type']} (confianza: {result['confidence']})"
            )
            print(f"âœ“ Lenguajes: {', '.join(result['summary']['languages'])}")
            print(f"âœ“ Frameworks: {', '.join(result['summary']['frameworks'][:5])}")
            print(f"âœ“ Archivos: {result['summary']['total_files']} total")
            print(f"âœ“ Entry points: {len(result['entry_points'])}")
            print(f"âœ“ Dependencias: {result['dependencies']['total_count']}")

            if result["recommendations"]:
                print(f"\n  Recomendaciones:")
                for rec in result["recommendations"][:3]:
                    print(f"  â€¢ {rec}")
        else:
            print(f"âœ— Error: {result.get('error')}")

        print("\n" + "=" * 60)
        print("Test completado!")
        print("=" * 60)

    asyncio.run(test())
