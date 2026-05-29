"""
Function Registry - Registro de funciones disponibles

v5.0: Registry centralizado de funciones/tool con validación y documentación.
"""
import inspect
import logging
from dataclasses import fields
from typing import Any, Callable, Dict, List, Optional, Type

from .schemas import FunctionSchema, ParameterSchema, ParameterType, ToolResponse

logger = logging.getLogger("lilith.functions.registry")


class FunctionRegistry:
    """
    Registro centralizado de funciones disponibles para el modelo.

    Features:
    - Registro de funciones con esquemas
    - Validación de parámetros
    - Conversión automática de tipos Python
    - Búsqueda por categoría
    """

    def __init__(self):
        self._functions: Dict[str, FunctionSchema] = {}
        self._handlers: Dict[str, Callable] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[FunctionSchema] = None,
        requires_confirmation: bool = False,
        confirmation_message: str = "",
        category: str = "general",
    ):
        """
        Decorador para registrar una función.

        Args:
            name: Nombre de la función (default: nombre de la función)
            description: Descripción (default: docstring)
            schema: Esquema manual (opcional)
            requires_confirmation: Si requiere confirmación del usuario
            confirmation_message: Mensaje de confirmación
            category: Categoría para agrupar
        """

        def decorator(func: Callable) -> Callable:
            func_name = name or func.__name__
            func_description = description or (func.__doc__ or "").strip()

            if schema:
                # Usar esquema proporcionado
                func_schema = FunctionSchema(
                    name=func_name,
                    description=func_description,
                    parameters=schema.parameters,
                    handler=func,
                    return_type=schema.return_type,
                    examples=schema.examples,
                    requires_confirmation=requires_confirmation
                    or schema.requires_confirmation,
                    confirmation_message=confirmation_message
                    or schema.confirmation_message,
                    category=category,
                )
            else:
                # Inferir esquema desde firma de función
                func_schema = self._infer_schema(
                    func,
                    func_name,
                    func_description,
                    requires_confirmation,
                    confirmation_message,
                    category,
                )

            # Registrar
            self._functions[func_name] = func_schema
            self._handlers[func_name] = func

            # Agregar a categoría
            if category not in self._categories:
                self._categories[category] = []
            if func_name not in self._categories[category]:
                self._categories[category].append(func_name)

            logger.debug(f"Función registrada: {func_name} ({category})")

            return func

        return decorator

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[ParameterSchema]] = None,
        requires_confirmation: bool = False,
        confirmation_message: str = "",
        category: str = "general",
    ) -> FunctionSchema:
        """
        Registra una función programáticamente.

        Args:
            func: Función a registrar
            name: Nombre (opcional)
            description: Descripción (opcional)
            parameters: Esquema de parámetros (opcional)
            requires_confirmation: Requiere confirmación
            confirmation_message: Mensaje de confirmación
            category: Categoría

        Returns:
            Esquema registrado
        """
        func_name = name or func.__name__
        func_description = description or (func.__doc__ or "").strip()

        if parameters:
            schema = FunctionSchema(
                name=func_name,
                description=func_description,
                parameters=parameters,
                handler=func,
                requires_confirmation=requires_confirmation,
                confirmation_message=confirmation_message,
                category=category,
            )
        else:
            schema = self._infer_schema(
                func,
                func_name,
                func_description,
                requires_confirmation,
                confirmation_message,
                category,
            )

        self._functions[func_name] = schema
        self._handlers[func_name] = func

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(func_name)

        return schema

    def _infer_schema(
        self,
        func: Callable,
        name: str,
        description: str,
        requires_confirmation: bool,
        confirmation_message: str,
        category: str,
    ) -> FunctionSchema:
        """Infiere esquema desde firma de función."""
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            # Ignorar parámetros especiales
            if param_name.startswith("_"):
                continue

            param_type = self._python_type_to_param_type(param.annotation)
            required = param.default is inspect.Parameter.empty
            default = None if required else param.default

            parameters.append(
                ParameterSchema(
                    name=param_name,
                    type=param_type,
                    description="",  # Podría parsearse del docstring
                    required=required,
                    default=default,
                )
            )

        # Detectar tipo de retorno
        return_annotation = sig.return_annotation
        return_type = "string"
        if return_annotation is not inspect.Signature.empty:
            if return_annotation == str:
                return_type = "string"
            elif return_annotation == int:
                return_type = "integer"
            elif return_annotation == float:
                return_type = "number"
            elif return_annotation == bool:
                return_type = "boolean"
            elif return_annotation == dict or return_annotation == Dict:
                return_type = "object"
            elif return_annotation == list or return_annotation == List:
                return_type = "array"

        return FunctionSchema(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            return_type=return_type,
            requires_confirmation=requires_confirmation,
            confirmation_message=confirmation_message,
            category=category,
        )

    def _python_type_to_param_type(self, annotation: Any) -> ParameterType:
        """Convierte tipo Python a ParameterType."""
        if annotation == str or annotation == "str":
            return ParameterType.STRING
        elif annotation == int or annotation == "int":
            return ParameterType.INTEGER
        elif annotation == float or annotation == "float":
            return ParameterType.NUMBER
        elif annotation == bool or annotation == "bool":
            return ParameterType.BOOLEAN
        elif annotation == list or annotation == List or annotation == "list":
            return ParameterType.ARRAY
        elif annotation == dict or annotation == Dict or annotation == "dict":
            return ParameterType.OBJECT
        else:
            return ParameterType.STRING  # Default

    def get(self, name: str) -> Optional[FunctionSchema]:
        """Obtiene el esquema de una función."""
        return self._functions.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """Obtiene el handler de una función."""
        return self._handlers.get(name)

    def list_functions(self, category: Optional[str] = None) -> List[FunctionSchema]:
        """Lista funciones registradas."""
        if category:
            names = self._categories.get(category, [])
            return [self._functions[n] for n in names if n in self._functions]
        return list(self._functions.values())

    def list_categories(self) -> List[str]:
        """Lista categorías disponibles."""
        return list(self._categories.keys())

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Exporta funciones en formato OpenAI."""
        return [f.to_openai_format() for f in self._functions.values()]

    def to_anthropic_format(self) -> List[Dict[str, Any]]:
        """Exporta funciones en formato Anthropic."""
        return [f.to_anthropic_format() for f in self._functions.values()]

    def validate_arguments(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Valida argumentos contra el esquema.

        Returns:
            Tuple (válido, mensaje_error)
        """
        schema = self.get(function_name)
        if not schema:
            return False, f"Función '{function_name}' no encontrada"

        # Verificar parámetros requeridos
        for param in schema.parameters:
            if param.required and param.name not in arguments:
                return False, f"Parámetro requerido faltante: {param.name}"

        # Verificar tipos (básico)
        for param in schema.parameters:
            if param.name in arguments:
                value = arguments[param.name]
                if not self._validate_type(value, param.type):
                    return False, (
                        f"Tipo inválido para {param.name}: "
                        f"esperado {param.type.value}, got {type(value).__name__}"
                    )

        return True, None

    def _validate_type(self, value: Any, expected_type: ParameterType) -> bool:
        """Valida que un valor coincida con el tipo esperado."""
        if expected_type == ParameterType.STRING:
            return isinstance(value, str)
        elif expected_type == ParameterType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == ParameterType.NUMBER:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == ParameterType.BOOLEAN:
            return isinstance(value, bool)
        elif expected_type == ParameterType.ARRAY:
            return isinstance(value, list)
        elif expected_type == ParameterType.OBJECT:
            return isinstance(value, dict)
        return True

    def requires_confirmation(self, function_name: str) -> bool:
        """Verifica si una función requiere confirmación."""
        schema = self.get(function_name)
        return schema.requires_confirmation if schema else False

    def get_confirmation_message(self, function_name: str, arguments: Dict) -> str:
        """Genera mensaje de confirmación."""
        schema = self.get(function_name)
        if not schema or not schema.confirmation_message:
            args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
            return f"¿Ejecutar {function_name}({args_str})?"

        # Intentar formatear con argumentos
        try:
            return schema.confirmation_message.format(**arguments)
        except KeyError:
            return schema.confirmation_message


# Singleton global
_registry: Optional[FunctionRegistry] = None


def get_function_registry() -> FunctionRegistry:
    """Obtiene instancia singleton del registry."""
    global _registry
    if _registry is None:
        _registry = FunctionRegistry()
    return _registry
