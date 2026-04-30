# -*- coding: utf-8 -*-
"""
Lilith v2.1 - PAIR PROGRAMMING MODE
FASE E: Intelligence Collective - Real-time Coding Assistant

Features:
- Real-time code analysis as user types
- Contextual suggestions based on current function
- Autocomplete predictions
- Live error detection
- Best practice suggestions
"""

import ast
import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class SuggestionType(Enum):
    """Tipos de sugerencias en tiempo real"""

    AUTOCOMPLETE = "autocomplete"
    IMPORT = "import"
    ERROR_PREVENTION = "error_prevention"
    BEST_PRACTICE = "best_practice"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TYPE_HINT = "type_hint"
    SECURITY = "security"


@dataclass
class LiveSuggestion:
    """Sugerencia en tiempo real"""

    type: SuggestionType
    message: str
    line: int
    column: int
    confidence: float
    code_snippet: str
    replacement: Optional[str] = None
    explanation: str = ""
    trigger: str = ""  # QuÃ© acciÃ³n del usuario disparÃ³ esto


@dataclass
class CodeContext:
    """Contexto del cÃ³digo actual"""

    current_function: Optional[str] = None
    current_class: Optional[str] = None
    variables_in_scope: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    last_edit_time: float = field(default_factory=time.time)
    edit_history: deque = field(default_factory=lambda: deque(maxlen=10))
    cursor_line: int = 0
    cursor_column: int = 0


class AutocompleteEngine:
    """Motor de autocompletado inteligente"""

    PYTHON_KEYWORDS = [
        "def",
        "class",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "try",
        "except",
        "finally",
        "with",
        "return",
        "yield",
        "import",
        "from",
        "as",
        "pass",
        "break",
        "continue",
        "lambda",
        "async",
        "await",
    ]

    COMMON_PATTERNS = {
        "def": [
            ("def __init__(self):", "Constructor de clase"),
            ("def __str__(self) -> str:", "String representation"),
            ("def __repr__(self) -> str:", "Debug representation"),
            ("def get_(self) -> :", "Getter method"),
            ("def set_(self, value):", "Setter method"),
        ],
        "for": [
            ("for item in items:", "Iterar sobre colecciÃ³n"),
            ("for i, item in enumerate(items):", "Iterar con Ã­ndice"),
            ("for key, value in dict.items():", "Iterar diccionario"),
        ],
        "if": [
            ('if __name__ == "__main__":', "Entry point check"),
            ("if isinstance(var, Type):", "Type checking"),
            ("if var is not None:", "None checking"),
        ],
        "try": [
            ("try:\n    \nexcept Exception as e:\n    ", "Try-except block"),
            (
                "try:\n    \nexcept (TypeError, ValueError) as e:\n    ",
                "Multiple exceptions",
            ),
        ],
        "with": [
            ('with open(file, "r") as f:', "File context manager"),
            ("with contextlib.suppress(Exception):", "Suppress exceptions"),
        ],
        "import": [
            ("import logging", "Logging module"),
            ("from typing import Optional, List, Dict", "Common types"),
            ("from dataclasses import dataclass", "Dataclass decorator"),
        ],
    }

    def get_suggestions(
        self, prefix: str, context: CodeContext
    ) -> List[Tuple[str, str]]:
        """Obtener sugerencias de autocompletado"""
        suggestions = []

        # Palabras clave de Python
        for kw in self.PYTHON_KEYWORDS:
            if kw.startswith(prefix.lower()):
                suggestions.append((kw, f"Python keyword: {kw}"))

        # Variables en scope
        for var in context.variables_in_scope:
            if var.startswith(prefix):
                suggestions.append((var, f"Variable: {var}"))

        # Patrones comunes
        if prefix in self.COMMON_PATTERNS:
            for pattern, desc in self.COMMON_PATTERNS[prefix]:
                suggestions.append((pattern, desc))

        # ComÃºn para ciertos prefijos
        if prefix.startswith("def "):
            suggestions.append(("def (self) -> None:", "Method definition"))
        elif prefix.startswith("class "):
            suggestions.append(("class (ABC):", "Abstract class"))
            suggestions.append(
                ('class :\n    """"""\n    def __init__(self):', "Documented class")
            )

        return suggestions[:10]  # Top 10


class ErrorPreventionEngine:
    """Detecta errores potenciales antes de que ocurran"""

    ERROR_PATTERNS = [
        {
            "pattern": r"if\s+\w+\s*=\s*",  # AsignaciÃ³n en vez de comparaciÃ³n
            "message": 'Â¿Quisiste decir "==" en lugar de "="?',
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "high",
        },
        {
            "pattern": r"except\s*:",  # Bare except
            "message": 'Evita "except:". Usa "except Exception:"',
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "medium",
        },
        {
            "pattern": r"\.has_key\s*\(",  # Python 2 relic
            "message": '"has_key" estÃ¡ obsoleto. Usa "in"',
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "medium",
        },
        {
            "pattern": r'print\s+["\']',  # Python 2 print
            "message": "Usa print() funciÃ³n en Python 3",
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "high",
        },
        {
            "pattern": r"==\s*(True|False|None)",  # ComparaciÃ³n innecesaria
            "message": 'No compares con True/False/None. Usa "is" o simplemente la variable',
            "type": SuggestionType.BEST_PRACTICE,
            "severity": "low",
        },
        {
            "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\(",  # Antipattern
            "message": 'Usa "enumerate()" en lugar de "range(len())"',
            "type": SuggestionType.BEST_PRACTICE,
            "severity": "medium",
        },
        {
            "pattern": r"def\s+\w+\s*\([^)]*\)\s*:",  # FunciÃ³n sin type hints
            "message": "Considera agregar type hints",
            "type": SuggestionType.TYPE_HINT,
            "severity": "low",
        },
        {
            "pattern": r"open\s*\([^)]*\)(?!\s+as)",  # Open sin context manager
            "message": 'Usa "with open(...) as f:" para manejo seguro de archivos',
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "high",
        },
        {
            "pattern": r"\.format\s*\(",  # f-strings preferidos
            "message": "Considera usar f-strings para mejor legibilidad",
            "type": SuggestionType.BEST_PRACTICE,
            "severity": "low",
        },
        {
            "pattern": r"except\s+Exception\s+as\s+\w+:\s*\n\s*pass",  # Except pass
            "message": 'Evita "except: pass". Maneja la excepciÃ³n o usa "suppress"',
            "type": SuggestionType.ERROR_PREVENTION,
            "severity": "high",
        },
    ]

    def check_line(self, line: str, line_num: int) -> List[LiveSuggestion]:
        """Verificar una lÃ­nea de cÃ³digo"""
        suggestions = []

        for error_def in self.ERROR_PATTERNS:
            if re.search(error_def["pattern"], line):
                suggestions.append(
                    LiveSuggestion(
                        type=error_def["type"],
                        message=error_def["message"],
                        line=line_num,
                        column=0,
                        confidence=0.9 if error_def["severity"] == "high" else 0.7,
                        code_snippet=line.strip(),
                        trigger="error_pattern",
                    )
                )

        return suggestions


class BestPracticeEngine:
    """Sugiere mejores prÃ¡cticas mientras se codea"""

    def analyze_function_context(
        self, lines: List[str], cursor_line: int
    ) -> List[LiveSuggestion]:
        """Analizar contexto de funciÃ³n actual"""
        suggestions = []

        # Encontrar inicio de funciÃ³n
        func_start = cursor_line
        while func_start >= 0:
            if re.match(r"\s*def\s+", lines[func_start]):
                break
            func_start -= 1

        if func_start < 0:
            return suggestions

        func_lines = lines[func_start : cursor_line + 1]
        func_text = "\n".join(func_lines)

        # Verificar si tiene docstring
        if (
            cursor_line > func_start
            and '"""' not in func_text
            and "'''" not in func_text
        ):
            suggestions.append(
                LiveSuggestion(
                    type=SuggestionType.DOCUMENTATION,
                    message="Agrega un docstring a esta funciÃ³n",
                    line=func_start + 1,
                    column=0,
                    confidence=0.8,
                    code_snippet=lines[func_start].strip(),
                    replacement=lines[func_start].rstrip() + '\n    """""\n    ',
                    explanation="Las funciones deberÃ­an tener documentaciÃ³n",
                )
            )

        # Verificar returns mÃºltiples
        return_count = sum(1 for l in func_lines if re.match(r"\s*return\s+", l))
        if return_count > 2:
            suggestions.append(
                LiveSuggestion(
                    type=SuggestionType.REFACTORING,
                    message=f"FunciÃ³n tiene {return_count} returns. Considera consolidar el flujo.",
                    line=cursor_line,
                    column=0,
                    confidence=0.6,
                    code_snippet="",
                    explanation="MÃºltiples returns pueden hacer el cÃ³digo difÃ­cil de seguir",
                )
            )

        # Verificar nested loops
        loop_depth = 0
        max_depth = 0
        for line in func_lines:
            if re.search(r"\s*(for|while)\s+", line):
                loop_depth += 1
                max_depth = max(max_depth, loop_depth)
            if loop_depth > 0 and not line.strip().endswith(":"):
                # Salida aproximada del loop
                pass

        if max_depth >= 3:
            suggestions.append(
                LiveSuggestion(
                    type=SuggestionType.REFACTORING,
                    message=f"FunciÃ³n tiene {max_depth} niveles de anidamiento. Considera extraer funciones.",
                    line=cursor_line,
                    column=0,
                    confidence=0.75,
                    code_snippet="",
                    explanation="CÃ³digo profundamente anidado es difÃ­cil de mantener",
                )
            )

        return suggestions


class PairProgrammingSession:
    """SesiÃ³n de pair programming con Lilith"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.context = CodeContext()
        self.autocomplete = AutocompleteEngine()
        self.error_prevention = ErrorPreventionEngine()
        self.best_practices = BestPracticeEngine()
        self.last_analysis = 0
        self.analysis_cooldown = 0.5  # segundos
        self.pending_suggestions: List[LiveSuggestion] = []

    def update_context(
        self, cursor_line: int, cursor_column: int, current_word: str = ""
    ):
        """Actualizar contexto basado en posiciÃ³n del cursor"""
        self.context.cursor_line = cursor_line
        self.context.cursor_column = cursor_column
        self.context.last_edit_time = time.time()

        # Analizar archivo si ha pasado suficiente tiempo
        if time.time() - self.last_analysis > self.analysis_cooldown:
            self._analyze_current_state()
            self.last_analysis = time.time()

    def _analyze_current_state(self):
        """Analizar estado actual del archivo"""
        try:
            source = self.file_path.read_text(encoding="utf-8")
            lines = source.split("\n")

            # Actualizar contexto
            self._update_scope_info(source)

            # Generar sugerencias
            self.pending_suggestions = []

            # Verificar lÃ­nea actual
            if self.context.cursor_line < len(lines):
                current_line = lines[self.context.cursor_line]

                # Error prevention
                self.pending_suggestions.extend(
                    self.error_prevention.check_line(
                        current_line, self.context.cursor_line
                    )
                )

                # Best practices en contexto de funciÃ³n
                self.pending_suggestions.extend(
                    self.best_practices.analyze_function_context(
                        lines, self.context.cursor_line
                    )
                )

        except Exception as e:
            logger.error(f"Error analyzing file: {e}")

    def _update_scope_info(self, source: str):
        """Actualizar informaciÃ³n de scope"""
        try:
            tree = ast.parse(source)

            # Encontrar funciÃ³n/clase actual
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, "end_lineno"):
                        if node.lineno <= self.context.cursor_line <= node.end_lineno:
                            self.context.current_function = node.name
                            # Extraer variables locales
                            self.context.variables_in_scope = [
                                target.id
                                for child in ast.walk(node)
                                if isinstance(child, ast.Assign)
                                for target in child.targets
                                if isinstance(target, ast.Name)
                            ]

                elif isinstance(node, ast.ClassDef):
                    if hasattr(node, "end_lineno"):
                        if node.lineno <= self.context.cursor_line <= node.end_lineno:
                            self.context.current_class = node.name

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        self.context.imports.append(alias.name)

        except SyntaxError:
            pass  # CÃ³digo incompleto es normal mientras se escribe

    def get_autocomplete_suggestions(self, prefix: str) -> List[Dict]:
        """Obtener sugerencias de autocompletado"""
        suggestions = self.autocomplete.get_suggestions(prefix, self.context)
        return [
            {"text": text, "description": desc, "type": "autocomplete"}
            for text, desc in suggestions
        ]

    def get_live_suggestions(self) -> List[Dict]:
        """Obtener sugerencias en tiempo real"""
        # Filtrar por relevancia
        high_confidence = [s for s in self.pending_suggestions if s.confidence >= 0.7]

        return [
            {
                "type": s.type.value,
                "message": s.message,
                "line": s.line,
                "confidence": s.confidence,
                "code": s.code_snippet,
                "replacement": s.replacement,
                "explanation": s.explanation,
            }
            for s in high_confidence[:5]  # Top 5
        ]

    def on_type(self, char: str, cursor_line: int, cursor_column: int) -> Dict:
        """Evento: usuario escribe un carÃ¡cter"""
        self.update_context(cursor_line, cursor_column)

        response = {
            "action": "typed",
            "suggestions": self.get_live_suggestions(),
            "autocomplete": None,
        }

        # Si escribiÃ³ un espacio o punto, mostrar autocompletado
        if char in (" ", ".", "("):
            # Extraer palabra actual
            try:
                source = self.file_path.read_text(encoding="utf-8")
                lines = source.split("\n")
                if cursor_line < len(lines):
                    line = lines[cursor_line][:cursor_column]
                    words = line.split()
                    if words:
                        prefix = words[-1]
                        response["autocomplete"] = self.get_autocomplete_suggestions(
                            prefix
                        )
            except:
                pass

        return response

    def on_save(self) -> Dict:
        """Evento: archivo guardado"""
        self._analyze_current_state()

        suggestions = self.get_live_suggestions()

        return {
            "action": "saved",
            "summary": f"{len(suggestions)} sugerencias encontradas",
            "suggestions": suggestions,
        }


class PairProgrammingManager:
    """Gestor de sesiones de pair programming"""

    def __init__(self):
        self.sessions: Dict[str, PairProgrammingSession] = {}

    def start_session(self, file_path: str) -> PairProgrammingSession:
        """Iniciar nueva sesiÃ³n"""
        session = PairProgrammingSession(Path(file_path))
        self.sessions[file_path] = session
        return session

    def get_session(self, file_path: str) -> Optional[PairProgrammingSession]:
        """Obtener sesiÃ³n existente"""
        return self.sessions.get(file_path)

    def end_session(self, file_path: str):
        """Terminar sesiÃ³n"""
        if file_path in self.sessions:
            del self.sessions[file_path]


# Instancia global
_pair_manager = None


def get_pair_programming_manager() -> PairProgrammingManager:
    """Obtener gestor de pair programming"""
    global _pair_manager
    if _pair_manager is None:
        _pair_manager = PairProgrammingManager()
    return _pair_manager
