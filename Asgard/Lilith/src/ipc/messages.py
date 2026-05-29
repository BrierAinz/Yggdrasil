import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


# --- Enums para seguridad y claridad ---
class IPCMessageType(str, Enum):
    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    GOOGLE = "google"
    GROK = "grok"
    QWEN = "qwen"


# --- Modelos de Mensajes ---
class BaseIPCMessage(BaseModel):
    type: IPCMessageType
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: datetime.now().isoformat())


class CommandSendMessage(BaseIPCMessage):
    type: Literal[IPCMessageType.COMMAND] = IPCMessageType.COMMAND
    action: Literal["send_message"] = "send_message"
    payload: Dict[str, str]  # {"text": "Hola"}


class QueryGetStatus(BaseIPCMessage):
    type: Literal[IPCMessageType.QUERY] = IPCMessageType.QUERY
    action: Literal["get_status"] = "get_status"
    payload: Optional[Dict[str, Any]] = None


class EventStatusUpdate(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["status_update"] = "status_update"
    payload: Dict[str, Any]
    # {
    #     "state": "running" | "idle" | "busy" | "error",
    #     "provider": Optional[LLMProvider],
    #     "health": Optional[dict]
    # }


class EventChatDelta(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["chat_delta"] = "chat_delta"
    payload: Dict[str, str]  # {"delta": "H"}


class EventChatFinal(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["chat_final"] = "chat_final"
    payload: Dict[str, Any]  # text, agent, agent_display, delegated (bool)


class EventDecisionRequest(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["decision_request"] = "decision_request"
    payload: Dict[str, Any]
    # {
    #     "command": str,
    #     "risk_level": "low" | "medium" | "high",
    #     "reason": str,
    #     "correlation_id": str
    # }


class CommandDecisionResult(BaseIPCMessage):
    type: Literal[IPCMessageType.COMMAND] = IPCMessageType.COMMAND
    action: Literal["decision_result"] = "decision_result"
    payload: Dict[str, Any]
    # {
    #     "correlation_id": str,
    #     "approved": bool
    # }


class EventError(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["error"] = "error"
    payload: Dict[str, str]  # {"message": "Error details"}


class QueryGetConfig(BaseIPCMessage):
    type: Literal[IPCMessageType.QUERY] = IPCMessageType.QUERY
    action: Literal["get_config"] = "get_config"
    payload: Optional[Dict[str, Any]] = None


class CommandUpdateConfig(BaseIPCMessage):
    type: Literal[IPCMessageType.COMMAND] = IPCMessageType.COMMAND
    action: Literal["update_config"] = "update_config"
    payload: Dict[str, Any]  # Full or partial config dict


class EventConfigData(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["config_data"] = "config_data"
    payload: Dict[str, Any]  # SebasConfig.model_dump()


class QueryGetStats(BaseIPCMessage):
    type: Literal[IPCMessageType.QUERY] = IPCMessageType.QUERY
    action: Literal["get_stats"] = "get_stats"
    payload: Optional[Dict[str, Any]] = None


class EventStatsData(BaseIPCMessage):
    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["stats_data"] = "stats_data"
    payload: Dict[str, Any]  # StatsTracker.get_all()


class CommandGeneric(BaseIPCMessage):
    """Generic command for actions not requiring specific validation"""

    type: Literal[IPCMessageType.COMMAND] = IPCMessageType.COMMAND
    action: str
    payload: Dict[str, Any] = {}


class EventData(BaseIPCMessage):
    """Generic event with payload (token_stats, session_history, pantheon_status, etc.)"""

    type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
    action: Literal["data"] = "data"
    payload: Dict[str, Any] = {}
