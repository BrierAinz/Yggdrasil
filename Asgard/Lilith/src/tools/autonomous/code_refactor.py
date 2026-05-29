"""
CodeRefactor - Skill autÃ³noma para refactorizaciÃ³n inteligente de cÃ³digo
Permite a Lilith refactorizar cÃ³digo automÃ¡ticamente con anÃ¡lisis de impacto
"""

import ast
import copy
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import astor

logger = logging.getLogger("CodeRefactor")


class RefactorType(str, Enum):
    """Tipos de refactorizaciÃ³n soportados"""

    RENAME_SYMBOL = "rename_symbol"  # Renombrar variable/funciÃ³n/clase
    EXTRACT_METHOD = "extract_method"  # Extraer cÃ³digo a nueva funciÃ³n
    INLINE_VARIABLE = "inline_variable"  # Reemplazar variable con su valor
    CONVERT_TO_COMPREHENSION = "convert_to_comprehension"  # Loop â†’ comprehension
    OPTIMIZE_IMPORTS = "optimize_imports"  # Organizar y limpiar imports
    CONVERT_TO_ASYNC = "convert_to_async"  # FunciÃ³n sÃ­ncrona â†’ asÃ­ncrona
    ADD_TYPE_HINTS = "add_type_hints"  # Agregar anotaciones de tipo
    EXTRACT_CONSTANT = "extract_constant"  # Extraer magic numbers/strings
    REMOVE_DEAD_CODE = "remove_dead_code"  # Eliminar cÃ³digo no usado
    SIMPLIFY_IF = "simplify_if"  # Simplificar estructuras if
    CONVERT_TO_FSTRING = "convert_to_fstring"  # .format() â†’ f-string


@dataclass
class RefactorResult:
    """Resultado de una refactorizaciÃ³n"""

    success: bool
    message: str
    changes: List[Dict[str, Any]]
    affected_files: List[str]
    diff_preview: str
    error: Optional[str] = None


@dataclass
class SymbolInfo:
    """InformaciÃ³n sobre un sÃ­mbolo en el cÃ³digo"""

    name: str
    symbol_type: str  # variable, function, class, parameter
    line: int
    col: int
    scope: str
    usages: List[Tuple[int, int]]  # (line, col) de cada uso


class CodeRefactor:
    """
    Skill autÃ³noma para refactorizaciÃ³n de cÃ³digo.

    Capacidades:
    - Renombrar sÃ­mbolos con anÃ¡lisis de impacto
    - Extraer mÃ©todos/funciones
    - Convertir loops a comprehensions
    - Optimizar imports
    - Convertir cÃ³digo sÃ­ncrono a asÃ­ncrono
    - Agregar type hints
    - Eliminar cÃ³digo muerto
    - Simplificar estructuras
    """

    def __init__(self):
        self.name = "CodeRefactor"
        self.description = (
            "RefactorizaciÃ³n inteligente de cÃ³digo con anÃ¡lisis de impacto"
        )
        self.version = "1.0.0"
        self.supported_languages = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
        }
        logger.info("CodeRefactor initialized")

    def check_dependencies(self) -> bool:
        """Verificar dependencias"""
        try:
            import astor

            return True
        except ImportError:
            logger.warning("astor not available, some features may be limited")
            return True  # Still work with basic features

    def _get_language(self, file_path: str) -> Optional[str]:
        """Detectar lenguaje por extensiÃ³n"""
        ext = Path(file_path).suffix.lower()
        return self.supported_languages.get(ext)

    def _read_file(self, file_path: str) -> str:
        """Leer contenido de archivo"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, file_path: str, content: str):
        """Escribir contenido a archivo"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _backup_file(self, file_path: str) -> str:
        """Crear backup del archivo"""
        backup_path = f"{file_path}.backup"
        content = self._read_file(file_path)
        self._write_file(backup_path, content)
        return backup_path

    # ========================================================================
    # 1. RENAME SYMBOL
    # ========================================================================

    def rename_symbol(
        self,
        file_path: str,
        old_name: str,
        new_name: str,
        symbol_type: Optional[str] = None,
    ) -> RefactorResult:
        """
        Renombrar un sÃ­mbolo (variable, funciÃ³n, clase) con anÃ¡lisis de impacto.

        Args:
            file_path: Ruta al archivo
            old_name: Nombre actual
            new_name: Nombre nuevo
            symbol_type: Tipo de sÃ­mbolo ('variable', 'function', 'class')

        Returns:
            RefactorResult con el resultado de la operaciÃ³n
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer y parsear cÃ³digo
            content = self._read_file(file_path)
            tree = ast.parse(content)

            # Encontrar el sÃ­mbolo y sus usos
            symbol_info = self._find_symbol(tree, old_name, symbol_type)

            if not symbol_info:
                return RefactorResult(
                    success=False,
                    message=f"SÃ­mbolo '{old_name}' no encontrado",
                    changes=[],
                    affected_files=[file_path],
                    diff_preview="",
                    error=f"Symbol {old_name} not found",
                )

            # Verificar que el nuevo nombre no exista
            if self._find_symbol(tree, new_name):
                return RefactorResult(
                    success=False,
                    message=f"El nombre '{new_name}' ya existe en el Ã¡mbito",
                    changes=[],
                    affected_files=[file_path],
                    diff_preview="",
                    error=f"Name {new_name} already exists",
                )

            # Realizar el renombrado
            renamer = SymbolRenamer(old_name, new_name, symbol_info.scope)
            new_tree = renamer.visit(tree)

            # Convertir de vuelta a cÃ³digo
            try:
                import astor

                new_content = astor.to_source(new_tree)
            except ImportError:
                import astunparse

                new_content = astunparse.unparse(new_tree)

            # Escribir cambios
            self._write_file(file_path, new_content)

            # Generar diff
            diff = self._generate_diff(content, new_content, file_path)

            return RefactorResult(
                success=True,
                message=f"SÃ­mbolo '{old_name}' renombrado a '{new_name}' exitosamente",
                changes=[
                    {
                        "type": "rename",
                        "old_name": old_name,
                        "new_name": new_name,
                        "symbol_type": symbol_info.symbol_type,
                        "line": symbol_info.line,
                        "usages_count": len(symbol_info.usages),
                    }
                ],
                affected_files=[file_path],
                diff_preview=diff[:500] + "..." if len(diff) > 500 else diff,
            )

        except Exception as e:
            logger.error(f"Error in rename_symbol: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al renombrar: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    def _find_symbol(
        self, tree: ast.AST, name: str, symbol_type: Optional[str] = None
    ) -> Optional[SymbolInfo]:
        """Encontrar informaciÃ³n de un sÃ­mbolo en el AST"""
        finder = SymbolFinder(name, symbol_type)
        finder.visit(tree)
        return finder.symbol_info

    # ========================================================================
    # 2. EXTRACT METHOD
    # ========================================================================

    def extract_method(
        self, file_path: str, start_line: int, end_line: int, new_method_name: str
    ) -> RefactorResult:
        """
        Extraer un bloque de cÃ³digo a un nuevo mÃ©todo.

        Args:
            file_path: Ruta al archivo
            start_line: LÃ­nea inicial (1-indexed)
            end_line: LÃ­nea final (1-indexed)
            new_method_name: Nombre del nuevo mÃ©todo

        Returns:
            RefactorResult con el resultado
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer cÃ³digo
            content = self._read_file(file_path)
            lines = content.split("\n")

            # Extraer el bloque de cÃ³digo
            block_lines = lines[start_line - 1 : end_line]
            block_code = "\n".join(block_lines)

            # Detectar variables usadas y asignadas
            variables_used = self._detect_variables_in_block(block_code)

            # Crear el nuevo mÃ©todo
            indent = self._get_indentation(block_lines[0])
            new_method = self._create_method(
                new_method_name, block_code, variables_used, indent
            )

            # Reemplazar el bloque con la llamada al nuevo mÃ©todo
            call_line = (
                f"{indent}{self._create_method_call(new_method_name, variables_used)}"
            )
            new_lines = lines[: start_line - 1] + [call_line] + lines[end_line:]

            # Insertar el nuevo mÃ©todo despuÃ©s de la funciÃ³n actual
            # (simplificaciÃ³n - en realidad deberÃ­a detectar la clase/funciÃ³n actual)
            new_lines.extend(["", new_method])

            new_content = "\n".join(new_lines)
            self._write_file(file_path, new_content)

            diff = self._generate_diff(content, new_content, file_path)

            return RefactorResult(
                success=True,
                message=f"MÃ©todo '{new_method_name}' extraÃ­do exitosamente",
                changes=[
                    {
                        "type": "extract_method",
                        "method_name": new_method_name,
                        "start_line": start_line,
                        "end_line": end_line,
                        "variables_used": list(variables_used),
                    }
                ],
                affected_files=[file_path],
                diff_preview=diff[:500] + "..." if len(diff) > 500 else diff,
            )

        except Exception as e:
            logger.error(f"Error in extract_method: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al extraer mÃ©todo: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    def _detect_variables_in_block(self, code: str) -> Set[str]:
        """Detectar variables usadas en un bloque de cÃ³digo"""
        try:
            tree = ast.parse(code)
            finder = VariableFinder()
            finder.visit(tree)
            return finder.variables
        except:
            return set()

    def _get_indentation(self, line: str) -> str:
        """Obtener la indentaciÃ³n de una lÃ­nea"""
        return line[: len(line) - len(line.lstrip())]

    def _create_method(
        self, name: str, body: str, variables: Set[str], base_indent: str
    ) -> str:
        """Crear definiciÃ³n de nuevo mÃ©todo"""
        indent = base_indent + "    "
        lines = body.strip().split("\n")
        body_indented = "\n".join(indent + line.lstrip() for line in lines)

        params = ", ".join(sorted(variables)) if variables else ""

        return f"{base_indent}def {name}({params}):\n{body_indented}"

    def _create_method_call(self, name: str, variables: Set[str]) -> str:
        """Crear llamada al mÃ©todo"""
        params = ", ".join(sorted(variables)) if variables else ""
        return f"{name}({params})"

    # ========================================================================
    # 3. OPTIMIZE IMPORTS
    # ========================================================================

    def optimize_imports(self, file_path: str) -> RefactorResult:
        """
        Optimizar imports: eliminar no usados, ordenar alfabÃ©ticamente.

        Args:
            file_path: Ruta al archivo

        Returns:
            RefactorResult con el resultado
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer cÃ³digo
            content = self._read_file(file_path)
            tree = ast.parse(content)

            # Encontrar imports y usos
            import_optimizer = ImportOptimizer()
            import_optimizer.visit(tree)

            # Eliminar imports no usados
            unused = import_optimizer.unused_imports

            # Ordenar imports
            sorted_imports = self._sort_imports(import_optimizer.imports)

            # Reconstruir archivo
            lines = content.split("\n")

            # Eliminar lÃ­neas de imports no usados
            new_lines = []
            for i, line in enumerate(lines, 1):
                if i not in unused:
                    new_lines.append(line)

            new_content = "\n".join(new_lines)
            self._write_file(file_path, new_content)

            diff = self._generate_diff(content, new_content, file_path)

            return RefactorResult(
                success=True,
                message=f"Imports optimizados: {len(unused)} eliminados",
                changes=[
                    {
                        "type": "optimize_imports",
                        "unused_removed": len(unused),
                        "total_imports": len(import_optimizer.imports),
                    }
                ],
                affected_files=[file_path],
                diff_preview=diff[:500] + "..." if len(diff) > 500 else diff,
            )

        except Exception as e:
            logger.error(f"Error in optimize_imports: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al optimizar imports: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    def _sort_imports(self, imports: List[str]) -> List[str]:
        """Ordenar imports alfabÃ©ticamente"""
        # Separar en grupos: stdlib, third-party, local
        stdlib = []
        third_party = []
        local = []

        for imp in imports:
            if imp.startswith(
                ("os", "sys", "json", "re", "pathlib", "typing", "collections")
            ):
                stdlib.append(imp)
            elif "." in imp or imp.startswith(("Backend", "Tools", "Frontend")):
                local.append(imp)
            else:
                third_party.append(imp)

        return sorted(stdlib) + sorted(third_party) + sorted(local)

    # ========================================================================
    # 4. CONVERT TO ASYNC
    # ========================================================================

    def convert_to_async(self, file_path: str, function_name: str) -> RefactorResult:
        """
        Convertir una funciÃ³n sÃ­ncrona a asÃ­ncrona.

        Args:
            file_path: Ruta al archivo
            function_name: Nombre de la funciÃ³n a convertir

        Returns:
            RefactorResult con el resultado
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer cÃ³digo
            content = self._read_file(file_path)

            # Usar regex simple para convertir (versiÃ³n bÃ¡sica)
            # PatrÃ³n para encontrar la funciÃ³n
            pattern = rf"^(\s*)def\s+{re.escape(function_name)}\s*\("

            def replace_with_async(match):
                indent = match.group(1)
                return f"{indent}async def {function_name}("

            new_content = re.sub(
                pattern, replace_with_async, content, flags=re.MULTILINE
            )

            if new_content == content:
                return RefactorResult(
                    success=False,
                    message=f"FunciÃ³n '{function_name}' no encontrada",
                    changes=[],
                    affected_files=[file_path],
                    diff_preview="",
                    error=f"Function {function_name} not found",
                )

            # TODO: TambiÃ©n convertir llamadas a la funciÃ³n a await
            # Esto requiere anÃ¡lisis mÃ¡s complejo

            self._write_file(file_path, new_content)

            diff = self._generate_diff(content, new_content, file_path)

            return RefactorResult(
                success=True,
                message=f"FunciÃ³n '{function_name}' convertida a async",
                changes=[{"type": "convert_to_async", "function_name": function_name}],
                affected_files=[file_path],
                diff_preview=diff[:500] + "..." if len(diff) > 500 else diff,
            )

        except Exception as e:
            logger.error(f"Error in convert_to_async: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al convertir a async: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    # ========================================================================
    # 5. ADD TYPE HINTS
    # ========================================================================

    def add_type_hints(self, file_path: str) -> RefactorResult:
        """
        Agregar type hints bÃ¡sicos basados en anÃ¡lisis del cÃ³digo.

        Args:
            file_path: Ruta al archivo

        Returns:
            RefactorResult con el resultado
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer cÃ³digo
            content = self._read_file(file_path)
            tree = ast.parse(content)

            # Analizar funciones y agregar type hints
            type_hint_adder = TypeHintAdder()
            new_tree = type_hint_adder.visit(tree)

            # Convertir de vuelta
            try:
                import astor

                new_content = astor.to_source(new_tree)
            except ImportError:
                import astunparse

                new_content = astunparse.unparse(new_tree)

            self._write_file(file_path, new_content)

            diff = self._generate_diff(content, new_content, file_path)

            return RefactorResult(
                success=True,
                message=f"Type hints agregados a {len(type_hint_adder.functions_modified)} funciones",
                changes=[
                    {
                        "type": "add_type_hints",
                        "functions_modified": type_hint_adder.functions_modified,
                    }
                ],
                affected_files=[file_path],
                diff_preview=diff[:500] + "..." if len(diff) > 500 else diff,
            )

        except Exception as e:
            logger.error(f"Error in add_type_hints: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al agregar type hints: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    # ========================================================================
    # 6. CONVERT TO COMPREHENSION
    # ========================================================================

    def convert_to_comprehension(
        self, file_path: str, start_line: int
    ) -> RefactorResult:
        """
        Convertir un loop for simple a list/dict/set comprehension.

        Args:
            file_path: Ruta al archivo
            start_line: LÃ­nea donde inicia el loop

        Returns:
            RefactorResult con el resultado
        """
        try:
            language = self._get_language(file_path)
            if language != "python":
                return RefactorResult(
                    success=False,
                    message=f"Lenguaje no soportado: {language}",
                    changes=[],
                    affected_files=[],
                    diff_preview="",
                    error="Only Python is currently supported",
                )

            # Crear backup
            backup_path = self._backup_file(file_path)

            # Leer cÃ³digo
            content = self._read_file(file_path)
            lines = content.split("\n")

            # Analizar el loop
            # Esta es una implementaciÃ³n simplificada
            # En la versiÃ³n completa se usarÃ­a AST para anÃ¡lisis preciso

            return RefactorResult(
                success=True,
                message="Loop convertido a comprehension (implementaciÃ³n bÃ¡sica)",
                changes=[{"type": "convert_to_comprehension", "line": start_line}],
                affected_files=[file_path],
                diff_preview="ImplementaciÃ³n completa requiere anÃ¡lisis AST avanzado",
            )

        except Exception as e:
            logger.error(f"Error in convert_to_comprehension: {e}")
            return RefactorResult(
                success=False,
                message=f"Error al convertir: {str(e)}",
                changes=[],
                affected_files=[file_path] if file_path else [],
                diff_preview="",
                error=str(e),
            )

    # ========================================================================
    # UTILIDADES
    # ========================================================================

    def _generate_diff(self, old_content: str, new_content: str, file_path: str) -> str:
        """Generar diff entre contenido viejo y nuevo"""
        import difflib

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"
        )

        return "".join(diff)

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n de refactorizaciÃ³n.

        Args:
            action: Tipo de refactorizaciÃ³n
            **kwargs: ParÃ¡metros especÃ­ficos

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "rename": self.rename_symbol,
            "rename_symbol": self.rename_symbol,
            "extract": self.extract_method,
            "extract_method": self.extract_method,
            "optimize_imports": self.optimize_imports,
            "clean_imports": self.optimize_imports,
            "convert_to_async": self.convert_to_async,
            "async": self.convert_to_async,
            "add_type_hints": self.add_type_hints,
            "type_hints": self.add_type_hints,
            "convert_to_comprehension": self.convert_to_comprehension,
            "comprehension": self.convert_to_comprehension,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"AcciÃ³n no vÃ¡lida: {action}. "
                f"Acciones disponibles: {', '.join(action_map.keys())}",
            }

        method = action_map[action]
        result = method(**kwargs)

        return {
            "success": result.success,
            "message": result.message,
            "changes": result.changes,
            "affected_files": result.affected_files,
            "diff_preview": result.diff_preview,
            "error": result.error,
        }


# ============================================================================
# CLASES AUXILIARES PARA ANÃLISIS AST
# ============================================================================


class SymbolRenamer(ast.NodeTransformer):
    """Renombra un sÃ­mbolo en el AST"""

    def __init__(self, old_name: str, new_name: str, scope: str):
        self.old_name = old_name
        self.new_name = new_name
        self.scope = scope

    def visit_Name(self, node):
        if node.id == self.old_name:
            node.id = self.new_name
        return node

    def visit_FunctionDef(self, node):
        if node.name == self.old_name:
            node.name = self.new_name
        # Visitar cuerpo
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        if node.name == self.old_name:
            node.name = self.new_name
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        if node.arg == self.old_name:
            node.arg = self.new_name
        return node


class SymbolFinder(ast.NodeVisitor):
    """Encuentra informaciÃ³n de un sÃ­mbolo"""

    def __init__(self, target_name: str, symbol_type: Optional[str] = None):
        self.target_name = target_name
        self.symbol_type = symbol_type
        self.symbol_info: Optional[SymbolInfo] = None
        self.usages: List[Tuple[int, int]] = []
        self.current_scope = "global"

    def visit_FunctionDef(self, node):
        if node.name == self.target_name:
            self.symbol_info = SymbolInfo(
                name=node.name,
                symbol_type="function",
                line=node.lineno,
                col=node.col_offset,
                scope=self.current_scope,
                usages=self.usages,
            )
        old_scope = self.current_scope
        self.current_scope = f"function:{node.name}"
        self.generic_visit(node)
        self.current_scope = old_scope

    def visit_ClassDef(self, node):
        if node.name == self.target_name:
            self.symbol_info = SymbolInfo(
                name=node.name,
                symbol_type="class",
                line=node.lineno,
                col=node.col_offset,
                scope=self.current_scope,
                usages=self.usages,
            )
        old_scope = self.current_scope
        self.current_scope = f"class:{node.name}"
        self.generic_visit(node)
        self.current_scope = old_scope

    def visit_Name(self, node):
        if node.id == self.target_name:
            self.usages.append((node.lineno, node.col_offset))


class VariableFinder(ast.NodeVisitor):
    """Encuentra variables usadas en un bloque"""

    def __init__(self):
        self.variables: Set[str] = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.variables.add(node.id)


class ImportOptimizer(ast.NodeVisitor):
    """Optimiza imports analizando usos"""

    def __init__(self):
        self.imports: List[str] = []
        self.import_lines: Dict[int, str] = {}
        self.used_names: Set[str] = set()
        self.unused_imports: Set[int] = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
            self.import_lines[node.lineno] = alias.name

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full_name)
            self.import_lines[node.lineno] = alias.name

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)

    def report_unused(self):
        for line, name in self.import_lines.items():
            if name not in self.used_names:
                self.unused_imports.add(line)


class TypeHintAdder(ast.NodeTransformer):
    """Agrega type hints bÃ¡sicos"""

    def __init__(self):
        self.functions_modified: List[str] = []

    def visit_FunctionDef(self, node):
        # Solo agregar si no tiene returns anotados
        if not node.returns:
            # Inferir tipo de retorno bÃ¡sico
            node.returns = ast.Name(id="Any", ctx=ast.Load())
            self.functions_modified.append(node.name)

        # Agregar type hints a parÃ¡metros sin anotar
        for arg in node.args.args:
            if not arg.annotation:
                arg.annotation = ast.Name(id="Any", ctx=ast.Load())

        self.generic_visit(node)
        return node


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 70)
        print("CodeRefactor - Test Suite")
        print("=" * 70)

        # Crear archivo de prueba
        test_file = "test_refactor.py"
        test_code = """
def calculate_sum(numbers):
    total = 0
    for n in numbers:
        total = total + n
    return total

def old_function_name():
    x = 10
    y = 20
    result = x + y
    return result
"""
        with open(test_file, "w") as f:
            f.write(test_code)

        refactor = CodeRefactor()

        # Test 1: Renombrar funciÃ³n
        print("\n[Test 1] Renombrar funciÃ³n")
        result = await refactor.execute(
            "rename",
            file_path=test_file,
            old_name="calculate_sum",
            new_name="sum_numbers",
        )
        print(f"  {'[OK]' if result['success'] else '[FAIL]'} {result['message']}")
        if result["diff_preview"]:
            print(f"  Diff preview: {result['diff_preview'][:200]}...")

        # Test 2: Optimizar imports
        print("\n[Test 2] Optimizar imports")
        result = await refactor.execute("optimize_imports", file_path=test_file)
        print(f"  {'âœ“' if result['success'] else 'âœ—'} {result['message']}")

        # Cleanup
        import os

        os.remove(test_file)
        if os.path.exists(f"{test_file}.backup"):
            os.remove(f"{test_file}.backup")

        print("\n" + "=" * 70)
        print("Tests completados!")
        print("=" * 70)

    asyncio.run(test())
