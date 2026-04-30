"""
AutoFixer - Skill autÃ³noma para detecciÃ³n y correcciÃ³n automÃ¡tica de errores

Permite a Lilith:
- Detectar errores de sintaxis en cÃ³digo
- Identificar problemas comunes (imports, indentaciÃ³n, typos)
- Sugerir y aplicar correcciones automÃ¡ticamente
- Integrarse con AutoHealer para fixes mÃ¡s complejos
"""

import ast
import difflib
import logging
import os
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("AutoFixer")


class ErrorSeverity(str, Enum):
    """Niveles de severidad de errores"""

    CRITICAL = "critical"  # Syntax errors, imports rotos
    HIGH = "high"  # Errores de runtime probables
    MEDIUM = "medium"  # Code smells, potenciales bugs
    LOW = "low"  # Warnings, style issues


class FixType(str, Enum):
    """Tipos de correcciones"""

    SYNTAX = "syntax"
    IMPORT = "import"
    INDENTATION = "indentation"
    TYPO = "typo"
    STYLE = "style"
    LOGIC = "logic"
    TYPE = "type"


@dataclass
class CodeIssue:
    """Representa un problema encontrado en el cÃ³digo"""

    line: int
    column: int
    severity: ErrorSeverity
    message: str
    fix_type: FixType
    code_snippet: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "severity": self.severity.value,
            "fix_type": self.fix_type.value,
        }


@dataclass
class FixResult:
    """Resultado de una correcciÃ³n"""

    success: bool
    original: str
    fixed: str
    issues_fixed: List[CodeIssue]
    issues_remaining: List[CodeIssue]
    diff: str
    message: str


class AutoFixer:
    """
    Skill autÃ³noma para detecciÃ³n y correcciÃ³n de errores de cÃ³digo.

    Capacidades:
    - AnÃ¡lisis de sintaxis Python (AST)
    - DetecciÃ³n de imports no usados/faltantes
    - CorrecciÃ³n de indentaciÃ³n comÃºn
    - DetecciÃ³n de typos en nombres
    - Sugerencias de tipo
    - GeneraciÃ³n de diffs
    """

    def __init__(self, backup_dir: Optional[str] = None):
        self.name = "AutoFixer"
        self.description = "Detecta y corrige errores de cÃ³digo automÃ¡ticamente"
        self.version = "1.0.0"

        # Directorio para backups
        self.backup_dir = backup_dir or os.path.join(
            os.path.expanduser("~"), ".Lilith", "backups"
        )
        os.makedirs(self.backup_dir, exist_ok=True)

        # Patrones comunes de errores y sus fixes
        self.syntax_fixes = [
            # Missing colon in function/class definition
            (
                r"^(\s*)(def|class|if|elif|else|for|while|try|except|finally|with)\s+(.+?)(?::\s*)?$",
                r"\1\2 \3:",
                FixType.SYNTAX,
                "Falta dos puntos al final de la declaraciÃ³n",
            ),
            # Double equals in assignment
            (
                r"(\w+)\s*==\s*([^=]+)(?![=])\s*$",
                r"\1 = \2",
                FixType.SYNTAX,
                "Usando == en lugar de = en asignaciÃ³n",
            ),
        ]

        # Imports comunes que se pueden sugerir
        self.common_imports = {
            "os": "import os",
            "sys": "import sys",
            "json": "import json",
            "re": "import re",
            "pathlib": "from pathlib import Path",
            "typing": "from typing import Dict, List, Any, Optional",
            "datetime": "from datetime import datetime",
            "logging": "import logging",
            "asyncio": "import asyncio",
            "requests": "import requests",
            "numpy": "import numpy as np",
            "pandas": "import pandas as pd",
        }

        logger.info("AutoFixer initialized")

    def _create_backup(self, file_path: str) -> str:
        """Crear backup de archivo antes de modificar"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{Path(file_path).name}.{timestamp}.bak"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""

    def analyze_syntax(self, code: str) -> List[CodeIssue]:
        """
        Analizar cÃ³digo Python para errores de sintaxis

        Args:
            code: CÃ³digo Python a analizar

        Returns:
            Lista de problemas encontrados
        """
        issues = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            # Error de sintaxis real
            lines = code.split("\n")
            error_line = (
                lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else ""
            )

            issue = CodeIssue(
                line=e.lineno or 1,
                column=e.offset or 0,
                severity=ErrorSeverity.CRITICAL,
                message=str(e),
                fix_type=FixType.SYNTAX,
                code_snippet=error_line,
                suggested_fix=None,
                auto_fixable=False,  # Errores de sintaxis requieren anÃ¡lisis manual
            )
            issues.append(issue)
        except Exception as e:
            issue = CodeIssue(
                line=1,
                column=0,
                severity=ErrorSeverity.CRITICAL,
                message=f"Error parseando cÃ³digo: {str(e)}",
                fix_type=FixType.SYNTAX,
                code_snippet=code[:100],
                auto_fixable=False,
            )
            issues.append(issue)

        return issues

    def analyze_imports(self, code: str) -> List[CodeIssue]:
        """
        Analizar imports del cÃ³digo

        Args:
            code: CÃ³digo a analizar

        Returns:
            Lista de problemas con imports
        """
        issues = []

        # Detectar imports no usados
        try:
            tree = ast.parse(code)
            imported_names = set()
            used_names = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)

            # Imports no usados
            unused = imported_names - used_names
            for imp in unused:
                # Encontrar lÃ­nea del import
                for i, line in enumerate(code.split("\n"), 1):
                    if imp in line and ("import" in line or "from" in line):
                        issue = CodeIssue(
                            line=i,
                            column=0,
                            severity=ErrorSeverity.LOW,
                            message=f"Import '{imp}' no estÃ¡ siendo usado",
                            fix_type=FixType.IMPORT,
                            code_snippet=line.strip(),
                            suggested_fix=f"# Eliminar: {line.strip()}",
                            auto_fixable=False,  # Mejor no eliminar automÃ¡ticamente
                        )
                        issues.append(issue)
                        break

            # Detectar uso de mÃ³dulos sin importar
            common_modules = [
                "os",
                "sys",
                "json",
                "re",
                "pathlib",
                "datetime",
                "logging",
                "typing",
                "asyncio",
                "requests",
            ]

            for module in common_modules:
                # Buscar uso del mÃ³dulo
                pattern = rf"\b{module}\.\w+"
                if re.search(pattern, code) and module not in imported_names:
                    # Verificar que realmente no estÃ¡ importado
                    if module not in used_names:
                        continue

                    # Encontrar primera lÃ­nea que usa el mÃ³dulo
                    for i, line in enumerate(code.split("\n"), 1):
                        if re.search(rf"\b{module}\.", line):
                            suggested = self.common_imports.get(
                                module, f"import {module}"
                            )
                            issue = CodeIssue(
                                line=i,
                                column=0,
                                severity=ErrorSeverity.CRITICAL,
                                message=f"Usando '{module}' pero no estÃ¡ importado",
                                fix_type=FixType.IMPORT,
                                code_snippet=line.strip(),
                                suggested_fix=suggested,
                                auto_fixable=True,
                            )
                            issues.append(issue)
                            break

        except Exception as e:
            logger.error(f"Error analyzing imports: {e}")

        return issues

    def analyze_indentation(self, code: str) -> List[CodeIssue]:
        """
        Analizar problemas de indentaciÃ³n comunes

        Args:
            code: CÃ³digo a analizar

        Returns:
            Lista de problemas de indentaciÃ³n
        """
        issues = []
        lines = code.split("\n")

        prev_indent = 0
        for i, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith("#"):
                continue

            current_indent = len(line) - len(line.lstrip())

            # Detectar cambios bruscos de indentaciÃ³n (mix de tabs y spaces)
            if "\t" in line[:current_indent] and " " in line[:current_indent]:
                issue = CodeIssue(
                    line=i,
                    column=0,
                    severity=ErrorSeverity.HIGH,
                    message="Mezcla de tabs y espacios en indentaciÃ³n",
                    fix_type=FixType.INDENTATION,
                    code_snippet=line,
                    suggested_fix=line.replace("\t", "    "),
                    auto_fixable=True,
                )
                issues.append(issue)

            prev_indent = current_indent

        return issues

    def analyze_common_issues(self, code: str) -> List[CodeIssue]:
        """
        Analizar problemas comunes de cÃ³digo

        Args:
            code: CÃ³digo a analizar

        Returns:
            Lista de problemas encontrados
        """
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Variable asignada pero nunca usada
            match = re.match(r"^(\s*)(\w+)\s*=\s*(.+)$", stripped)
            if match and not stripped.startswith("#"):
                var_name = match.group(2)
                # Verificar si se usa despuÃ©s (simplificado)
                rest_of_code = "\n".join(lines[i:])
                if not re.search(rf"\b{var_name}\b", rest_of_code):
                    # PodrÃ­a ser falso positivo, solo warning
                    pass

            # ComparaciÃ³n con None usando ==
            if re.search(r"==\s*None", line) or re.search(r"None\s*==", line):
                issue = CodeIssue(
                    line=i,
                    column=line.find("None"),
                    severity=ErrorSeverity.MEDIUM,
                    message="Usar 'is None' en lugar de '== None'",
                    fix_type=FixType.STYLE,
                    code_snippet=stripped,
                    suggested_fix=re.sub(
                        r"==\s*None",
                        "is None",
                        re.sub(r"None\s*==", "is None", stripped),
                    ),
                    auto_fixable=True,
                )
                issues.append(issue)

            # ComparaciÃ³n con True/False usando ==
            if re.search(r"==\s*True", line) or re.search(r"True\s*==", line):
                issue = CodeIssue(
                    line=i,
                    column=line.find("True"),
                    severity=ErrorSeverity.LOW,
                    message="No es necesario comparar con True explÃ­citamente",
                    fix_type=FixType.STYLE,
                    code_snippet=stripped,
                    suggested_fix=re.sub(
                        r"==\s*True\b", "", re.sub(r"\bTrue\s*==", "", stripped)
                    ).strip(),
                    auto_fixable=True,
                )
                issues.append(issue)

            # print sin parÃ©ntesis (Python 2 style)
            if re.match(r"^\s*print\s+[^(]", stripped):
                issue = CodeIssue(
                    line=i,
                    column=line.find("print"),
                    severity=ErrorSeverity.CRITICAL,
                    message="Sintaxis de Python 2 detectada, usar print()",
                    fix_type=FixType.SYNTAX,
                    code_snippet=stripped,
                    suggested_fix=re.sub(r"print\s+(.+)", r"print(\1)", stripped),
                    auto_fixable=True,
                )
                issues.append(issue)

            # mutable default argument
            if re.search(r"def\s+\w+\s*\([^)]*=\s*(\[|\{)", stripped):
                issue = CodeIssue(
                    line=i,
                    column=0,
                    severity=ErrorSeverity.HIGH,
                    message="Argumento mutable por defecto detectado (lista/dict)",
                    fix_type=FixType.LOGIC,
                    code_snippet=stripped,
                    suggested_fix="Usar None como default y crear mutable dentro de la funciÃ³n",
                    auto_fixable=False,
                )
                issues.append(issue)

            # bare except
            if (
                re.search(r"except\s*:", stripped)
                and "except Exception" not in stripped
            ):
                issue = CodeIssue(
                    line=i,
                    column=line.find("except"),
                    severity=ErrorSeverity.MEDIUM,
                    message="Bare except: captura todas las excepciones incluyendo KeyboardInterrupt",
                    fix_type=FixType.STYLE,
                    code_snippet=stripped,
                    suggested_fix="Usar 'except Exception:' como mÃ­nimo",
                    auto_fixable=True,
                )
                issues.append(issue)

        return issues

    def analyze(self, code: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Analizar cÃ³digo completo

        Args:
            code: CÃ³digo a analizar
            file_path: Ruta del archivo (opcional)

        Returns:
            Dict con todos los problemas encontrados
        """
        all_issues = []

        # Ejecutar todos los anÃ¡lisis
        all_issues.extend(self.analyze_syntax(code))
        all_issues.extend(self.analyze_imports(code))
        all_issues.extend(self.analyze_indentation(code))
        all_issues.extend(self.analyze_common_issues(code))

        # Contar por severidad
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        auto_fixable_count = 0
        for issue in all_issues:
            severity_counts[issue.severity.value] += 1
            if issue.auto_fixable:
                auto_fixable_count += 1

        # Ordenar por severidad y lÃ­nea
        severity_order = {
            ErrorSeverity.CRITICAL: 0,
            ErrorSeverity.HIGH: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.LOW: 3,
        }
        all_issues.sort(key=lambda x: (severity_order[x.severity], x.line))

        return {
            "success": True,
            "file_path": file_path,
            "total_issues": len(all_issues),
            "auto_fixable": auto_fixable_count,
            "by_severity": severity_counts,
            "issues": [issue.to_dict() for issue in all_issues],
        }

    def apply_fixes(self, code: str, issues: List[CodeIssue]) -> FixResult:
        """
        Aplicar correcciones automÃ¡ticas

        Args:
            code: CÃ³digo original
            issues: Lista de problemas a corregir

        Returns:
            Resultado de las correcciones
        """
        lines = code.split("\n")
        fixed_lines = lines.copy()
        fixed_issues = []
        remaining_issues = []

        for issue in issues:
            if not issue.auto_fixable or not issue.suggested_fix:
                remaining_issues.append(issue)
                continue

            try:
                line_idx = issue.line - 1
                if 0 <= line_idx < len(fixed_lines):
                    original_line = fixed_lines[line_idx]

                    # Aplicar fix segÃºn tipo
                    if issue.fix_type == FixType.INDENTATION:
                        fixed_lines[line_idx] = issue.suggested_fix
                    elif issue.fix_type == FixType.SYNTAX and "print" in original_line:
                        fixed_lines[line_idx] = issue.suggested_fix
                    elif (
                        issue.fix_type == FixType.STYLE
                        and issue.message == "Usar 'is None'"
                    ):
                        fixed_lines[line_idx] = issue.suggested_fix
                    elif issue.fix_type == FixType.STYLE and "except" in original_line:
                        fixed_lines[line_idx] = re.sub(
                            r"except\s*:", "except Exception:", original_line
                        )
                    else:
                        remaining_issues.append(issue)
                        continue

                    fixed_issues.append(issue)
            except Exception as e:
                logger.error(f"Error applying fix: {e}")
                remaining_issues.append(issue)

        fixed_code = "\n".join(fixed_lines)

        # Generar diff
        diff = "\n".join(
            difflib.unified_diff(
                lines, fixed_lines, fromfile="original", tofile="fixed", lineterm=""
            )
        )

        return FixResult(
            success=True,
            original=code,
            fixed=fixed_code,
            issues_fixed=fixed_issues,
            issues_remaining=remaining_issues,
            diff=diff,
            message=f"Corregidos {len(fixed_issues)} de {len(issues)} problemas",
        )

    def fix_file(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Analizar y corregir un archivo

        Args:
            file_path: Ruta del archivo
            dry_run: Si True, no modifica el archivo

        Returns:
            Dict con resultado
        """
        try:
            # Verificar que es archivo Python
            if not file_path.endswith(".py"):
                return {
                    "success": False,
                    "error": f"Solo archivos .py son soportados: {file_path}",
                }

            # Leer archivo
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Analizar
            analysis = self.analyze(code, file_path)

            if analysis["total_issues"] == 0:
                return {
                    "success": True,
                    "message": "No se encontraron problemas",
                    "file_path": file_path,
                    "issues": [],
                    "changes_made": False,
                }

            # Convertir dict issues a objetos
            issues = []
            for issue_dict in analysis["issues"]:
                issue = CodeIssue(
                    line=issue_dict["line"],
                    column=issue_dict["column"],
                    severity=ErrorSeverity(issue_dict["severity"]),
                    message=issue_dict["message"],
                    fix_type=FixType(issue_dict["fix_type"]),
                    code_snippet=issue_dict["code_snippet"],
                    suggested_fix=issue_dict.get("suggested_fix"),
                    auto_fixable=issue_dict.get("auto_fixable", False),
                )
                issues.append(issue)

            # Aplicar fixes
            fix_result = self.apply_fixes(code, issues)

            if dry_run:
                return {
                    "success": True,
                    "message": f"AnÃ¡lisis completado (dry-run). {fix_result.message}",
                    "file_path": file_path,
                    "issues_found": analysis["total_issues"],
                    "auto_fixable": analysis["auto_fixable"],
                    "issues_fixed": len(fix_result.issues_fixed),
                    "issues_remaining": len(fix_result.issues_remaining),
                    "diff": fix_result.diff,
                    "changes_made": False,
                }

            # Crear backup
            backup_path = self._create_backup(file_path)

            # Escribir archivo corregido
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fix_result.fixed)

            return {
                "success": True,
                "message": fix_result.message,
                "file_path": file_path,
                "backup_path": backup_path,
                "issues_found": analysis["total_issues"],
                "issues_fixed": len(fix_result.issues_fixed),
                "issues_remaining": len(fix_result.issues_remaining),
                "diff": fix_result.diff,
                "changes_made": len(fix_result.issues_fixed) > 0,
            }

        except Exception as e:
            return {"success": False, "error": f"Error procesando archivo: {str(e)}"}

    def fix_code(self, code: str) -> Dict[str, Any]:
        """
        Analizar y corregir cÃ³digo en memoria

        Args:
            code: CÃ³digo a analizar

        Returns:
            Dict con resultado y cÃ³digo corregido
        """
        try:
            # Analizar
            analysis = self.analyze(code)

            if analysis["total_issues"] == 0:
                return {
                    "success": True,
                    "message": "No se encontraron problemas",
                    "original_code": code,
                    "fixed_code": code,
                    "changes_made": False,
                    "issues": [],
                }

            # Convertir issues
            issues = []
            for issue_dict in analysis["issues"]:
                issue = CodeIssue(
                    line=issue_dict["line"],
                    column=issue_dict["column"],
                    severity=ErrorSeverity(issue_dict["severity"]),
                    message=issue_dict["message"],
                    fix_type=FixType(issue_dict["fix_type"]),
                    code_snippet=issue_dict["code_snippet"],
                    suggested_fix=issue_dict.get("suggested_fix"),
                    auto_fixable=issue_dict.get("auto_fixable", False),
                )
                issues.append(issue)

            # Aplicar fixes
            fix_result = self.apply_fixes(code, issues)

            return {
                "success": True,
                "message": fix_result.message,
                "original_code": code,
                "fixed_code": fix_result.fixed,
                "changes_made": len(fix_result.issues_fixed) > 0,
                "diff": fix_result.diff,
                "issues_found": analysis["total_issues"],
                "issues_fixed": len(fix_result.issues_fixed),
                "issues": analysis["issues"],
            }

        except Exception as e:
            return {"success": False, "error": f"Error analizando cÃ³digo: {str(e)}"}

    # === MÃ©todo principal de ejecuciÃ³n ===

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del AutoFixer

        Args:
            action: AcciÃ³n a ejecutar
            **kwargs: ParÃ¡metros especÃ­ficos

        Returns:
            Resultado de la operaciÃ³n
        """
        action_map = {
            "analyze": self.analyze,
            "check": self.analyze,
            "lint": self.analyze,
            "fix": self.fix_code,
            "fix_code": self.fix_code,
            "fix_file": self.fix_file,
            "apply": self.fix_file,
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
        print("AutoFixer - Test Suite")
        print("=" * 60)

        fixer = AutoFixer()

        # Test 1: CÃ³digo con errores
        print("\n[Test 1] Analizar cÃ³digo con errores")
        bad_code = """
def greet(name)
    print "Hola", name

def check(x)
    if x == None:
        return True
    return False

def process(items=[]):
    items.append(1)
    return items

try:
    result = 1/0
except:
    pass
"""
        result = await fixer.execute("analyze", code=bad_code)
        print(f"âœ“ {result.get('total_issues')} problemas encontrados")
        print(f"  - CrÃ­ticos: {result.get('by_severity', {}).get('critical', 0)}")
        print(f"  - Auto-fixables: {result.get('auto_fixable', 0)}")

        # Test 2: Corregir cÃ³digo
        print("\n[Test 2] Corregir cÃ³digo automÃ¡ticamente")
        result = await fixer.execute("fix", code=bad_code)
        print(f"âœ“ {result.get('message')}")
        print(f"âœ“ Changes made: {result.get('changes_made')}")
        if result.get("diff"):
            print("\n  Diff preview:")
            print("  " + "\n  ".join(result["diff"].split("\n")[:10]))

        # Test 3: CÃ³digo con import faltante
        print("\n[Test 3] Detectar import faltante")
        code_with_import = """
result = os.path.join("path", "to", "file")
data = json.dumps({"key": "value"})
"""
        result = await fixer.execute("analyze", code=code_with_import)
        print(f"âœ“ {result.get('total_issues')} problemas encontrados")

        print("\n" + "=" * 60)
        print("Tests completados!")
        print("=" * 60)

    asyncio.run(test())
