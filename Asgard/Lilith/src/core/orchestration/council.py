"""
Council Vanaheim v5.3 — CouncilOrchestrator
===========================================

Orquestador avanzado de deliberación multi-agente.

Features v5.3:
- Async deliberation con streaming
- Agent-to-agent debate (respuestas cruzadas)
- Integración con Lilith orchestrator
- WebSocket support para tiempo real
- ADR auto-generation
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set

from src.core.council.deliberation_engine import AGENT_WEIGHTS, DeliberationEngine
from src.core.council.models import (
    AgentOpinion,
    CouncilProposal,
    CouncilSession,
    ProposalOption,
    VoteOption,
)

logger = logging.getLogger("lilith.council.orchestrator")


class DebatePhase(Enum):
    """Fases de una sesión de debate."""

    INITIAL_ANALYSIS = "initial_analysis"
    DEBATE = "debate"
    REBUTTAL = "rebuttal"
    FINAL_VOTE = "final_vote"
    COMPLETED = "completed"


@dataclass
class DebateMessage:
    """Un mensaje en el debate entre agentes."""

    agent_name: str
    phase: DebatePhase
    target_option: str
    content: str
    vote: Optional[VoteOption] = None
    confidence: float = 0.5
    responding_to: Optional[str] = None  # Nombre del agente al que responde
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class DebateSession:
    """Sesión de debate con historial de mensajes."""

    session_id: str
    proposal: CouncilProposal
    participants: List[str]
    messages: List[DebateMessage] = field(default_factory=list)
    current_phase: DebatePhase = DebatePhase.INITIAL_ANALYSIS
    max_debate_rounds: int = 2
    current_round: int = 0
    final_decision: Optional[str] = None
    consensus_reached: bool = False
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


@dataclass
class CouncilConfig:
    """Configuración para el Council."""

    min_participants: int = 2
    max_debate_rounds: int = 2
    consensus_threshold: float = 0.6
    require_unanimity: bool = False
    streaming_enabled: bool = True
    auto_generate_adr: bool = True
    adrs_path: Optional[Path] = None


class CouncilOrchestrator:
    """
    Orquestador avanzado de sesiones deliberativas del Council.

    Features:
    - Async deliberation completo
    - Streaming de eventos en tiempo real
    - Debate multi-ronda con respuestas cruzadas
    - Integración nativa con Lilith
    """

    def __init__(
        self, base_path: Optional[Path] = None, config: Optional[CouncilConfig] = None
    ):
        self.base_path = base_path
        self.config = config or CouncilConfig()
        self._engine = DeliberationEngine()
        self._agents: Optional[Dict] = None
        self._active_sessions: Dict[str, DebateSession] = {}
        self._subscribers: List[Callable[[str, Dict], None]] = []

    def _load_agents(self) -> Dict:
        """Carga agentes disponibles del Panteón."""
        if self._agents is not None:
            return self._agents

        from src.core.agents.panteon.adan import AdanAgent
        from src.core.agents.panteon.archivero import ArchiveroAgent
        from src.core.agents.panteon.eva import EvaAgent
        from src.core.agents.panteon.odin import OdinAgent

        agents = {}
        for name, cls in [
            ("eva", EvaAgent),
            ("adan", AdanAgent),
            ("odin", OdinAgent),
            ("archivero", ArchiveroAgent),
        ]:
            try:
                instance = cls()
                if instance.is_available():
                    agents[name] = instance
                    logger.info("[Council] Agente %s disponible", name)
                else:
                    logger.warning("[Council] Agente %s no disponible", name)
            except Exception as e:
                logger.warning("[Council] Error cargando %s: %s", name, e)

        self._agents = agents
        return agents

    def subscribe(self, callback: Callable[[str, Dict], None]) -> None:
        """Suscribe un callback para recibir eventos de streaming."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, Dict], None]) -> None:
        """Desuscribe un callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _emit(self, event_type: str, data: Dict) -> None:
        """Emite un evento a todos los suscriptores."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        for callback in self._subscribers:
            try:
                callback(event_type, event)
            except Exception as e:
                logger.warning("[Council] Error en subscriber: %s", e)

    async def create_proposal(
        self,
        title: str,
        context: str,
        question: str,
        options: List[Dict[str, Any]],
        created_by: str = "lilith",
    ) -> CouncilProposal:
        """Crea una nueva propuesta para deliberación."""
        proposal_options = [
            ProposalOption(
                id=opt.get("id", chr(65 + i)),  # A, B, C...
                title=opt["title"],
                description=opt.get("description", ""),
                pros=opt.get("pros", []),
                cons=opt.get("cons", []),
                implications=opt.get("implications", []),
            )
            for i, opt in enumerate(options)
        ]

        proposal = CouncilProposal(
            id=str(uuid.uuid4())[:8],
            title=title,
            context=context,
            question=question,
            options=proposal_options,
        )

        self._emit(
            "proposal_created",
            {
                "proposal_id": proposal.id,
                "title": title,
                "options_count": len(options),
                "created_by": created_by,
            },
        )

        return proposal

    async def conduct_deliberation(
        self,
        proposal: CouncilProposal,
        participants: Optional[List[str]] = None,
    ) -> DebateSession:
        """
        Conduce una deliberación completa con debate multi-agente.

        Args:
            proposal: La propuesta a deliberar
            participants: Lista de nombres de agentes (None = todos)

        Returns:
            DebateSession con historial completo
        """
        agents = self._load_agents()

        if participants is None:
            participants = list(agents.keys())
        else:
            participants = [p for p in participants if p in agents]

        if len(participants) < self.config.min_participants:
            raise ValueError(
                f"Se necesitan al menos {self.config.min_participants} participantes"
            )

        session = DebateSession(
            session_id=str(uuid.uuid4())[:12],
            proposal=proposal,
            participants=participants,
            max_debate_rounds=self.config.max_debate_rounds,
        )

        self._active_sessions[session.session_id] = session

        self._emit(
            "session_started",
            {
                "session_id": session.session_id,
                "proposal_id": proposal.id,
                "participants": participants,
            },
        )

        try:
            # FASE 1: Análisis individual
            await self._phase_initial_analysis(session, agents)

            # FASE 2: Debate multi-ronda
            for round_num in range(self.config.max_debate_rounds):
                session.current_round = round_num + 1
                await self._phase_debate(session, agents, round_num)

            # FASE 3: Réplicas (opcional)
            await self._phase_rebuttal(session, agents)

            # FASE 4: Votación final
            await self._phase_final_vote(session, agents)

        except Exception as e:
            logger.exception("[Council] Error en deliberación")
            self._emit(
                "session_error",
                {
                    "session_id": session.session_id,
                    "error": str(e),
                },
            )
            raise

        finally:
            session.ended_at = datetime.now()
            session.current_phase = DebatePhase.COMPLETED

            self._emit(
                "session_completed",
                {
                    "session_id": session.session_id,
                    "final_decision": session.final_decision,
                    "consensus_reached": session.consensus_reached,
                    "duration_seconds": (
                        session.ended_at - session.started_at
                    ).total_seconds(),
                },
            )

            # Generar ADR si está habilitado
            if self.config.auto_generate_adr:
                await self._generate_adr(session)

        return session

    async def _phase_initial_analysis(
        self,
        session: DebateSession,
        agents: Dict,
    ) -> None:
        """Fase 1: Cada agente analiza las opciones individualmente."""
        session.current_phase = DebatePhase.INITIAL_ANALYSIS

        self._emit(
            "phase_started",
            {
                "session_id": session.session_id,
                "phase": "initial_analysis",
            },
        )

        # Procesar en paralelo
        tasks = [
            self._agent_initial_analysis(agent_name, agents[agent_name], session)
            for agent_name in session.participants
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._emit(
            "phase_completed",
            {
                "session_id": session.session_id,
                "phase": "initial_analysis",
                "messages_count": len(session.messages),
            },
        )

    async def _agent_initial_analysis(
        self,
        agent_name: str,
        agent,
        session: DebateSession,
    ) -> None:
        """Un agente realiza su análisis inicial."""
        from src.core.council.deliberation_engine import (
            _ANALYSIS_PROMPT,
            _format_options,
        )

        prompt = _ANALYSIS_PROMPT.format(
            title=session.proposal.title,
            context=session.proposal.context,
            question=session.proposal.question,
            options_text=_format_options(session.proposal.options),
        )

        # Llamar al agente
        try:
            if asyncio.iscoroutinefunction(agent.execute):
                response = await asyncio.wait_for(agent.execute(prompt), timeout=60)
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, agent.execute, prompt
                )
        except Exception as e:
            logger.warning("[Council] Error en análisis de %s: %s", agent_name, e)
            response = '{"evaluations": []}'

        # Parsear respuesta
        from src.core.council.deliberation_engine import _parse_evaluations

        evaluations = _parse_evaluations(response)

        for ev in evaluations:
            try:
                vote = VoteOption[ev.get("vote", "NEUTRAL")]
            except KeyError:
                vote = VoteOption.NEUTRAL

            message = DebateMessage(
                agent_name=agent_name,
                phase=DebatePhase.INITIAL_ANALYSIS,
                target_option=str(ev.get("option_id", "?")),
                content=str(ev.get("reasoning", "")),
                vote=vote,
                confidence=float(ev.get("confidence", 0.5)),
            )
            session.messages.append(message)

            self._emit(
                "message",
                {
                    "session_id": session.session_id,
                    "message": {
                        "agent": agent_name,
                        "phase": "initial_analysis",
                        "option": message.target_option,
                        "vote": vote.name,
                        "confidence": message.confidence,
                        "content": message.content,
                    },
                },
            )

    async def _phase_debate(
        self,
        session: DebateSession,
        agents: Dict,
        round_num: int,
    ) -> None:
        """Fase 2: Debate entre agentes con respuestas cruzadas."""
        session.current_phase = DebatePhase.DEBATE

        self._emit(
            "phase_started",
            {
                "session_id": session.session_id,
                "phase": "debate",
                "round": round_num + 1,
            },
        )

        # Para cada opción controversial, permitir debate
        controversial = self._find_controversial_options(session)

        for option_id in controversial:
            # Ordenar agentes por voto (favor primero, luego contra)
            opinions = [
                m
                for m in session.messages
                if m.target_option == option_id and m.vote is not None
            ]

            favor = [m for m in opinions if m.vote.value > 0]
            against = [m for m in opinions if m.vote.value < 0]

            # Agente pro defiende su posición
            for pro_msg in favor[:1]:  # Limitar para no exceder tokens
                await self._agent_defend_position(
                    pro_msg.agent_name,
                    agents[pro_msg.agent_name],
                    session,
                    option_id,
                    True,
                    pro_msg.content,
                )

            # Agente contra responde
            for con_msg in against[:1]:
                await self._agent_defend_position(
                    con_msg.agent_name,
                    agents[con_msg.agent_name],
                    session,
                    option_id,
                    False,
                    con_msg.content,
                    responding_to=pro_msg.agent_name if favor else None,
                )

        self._emit(
            "phase_completed",
            {
                "session_id": session.session_id,
                "phase": "debate",
                "round": round_num + 1,
            },
        )

    async def _agent_defend_position(
        self,
        agent_name: str,
        agent,
        session: DebateSession,
        option_id: str,
        is_pro: bool,
        previous_argument: str,
        responding_to: Optional[str] = None,
    ) -> None:
        """Un agente defiende su posición en el debate."""
        option = next((o for o in session.proposal.options if o.id == option_id), None)
        if not option:
            return

        stance = "a favor" if is_pro else "en contra"
        prompt = f"""Eres {agent_name} en el Council de Lilith. Estás debatiendo sobre:

OPCIÓN {option_id}: {option.title}
{option.description}

Tu posición: {stance.upper()}
Argumento previo: {previous_argument}

{"Responde a los argumentos en contra. Sé conciso (máx 3 líneas)." if responding_to else "Defiende tu posición con argumentos sólidos (máx 3 líneas)."}

Responde SOLO con JSON:
{{"argument": "tu argumento", "confidence": 0.8}}"""

        try:
            if asyncio.iscoroutinefunction(agent.execute):
                response = await asyncio.wait_for(agent.execute(prompt), timeout=45)
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, agent.execute, prompt
                )

            # Extracer JSON
            import re

            match = re.search(r'\{.*"argument".*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                argument = data.get("argument", response[:200])
                confidence = float(data.get("confidence", 0.7))
            else:
                argument = response[:200]
                confidence = 0.7

        except Exception as e:
            logger.warning("[Council] Error en debate de %s: %s", agent_name, e)
            argument = f"[{agent_name} no pudo argumentar]"
            confidence = 0.3

        message = DebateMessage(
            agent_name=agent_name,
            phase=DebatePhase.DEBATE,
            target_option=option_id,
            content=argument,
            confidence=confidence,
            responding_to=responding_to,
        )
        session.messages.append(message)

        self._emit(
            "message",
            {
                "session_id": session.session_id,
                "message": {
                    "agent": agent_name,
                    "phase": "debate",
                    "option": option_id,
                    "stance": "pro" if is_pro else "con",
                    "responding_to": responding_to,
                    "content": argument,
                    "confidence": confidence,
                },
            },
        )

    async def _phase_rebuttal(self, session: DebateSession, agents: Dict) -> None:
        """Fase 3: Réplicas breves (opcional)."""
        session.current_phase = DebatePhase.REBUTTAL
        # Por ahora, skip para mantener deliberación eficiente
        pass

    async def _phase_final_vote(self, session: DebateSession, agents: Dict) -> None:
        """Fase 4: Votación final ponderada."""
        session.current_phase = DebatePhase.FINAL_VOTE

        self._emit(
            "phase_started",
            {
                "session_id": session.session_id,
                "phase": "final_vote",
            },
        )

        # Calcular scores basados en todos los mensajes
        scores: Dict[str, float] = {opt.id: 0.0 for opt in session.proposal.options}

        for msg in session.messages:
            if msg.vote is None or msg.target_option not in scores:
                continue

            base = msg.vote.value * msg.confidence
            weight = AGENT_WEIGHTS.get(msg.agent_name, {}).get("architecture", 1.0)
            scores[msg.target_option] += base * weight

        # Normalizar
        total = sum(abs(s) for s in scores.values()) or 1
        for opt_id in scores:
            scores[opt_id] = scores[opt_id] / total

        # Determinar ganador
        if scores:
            winner = max(scores.items(), key=lambda x: x[1])
            session.final_decision = winner[0]
            session.consensus_reached = winner[1] > 0

        self._emit(
            "phase_completed",
            {
                "session_id": session.session_id,
                "phase": "final_vote",
                "scores": scores,
                "winner": session.final_decision,
            },
        )

    def _find_controversial_options(self, session: DebateSession) -> List[str]:
        """Encuentra opciones con desacuerdo significativo."""
        by_option: Dict[str, List[VoteOption]] = {}
        for msg in session.messages:
            if msg.vote:
                by_option.setdefault(msg.target_option, []).append(msg.vote)

        controversial = []
        for opt_id, votes in by_option.items():
            has_favor = any(v.value > 0 for v in votes)
            has_against = any(v.value < 0 for v in votes)
            if has_favor and has_against:
                controversial.append(opt_id)

        return controversial

    async def _generate_adr(self, session: DebateSession) -> Path:
        """Genera un Architecture Decision Record de la sesión."""
        if not self.config.adrs_path:
            return None

        self.config.adrs_path.mkdir(parents=True, exist_ok=True)

        date_str = session.started_at.strftime("%Y-%m-%d")
        filename = f"ADR-{date_str}-{session.session_id}.md"
        filepath = self.config.adrs_path / filename

        # Construir contenido
        content = f"""# ADR-{session.session_id}: {session.proposal.title}

## Status
Accepted via Council deliberation

## Context
{session.proposal.context}

## Decision
**{session.final_decision}**: {next((o.title for o in session.proposal.options if o.id == session.final_decision), "Unknown")}

## Consequences
"""

        # Agregar opiniones resumidas
        content += "\n## Council Opinions\n\n"
        for msg in session.messages:
            if msg.phase == DebatePhase.INITIAL_ANALYSIS and msg.vote:
                content += (
                    f"- **{msg.agent_name}**: {msg.vote.name} ({msg.target_option})\n"
                )
                content += f"  - {msg.content}\n\n"

        content += f"""\n## Deliberation Log
- Participants: {', '.join(session.participants)}
- Started: {session.started_at.isoformat()}
- Ended: {session.ended_at.isoformat() if session.ended_at else 'N/A'}
- Consensus: {'Yes' if session.consensus_reached else 'No'}
- Rounds: {session.current_round}
"""

        filepath.write_text(content, encoding="utf-8")
        logger.info("[Council] ADR generado: %s", filepath)

        self._emit(
            "adr_generated",
            {
                "session_id": session.session_id,
                "path": str(filepath),
            },
        )

        return filepath

    async def stream_deliberation(
        self,
        proposal: CouncilProposal,
        participants: Optional[List[str]] = None,
    ) -> AsyncIterator[Dict]:
        """
        Streaming de una deliberación en tiempo real.

        Yields eventos: phase_started, message, phase_completed, session_completed
        """
        queue: asyncio.Queue = asyncio.Queue()

        def on_event(event_type: str, data: Dict):
            queue.put_nowait({"type": event_type, "data": data})

        self.subscribe(on_event)

        try:
            # Iniciar deliberación en background
            task = asyncio.create_task(
                self.conduct_deliberation(proposal, participants)
            )

            # Stream eventos mientras corre
            while not task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield event
                except asyncio.TimeoutError:
                    continue

            # Yield eventos restantes
            while not queue.empty():
                yield await queue.get()

            # Resultado final
            session = await task
            yield {
                "type": "final_result",
                "data": {
                    "session_id": session.session_id,
                    "final_decision": session.final_decision,
                    "consensus_reached": session.consensus_reached,
                    "messages_count": len(session.messages),
                },
            }

        finally:
            self.unsubscribe(on_event)


# Singleton
_council_orchestrator: Optional[CouncilOrchestrator] = None


def get_council_orchestrator(base_path: Optional[Path] = None) -> CouncilOrchestrator:
    """Obtiene el singleton del CouncilOrchestrator."""
    global _council_orchestrator
    if _council_orchestrator is None:
        config = CouncilConfig(
            adrs_path=Path(base_path) / "Vanaheim" / "Council" / "ADRs"
            if base_path
            else None,
        )
        _council_orchestrator = CouncilOrchestrator(base_path, config)
    return _council_orchestrator
