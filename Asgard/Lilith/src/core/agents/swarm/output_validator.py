"""
OutputValidator — Validación heurística de respuestas de agentes.
Detecta respuestas vacías, truncadas, con placeholders o de baja calidad
y marca el resultado para posible re-intento o escalado.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("lilith.output_validator")

# ─── Señales de salida deficiente ─────────────────────────────────────────────

# Respuestas que indican que el agente no pudo responder
_FAILURE_PATTERNS = [
    r"^\s*\[?error\]?\s*$",
    r"^\s*\(sin respuesta\)\s*$",
    r"^\s*undefined\s*$",
    r"^\s*null\s*$",
    r"^\s*none\s*$",
    r"^\s*\.\.\.\s*$",
]

# Frases que indican respuesta genérica / placeholder no resuelta
_PLACEHOLDER_PATTERNS = [
    r"\[inserta\s+\w+\s+aquí\]",
    r"\[TODO\]",
    r"\[FIXME\]",
    r"<placeholder>",
    r"\{\{[^}]+\}\}",  # plantillas sin rellenar: {{variable}}
    r"\[tu\s+\w+\s+aquí\]",
]

# Señales de truncación prematura
_TRUNCATION_SIGNALS = [
    r"…\s*\(truncado\)\s*$",
    r"\.\.\.\s*$",
    r"continúa\s+en\s+la\s+siguiente\s+respuesta",
]

_FAIL_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _FAILURE_PATTERNS]
_PLAC_RE = [re.compile(p, re.IGNORECASE) for p in _PLACEHOLDER_PATTERNS]
_TRUNC_RE = [re.compile(p, re.IGNORECASE) for p in _TRUNCATION_SIGNALS]

# Longitud mínima de una respuesta útil (caracteres)
_MIN_USEFUL_LENGTH = 20


@dataclass
class ValidationResult:
    valid: bool
    issues: List[str]
    score: float  # 0.0 = inútil, 1.0 = perfecta
    suggestion: str = ""  # acción recomendada: "retry", "escalate", "accept"

    def __bool__(self) -> bool:
        return self.valid


class OutputValidator:
    """
    Valida la calidad heurística de la respuesta de un agente.
    No hace llamadas a LLM; sólo heurísticas de texto.
    """

    def validate(
        self, text: str, tool_name: str = "", task: str = ""
    ) -> ValidationResult:
        """
        Valida `text` como respuesta de `tool_name` para `task`.
        """
        issues: List[str] = []
        score = 1.0

        if not text or not text.strip():
            return ValidationResult(
                valid=False, issues=["empty_response"], score=0.0, suggestion="retry"
            )

        stripped = text.strip()

        # Longitud mínima
        if len(stripped) < _MIN_USEFUL_LENGTH:
            issues.append(f"too_short ({len(stripped)} chars)")
            score -= 0.4

        # Patrón de fallo explícito
        for r in _FAIL_RE:
            if r.search(stripped):
                issues.append("failure_pattern")
                score -= 0.5
                break

        # Placeholders sin rellenar
        for r in _PLAC_RE:
            if r.search(stripped):
                issues.append("unresolved_placeholder")
                score -= 0.3
                break

        # Señales de truncación
        for r in _TRUNC_RE:
            if r.search(stripped):
                issues.append("truncated")
                score -= 0.2
                break

        # Para delegate_adan: una respuesta útil de código debería contener algo de código
        if (
            tool_name == "delegate_adan"
            and "```" not in stripped
            and "def " not in stripped
            and "function " not in stripped
        ):
            if task and any(
                w in task.lower()
                for w in (
                    "código",
                    "code",
                    "función",
                    "function",
                    "script",
                    "clase",
                    "class",
                )
            ):
                issues.append("no_code_in_code_task")
                score -= 0.25

        score = max(0.0, min(1.0, score))
        valid = score >= 0.5 and not any(
            i in issues for i in ("empty_response", "failure_pattern")
        )

        suggestion = "accept"
        if not valid:
            if score <= 0.2:
                suggestion = "escalate"
            else:
                suggestion = "retry"
        elif issues:
            suggestion = "accept_with_warning"

        return ValidationResult(
            valid=valid, issues=issues, score=round(score, 2), suggestion=suggestion
        )

    def is_acceptable(self, text: str, tool_name: str = "", task: str = "") -> bool:
        return self.validate(text, tool_name, task).valid


# ─── Singleton ────────────────────────────────────────────────────────────────

_validator: Optional[OutputValidator] = None


def get_validator() -> OutputValidator:
    global _validator
    if _validator is None:
        _validator = OutputValidator()
    return _validator
