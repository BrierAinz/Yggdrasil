"""
Workflows - Definición de nodos

v4.2.8: Nodos para el editor de workflows
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.workflows.nodes")


class NodeType(Enum):
    """Tipos de nodos soportados."""

    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    DELAY = "delay"


@dataclass
class WorkflowNode:
    """Nodo base para workflows."""

    id: str
    type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    connections: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "config": self.config,
            "position": self.position,
            "connections": self.connections,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowNode":
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            config=data.get("config", {}),
            position=data.get("position", {"x": 0, "y": 0}),
            connections=data.get("connections", []),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta el nodo. Debe ser implementado por subclases."""
        raise NotImplementedError("Subclases deben implementar execute()")


@dataclass
class TriggerNode(WorkflowNode):
    """Nodo trigger - inicia un workflow."""

    def __post_init__(self):
        self.type = NodeType.TRIGGER

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Un trigger solo propaga el contexto inicial."""
        trigger_type = self.config.get("trigger_type", "manual")

        logger.info(f"Trigger '{self.id}' activado: {trigger_type}")

        return {
            "success": True,
            "trigger_type": trigger_type,
            "triggered_at": datetime.utcnow().isoformat(),
            "output": self.config.get("initial_data", {}),
        }


@dataclass
class ActionNode(WorkflowNode):
    """Nodo acción - ejecuta una operación."""

    def __post_init__(self):
        self.type = NodeType.ACTION

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la acción configurada."""
        action_type = self.config.get("action_type")
        action_config = self.config.get("action_config", {})

        logger.info(f"Action '{self.id}' ejecutando: {action_type}")

        # Ejecutar handler según tipo
        handler = ACTION_HANDLERS.get(action_type)
        if not handler:
            return {
                "success": False,
                "error": f"Tipo de acción no soportado: {action_type}",
            }

        try:
            result = await handler(action_config, context)
            return {"success": True, "action_type": action_type, "output": result}
        except Exception as e:
            logger.error(f"Action '{self.id}' falló: {e}")
            return {"success": False, "action_type": action_type, "error": str(e)}


@dataclass
class ConditionNode(WorkflowNode):
    """Nodo condición - bifurca el flujo."""

    def __post_init__(self):
        self.type = NodeType.CONDITION

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evalúa la condición y retorna qué rama seguir."""
        condition_type = self.config.get("condition_type", "equals")
        condition_config = self.config.get("condition_config", {})

        logger.info(f"Condition '{self.id}' evaluando: {condition_type}")

        # Usar el evaluador de condiciones
        from .conditions import ConditionEvaluator

        evaluator = ConditionEvaluator()

        result = await evaluator.evaluate(condition_type, condition_config, context)

        # Determinar conexiones según resultado
        if result:
            branch = "true_branch"
        else:
            branch = "false_branch"

        connections = self.config.get(branch, [])

        return {
            "success": True,
            "result": result,
            "branch": branch,
            "next_nodes": connections,
        }


@dataclass
class DelayNode(WorkflowNode):
    """Nodo delay - pausa la ejecución."""

    def __post_init__(self):
        self.type = NodeType.DELAY

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Pausa la ejecución por el tiempo configurado."""
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_until = self.config.get("delay_until")  # ISO timestamp

        if delay_until:
            # Calcular delay hasta timestamp específico
            target = datetime.fromisoformat(delay_until.replace("Z", "+00:00"))
            now = datetime.utcnow()
            delay_seconds = max(0, (target - now).total_seconds())

        logger.info(f"Delay '{self.id}' pausando por {delay_seconds}s")

        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        return {
            "success": True,
            "delay_seconds": delay_seconds,
            "resumed_at": datetime.utcnow().isoformat(),
        }


# Handlers de acciones


async def _send_webhook(
    config: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Envía un webhook."""
    url = config.get("url")
    payload = config.get("payload", {})

    # Renderizar payload con contexto
    rendered_payload = _render_template(payload, context)

    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=rendered_payload, timeout=30.0)
        response.raise_for_status()

    return {"url": url, "status_code": response.status_code}


async def _send_notification(
    config: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Envía una notificación (Discord, etc)."""
    channel = config.get("channel", "discord")
    message = config.get("message", "")

    # Renderizar mensaje con contexto
    rendered_message = _render_template_string(message, context)

    # Integración con sistema de notificaciones existente
    if channel == "discord":
        # Usar webhook manager si existe
        try:
            from src.core.webhooks import get_webhook_manager

            webhook_mgr = get_webhook_manager()
            # Aquí se integraría con el sistema específico
            return {"channel": channel, "message": rendered_message}
        except:
            pass

    return {"channel": channel, "message": rendered_message, "simulated": True}


async def _execute_tool(
    config: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Ejecuta una herramienta del sistema."""
    tool_name = config.get("tool_name")
    tool_params = config.get("params", {})

    # Renderizar parámetros
    rendered_params = _render_template(tool_params, context)

    # Aquí se integraría con el sistema de herramientas
    return {
        "tool": tool_name,
        "params": rendered_params,
        "note": "Integración con tool system pendiente",
    }


async def _update_cache(
    config: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Actualiza una entrada de caché."""
    key = config.get("key")
    value = config.get("value")
    namespace = config.get("namespace", "workflows")
    ttl = config.get("ttl", 300)

    # Renderizar valor
    rendered_value = (
        _render_template_string(value, context) if isinstance(value, str) else value
    )

    try:
        from src.core.cache import get_cache

        cache = get_cache()
        await cache.set(key, rendered_value, namespace=namespace, ttl=ttl)
        return {"key": key, "namespace": namespace, "ttl": ttl}
    except Exception as e:
        return {"error": str(e)}


async def _create_task(
    config: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Crea una tarea en el sistema."""
    title = config.get("title", "Task from workflow")
    description = config.get("description", "")
    assignee = config.get("assignee")

    rendered_title = _render_template_string(title, context)
    rendered_description = _render_template_string(description, context)

    return {
        "title": rendered_title,
        "description": rendered_description,
        "assignee": assignee,
        "created_at": datetime.utcnow().isoformat(),
    }


async def _log_event(config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Registra un evento en el audit trail."""
    event_type = config.get("event_type", "workflow.action")
    message = config.get("message", "")

    rendered_message = _render_template_string(message, context)

    logger.info(f"[Audit] {event_type}: {rendered_message}")

    # Integración con audit logger existente
    try:
        from src.core.auditor import get_auditor

        auditor = get_auditor()
        auditor.log(
            {
                "event_type": event_type,
                "message": rendered_message,
                "workflow_context": context.get("workflow_id"),
            }
        )
    except:
        pass

    return {"event_type": event_type, "message": rendered_message}


# Registro de handlers
ACTION_HANDLERS: Dict[str, Callable] = {
    "webhook": _send_webhook,
    "notification": _send_notification,
    "tool": _execute_tool,
    "cache_update": _update_cache,
    "create_task": _create_task,
    "log": _log_event,
}


def _render_template(obj: Any, context: Dict[str, Any]) -> Any:
    """Renderiza un objeto reemplazando templates {{variable}}."""
    if isinstance(obj, str):
        return _render_template_string(obj, context)
    elif isinstance(obj, dict):
        return {k: _render_template(v, context) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_render_template(item, context) for item in obj]
    return obj


def _render_template_string(template: str, context: Dict[str, Any]) -> str:
    """Reemplaza {{variable}} con valores del contexto."""
    import re

    def replace(match):
        key = match.group(1).strip()
        # Soporte para notación punto: data.user.name
        keys = key.split(".")
        value = context
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, match.group(0))
            else:
                return match.group(0)
        return str(value) if value is not None else match.group(0)

    return re.sub(r"\{\{(\s*[\w.]+\s*)\}\}", replace, template)


def create_node(data: Dict[str, Any]) -> WorkflowNode:
    """Factory para crear nodos según su tipo."""
    node_type = NodeType(data.get("type", "action"))

    node_classes = {
        NodeType.TRIGGER: TriggerNode,
        NodeType.ACTION: ActionNode,
        NodeType.CONDITION: ConditionNode,
        NodeType.DELAY: DelayNode,
    }

    cls = node_classes.get(node_type, WorkflowNode)
    return cls.from_dict(data)
