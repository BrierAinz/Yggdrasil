"""
DependencyManager - Skill autÃ³noma para gestiÃ³n de dependencias
Gestiona dependencias de proyectos Python (pip) y JavaScript (npm/yarn)
"""

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

logger = logging.getLogger("DependencyManager")


class PackageManager(str, Enum):
    """Gestores de paquetes soportados"""

    PIP = "pip"
    POETRY = "poetry"
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    CARGO = "cargo"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    """Tipos de dependencias"""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    OPTIONAL = "optional"


@dataclass
class Dependency:
    """Representa una dependencia"""

    name: str
    version: str
    latest_version: Optional[str] = None
    outdated: bool = False
    vulnerability: Optional[str] = None
    dependency_type: DependencyType = DependencyType.PRODUCTION


@dataclass
class PackageInfo:
    """InformaciÃ³n de un paquete"""

    name: str
    current_version: str
    wanted_version: Optional[str] = None
    latest_version: Optional[str] = None
    location: Optional[str] = None
    dependency_type: str = "production"
    homepage: Optional[str] = None
    description: Optional[str] = None


class DependencyManager:
    """
    Skill autÃ³noma para gestiÃ³n de dependencias.

    Capacidades:
    - Detectar gestor de paquetes (pip, npm, yarn, poetry)
    - Instalar nuevas dependencias
    - Actualizar dependencias con changelog
    - Auditar vulnerabilidades de seguridad
    - Encontrar dependencias no usadas
    - Buscar informaciÃ³n de paquetes
    - Bloquear versiones (lock files)
    """

    def __init__(self):
        self.name = "DependencyManager"
        self.description = "GestiÃ³n de dependencias de proyectos"
        self.version = "1.0.0"
        self.supported_managers = {
            "requirements.txt": PackageManager.PIP,
            "setup.py": PackageManager.PIP,
            "pyproject.toml": PackageManager.POETRY,
            "Pipfile": PackageManager.PIP,
            "package.json": PackageManager.NPM,
            "yarn.lock": PackageManager.YARN,
            "pnpm-lock.yaml": PackageManager.PNPM,
            "Cargo.toml": PackageManager.CARGO,
        }
        logger.info("DependencyManager initialized")

    def check_dependencies(self) -> bool:
        """Verificar dependencias"""
        return True

    def _detect_package_manager(self, project_path: str) -> Tuple[PackageManager, str]:
        """
        Detectar el gestor de paquetes usado en el proyecto.

        Returns:
            Tuple de (gestor, archivo_config)
        """
        path = Path(project_path)

        # Orden de prioridad
        checks = [
            ("pnpm-lock.yaml", PackageManager.PNPM),
            ("yarn.lock", PackageManager.YARN),
            ("package-lock.json", PackageManager.NPM),
            ("package.json", PackageManager.NPM),
            ("poetry.lock", PackageManager.POETRY),
            ("pyproject.toml", PackageManager.POETRY),
            ("Pipfile.lock", PackageManager.PIP),
            ("Pipfile", PackageManager.PIP),
            ("requirements.txt", PackageManager.PIP),
            ("setup.py", PackageManager.PIP),
            ("Cargo.lock", PackageManager.CARGO),
            ("Cargo.toml", PackageManager.CARGO),
        ]

        for filename, manager in checks:
            if (path / filename).exists():
                return manager, str(path / filename)

        return PackageManager.UNKNOWN, ""

    def list_dependencies(self, project_path: str) -> Dict[str, Any]:
        """
        Listar todas las dependencias del proyecto.

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con lista de dependencias
        """
        try:
            manager, config_file = self._detect_package_manager(project_path)

            if manager == PackageManager.UNKNOWN:
                return {
                    "success": False,
                    "error": "No se detectÃ³ gestor de paquetes",
                    "message": "AsegÃºrate de tener requirements.txt, package.json, pyproject.toml, etc.",
                }

            if manager in [PackageManager.PIP, PackageManager.POETRY]:
                return self._list_python_dependencies(project_path, manager)
            elif manager in [
                PackageManager.NPM,
                PackageManager.YARN,
                PackageManager.PNPM,
            ]:
                return self._list_npm_dependencies(project_path, manager)
            elif manager == PackageManager.CARGO:
                return self._list_cargo_dependencies(project_path)
            else:
                return {"success": False, "error": f"Gestor no soportado: {manager}"}

        except Exception as e:
            logger.error(f"Error listing dependencies: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error listando dependencias: {str(e)}",
            }

    def _list_python_dependencies(
        self, project_path: str, manager: PackageManager
    ) -> Dict[str, Any]:
        """Listar dependencias de Python"""
        try:
            if manager == PackageManager.PIP:
                # Usar pip list
                cmd = ["pip", "list", "--format=json"]
                result = subprocess.run(
                    cmd, cwd=project_path, capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    packages = json.loads(result.stdout)

                    # Separar en producciÃ³n y desarrollo
                    prod_deps = []
                    dev_deps = []

                    # Intentar leer requirements.txt para clasificar
                    req_file = Path(project_path) / "requirements.txt"
                    if req_file.exists():
                        req_content = req_file.read_text().lower()

                        for pkg in packages:
                            pkg_name = pkg.get("name", "").lower()
                            # Simple heuristic: si estÃ¡ en requirements.txt es prod
                            if pkg_name in req_content:
                                prod_deps.append(pkg)
                            else:
                                dev_deps.append(pkg)
                    else:
                        prod_deps = packages

                    return {
                        "success": True,
                        "manager": "pip",
                        "total": len(packages),
                        "production": prod_deps,
                        "development": dev_deps,
                        "packages": packages[:50],  # Limitar a 50
                    }
                else:
                    return {"success": False, "error": result.stderr}

            elif manager == PackageManager.POETRY:
                cmd = ["poetry", "show", "--tree"]
                result = subprocess.run(
                    cmd, cwd=project_path, capture_output=True, text=True, timeout=60
                )

                return {
                    "success": result.returncode == 0,
                    "manager": "poetry",
                    "output": result.stdout
                    if result.returncode == 0
                    else result.stderr,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_npm_dependencies(
        self, project_path: str, manager: PackageManager
    ) -> Dict[str, Any]:
        """Listar dependencias de npm/yarn/pnpm"""
        try:
            cmd_map = {
                PackageManager.NPM: ["npm", "list", "--json"],
                PackageManager.YARN: ["yarn", "list", "--json"],
                PackageManager.PNPM: ["pnpm", "list", "--json"],
            }

            cmd = cmd_map.get(manager, ["npm", "list", "--json"])

            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=60
            )

            # npm list puede fallar si hay dependencias faltantes pero aÃºn da output
            try:
                data = json.loads(result.stdout)

                # Parsear dependencias
                deps = data.get("dependencies", {})
                packages = []

                for name, info in deps.items():
                    packages.append(
                        {
                            "name": name,
                            "version": info.get("version", "unknown"),
                            "dependency_type": "production",
                        }
                    )

                return {
                    "success": True,
                    "manager": manager.value,
                    "total": len(packages),
                    "packages": packages[:50],
                }

            except json.JSONDecodeError:
                # Fallback a texto
                return {
                    "success": True,
                    "manager": manager.value,
                    "output": result.stdout[:2000],
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_cargo_dependencies(self, project_path: str) -> Dict[str, Any]:
        """Listar dependencias de Cargo (Rust)"""
        try:
            cmd = ["cargo", "tree", "--format", "json"]
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=60
            )

            return {
                "success": result.returncode == 0,
                "manager": "cargo",
                "output": result.stdout if result.returncode == 0 else result.stderr,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def install_dependency(
        self,
        project_path: str,
        package_name: str,
        version: Optional[str] = None,
        dev: bool = False,
    ) -> Dict[str, Any]:
        """
        Instalar una nueva dependencia.

        Args:
            project_path: Ruta raÃ­z del proyecto
            package_name: Nombre del paquete
            version: VersiÃ³n especÃ­fica (opcional)
            dev: Si es dependencia de desarrollo

        Returns:
            Dict con resultado de la instalaciÃ³n
        """
        try:
            manager, _ = self._detect_package_manager(project_path)

            if manager == PackageManager.UNKNOWN:
                return {"success": False, "error": "No se detectÃ³ gestor de paquetes"}

            # Construir comando segÃºn gestor
            if manager == PackageManager.PIP:
                cmd = ["pip", "install"]
                if dev:
                    # pip no tiene concepto nativo de dev, pero podemos usar extras
                    pass
                if version:
                    cmd.append(f"{package_name}=={version}")
                else:
                    cmd.append(package_name)

            elif manager == PackageManager.POETRY:
                cmd = ["poetry", "add"]
                if dev:
                    cmd.append("--dev")
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)

            elif manager == PackageManager.NPM:
                cmd = ["npm", "install"]
                if dev:
                    cmd.append("--save-dev")
                else:
                    cmd.append("--save")
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)

            elif manager == PackageManager.YARN:
                cmd = ["yarn", "add"]
                if dev:
                    cmd.append("--dev")
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)

            else:
                return {
                    "success": False,
                    "error": f"InstalaciÃ³n no soportada para {manager}",
                }

            # Ejecutar comando
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=120
            )

            success = result.returncode == 0

            return {
                "success": success,
                "manager": manager.value,
                "package": package_name,
                "version": version,
                "dev": dev,
                "message": f"{package_name} instalado correctamente"
                if success
                else result.stderr,
                "stdout": result.stdout[-1000:]
                if len(result.stdout) > 1000
                else result.stdout,
            }

        except Exception as e:
            logger.error(f"Error installing dependency: {e}")
            return {"success": False, "error": str(e), "package": package_name}

    def update_dependencies(
        self, project_path: str, package_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Actualizar dependencias.

        Args:
            project_path: Ruta raÃ­z del proyecto
            package_name: Paquete especÃ­fico (None = todos)

        Returns:
            Dict con resultado de la actualizaciÃ³n
        """
        try:
            manager, _ = self._detect_package_manager(project_path)

            if manager == PackageManager.UNKNOWN:
                return {"success": False, "error": "No se detectÃ³ gestor de paquetes"}

            # Construir comando
            if manager == PackageManager.PIP:
                if package_name:
                    cmd = ["pip", "install", "--upgrade", package_name]
                else:
                    # Actualizar todo desde requirements.txt
                    cmd = ["pip", "install", "--upgrade", "-r", "requirements.txt"]

            elif manager == PackageManager.POETRY:
                if package_name:
                    cmd = ["poetry", "update", package_name]
                else:
                    cmd = ["poetry", "update"]

            elif manager == PackageManager.NPM:
                if package_name:
                    cmd = ["npm", "update", package_name]
                else:
                    cmd = ["npm", "update"]

            elif manager == PackageManager.YARN:
                if package_name:
                    cmd = ["yarn", "upgrade", package_name]
                else:
                    cmd = ["yarn", "upgrade"]

            else:
                return {
                    "success": False,
                    "error": f"ActualizaciÃ³n no soportada para {manager}",
                }

            # Ejecutar
            result = subprocess.run(
                cmd, cwd=project_path, capture_output=True, text=True, timeout=180
            )

            success = result.returncode == 0

            return {
                "success": success,
                "manager": manager.value,
                "package": package_name or "all",
                "message": "Dependencias actualizadas" if success else result.stderr,
                "stdout": result.stdout[-1500:]
                if len(result.stdout) > 1500
                else result.stdout,
            }

        except Exception as e:
            logger.error(f"Error updating dependencies: {e}")
            return {"success": False, "error": str(e)}

    def audit_security(self, project_path: str) -> Dict[str, Any]:
        """
        Auditar vulnerabilidades de seguridad en dependencias.

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con vulnerabilidades encontradas
        """
        try:
            manager, _ = self._detect_package_manager(project_path)

            if manager in [PackageManager.PIP, PackageManager.POETRY]:
                # Usar safety si estÃ¡ disponible, sino pip-audit
                cmd = ["pip-audit", "--format=json"]

                try:
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                    if result.returncode == 0:
                        try:
                            audit_data = json.loads(result.stdout)
                            vulnerabilities = audit_data.get("dependencies", [])

                            high_severity = [
                                v for v in vulnerabilities if v.get("vulns")
                            ]

                            return {
                                "success": True,
                                "manager": manager.value,
                                "vulnerabilities_found": len(vulnerabilities),
                                "high_severity": len(high_severity),
                                "details": vulnerabilities[:20],
                            }
                        except json.JSONDecodeError:
                            pass

                    # Fallback
                    return {
                        "success": True,
                        "manager": manager.value,
                        "note": "Instala pip-audit: pip install pip-audit",
                        "output": result.stdout[:1000],
                    }

                except FileNotFoundError:
                    return {
                        "success": False,
                        "error": "pip-audit no instalado",
                        "message": "Instala: pip install pip-audit",
                    }

            elif manager in [PackageManager.NPM, PackageManager.YARN]:
                cmd = ["npm", "audit", "--json"]

                result = subprocess.run(
                    cmd, cwd=project_path, capture_output=True, text=True, timeout=120
                )

                try:
                    audit_data = json.loads(result.stdout)

                    vulnerabilities = audit_data.get("vulnerabilities", {})
                    metadata = audit_data.get("metadata", {})

                    total = sum(
                        v.get("severityCounts", {}).values()
                        for v in [metadata.get("vulnerabilities", {})]
                    )

                    return {
                        "success": True,
                        "manager": manager.value,
                        "vulnerabilities_found": len(vulnerabilities),
                        "severity": metadata.get("vulnerabilities", {}),
                        "details": list(vulnerabilities.keys())[:20],
                    }

                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "manager": manager.value,
                        "output": result.stdout[:1500],
                    }

            else:
                return {
                    "success": False,
                    "error": f"AuditorÃ­a no soportada para {manager}",
                }

        except Exception as e:
            logger.error(f"Error auditing dependencies: {e}")
            return {"success": False, "error": str(e)}

    def find_unused_dependencies(self, project_path: str) -> Dict[str, Any]:
        """
        Encontrar dependencias que no se usan.

        Args:
            project_path: Ruta raÃ­z del proyecto

        Returns:
            Dict con dependencias no usadas
        """
        try:
            manager, _ = self._detect_package_manager(project_path)

            if manager in [PackageManager.NPM, PackageManager.YARN]:
                # Usar depcheck si estÃ¡ disponible
                cmd = ["depcheck", "--json"]

                try:
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )

                    data = json.loads(result.stdout)

                    unused = data.get("dependencies", []) + data.get(
                        "devDependencies", []
                    )
                    missing = data.get("missing", {})

                    return {
                        "success": True,
                        "manager": manager.value,
                        "unused_dependencies": unused,
                        "missing_dependencies": list(missing.keys()),
                        "total_unused": len(unused),
                    }

                except (FileNotFoundError, json.JSONDecodeError):
                    return {
                        "success": False,
                        "error": "depcheck no instalado",
                        "message": "Instala: npm install -g depcheck",
                    }

            elif manager == PackageManager.PIP:
                # Para Python es mÃ¡s complejo, requerirÃ­a anÃ¡lisis de imports
                return {
                    "success": False,
                    "error": "AnÃ¡lisis de dependencias no usadas no implementado para pip",
                    "message": "Usa herramientas como pip-check-reqs",
                }

            else:
                return {
                    "success": False,
                    "error": f"AnÃ¡lisis no soportado para {manager}",
                }

        except Exception as e:
            logger.error(f"Error finding unused dependencies: {e}")
            return {"success": False, "error": str(e)}

    def search_package(
        self, query: str, manager: Optional[PackageManager] = None
    ) -> Dict[str, Any]:
        """
        Buscar informaciÃ³n de un paquete.

        Args:
            query: Nombre del paquete a buscar
            manager: Gestor especÃ­fico (opcional)

        Returns:
            Dict con informaciÃ³n del paquete
        """
        try:
            # Default a pip si no se especifica
            if not manager:
                manager = PackageManager.PIP

            if manager == PackageManager.PIP:
                cmd = ["pip", "search", query]

                # pip search ya no funciona en PyPI moderno
                # Usar pip index en versiones nuevas o fallback a pip show
                cmd = ["pip", "index", "versions", query]

                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=30
                    )

                    if result.returncode == 0:
                        return {
                            "success": True,
                            "manager": "pip",
                            "query": query,
                            "result": result.stdout,
                        }
                    else:
                        # Fallback: usar pip show si estÃ¡ instalado
                        cmd = ["pip", "show", query]
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=30
                        )

                        return {
                            "success": result.returncode == 0,
                            "manager": "pip",
                            "query": query,
                            "result": result.stdout
                            if result.returncode == 0
                            else "Paquete no encontrado",
                        }

                except Exception as e:
                    return {"success": False, "error": str(e)}

            elif manager in [PackageManager.NPM, PackageManager.YARN]:
                cmd = ["npm", "search", query, "--json"]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                try:
                    packages = json.loads(result.stdout)
                    return {
                        "success": True,
                        "manager": "npm",
                        "query": query,
                        "results": packages[:10],
                    }
                except:
                    return {
                        "success": True,
                        "manager": "npm",
                        "output": result.stdout[:1000],
                    }

            else:
                return {
                    "success": False,
                    "error": f"BÃºsqueda no soportada para {manager}",
                }

        except Exception as e:
            logger.error(f"Error searching package: {e}")
            return {"success": False, "error": str(e)}

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del DependencyManager.

        Args:
            action: Tipo de acciÃ³n
            **kwargs: ParÃ¡metros especÃ­ficos

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "list": self.list_dependencies,
            "list_dependencies": self.list_dependencies,
            "install": self.install_dependency,
            "install_dependency": self.install_dependency,
            "add": self.install_dependency,
            "update": self.update_dependencies,
            "update_dependencies": self.update_dependencies,
            "upgrade": self.update_dependencies,
            "audit": self.audit_security,
            "audit_security": self.audit_security,
            "check_security": self.audit_security,
            "find_unused": self.find_unused_dependencies,
            "unused": self.find_unused_dependencies,
            "search": self.search_package,
            "search_package": self.search_package,
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
        print("DependencyManager - Test Suite")
        print("=" * 70)

        dm = DependencyManager()

        # Test 1: Detectar gestor
        print("\n[Test 1] Detectar gestor de paquetes")
        manager, config = dm._detect_package_manager(".")
        print(f"  Manager: {manager.value}")
        print(f"  Config: {config}")

        # Test 2: Listar dependencias
        print("\n[Test 2] Listar dependencias")
        result = await dm.execute("list", project_path=".")
        if result.get("success"):
            print(f"  Total: {result.get('total', 0)}")
            print(f"  Manager: {result.get('manager', 'N/A')}")
        else:
            print(f"  Error: {result.get('error', 'Unknown')}")

        print("\n" + "=" * 70)
        print("Tests completados!")
        print("=" * 70)

    asyncio.run(test())
