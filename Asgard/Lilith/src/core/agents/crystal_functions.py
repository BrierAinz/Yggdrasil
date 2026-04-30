"""
Crystal Function Integration - Integra Function Calling v2 con Crystal

v5.0: Permite a Crystal usar el sistema nativo de funciones con tool calling.
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.functions import (
    ToolCallParser,
    ToolResponse,
    get_executor,
    get_function_registry,
)
from src.core.functions.schemas import FunctionSchema

logger = logging.getLogger("lilith.crystal.functions")


@dataclass
class CrystalFunctionResult:
    """Resultado de ejecución de función para Crystal."""

    success: bool
    response: str
    tool_used: Optional[str] = None
    execution_time_ms: float = 0.0


class CrystalFunctionIntegration:
    """
    Integra el sistema de Function Calling v2 con Crystal Agent.

    Features:
    - Registra automáticamente funciones permitidas para Crystal
    - Parsea tool_calls de la respuesta de Kimi
    - Ejecuta funciones de forma segura
    - Formatea resultados para Crystal
    """

    # Funciones que Crystal puede usar
    CRYSTAL_ALLOWED_FUNCTIONS = [
        "web_search",
        "get_weather",
        "calculate",
        "translate",
        "get_time",
        "get_date",
        "format_text",
        "summarize",
        "faq_lookup",
    ]

    def __init__(self):
        self.registry = get_function_registry()
        self.executor = get_executor()
        self.parser = ToolCallParser()
        self._register_default_functions()

    def _register_default_functions(self):
        """Registra funciones por defecto disponibles para Crystal."""
        # Registrar funciones básicas si no existen
        if "calculate" not in self.registry._functions:
            self.registry.register_function(
                func=self._func_calculate,
                name="calculate",
                description="Realiza cálculos matemáticos",
                category="utilities",
            )

        if "get_time" not in self.registry._functions:
            self.registry.register_function(
                func=self._func_get_time,
                name="get_time",
                description="Obtiene la hora actual",
                category="utilities",
            )

        if "get_date" not in self.registry._functions:
            self.registry.register_function(
                func=self._func_get_date,
                name="get_date",
                description="Obtiene la fecha actual",
                category="utilities",
            )

        if "summarize" not in self.registry._functions:
            self.registry.register_function(
                func=self._func_summarize,
                name="summarize",
                description="Resume texto largo",
                category="text",
            )

    def _func_calculate(self, expression: str) -> str:
        """Función de cálculo seguro."""
        try:
            # Solo permitir caracteres seguros
            allowed_chars = set("0123456789+-*/().^ sqrt log sin cos tan pi e ")
            if not all(c in allowed_chars for c in expression.lower()):
                return "Error: Expresión contiene caracteres no permitidos"

            # Evaluación segura (limitada)
            result = eval(
                expression,
                {"__builtins__": {}},
                {
                    "sqrt": lambda x: x**0.5,
                    "log": lambda x: __import__("math").log(x),
                    "sin": lambda x: __import__("math").sin(x),
                    "cos": lambda x: __import__("math").cos(x),
                    "tan": lambda x: __import__("math").tan(x),
                    "pi": 3.14159,
                    "e": 2.71828,
                },
            )
            return f"Resultado: {result}"
        except Exception as e:
            return f"Error en cálculo: {str(e)}"

    def _func_get_time(self, timezone: str = "UTC") -> str:
        """Obtiene hora actual."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    def _func_get_date(self, format: str = "%Y-%m-%d") -> str:
        """Obtiene fecha actual."""
        from datetime import datetime

        return datetime.now().strftime(format)

    def _func_summarize(self, text: str, max_length: int = 100) -> str:
        """Resume texto (placeholder simple)."""
        sentences = text.split(".")
        if len(sentences) <= 2:
            return text
        return ". ".join(sentences[:2]) + "."

    def get_available_functions(self) -> List[Dict[str, Any]]:
        """
        Obtiene funciones disponibles para Crystal en formato Kimi/OpenAI.

        Returns:
            Lista de funciones en formato tool calling
        """
        functions = []
        for func_name in self.CRYSTAL_ALLOWED_FUNCTIONS:
            schema = self.registry.get(func_name)
            if schema:
                functions.append(schema.to_openai_format())
        return functions

    def augment_system_prompt(self, base_prompt: str) -> str:
        """
        Agrega información de funciones al system prompt.

        Args:
            base_prompt: Prompt base de Crystal

        Returns:
            Prompt enriquecido con información de funciones
        """
        functions = self.get_available_functions()

        if not functions:
            return base_prompt

        prompt_parts = [base_prompt]
        prompt_parts.append("\n\n## Funciones disponibles\n")
        prompt_parts.append("Puedes usar estas funciones cuando sea necesario:\n")

        for func in functions:
            fn = func.get("function", {})
            prompt_parts.append(f"\n- **{fn.get('name')}**: {fn.get('description')}")
            params = fn.get("parameters", {}).get("properties", {})
            if params:
                prompt_parts.append("  Parámetros:")
                for param_name, param_info in params.items():
                    prompt_parts.append(
                        f"    - {param_name}: {param_info.get('description', '')}"
                    )

        prompt_parts.append(
            "\n\nPara usar una función, responde con el formato:\n"
            '<tool_call>{"name": "nombre_funcion", "arguments": {...</tool_call>'
        )

        return "\n".join(prompt_parts)

    async def process_response(
        self, response: str, tool_calls: Optional[List[Dict]] = None
    ) -> CrystalFunctionResult:
        """
        Procesa respuesta de Crystal detectando y ejecutando tool calls.

        Args:
            response: Respuesta del modelo
            tool_calls: Tool calls estructurados (si vienen en formato nativo)

        Returns:
            Resultado procesado
        """
        # Parsear tool calls
        parsed = self.parser.parse(response, tool_calls)

        if not parsed:
            # No hay tool calls, retornar respuesta original
            return CrystalFunctionResult(
                success=True, response=response, tool_used=None
            )

        # Ejecutar tool calls
        results = []
        total_time = 0.0

        for tool_call in parsed:
            # Verificar que la función está permitida
            if tool_call.name not in self.CRYSTAL_ALLOWED_FUNCTIONS:
                results.append(f"[Error: Función '{tool_call.name}' no permitida]")
                continue

            # Ejecutar
            exec_result = await self.executor.execute(
                function_name=tool_call.name, arguments=tool_call.arguments
            )

            total_time += exec_result.execution_time_ms

            if exec_result.success:
                results.append(f"[Resultado de {tool_call.name}]: {exec_result.result}")
            else:
                results.append(f"[Error en {tool_call.name}]: {exec_result.error}")

        # Construir respuesta final
        final_response = response
        if results:
            # Eliminar los tool_calls del texto
            clean_response, _ = self.parser.extract_tool_calls_from_text(response)
            final_response = clean_response + "\n\n" + "\n".join(results)

        return CrystalFunctionResult(
            success=True,
            response=final_response,
            tool_used=parsed[0].name if parsed else None,
            execution_time_ms=total_time,
        )

    async def execute_direct(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> ToolResponse:
        """
        Ejecuta una función directamente (para uso interno).

        Args:
            function_name: Nombre de la función
            arguments: Argumentos

        Returns:
            Resultado de la ejecución
        """
        if function_name not in self.CRYSTAL_ALLOWED_FUNCTIONS:
            return ToolResponse.error_response(
                error=f"Función '{function_name}' no permitida para Crystal",
                tool_name=function_name,
            )

        return await self.executor.execute(function_name, arguments)


# Singleton global
_crystal_functions: Optional[CrystalFunctionIntegration] = None


def get_crystal_function_integration() -> CrystalFunctionIntegration:
    """Obtiene instancia singleton de la integración."""
    global _crystal_functions
    if _crystal_functions is None:
        _crystal_functions = CrystalFunctionIntegration()
    return _crystal_functions
