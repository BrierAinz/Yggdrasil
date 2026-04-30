"""
Tool: activate_council

Activa el sistema deliberativo multi-agente del Council.
Los agentes del Panteón debaten opciones y generan un ADR en Vanaheim.
"""
import logging
from typing import Any, Dict, List

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("lilith.tools.council")


class ActivateCouncilTool(LilithTool):
    """
    Activa el Council multi-agente para tomar una decisión arquitectónica.

    Los agentes Eva, Adán, Odín y Archivero debaten las opciones,
    votan y generan un ADR (Architecture Decision Record) en Vanaheim/Council/.
    """

    @property
    def name(self) -> str:
        return "activate_council"

    def get_description(self) -> str:
        return (
            "Activa el Council deliberativo: los agentes del Panteón debaten opciones "
            "y generan un Architecture Decision Record (ADR) en Vanaheim."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la decisión a tomar",
                },
                "context": {
                    "type": "string",
                    "description": "Contexto y antecedentes de la decisión",
                },
                "question": {
                    "type": "string",
                    "description": "Pregunta específica a resolver",
                },
                "options": {
                    "type": "array",
                    "description": "Lista de opciones a evaluar",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "pros": {"type": "array", "items": {"type": "string"}},
                            "cons": {"type": "array", "items": {"type": "string"}},
                            "implications": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["id", "title", "description"],
                    },
                },
                "participants": {
                    "type": "array",
                    "description": "Agentes a incluir (default: todos disponibles)",
                    "items": {"type": "string"},
                },
            },
            "required": ["title", "context", "question", "options"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        title = str(params.get("title", "")).strip()
        context = str(params.get("context", "")).strip()
        question = str(params.get("question", "")).strip()
        raw_options: List[Dict] = params.get("options", [])
        participants: List[str] = params.get("participants") or None

        # Validaciones básicas
        if not title:
            return {"response": "[Council] Parámetro 'title' requerido.", "error": True}
        if not raw_options or len(raw_options) < 2:
            return {
                "response": "[Council] Se necesitan al menos 2 opciones.",
                "error": True,
            }

        try:
            from src.core.council.deliberation_engine import DeliberationEngine
            from src.core.council.models import CouncilProposal, ProposalOption
            from src.core.council.session_recorder import SessionRecorder

            # Construir propuesta
            options = []
            for opt in raw_options:
                options.append(
                    ProposalOption(
                        id=str(opt.get("id", "?")),
                        title=str(opt.get("title", "")),
                        description=str(opt.get("description", "")),
                        pros=list(opt.get("pros") or []),
                        cons=list(opt.get("cons") or []),
                        implications=list(opt.get("implications") or []),
                    )
                )

            proposal = CouncilProposal(
                id=title.lower().replace(" ", "_")[:40],
                title=title,
                context=context,
                question=question,
                options=options,
            )

            logger.info("[Council] Iniciando sesión: %s", title)

            # Conducir sesión
            engine = DeliberationEngine()
            session = engine.conduct_session(proposal, participants)

            # Persistir resultados
            recorder = SessionRecorder()
            session_file = recorder.save_session(session)
            adr_file = recorder.save_decision_record(session)
            recorder.log_votes(session)

            # Resumen del log (últimas líneas relevantes)
            log_summary = "\n".join(session.deliberation_log[-15:])

            response = (
                f"Council completado.\n"
                f"Decisión: **Opción {session.final_decision}**\n"
                f"Participantes: {', '.join(session.participants)}\n"
                f"ADR: {adr_file.name}\n\n"
                f"--- Deliberación ---\n{log_summary}"
            )

            return {
                "response": response,
                "data": {
                    "decision": session.final_decision,
                    "participants": session.participants,
                    "consensus_reached": session.consensus_reached,
                    "session_file": str(session_file),
                    "adr_file": str(adr_file),
                    "opinions_count": len(session.opinions),
                },
            }

        except Exception as e:
            logger.exception("[Council] Error en sesión: %s", e)
            return {
                "response": f"[Council] Error durante la deliberación: {e}",
                "error": True,
            }
