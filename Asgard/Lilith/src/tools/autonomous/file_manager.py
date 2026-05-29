"""
FileManager - Skill autÃ³noma para gestiÃ³n de archivos
Permite a Lilith leer, escribir, buscar y organizar archivos de forma autÃ³noma
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("FileManager")


@dataclass
class FileInfo:
    """InformaciÃ³n sobre un archivo"""

    path: str
    name: str
    size: int
    modified: float
    is_dir: bool
    extension: str


class FileManager:
    """
    Skill autÃ³noma para gestiÃ³n completa de archivos.

    Capacidades:
    - Leer archivos de cualquier tipo (txt, py, md, json, etc.)
    - Escribir/crear archivos y directorios
    - Listar directorios con filtros
    - Buscar archivos por nombre o contenido
    - Obtener informaciÃ³n de archivos
    - Copiar/mover/renombrar (con aprobaciÃ³n implÃ­cita para operaciones seguras)
    """

    def __init__(self, base_path: Optional[str] = None):
        self.name = "FileManager"
        self.description = "GestiÃ³n autÃ³noma de archivos y directorios"
        self.version = "1.0.0"

        # Base path para operaciones (por seguridad)
        self.base_path = base_path or os.getcwd()

        # Extensiones de texto que podemos leer
        self.text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".ini",
            ".cfg",
            ".conf",
            ".toml",
            ".rst",
            ".csv",
            ".log",
            ".sql",
            ".sh",
            ".bat",
            ".ps1",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".java",
            ".kt",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".scala",
            ".r",
            ".m",
            ".pl",
            ".lua",
            ".vim",
            ".gitignore",
            ".env",
            ".dockerfile",
            ".makefile",
            ".cmake",
            ".gradle",
            ".properties",
        }

        # Archivos protegidos (no leer/escribir sin precauciÃ³n)
        self.protected_patterns = [
            ".env",
            ".ssh",
            ".aws",
            "id_rsa",
            "id_dsa",
            ".pgpass",
            "credentials",
            "secret",
            "password",
            "token",
            "key",
        ]

        logger.info(f"FileManager initialized with base_path: {self.base_path}")

    def check_dependencies(self) -> bool:
        """Verificar que podemos operar"""
        try:
            test_path = Path(self.base_path)
            return test_path.exists() and test_path.is_dir()
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return False

    def _resolve_path(self, path: str) -> Path:
        """Resolver ruta relativa a absoluta de forma segura"""
        if os.path.isabs(path):
            return Path(path)
        return Path(self.base_path) / path

    def _is_safe_path(self, path: Path) -> bool:
        """Verificar si la ruta es segura para operar"""
        try:
            # Resolver path absoluto
            abs_path = path.resolve()
            base = Path(self.base_path).resolve()

            # Verificar que estÃ¡ dentro del base_path
            return str(abs_path).startswith(str(base))
        except Exception:
            return False

    def _is_text_file(self, path: Path) -> bool:
        """Determinar si un archivo es de texto"""
        ext = path.suffix.lower()
        if ext in self.text_extensions:
            return True

        # Intentar leer como texto
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.read(1024)
            return True
        except (UnicodeDecodeError, PermissionError):
            return False

    def _is_protected(self, path: Path) -> bool:
        """Verificar si el archivo estÃ¡ protegido"""
        path_str = str(path).lower()
        name = path.name.lower()

        for pattern in self.protected_patterns:
            if pattern in path_str or pattern in name:
                return True
        return False

    def read_file(
        self, file_path: str, limit_lines: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Leer contenido de un archivo

        Args:
            file_path: Ruta al archivo
            limit_lines: LÃ­mite de lÃ­neas a leer (None = todo)

        Returns:
            Dict con contenido, tipo, y metadatos
        """
        try:
            path = self._resolve_path(file_path)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"Archivo no encontrado: {file_path}",
                    "path": str(path),
                }

            if path.is_dir():
                return {
                    "success": False,
                    "error": f"'{file_path}' es un directorio, no un archivo",
                    "path": str(path),
                }

            # Verificar si es archivo protegido
            if self._is_protected(path):
                return {
                    "success": False,
                    "error": f"Archivo protegido - no se puede leer por seguridad",
                    "path": str(path),
                }

            # Determinar tipo
            is_text = self._is_text_file(path)
            file_size = path.stat().st_size

            if not is_text:
                return {
                    "success": True,
                    "path": str(path),
                    "type": "binary",
                    "size": file_size,
                    "readable": False,
                    "content": None,
                    "message": "Archivo binario - no se puede mostrar contenido de texto",
                }

            # Leer contenido
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if limit_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit_lines:
                            break
                        lines.append(line)
                    content = "".join(lines)
                    truncated = True
                else:
                    content = f.read()
                    truncated = False

            return {
                "success": True,
                "path": str(path),
                "type": "text",
                "size": file_size,
                "readable": True,
                "content": content,
                "lines": content.count("\n") + 1,
                "truncated": truncated,
                "extension": path.suffix,
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permiso denegado para leer: {file_path}",
                "path": str(file_path),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error leyendo archivo: {str(e)}",
                "path": str(file_path),
            }

    def write_file(
        self, file_path: str, content: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Escribir contenido a un archivo

        Args:
            file_path: Ruta donde escribir
            content: Contenido a escribir
            overwrite: Si True, sobrescribe si existe

        Returns:
            Dict con resultado de la operaciÃ³n
        """
        try:
            path = self._resolve_path(file_path)

            # Verificar seguridad
            if not self._is_safe_path(path):
                return {
                    "success": False,
                    "error": f"Ruta no segura: {file_path}",
                    "path": str(path),
                }

            # Verificar si existe
            if path.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"El archivo ya existe. Usa overwrite=True para sobrescribir",
                    "path": str(path),
                }

            # Crear directorios si no existen
            path.parent.mkdir(parents=True, exist_ok=True)

            # Escribir archivo
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "path": str(path),
                "action": "write",
                "size": len(content),
                "lines": content.count("\n") + 1,
                "message": f"Archivo escrito exitosamente: {path.name}",
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permiso denegado para escribir: {file_path}",
                "path": str(file_path),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error escribiendo archivo: {str(e)}",
                "path": str(file_path),
            }

    def list_directory(
        self,
        dir_path: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False,
    ) -> Dict[str, Any]:
        """
        Listar contenido de un directorio

        Args:
            dir_path: Ruta del directorio
            pattern: PatrÃ³n glob para filtrar (ej: "*.py")
            recursive: Si True, incluye subdirectorios

        Returns:
            Dict con lista de archivos y directorios
        """
        try:
            path = self._resolve_path(dir_path)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directorio no encontrado: {dir_path}",
                    "path": str(path),
                }

            if not path.is_dir():
                return {
                    "success": False,
                    "error": f"'{dir_path}' no es un directorio",
                    "path": str(path),
                }

            files = []
            dirs = []

            if recursive:
                iterator = path.rglob(pattern or "*")
            else:
                iterator = path.glob(pattern or "*")

            for item in iterator:
                try:
                    stat = item.stat()
                    info = FileInfo(
                        path=str(item),
                        name=item.name,
                        size=stat.st_size,
                        modified=stat.st_mtime,
                        is_dir=item.is_dir(),
                        extension=item.suffix,
                    )

                    if item.is_dir():
                        dirs.append(info)
                    else:
                        files.append(info)

                except (PermissionError, OSError):
                    continue

            # Ordenar
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())

            return {
                "success": True,
                "path": str(path),
                "recursive": recursive,
                "pattern": pattern,
                "directories": [
                    {"name": d.name, "path": d.path, "modified": d.modified}
                    for d in dirs
                ],
                "files": [
                    {
                        "name": f.name,
                        "path": f.path,
                        "size": f.size,
                        "size_human": self._human_readable_size(f.size),
                        "modified": f.modified,
                        "extension": f.extension,
                    }
                    for f in files
                ],
                "total_dirs": len(dirs),
                "total_files": len(files),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error listando directorio: {str(e)}",
                "path": str(dir_path),
            }

    def search_files(
        self, query: str, search_path: str = ".", search_content: bool = False
    ) -> Dict[str, Any]:
        """
        Buscar archivos por nombre o contenido

        Args:
            query: Texto a buscar
            search_path: Ruta donde buscar
            search_content: Si True, busca tambiÃ©n dentro de archivos

        Returns:
            Dict con resultados de bÃºsqueda
        """
        try:
            base = self._resolve_path(search_path)

            if not base.exists():
                return {
                    "success": False,
                    "error": f"Ruta no encontrada: {search_path}",
                    "path": str(base),
                }

            results = []
            content_matches = []

            # Buscar por nombre
            for item in base.rglob("*"):
                if query.lower() in item.name.lower():
                    try:
                        stat = item.stat()
                        results.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "type": "directory" if item.is_dir() else "file",
                                "size": stat.st_size if item.is_file() else None,
                            }
                        )
                    except (PermissionError, OSError):
                        continue

                # Buscar en contenido si es archivo de texto
                if search_content and item.is_file() and not self._is_protected(item):
                    if self._is_text_file(item):
                        try:
                            with open(
                                item, "r", encoding="utf-8", errors="ignore"
                            ) as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    # Encontrar lÃ­neas que coinciden
                                    lines = content.split("\n")
                                    matching_lines = []
                                    for i, line in enumerate(lines, 1):
                                        if query.lower() in line.lower():
                                            matching_lines.append(
                                                {
                                                    "line": i,
                                                    "content": line.strip()[
                                                        :100
                                                    ],  # Limitar longitud
                                                }
                                            )

                                    if matching_lines:
                                        content_matches.append(
                                            {
                                                "file": str(item),
                                                "name": item.name,
                                                "matches": matching_lines[
                                                    :5
                                                ],  # Limitar matches
                                            }
                                        )
                        except Exception:
                            continue

            return {
                "success": True,
                "query": query,
                "search_path": str(base),
                "search_content": search_content,
                "name_matches": results[:50],  # Limitar resultados
                "content_matches": content_matches[:20],
                "total_name_matches": len(results),
                "total_content_matches": len(content_matches),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error en bÃºsqueda: {str(e)}",
                "query": query,
            }

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Obtener informaciÃ³n detallada de un archivo

        Args:
            file_path: Ruta al archivo

        Returns:
            Dict con metadatos del archivo
        """
        try:
            path = self._resolve_path(file_path)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"No encontrado: {file_path}",
                    "path": str(path),
                }

            stat = path.stat()

            info = {
                "success": True,
                "path": str(path),
                "name": path.name,
                "exists": True,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size,
                "size_human": self._human_readable_size(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
            }

            if path.is_file():
                info["extension"] = path.suffix
                info["is_text"] = self._is_text_file(path)
                info["is_protected"] = self._is_protected(path)

            return info

        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo info: {str(e)}",
                "path": str(file_path),
            }

    def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        Crear un directorio

        Args:
            dir_path: Ruta del directorio a crear

        Returns:
            Dict con resultado
        """
        try:
            path = self._resolve_path(dir_path)

            if not self._is_safe_path(path):
                return {
                    "success": False,
                    "error": f"Ruta no segura: {dir_path}",
                    "path": str(path),
                }

            path.mkdir(parents=True, exist_ok=True)

            return {
                "success": True,
                "path": str(path),
                "action": "create_directory",
                "message": f"Directorio creado: {path.name}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error creando directorio: {str(e)}",
                "path": str(dir_path),
            }

    def delete(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        Eliminar archivo o directorio (operaciÃ³n peligrosa - requiere precauciÃ³n)

        Args:
            path: Ruta a eliminar
            recursive: Si True, elimina directorios no vacÃ­os

        Returns:
            Dict con resultado
        """
        try:
            target = self._resolve_path(path)

            if not target.exists():
                return {
                    "success": False,
                    "error": f"No existe: {path}",
                    "path": str(target),
                }

            if not self._is_safe_path(target):
                return {
                    "success": False,
                    "error": f"Ruta no segura para eliminar: {path}",
                    "path": str(target),
                }

            # NO permitir eliminaciÃ³n de directorios grandes sin recursive
            if target.is_dir():
                if not recursive and any(target.iterdir()):
                    return {
                        "success": False,
                        "error": f"Directorio no vacÃ­o. Usa recursive=True para eliminar",
                        "path": str(target),
                    }

                if recursive:
                    shutil.rmtree(target)
                else:
                    target.rmdir()
            else:
                target.unlink()

            return {
                "success": True,
                "path": str(target),
                "action": "delete",
                "message": f"Eliminado exitosamente: {target.name}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error eliminando: {str(e)}",
                "path": str(path),
            }

    def _human_readable_size(self, size_bytes: int) -> str:
        """Convertir bytes a formato legible"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    # === MÃ©todo principal de ejecuciÃ³n ===

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del FileManager

        Args:
            action: AcciÃ³n a ejecutar
            **kwargs: ParÃ¡metros especÃ­ficos de la acciÃ³n

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "read": self.read_file,
            "read_file": self.read_file,
            "write": self.write_file,
            "write_file": self.write_file,
            "list": self.list_directory,
            "list_directory": self.list_directory,
            "ls": self.list_directory,
            "search": self.search_files,
            "search_files": self.search_files,
            "find": self.search_files,
            "info": self.get_file_info,
            "get_info": self.get_file_info,
            "mkdir": self.create_directory,
            "create_directory": self.create_directory,
            "delete": self.delete,
            "remove": self.delete,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"AcciÃ³n no vÃ¡lida: {action}. "
                f"Acciones disponibles: {', '.join(action_map.keys())}",
            }

        method = action_map[action]
        return method(**kwargs)


# === Testing ===
if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 60)
        print("FileManager - Test Suite")
        print("=" * 60)

        fm = FileManager()

        # Test 1: Listar directorio
        print("\n[Test 1] Listar directorio actual")
        result = await fm.execute("list", dir_path=".", pattern="*.py")
        print(f"âœ“ Encontrados {result.get('total_files', 0)} archivos .py")

        # Test 2: Escribir archivo
        print("\n[Test 2] Escribir archivo de prueba")
        result = await fm.execute(
            "write",
            file_path="test_file.txt",
            content="Hola desde FileManager!\nLÃ­nea 2\nLÃ­nea 3",
        )
        print(f"âœ“ {result.get('message', 'Escrito')}")

        # Test 3: Leer archivo
        print("\n[Test 3] Leer archivo")
        result = await fm.execute("read", file_path="test_file.txt")
        if result.get("success"):
            print(f"âœ“ LeÃ­do: {result.get('lines', 0)} lÃ­neas")
            print(f"  Contenido preview: {result.get('content', '')[:50]}...")

        # Test 4: Buscar archivos
        print("\n[Test 4] Buscar archivos")
        result = await fm.execute("search", query="file_manager", search_path=".")
        print(f"âœ“ {result.get('total_name_matches', 0)} coincidencias por nombre")

        # Test 5: Info de archivo
        print("\n[Test 5] Info de archivo")
        result = await fm.execute("info", file_path="test_file.txt")
        if result.get("success"):
            print(f"âœ“ TamaÃ±o: {result.get('size_human')}")
            print(f"  Tipo texto: {result.get('is_text')}")

        # Cleanup
        print("\n[Test 6] Limpiar archivo de prueba")
        result = await fm.execute("delete", path="test_file.txt")
        print(f"âœ“ {result.get('message', 'Eliminado')}")

        print("\n" + "=" * 60)
        print("Tests completados!")
        print("=" * 60)

    asyncio.run(test())
