"""
Context Enricher - Integración de Stack y Modos con Orchestrator

Enriquece el contexto del Planner con:
- Attention Stack (tareas pendientes)
- Personality Mode (overlay activo)
- Extracción automática de subtareas
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    Enriquecedor de contexto para el Planner

    Funciones:
    - Inyectar attention stack en contexto
    - Inyectar personality mode overlay
    - Extraer y agregar subtareas automáticamente
    """

    def __init__(
        self, attention_stack_module, personality_mode_module, task_extractor_module
    ):
        """
        Args:
            attention_stack_module: Módulo attention_stack
            personality_mode_module: Módulo personality_mode_manager
            task_extractor_module: Módulo task_extractor
        """
        self.attention_stack = attention_stack_module
        self.personality_mode = personality_mode_module
        self.task_extractor = task_extractor_module

    def enrich_context_for_planner(
        self,
        session_id: str,
        message: str,
        base_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enriquecer contexto antes de enviarlo al Planner

        Args:
            session_id: ID de sesión (channel_id, chat_id)
            message: Mensaje del usuario
            base_context: Contexto base (memoria, usuario, etc.)

        Returns:
            Contexto enriquecido con stack, modo, y subtareas extraídas
        """
        if base_context is None:
            base_context = {}

        enriched = base_context.copy()

        # 1. Obtener attention stack
        try:
            stack = self.attention_stack.get_attention_stack(session_id)
            active_tasks = stack.get_active()

            if active_tasks:
                enriched["attention_stack"] = {
                    "has_pending": True,
                    "count": len(active_tasks),
                    "tasks": [
                        {
                            "id": task.id,
                            "description": task.description,
                            "priority": task.priority,
                            "status": task.status,
                        }
                        for task in active_tasks
                    ],
                    "context_block": stack.to_context_block(),
                }
            else:
                enriched["attention_stack"] = {
                    "has_pending": False,
                    "count": 0,
                    "tasks": [],
                }

        except Exception as e:
            logger.error(f"Failed to get attention stack: {e}")
            enriched["attention_stack"] = {
                "has_pending": False,
                "count": 0,
                "tasks": [],
            }

        # 2. Detectar y activar personality mode
        try:
            # Intentar detección automática
            detected_mode = self.personality_mode.detect_and_set_mode(
                message, session_id
            )

            # Obtener info del modo actual (detectado o sticky previo)
            mode_info = self.personality_mode.get_personality_mode_manager().get_current_mode_info(
                session_id
            )

            if mode_info:
                enriched["personality_mode"] = {
                    "active": True,
                    "mode_id": mode_info["id"],
                    "mode_name": mode_info["name"],
                    "emoji": mode_info["emoji"],
                    "overlay": self.personality_mode.get_personality_mode_manager().get_mode_overlay(
                        session_id
                    ),
                    "was_auto_detected": detected_mode is not None,
                }
            else:
                enriched["personality_mode"] = {"active": False}

        except Exception as e:
            logger.error(f"Failed to process personality mode: {e}")
            enriched["personality_mode"] = {"active": False}

        # 3. Extraer subtareas del mensaje (si aplica)
        try:
            extractor = self.task_extractor.get_task_extractor()

            if extractor.should_extract(message):
                extracted_tasks = extractor.extract_tasks(message)

                if extracted_tasks:
                    enriched["extracted_tasks"] = {
                        "found": True,
                        "count": len(extracted_tasks),
                        "tasks": [
                            {
                                "description": task.description,
                                "confidence": task.confidence,
                                "priority": task.priority,
                                "order": task.order,
                            }
                            for task in extracted_tasks
                        ],
                    }

                    # Agregar automáticamente al stack
                    stack = self.attention_stack.get_attention_stack(session_id)
                    for task in extracted_tasks:
                        stack.push(
                            description=task.description,
                            priority=task.priority,
                            metadata={
                                "auto_extracted": True,
                                "confidence": task.confidence,
                            },
                        )

                    logger.info(
                        f"Auto-extracted and added {len(extracted_tasks)} tasks to stack"
                    )
                else:
                    enriched["extracted_tasks"] = {"found": False}
            else:
                enriched["extracted_tasks"] = {"found": False}

        except Exception as e:
            logger.error(f"Failed to extract tasks: {e}")
            enriched["extracted_tasks"] = {"found": False}

        return enriched

    def build_system_prompt_with_enrichment(
        self, base_system_prompt: str, enriched_context: Dict[str, Any]
    ) -> str:
        """
        Construir system prompt con contexto enriquecido

        Args:
            base_system_prompt: Prompt base de Lilith
            enriched_context: Contexto enriquecido

        Returns:
            System prompt completo con stack + modo inyectados
        """
        parts = [base_system_prompt]

        # Inyectar personality mode overlay (al principio)
        mode_data = enriched_context.get("personality_mode", {})
        if mode_data.get("active"):
            overlay = mode_data.get("overlay", "")
            if overlay:
                parts.insert(0, overlay)
                parts.insert(1, "\n---\n")

        # Inyectar attention stack (después del base prompt)
        stack_data = enriched_context.get("attention_stack", {})
        if stack_data.get("has_pending"):
            context_block = stack_data.get("context_block", "")
            if context_block:
                parts.append("\n---\n")
                parts.append(context_block)

        return "\n".join(parts)

    def mark_task_done_if_completed(
        self, session_id: str, executed_steps: List[Dict[str, Any]]
    ):
        """
        Marcar tareas como done si se completaron en el plan

        Args:
            session_id: ID de sesión
            executed_steps: Pasos ejecutados del plan
        """
        try:
            stack = self.attention_stack.get_attention_stack(session_id)
            active_tasks = stack.get_active()

            # Heurística simple: si un step menciona parte de la descripción de una tarea, marcarla done
            for task in active_tasks:
                task_keywords = set(task.description.lower().split())

                for step in executed_steps:
                    step_text = (
                        str(step.get("tool", "")) + " " + str(step.get("params", ""))
                    )
                    step_text_lower = step_text.lower()

                    # Match si al menos 2 keywords coinciden
                    matches = sum(
                        1
                        for kw in task_keywords
                        if kw in step_text_lower and len(kw) > 3
                    )

                    if matches >= 2:
                        stack.pop(task.id)
                        logger.info(
                            f"Auto-marked task {task.id} as done (matched step: {step.get('tool')})"
                        )
                        break

        except Exception as e:
            logger.error(f"Failed to mark tasks as done: {e}")


# Singleton global
_context_enricher: Optional[ContextEnricher] = None


def initialize_context_enricher(
    attention_stack_module, personality_mode_module, task_extractor_module
):
    """Inicializar el context enricher global"""
    global _context_enricher
    _context_enricher = ContextEnricher(
        attention_stack_module=attention_stack_module,
        personality_mode_module=personality_mode_module,
        task_extractor_module=task_extractor_module,
    )


def get_context_enricher() -> ContextEnricher:
    """Obtener instancia singleton del context enricher"""
    if _context_enricher is None:
        raise ValueError("Context enricher not initialized")
    return _context_enricher
