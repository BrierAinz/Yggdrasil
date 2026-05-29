"""
Persistencia de sesiones del Council.

Guarda:
  - Sesión completa como JSON en Vanaheim/Council/sessions/
  - ADR (Architecture Decision Record) como Markdown en Vanaheim/Council/decisions/
  - Registro de votos en JSONL en Vanaheim/Council/voting_records/
"""
import json
import logging
from pathlib import Path
from typing import List

from .models import CouncilSession

logger = logging.getLogger("lilith.council")

# Raíz de Vanaheim relativa al módulo (sube 6 niveles desde core/council/)
# core/council/ → core/ → Backend/ → Core/ → Lilith/ → Asgard/ → Yggdrasil/
_MODULE_DIR = Path(__file__).resolve().parent
_YGGDRASIL_ROOT = _MODULE_DIR.parents[5]  # D:/Proyectos/Yggdrasil
_COUNCIL_ROOT = _YGGDRASIL_ROOT / "Vanaheim" / "Council"


class SessionRecorder:
    """Guarda sesiones, ADRs y votos del Council en Vanaheim."""

    def __init__(self, council_root: Path = _COUNCIL_ROOT):
        self.sessions_dir = council_root / "sessions"
        self.decisions_dir = council_root / "decisions"
        self.votes_file = council_root / "voting_records" / "votes.jsonl"

        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.votes_file.parent.mkdir(parents=True, exist_ok=True)

    # ── Sesión JSON ──────────────────────────────────────────────────────────

    def save_session(self, session: CouncilSession) -> Path:
        """Guarda la sesión completa como JSON."""
        ts = session.started_at.strftime("%Y-%m-%d_%H%M%S_%f")
        filename = f"{ts}_{session.proposal.id}.json"
        filepath = self.sessions_dir / filename

        data = {
            "proposal": {
                "id": session.proposal.id,
                "title": session.proposal.title,
                "context": session.proposal.context,
                "question": session.proposal.question,
                "options": [
                    {
                        "id": o.id,
                        "title": o.title,
                        "description": o.description,
                        "pros": o.pros,
                        "cons": o.cons,
                        "implications": o.implications,
                    }
                    for o in session.proposal.options
                ],
            },
            "participants": session.participants,
            "opinions": [
                {
                    "agent": op.agent_name,
                    "option": op.option_id,
                    "vote": op.vote.name,
                    "reasoning": op.reasoning,
                    "confidence": op.confidence,
                }
                for op in session.opinions
            ],
            "deliberation_log": session.deliberation_log,
            "final_decision": session.final_decision,
            "consensus_reached": session.consensus_reached,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        }

        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("[Council] Sesión guardada: %s", filepath.name)
        return filepath

    # ── ADR Markdown ─────────────────────────────────────────────────────────

    def next_adr_id(self) -> str:
        """Calcula el siguiente ID de ADR (ej. '002')."""
        existing = list(self.decisions_dir.glob("ADR-*.md"))
        return f"{len(existing) + 1:03d}"

    def save_decision_record(self, session: CouncilSession, adr_id: str = None) -> Path:
        """Genera ADR en Markdown y lo guarda."""
        if adr_id is None:
            adr_id = self.next_adr_id()

        filename = f"ADR-{adr_id}_{session.proposal.id}.md"
        filepath = self.decisions_dir / filename

        # Votos agrupados por opción
        votes_by_option = {}
        for op in session.opinions:
            votes_by_option.setdefault(op.option_id, []).append(op)

        date_str = session.started_at.strftime("%Y-%m-%d")
        participants_str = ", ".join(session.participants)

        md = f"# ADR-{adr_id}: {session.proposal.title}\n\n"
        md += f"**Fecha**: {date_str}  \n"
        md += f"**Status**: Aceptada  \n"
        md += f"**Participantes**: {participants_str}\n\n"
        md += f"## Contexto\n{session.proposal.context}\n\n"
        md += f"## Pregunta\n{session.proposal.question}\n\n"
        md += "## Opciones Evaluadas\n"

        for option in session.proposal.options:
            votes = votes_by_option.get(option.id, [])
            favor = sum(1 for v in votes if v.vote.value > 0)
            against = sum(1 for v in votes if v.vote.value < 0)
            neutral = len(votes) - favor - against

            md += f"\n### Opción {option.id}: {option.title}\n"
            md += f"{option.description}\n\n"

            if option.pros:
                md += "**Pros**:\n" + "\n".join(f"- {p}" for p in option.pros) + "\n\n"
            if option.cons:
                md += "**Cons**:\n" + "\n".join(f"- {c}" for c in option.cons) + "\n\n"

            md += (
                f"**Votos**: {favor} a favor, {against} en contra, {neutral} neutral\n"
            )

            # Detalle de votos por agente
            vote_details = []
            for v in votes:
                emoji = {
                    "STRONGLY_FAVOR": "✅✅",
                    "FAVOR": "✅",
                    "NEUTRAL": "➖",
                    "AGAINST": "❌",
                    "STRONGLY_AGAINST": "❌❌",
                }.get(v.vote.name, "?")
                vote_details.append(f"  - {v.agent_name} {emoji}: {v.reasoning}")
            if vote_details:
                md += "\n".join(vote_details) + "\n"

        md += "\n## Deliberación\n"
        md += "\n".join(session.deliberation_log) + "\n\n"

        md += "## Decisión\n"
        winning_option = next(
            (o for o in session.proposal.options if o.id == session.final_decision),
            None,
        )
        md += f"**Consenso**: Opción {session.final_decision}"
        if winning_option:
            md += f" — {winning_option.title}"
        md += "\n\n"

        # Síntesis de razones ganadoras
        winning_votes = [
            op
            for op in session.opinions
            if op.option_id == session.final_decision and op.vote.value > 0
        ]
        if winning_votes:
            md += "**Razones principales**:\n"
            for wv in winning_votes[:3]:
                md += f"- [{wv.agent_name}] {wv.reasoning}\n"
            md += "\n"

        if winning_option and winning_option.implications:
            md += "## Consecuencias\n"
            md += "\n".join(f"- {i}" for i in winning_option.implications) + "\n"

        filepath.write_text(md, encoding="utf-8")
        logger.info("[Council] ADR-%s guardado: %s", adr_id, filepath.name)
        return filepath

    # ── Votos JSONL ──────────────────────────────────────────────────────────

    def log_votes(self, session: CouncilSession) -> None:
        """Append registro de votos al JSONL histórico."""
        record = {
            "timestamp": session.started_at.isoformat(),
            "proposal_id": session.proposal.id,
            "proposal_title": session.proposal.title,
            "participants": session.participants,
            "votes": [
                {
                    "agent": op.agent_name,
                    "option": op.option_id,
                    "vote": op.vote.name,
                    "confidence": op.confidence,
                }
                for op in session.opinions
            ],
            "decision": session.final_decision,
            "consensus_reached": session.consensus_reached,
        }
        with open(self.votes_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug("[Council] Votos registrados en %s", self.votes_file.name)

    # ── Consultas ─────────────────────────────────────────────────────────────

    def list_decisions(self) -> List[str]:
        """Lista los ADRs existentes."""
        return [f.name for f in sorted(self.decisions_dir.glob("ADR-*.md"))]

    def get_session_count(self) -> int:
        return len(list(self.sessions_dir.glob("*.json")))
