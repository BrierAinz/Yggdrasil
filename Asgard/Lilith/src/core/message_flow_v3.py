"""
Lilith 3.0 — Flujo unificado de mensaje (Fase 1).
mensaje → SimpleRouter → ToolRegistryV3 → execute() → respuesta
Si el router no sugiere tool, se usa generate_reply (Kimi).
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.tools.registry import ToolRegistryV3, create_default_registry

from .simple_router import route

logger = logging.getLogger("MessageFlowV3")

# Registry por defecto (se crea con project_root al first use)
_default_registry: Optional[ToolRegistryV3] = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_registry() -> ToolRegistryV3:
    """Devuelve el ToolRegistryV3 por defecto (singleton)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry(_project_root())
    return _default_registry


def process_message(
    message: str,
    context: str = "",
    registry: Optional[ToolRegistryV3] = None,
) -> Dict[str, Any]:
    """
    Procesa un mensaje con el flujo 3.0: router → tool o generate_reply.
    Args:
        message: texto del usuario
        context: contexto opcional (system prompt / memoria) para generate_reply
        registry: si no se pasa, se usa el por defecto
    Returns:
        dict con "response" (str) y opcionalmente "tool_used" (str), "error" (bool)
    """
    reg = registry or get_registry()
    text = (message or "").strip()
    if not text:
        return {"response": "(mensaje vacío)", "tool_used": None}

    tool_name, params = route(text)
    if tool_name and reg.has(tool_name):
        logger.info("FlowV3: ejecutando tool %s", tool_name)
        result = reg.execute(tool_name, params)
        response = (
            result.get("response", "") if isinstance(result, dict) else str(result)
        )
        return {
            "response": response,
            "tool_used": tool_name,
            "data": result.get("data") if isinstance(result, dict) else None,
        }
    # Fallback a generate_reply
    logger.debug("FlowV3: sin match de tool, usando generate_reply")
    params_reply = {"message": text, "context": context}
    result = reg.execute("generate_reply", params_reply)
    response = result.get("response", "") if isinstance(result, dict) else str(result)
    return {"response": response, "tool_used": "generate_reply"}
