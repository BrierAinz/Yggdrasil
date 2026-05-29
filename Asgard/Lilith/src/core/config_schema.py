from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Provider = Literal[
    "ollama", "openai", "anthropic", "deepseek", "qwen", "grok", "venice", "kimi"
]


class LLMProviderConfig(BaseModel):
    # Provider-specific knobs; keep minimal and extend later.
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_sec: int = 60

    @field_validator("timeout_sec")
    @classmethod
    def _timeout_range(cls, v: int) -> int:
        if not (5 <= v <= 600):
            raise ValueError("timeout_sec out of range (5..600)")
        return v


class LLMConfig(BaseModel):
    provider: Provider = "ollama"
    model: str = "llama3"
    system_prompt: Optional[str] = Field(
        default=None, description="System prompt defining the AI persona."
    )
    providers: Dict[Provider, LLMProviderConfig] = Field(default_factory=dict)

    @field_validator("model")
    @classmethod
    def _model_required(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("model is required")
        return v


class SystemConfig(BaseModel):
    memory_window: int = 40
    max_tool_runtime_sec: int = 120

    @field_validator("memory_window")
    @classmethod
    def _mem_window_range(cls, v: int) -> int:
        if not (5 <= v <= 400):
            raise ValueError("memory_window out of range (5..400)")
        return v

    @field_validator("max_tool_runtime_sec")
    @classmethod
    def _runtime_range(cls, v: int) -> int:
        if not (5 <= v <= 3600):
            raise ValueError("max_tool_runtime_sec out of range (5..3600)")
        return v


class SafetyConfig(BaseModel):
    approval_timeout_sec: int = 45
    block_on_pending_approval: bool = True

    @field_validator("approval_timeout_sec")
    @classmethod
    def _approval_timeout_range(cls, v: int) -> int:
        if not (5 <= v <= 600):
            raise ValueError("approval_timeout_sec out of range (5..600)")
        return v


class AppConfig(BaseModel):
    config_version: int = Field(default=1)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
