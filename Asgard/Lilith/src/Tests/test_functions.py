"""
Tests for Function Registry and Executor

v5.0: Tests unitarios para el sistema de function calling.
"""
import asyncio
from typing import Any, Dict

import pytest
from src.core.functions import (
    FunctionSchema,
    ParameterSchema,
    ParameterType,
    ToolResponse,
    get_executor,
    get_function_registry,
)
from src.core.functions.parser import ParsedToolCall, ToolCallParser


class TestFunctionRegistry:
    """Tests para el registro de funciones."""

    def setup_method(self):
        """Setup before each test."""
        self.registry = get_function_registry()
        # Limpiar registro para tests
        self.registry._functions.clear()
        self.registry._handlers.clear()
        self.registry._categories.clear()

    def test_register_simple_function(self):
        """Test registro de función simple."""

        def sample_func(name: str) -> str:
            """Sample function."""
            return f"Hello {name}"

        self.registry.register_function(
            func=sample_func, name="greet", description="Greets a person"
        )

        schema = self.registry.get("greet")
        assert schema is not None
        assert schema.name == "greet"
        assert schema.description == "Greets a person"

    def test_register_with_decorator(self):
        """Test registro con decorador."""

        @self.registry.register(
            name="calculate",
            description="Performs calculation",
            requires_confirmation=True,
        )
        def calc_func(expression: str) -> str:
            return f"Result: {expression}"

        schema = self.registry.get("calculate")
        assert schema.requires_confirmation is True

    def test_infer_schema_from_signature(self):
        """Test inferencia de esquema desde firma."""

        def complex_func(
            name: str, age: int, score: float, active: bool, tags: list
        ) -> dict:
            """Complex function."""
            return {"name": name, "age": age}

        self.registry.register_function(complex_func)
        schema = self.registry.get("complex_func")

        params = {p.name: p.type for p in schema.parameters}
        assert params["name"] == ParameterType.STRING
        assert params["age"] == ParameterType.INTEGER
        assert params["score"] == ParameterType.NUMBER
        assert params["active"] == ParameterType.BOOLEAN
        assert params["tags"] == ParameterType.ARRAY

    def test_validate_arguments_success(self):
        """Test validación exitosa de argumentos."""

        def test_func(name: str, count: int = 1) -> str:
            return f"{name} x{count}"

        self.registry.register_function(test_func)

        valid, error = self.registry.validate_arguments(
            "test_func", {"name": "test", "count": 5}
        )
        assert valid is True
        assert error is None

    def test_validate_arguments_missing_required(self):
        """Test validación con parámetro requerido faltante."""

        def test_func(name: str) -> str:
            return name

        self.registry.register_function(test_func)

        valid, error = self.registry.validate_arguments("test_func", {})
        assert valid is False
        assert "faltante" in error or "missing" in error.lower()

    def test_to_openai_format(self):
        """Test conversión a formato OpenAI."""

        def sample_func(query: str, limit: int = 10) -> str:
            """Sample search."""
            return query

        self.registry.register_function(sample_func)
        openai_format = self.registry.to_openai_format()

        assert len(openai_format) == 1
        func = openai_format[0]["function"]
        assert func["name"] == "sample_func"
        assert "parameters" in func
        assert "query" in func["parameters"]["properties"]


class TestFunctionExecutor:
    """Tests para el executor de funciones."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.registry = get_function_registry()
        self.executor = get_executor(self.registry)
        self.registry._functions.clear()
        self.registry._handlers.clear()

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test ejecución exitosa."""

        def simple_add(a: int, b: int) -> int:
            return a + b

        self.registry.register_function(simple_add)

        result = await self.executor.execute("simple_add", {"a": 5, "b": 3})

        assert result.success is True
        assert result.result == 8
        assert result.tool_name == "simple_add"

    @pytest.mark.asyncio
    async def test_execute_function_not_found(self):
        """Test ejecución de función inexistente."""
        result = await self.executor.execute("nonexistent", {})

        assert result.success is False
        assert "no encontrada" in result.error or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validation_failure(self):
        """Test ejecución con falla de validación."""

        def required_args(required: str) -> str:
            return required

        self.registry.register_function(required_args)

        result = await self.executor.execute(
            "required_args", {}  # Missing required arg
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test ejecución que lanza excepción."""

        def failing_func() -> str:
            raise ValueError("Test error")

        self.registry.register_function(failing_func)

        result = await self.executor.execute("failing_func", {})

        assert result.success is False
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_execute_async_function(self):
        """Test ejecución de función async."""

        async def async_greet(name: str) -> str:
            return f"Hello {name}"

        self.registry.register_function(async_greet)

        result = await self.executor.execute("async_greet", {"name": "World"})

        assert result.success is True
        assert result.result == "Hello World"

    def test_get_stats(self):
        """Test obtención de estadísticas."""
        stats = self.executor.get_stats()

        assert "total_executions" in stats
        assert "success_rate" in stats


class TestToolCallParser:
    """Tests para el parser de tool calls."""

    def setup_method(self):
        """Setup."""
        self.parser = ToolCallParser()

    def test_parse_structured_format(self):
        """Test parseo de formato estructurado."""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "search", "arguments": '{"query": "test"}'},
            }
        ]

        result = self.parser.parse("", tool_calls)

        assert len(result) == 1
        assert result[0].name == "search"
        assert result[0].arguments == {"query": "test"}

    def test_parse_tag_format(self):
        """Test parseo de formato con tags."""
        content = 'Some text <tool_call>{"name": "calc", "arguments": {"a": 1}}</tool_call> more text'

        clean_text, result = self.parser.extract_tool_calls_from_text(content)

        assert len(result) == 1
        assert result[0].name == "calc"
        assert clean_text == "Some text  more text"

    def test_parse_no_tool_calls(self):
        """Test texto sin tool calls."""
        result = self.parser.parse("Just a normal message", None)

        assert len(result) == 0

    def test_parse_anthropic_format(self):
        """Test parseo de formato Anthropic."""
        content_blocks = [
            {
                "type": "tool_use",
                "id": "tool_123",
                "name": "get_weather",
                "input": {"location": "NYC"},
            }
        ]

        result = self.parser.parse_anthropic_content(content_blocks)

        assert len(result) == 1
        assert result[0].name == "get_weather"
        assert result[0].arguments == {"location": "NYC"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
