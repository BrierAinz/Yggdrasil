"""
Workflows - Evaluador de condiciones

v4.2.8: Sistema de evaluación de condiciones para nodos condition
"""
import logging
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.workflows.conditions")


class ConditionEvaluator:
    """
    Evaluador de condiciones para workflows.

    Soporta operadores:
    - equals: Igualdad exacta
    - not_equals: Desigualdad
    - contains: Contiene substring o elemento
    - starts_with: Comienza con
    - ends_with: Termina con
    - gt, gte, lt, lte: Comparaciones numéricas
    - in_range: Dentro de rango numérico
    - regex: Coincide con expresión regular
    - exists: Existe la variable
    - all: Todas las condiciones deben cumplirse
    - any: Al menos una condición debe cumplirse
    """

    def __init__(self):
        self._operators: Dict[str, Callable] = {
            "equals": self._op_equals,
            "not_equals": self._op_not_equals,
            "contains": self._op_contains,
            "starts_with": self._op_starts_with,
            "ends_with": self._op_ends_with,
            "gt": self._op_gt,
            "gte": self._op_gte,
            "lt": self._op_lt,
            "lte": self._op_lte,
            "in_range": self._op_in_range,
            "regex": self._op_regex,
            "exists": self._op_exists,
            "all": self._op_all,
            "any": self._op_any,
        }

    async def evaluate(
        self, operator: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """
        Evalúa una condición.

        Args:
            operator: Tipo de operador
            config: Configuración de la condición
            context: Contexto de ejecución con variables

        Returns:
            True si la condición se cumple
        """
        handler = self._operators.get(operator)
        if not handler:
            logger.warning(f"Operador desconocido: {operator}")
            return False

        try:
            return await handler(config, context)
        except Exception as e:
            logger.error(f"Error evaluando condición {operator}: {e}")
            return False

    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """Obtiene un valor del contexto usando notación punto."""
        if not path:
            return None

        # Variables especiales
        if path == "@timestamp":
            return datetime.utcnow().isoformat()
        if path == "@date":
            return datetime.utcnow().strftime("%Y-%m-%d")

        # Navegar por el contexto
        keys = path.split(".")
        value = context

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    # Operadores básicos

    async def _op_equals(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Igualdad exacta."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        # Resolver valor derecho si es referencia
        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        return left == right

    async def _op_not_equals(
        self, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Desigualdad."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        return left != right

    async def _op_contains(
        self, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Contiene substring o elemento en lista."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        if isinstance(left, str) and isinstance(right, str):
            return right in left
        elif isinstance(left, (list, tuple)):
            return right in left
        elif isinstance(left, dict):
            return right in left.values() or right in left.keys()

        return False

    async def _op_starts_with(
        self, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Comienza con."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right", "")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        if isinstance(left, str) and isinstance(right, str):
            return left.startswith(right)
        return False

    async def _op_ends_with(
        self, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Termina con."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right", "")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        if isinstance(left, str) and isinstance(right, str):
            return left.endswith(right)
        return False

    # Operadores numéricos

    async def _op_gt(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Mayor que."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        try:
            return float(left) > float(right)
        except (TypeError, ValueError):
            return False

    async def _op_gte(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Mayor o igual que."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        try:
            return float(left) >= float(right)
        except (TypeError, ValueError):
            return False

    async def _op_lt(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Menor que."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        try:
            return float(left) < float(right)
        except (TypeError, ValueError):
            return False

    async def _op_lte(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Menor o igual que."""
        left = self._get_value(config.get("left"), context)
        right = config.get("right")

        if isinstance(right, str) and right.startswith("$"):
            right = self._get_value(right[1:], context)

        try:
            return float(left) <= float(right)
        except (TypeError, ValueError):
            return False

    async def _op_in_range(
        self, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Dentro de rango numérico [min, max]."""
        value = self._get_value(config.get("value"), context)
        min_val = config.get("min")
        max_val = config.get("max")

        try:
            num = float(value)
            if min_val is not None and num < float(min_val):
                return False
            if max_val is not None and num > float(max_val):
                return False
            return True
        except (TypeError, ValueError):
            return False

    # Operadores avanzados

    async def _op_regex(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Coincide con expresión regular."""
        left = self._get_value(config.get("left"), context)
        pattern = config.get("pattern", "")
        flags = config.get("flags", "")

        if not isinstance(left, str):
            left = str(left) if left is not None else ""

        try:
            regex_flags = 0
            if "i" in flags:
                regex_flags |= re.IGNORECASE
            if "m" in flags:
                regex_flags |= re.MULTILINE
            if "s" in flags:
                regex_flags |= re.DOTALL

            return bool(re.search(pattern, left, regex_flags))
        except re.error:
            return False

    async def _op_exists(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Verifica si una variable existe en el contexto."""
        path = config.get("path")
        value = self._get_value(path, context)
        return value is not None

    # Operadores compuestos

    async def _op_all(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Todas las condiciones deben cumplirse."""
        conditions = config.get("conditions", [])

        for cond in conditions:
            operator = cond.get("operator")
            cond_config = cond.get("config", cond)

            if not await self.evaluate(operator, cond_config, context):
                return False

        return True

    async def _op_any(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Al menos una condición debe cumplirse."""
        conditions = config.get("conditions", [])

        for cond in conditions:
            operator = cond.get("operator")
            cond_config = cond.get("config", cond)

            if await self.evaluate(operator, cond_config, context):
                return True

        return False

    # Helpers

    def get_available_operators(self) -> List[Dict[str, str]]:
        """Retorna lista de operadores disponibles con descripción."""
        return [
            {"value": "equals", "label": "Es igual a", "category": "básico"},
            {"value": "not_equals", "label": "No es igual a", "category": "básico"},
            {"value": "contains", "label": "Contiene", "category": "básico"},
            {"value": "starts_with", "label": "Comienza con", "category": "texto"},
            {"value": "ends_with", "label": "Termina con", "category": "texto"},
            {"value": "regex", "label": "Coincide con regex", "category": "texto"},
            {"value": "gt", "label": "Mayor que", "category": "numérico"},
            {"value": "gte", "label": "Mayor o igual que", "category": "numérico"},
            {"value": "lt", "label": "Menor que", "category": "numérico"},
            {"value": "lte", "label": "Menor o igual que", "category": "numérico"},
            {"value": "in_range", "label": "Dentro de rango", "category": "numérico"},
            {"value": "exists", "label": "Existe", "category": "avanzado"},
            {"value": "all", "label": "Todas las condiciones", "category": "compuesto"},
            {"value": "any", "label": "Alguna condición", "category": "compuesto"},
        ]
