"""
API — Endpoints del sistema Council deliberativo v5.3

Endpoints:
POST /api/council/activate      — Inicia sesión de deliberación (sync)
POST /api/council/deliberate    — Inicia deliberación async con streaming
GET  /api/council/stream/{session_id} — SSE streaming de deliberación en curso
GET  /api/council/decisions     — Lista ADRs existentes
GET  /api/council/sessions      — Estadísticas de sesiones
GET  /api/council/session/{session_id} — Detalle de una sesión
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/council", tags=["council"])
logger = logging.getLogger("lilith.council_api")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _json_response(data: dict, status_code: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
    )


# ── Modelos Pydantic ─────────────────────────────────────────────────────────


class OptionModel(BaseModel):
    id: str
    title: str
    description: str
    pros: List[str] = []
    cons: List[str] = []
    implications: List[str] = []


class CouncilActivateRequest(BaseModel):
    title: str
    context: str
    question: str
    options: List[OptionModel]
    participants: Optional[List[str]] = None


class CouncilDeliberateRequest(BaseModel):
    title: str
    context: str
    question: str
    options: List[OptionModel]
    participants: Optional[List[str]] = None
    max_rounds: int = Field(default=2, ge=1, le=5)
    streaming: bool = Field(default=True)


# ── Endpoints v5.0 (legacy compat) ───────────────────────────────────────────


@router.post("/activate")
async def activate_council(request: CouncilActivateRequest) -> Response:
    """Inicia una sesión de deliberación multi-agente (síncrono, legacy)."""
    try:
        from src.core.council import (
            CouncilProposal,
            DeliberationEngine,
            ProposalOption,
            SessionRecorder,
        )

        options = [
            ProposalOption(
                id=opt.id,
                title=opt.title,
                description=opt.description,
                pros=opt.pros,
                cons=opt.cons,
                implications=opt.implications,
            )
            for opt in request.options
        ]

        proposal = CouncilProposal(
            id=request.title.lower().replace(" ", "_")[:40],
            title=request.title,
            context=request.context,
            question=request.question,
            options=options,
        )

        logger.info("[Council API] Iniciando sesión: %s", request.title)

        engine = DeliberationEngine()
        session = engine.conduct_session(proposal, request.participants)

        recorder = SessionRecorder()
        session_file = recorder.save_session(session)
        adr_file = recorder.save_decision_record(session)
        recorder.log_votes(session)

        log_summary = "\n".join(session.deliberation_log[-15:])

        return _json_response(
            {
                "ok": True,
                "response": (
                    f"Council completado. Decisión: Opción {session.final_decision}\n\n"
                    f"--- Deliberación ---\n{log_summary}"
                ),
                "data": {
                    "decision": session.final_decision,
                    "participants": session.participants,
                    "consensus_reached": session.consensus_reached,
                    "session_file": str(session_file),
                    "adr_file": str(adr_file),
                    "opinions_count": len(session.opinions),
                },
            }
        )

    except Exception as e:
        logger.exception("[Council API] Error: %s", e)
        return _json_response({"ok": False, "error": str(e)}, status_code=500)


# ── Endpoints v5.3 (async + streaming) ───────────────────────────────────────


@router.post("/deliberate")
async def start_deliberation(request: CouncilDeliberateRequest) -> Response:
    """
    Inicia una deliberación async v5.3 con debate multi-agente.

    Si streaming=True, usa GET /api/council/stream/{session_id} para recibir eventos.
    """
    try:
        from src.core.council import (
            CouncilConfig,
            CouncilOrchestrator,
            get_council_orchestrator,
        )

        orchestrator = get_council_orchestrator(_project_root())
        orchestrator.config.max_debate_rounds = request.max_rounds

        # Crear propuesta
        proposal = await orchestrator.create_proposal(
            title=request.title,
            context=request.context,
            question=request.question,
            options=[opt.model_dump() for opt in request.options],
        )

        if request.streaming:
            # Iniciar en background, retornar session_id
            asyncio.create_task(
                orchestrator.conduct_deliberation(proposal, request.participants)
            )

            return _json_response(
                {
                    "ok": True,
                    "session_id": proposal.id,
                    "status": "streaming",
                    "message": "Conecta a /api/council/stream/{session_id} para ver la deliberación",
                }
            )
        else:
            # Ejecutar y esperar
            session = await orchestrator.conduct_deliberation(
                proposal, request.participants
            )

            return _json_response(
                {
                    "ok": True,
                    "session_id": session.session_id,
                    "final_decision": session.final_decision,
                    "consensus_reached": session.consensus_reached,
                    "participants": session.participants,
                    "messages_count": len(session.messages),
                    "rounds": session.current_round,
                }
            )

    except Exception as e:
        logger.exception("[Council API] Error en deliberation: %s", e)
        return _json_response({"ok": False, "error": str(e)}, status_code=500)


@router.get("/stream/{session_id}")
async def stream_deliberation(session_id: str, request: Request) -> StreamingResponse:
    """
    Streaming SSE de una deliberación en curso.

    Eventos:
    - session_started
    - phase_started (initial_analysis, debate, final_vote)
    - message (cada intervención de agente)
    - phase_completed
    - session_completed
    - final_result
    """
    from src.core.council import get_council_orchestrator

    orchestrator = get_council_orchestrator(_project_root())

    async def event_generator():
        """Generador de eventos SSE."""
        session = orchestrator._active_sessions.get(session_id)
        if not session:
            yield f"event: error\ndata: {{'error': 'Session not found'}}\n\n"
            return

        # Enviar estado actual
        yield f"event: connected\ndata: {{'session_id': '{session_id}', 'phase': '{session.current_phase.value}'}}\n\n"

        # Esperar y emitir nuevos mensajes
        last_message_count = len(session.messages)
        import asyncio

        while session.current_phase.value != "completed":
            await asyncio.sleep(0.5)

            if len(session.messages) > last_message_count:
                for msg in session.messages[last_message_count:]:
                    event_data = json.dumps(
                        {
                            "agent": msg.agent_name,
                            "phase": msg.phase.value,
                            "option": msg.target_option,
                            "content": msg.content[:200],
                        }
                    )
                    yield f"event: message\ndata: {event_data}\n\n"
                last_message_count = len(session.messages)

        # Resultado final
        yield f"event: final_result\ndata: {{'decision': '{session.final_decision}', 'consensus': {str(session.consensus_reached).lower()}}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> Response:
    """Obtiene detalle de una sesión de deliberación."""
    try:
        from src.core.council import get_council_orchestrator

        orchestrator = get_council_orchestrator(_project_root())
        session = orchestrator._active_sessions.get(session_id)

        if not session:
            return _json_response(
                {
                    "ok": False,
                    "error": "Session not found",
                },
                status_code=404,
            )

        return _json_response(
            {
                "ok": True,
                "session": {
                    "session_id": session.session_id,
                    "proposal": {
                        "id": session.proposal.id,
                        "title": session.proposal.title,
                        "question": session.proposal.question,
                    },
                    "participants": session.participants,
                    "current_phase": session.current_phase.value,
                    "current_round": session.current_round,
                    "messages_count": len(session.messages),
                    "final_decision": session.final_decision,
                    "consensus_reached": session.consensus_reached,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": session.ended_at.isoformat()
                    if session.ended_at
                    else None,
                },
            }
        )

    except Exception as e:
        logger.exception("[Council API] Error: %s", e)
        return _json_response({"ok": False, "error": str(e)}, status_code=500)


@router.get("/decisions")
async def list_decisions() -> Response:
    """Lista los ADRs existentes en Vanaheim/Council/decisions/."""
    try:
        from src.core.council.session_recorder import SessionRecorder

        recorder = SessionRecorder()
        decisions = recorder.list_decisions()
        return _json_response(
            {"ok": True, "decisions": decisions, "count": len(decisions)}
        )
    except Exception as e:
        return _json_response({"ok": False, "error": str(e)}, status_code=500)


@router.get("/sessions")
async def session_stats() -> Response:
    """Estadísticas de sesiones del Council."""
    try:
        from src.core.council.session_recorder import SessionRecorder

        recorder = SessionRecorder()
        return _json_response(
            {
                "ok": True,
                "session_count": recorder.get_session_count(),
                "decision_count": len(recorder.list_decisions()),
            }
        )
    except Exception as e:
        return _json_response({"ok": False, "error": str(e)}, status_code=500)
