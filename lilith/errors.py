"""Lilith Agent — Error hierarchy."""


class LilithError(Exception):
    """Base exception for Lilith Agent."""
    pass


class ToolError(LilithError):
    """Tool execution error."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"[{tool_name}] {message}")


class APIError(LilithError):
    """API communication error."""
    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {status_code}: {message}")


class ConfigError(LilithError):
    """Configuration error."""
    pass
