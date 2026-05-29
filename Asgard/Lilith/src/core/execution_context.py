from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

current_agent: ContextVar[str] = ContextVar("current_agent", default="nobody")


def get_current_agent() -> str:
    val = (current_agent.get() or "").strip().lower()
    return val or "nobody"


def set_current_agent(name: Optional[str]) -> None:
    current_agent.set(((name or "").strip().lower()) or "nobody")
