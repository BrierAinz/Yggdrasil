class LilithError(Exception):
    """Error base de Lilith."""

    pass


class ToolError(LilithError):
    """Error en ejecucion de tool."""

    pass


class LLMError(LilithError):
    """Error en comunicacion con LLM."""

    pass
