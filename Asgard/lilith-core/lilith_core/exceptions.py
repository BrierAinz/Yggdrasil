"""Custom exception hierarchy for the Lilith agent ecosystem."""


class LilithError(Exception):
    """Base exception for all Lilith errors."""

    pass


class ToolError(LilithError):
    """Exception raised when a tool execution fails."""

    pass


class LLMError(LilithError):
    """Exception raised when communication with an LLM provider fails."""

    pass
