"""
Motor de deliberación del Council.

Conduce sesiones de debate en 3 fases:
  1. Análisis individual (cada agente evalúa las opciones)
  2. Debate sobre desacuerdos
  3. Votación final ponderada → consenso
"""
import asyncio
import inspect
import json
import logging
import re
from typing import Dict, List, Optional

from .models import (
    AgentOpinion,
    CouncilProposal,
    CouncilSession,
    ProposalOption,
    VoteOption,
)

logger = logging.getLogger("lilith.council")

# Pesos de especialidad por agente y dominio
AGENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "eva": {"research": 1.5, "analysis": 1.3, "documentation": 1.2},
    "adan": {"code": 1.5, "refactor": 1.3, "testing": 1.2, "performance": 1.3},
    "odin": {"architecture": 1.5, "planning": 1.3, "strategy": 1.4},
    "archivero": {"documentation": 1.5, "history": 1.3, "knowledge": 1.2},
}

# Prompt para análisis individual
_ANALYSIS_PROMPT = """Eres parte del Council de Lilith. Analiza esta propuesta desde tu especialidad.

PROPUESTA: {title}

CONTEXTO:
{context}

PREGUNTA:
{question}

OPCIONES:
{options_text}

Evalúa cada opción con tu perspectiva especializada. Para cada una indica:
- Tu voto: STRONGLY_FAVOR, FAVOR, NEUTRAL, AGAINST, o STRONGLY_AGAINST
- Confianza (0.0–1.0)
- Razones concretas (máx 2 líneas)

Responde SOLO con JSON válido, sin texto adicional:
{{
  "evaluations": [
    {{
      "option_id": "A",
      "vote": "FAVOR",
      "confidence": 0.8,
      "reasoning": "razón breve"
    }}
  ]
}}"""


def _format_options(options: List[ProposalOption]) -> str:
    lines = []
    for opt in options:
        pros = "\n".join(f"  + {p}" for p in opt.pros) or "  (sin pros listados)"
        cons = "\n".join(f"  - {c}" for c in opt.cons) or "  (sin cons listados)"
        lines.append(
            f"Opción {opt.id}: {opt.title}\n{opt.description}\n\nPros:\n{pros}\n\nCons:\n{cons}"
        )
    return "\n\n---\n\n".join(lines)


def _parse_evaluations(raw: str) -> List[dict]:
    """Extrae lista de evaluaciones del JSON que devuelve el agente."""
    # Intentar parsear directamente
    try:
        data = json.loads(raw)
        return data.get("evaluations", [])
    except Exception:
        pass
    # Buscar bloque JSON con regex
    match = re.search(r'\{.*"evaluations".*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data.get("evaluations", [])
        except Exception:
            pass
    logger.warning("[Council] No se pudo parsear respuesta de agente: %s", raw[:200])
    return []


def _call_agent(agent, task: str, context: str = "") -> str:
    """Invoca execute() del agente manejando tanto sync como async."""
    try:
        if inspect.iscoroutinefunction(agent.execute):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(asyncio.run, agent.execute(task, context))
                        return future.result(timeout=90)
                else:
                    return loop.run_until_complete(agent.execute(task, context))
            except Exception:
                return asyncio.run(agent.execute(task, context))
        else:
            return agent.execute(task, context)
    except Exception as e:
        logger.warning(
            "[Council] Error llamando a agente %s: %s", getattr(agent, "name", "?"), e
        )
        return ""


class DeliberationEngine:
    """Motor que conduce sesiones de deliberación multi-agente."""

    def __init__(self):
        self._agents: Optional[Dict] = None

    def _load_agents(self) -> Dict:
        """Carga agentes lazy para evitar imports circulares al importar el módulo."""
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
                else:
                    logger.info(
                        "[Council] Agente %s no disponible (offline), omitido.", name
                    )
            except Exception as e:
                logger.warning("[Council] No se pudo instanciar %s: %s", name, e)

        self._agents = agents
        return agents

    def conduct_session(
        self,
        proposal: CouncilProposal,
        participants: Optional[List[str]] = None,
    ) -> CouncilSession:
        """
        Conduce una sesión completa de deliberación (síncrono).

        Fases:
          1. Análisis individual
          2. Debate (identificar desacuerdos, cada agente defiende posición)
          3. Votación final → consenso ponderado
        """
        agents = self._load_agents()

        if participants is None:
            participants = list(agents.keys())
        else:
            participants = [p for p in participants if p in agents]

        if not participants:
            logger.warning("[Council] Ningún agente disponible para la sesión.")

        session = CouncilSession(proposal=proposal, participants=participants)

        # ── FASE 1: Análisis individual ──────────────────────────────────────
        session.deliberation_log.append("=== FASE 1: Análisis Individual ===")
        logger.info("[Council] Fase 1: analizando con %d agentes.", len(participants))

        options_text = _format_options(proposal.options)

        for agent_name in participants:
            agent = agents[agent_name]
            prompt = _ANALYSIS_PROMPT.format(
                title=proposal.title,
                context=proposal.context,
                question=proposal.question,
                options_text=options_text,
            )
            raw = _call_agent(agent, prompt)
            evaluations = _parse_evaluations(raw)

            if not evaluations:
                # Fallback: NEUTRAL con confianza baja
                logger.warning(
                    "[Council] %s no devolvió evaluaciones válidas, usando NEUTRAL.",
                    agent_name,
                )
                for opt in proposal.options:
                    evaluations.append(
                        {
                            "option_id": opt.id,
                            "vote": "NEUTRAL",
                            "confidence": 0.3,
                            "reasoning": f"[{agent_name} no pudo evaluar]",
                        }
                    )

            for ev in evaluations:
                try:
                    vote = VoteOption[ev.get("vote", "NEUTRAL")]
                except KeyError:
                    vote = VoteOption.NEUTRAL
                opinion = AgentOpinion(
                    agent_name=agent_name,
                    option_id=str(ev.get("option_id", "?")),
                    vote=vote,
                    reasoning=str(ev.get("reasoning", ""))[:300],
                    confidence=float(ev.get("confidence", 0.5)),
                )
                session.opinions.append(opinion)
                session.deliberation_log.append(
                    f"  [{agent_name}] Opción {opinion.option_id}: "
                    f"{opinion.vote.name} (conf={opinion.confidence:.1f}) — {opinion.reasoning}"
                )

        # ── FASE 2: Debate ───────────────────────────────────────────────────
        session.deliberation_log.append("\n=== FASE 2: Debate ===")
        disagreements = self._find_disagreements(session.opinions)

        if not disagreements:
            session.deliberation_log.append(
                "  Consenso natural — no hay desacuerdos significativos."
            )
        else:
            for dis in disagreements:
                opt_id = dis["option_id"]
                session.deliberation_log.append(f"\n  Desacuerdo en Opción {opt_id}:")
                for agent_name in participants:
                    op = next(
                        (
                            o
                            for o in session.opinions
                            if o.agent_name == agent_name and o.option_id == opt_id
                        ),
                        None,
                    )
                    if op:
                        session.deliberation_log.append(
                            f"    {agent_name}: {op.vote.name} — {op.reasoning}"
                        )

        # ── FASE 3: Votación final ───────────────────────────────────────────
        session.deliberation_log.append("\n=== FASE 3: Votación Final ===")
        scores = self._calculate_scores(session.opinions, proposal)

        for opt_id, score in sorted(scores.items(), key=lambda x: -x[1]):
            session.deliberation_log.append(f"  Opción {opt_id}: score={score:.2f}")

        if scores:
            winner = max(scores.items(), key=lambda x: x[1])
            session.final_decision = winner[0]
            session.consensus_reached = True
            session.deliberation_log.append(
                f"\n  DECISIÓN: Opción {winner[0]} (score={winner[1]:.2f})"
            )
        else:
            session.final_decision = (
                proposal.options[0].id if proposal.options else None
            )
            session.consensus_reached = False
            session.deliberation_log.append(
                "\n  DECISIÓN: sin datos suficientes — primera opción por defecto."
            )

        from datetime import datetime

        session.ended_at = datetime.now()
        logger.info(
            "[Council] Sesión completada. Decisión: Opción %s", session.final_decision
        )
        return session

    def _find_disagreements(self, opinions: List[AgentOpinion]) -> List[Dict]:
        by_option: Dict[str, List[VoteOption]] = {}
        for op in opinions:
            by_option.setdefault(op.option_id, []).append(op.vote)

        result = []
        for opt_id, votes in by_option.items():
            has_favor = any(v.value > 0 for v in votes)
            has_against = any(v.value < 0 for v in votes)
            if has_favor and has_against:
                result.append({"option_id": opt_id})
        return result

    def _calculate_scores(
        self,
        opinions: List[AgentOpinion],
        proposal: CouncilProposal,
    ) -> Dict[str, float]:
        scores: Dict[str, float] = {opt.id: 0.0 for opt in proposal.options}

        for op in opinions:
            if op.option_id not in scores:
                continue
            base = op.vote.value * op.confidence
            # Peso de especialidad (por ahora uniforme; extensible por dominio)
            weight = AGENT_WEIGHTS.get(op.agent_name, {}).get("architecture", 1.0)
            scores[op.option_id] += base * weight

        return scores
