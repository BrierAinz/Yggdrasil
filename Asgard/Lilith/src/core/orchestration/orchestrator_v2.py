"""
Orchestrator con Stack de Atención y Modos de Personalidad.

Extensión del orchestrator original que integra:
- Extracción automática de subtareas
- Stack de atención persistente
- Modos de personalidad dinámicos
- Inyección de contexto en el planner
"""
import logging
from typing import Any, Dict, List, Optional

from src.core.attention_stack import AttentionStack, get_attention_stack
from src.core.persona.manager import detect_and_set_mode, get_personality_mode_manager
from src.core.task_extractor import TaskExtractor, extract_tasks_simple

logger = logging.getLogger("lilith.orchestrator.v2")


class OrchestratorV2:
    """
    Orchestrator extendido con stack de atención y modos de personalidad.

    Esta clase se puede usar como mixin o wrapper del orchestrator existente.
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path
        self.task_extractor = TaskExtractor(base_path, use_llm=False)
        logger.info("[OrchestratorV2] Initialized")

    async def process_request_with_context(
        self,
        session_id: str,
        user_message: str,
        user_role: str = "public",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Procesa un request con extracción de subtareas y gestión de stack.

        Args:
            session_id: ID de la sesión
            user_message: Mensaje del usuario
            user_role: Rol del usuario
            context: Contexto adicional

        Returns:
            Dict con resultado y metadata
        """
        context = context or {}

        # 1. Extraer subtareas del mensaje
        extracted_tasks = self.task_extractor.extract(user_message)

        if extracted_tasks:
            logger.info(
                "[OrchestratorV2] Found %d subtasks in message", len(extracted_tasks)
            )

            # Añadir al stack de atención
            stack = get_attention_stack(session_id, self.base_path)
            for task in extracted_tasks:
                stack.push(
                    description=task.description,
                    priority=4 if task.confidence >= 0.8 else 3,
                    metadata={
                        "source": task.source,
                        "confidence": task.confidence,
                        "is_explicit": task.is_explicit,
                    },
                )

        # 2. Detectar modo de personalidad
        detected_mode = detect_and_set_mode(user_message, session_id, self.base_path)

        if detected_mode:
            logger.info("[OrchestratorV2] Auto-detected mode: %s", detected_mode)

        # 3. Preparar contexto enriquecido
        enriched_context = self._enrich_context(session_id, context)

        # 4. Retornar información para el planner
        return {
            "session_id": session_id,
            "user_message": user_message,
            "user_role": user_role,
            "extracted_tasks": [
                {
                    "description": t.description,
                    "confidence": t.confidence,
                    "source": t.source,
                }
                for t in extracted_tasks
            ],
            "detected_mode": detected_mode,
            "enriched_context": enriched_context,
        }

    def _enrich_context(
        self, session_id: str, base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enriquece el contexto con stack y modo.

        Args:
            session_id: ID de la sesión
            base_context: Contexto base

        Returns:
            Contexto enriquecido
        """
        context = base_context.copy()

        # Añadir stack de atención
        stack = get_attention_stack(session_id, self.base_path)
        stack_block = stack.to_context_block()

        if stack_block:
            context["attention_stack"] = stack_block
            context["has_pending_tasks"] = True
        else:
            context["has_pending_tasks"] = False

        # Añadir modo de personalidad
        mode_manager = get_personality_mode_manager(self.base_path)
        mode_overlay = mode_manager.get_mode_overlay(session_id)

        if mode_overlay:
            context["personality_mode"] = mode_overlay
            context["mode_info"] = mode_manager.get_current_mode_info(session_id)

        return context

    def complete_task(self, session_id: str, task_description: str) -> bool:
        """
        Marca una tarea como completada buscando por descripción.

        Args:
            session_id: ID de la sesión
            task_description: Descripción de la tarea (o parte)

        Returns:
            True si se encontró y marcó
        """
        stack = get_attention_stack(session_id, self.base_path)
        items = stack.get_active()

        for item in items:
            if task_description.lower() in item.description.lower():
                success = stack.pop(item.id)
                if success:
                    logger.info("[OrchestratorV2] Completed task: %s", item.description)
                return success

        return False

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene resumen completo de una sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Dict con resumen
        """
        stack = get_attention_stack(session_id, self.base_path)
        mode_manager = get_personality_mode_manager(self.base_path)

        return {
            "session_id": session_id,
            "attention_stack": {
                "stats": stack.get_stats(),
                "active_items": [item.to_dict() for item in stack.get_active()],
            },
            "personality_mode": mode_manager.get_current_mode_info(session_id),
            "mode_history": [
                {"from": t.from_mode, "to": t.to_mode, "reason": t.reason}
                for t in mode_manager.get_mode_history(session_id, limit=5)
            ],
        }


# Funciones conveniencia


def enrich_context_for_planner(
    session_id: str, base_context: Dict[str, Any], base_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Función conveniencia para enriquecer contexto antes de pasar al planner.

    Args:
        session_id: ID de la sesión
        base_context: Contexto base
        base_path: Ruta base

    Returns:
        Contexto enriquecido
    """
    orchestrator = OrchestratorV2(base_path)
    return orchestrator._enrich_context(session_id, base_context)


def extract_and_push_tasks(
    message: str, session_id: str, base_path: Optional[str] = None
) -> List[str]:
    """
    Extrae tareas de un mensaje y las añade al stack.

    Args:
        message: Mensaje del usuario
        session_id: ID de la sesión
        base_path: Ruta base

    Returns:
        Lista de descripciones de tareas añadidas
    """
    tasks = extract_tasks_simple(message, base_path)

    if tasks:
        stack = get_attention_stack(session_id, base_path)
        for task in tasks:
            stack.push(description=task, priority=3)

    return tasks


__all__ = ["OrchestratorV2", "enrich_context_for_planner", "extract_and_push_tasks"]
