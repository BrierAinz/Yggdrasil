"""
ReviewChain — Revisión inter-agente de respuestas.
Permite que un agente revisor evalúe la salida de otro antes de retornarla.
Integración ligera: solo activa si el tool es delegate_adan o delegate_eva
y la respuesta supera el umbral de longitud (para no desperdiciar tokens en snippets triviales).
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("lilith.review_chain")

# Longitud mínima de respuesta para activar revisión (caracteres)
_MIN_REVIEW_LENGTH = 300

# Tools que admiten revisión por Albedo
_REVIEWABLE_TOOLS = {"delegate_adan", "delegate_eva", "delegate_odin"}


class ReviewChain:
    """
    Pide a Albedo (centinela) que evalúe la respuesta de un agente.
    Si la puntuación es baja (< min_score), añade una nota de calidad al resultado.
    No bloquea la respuesta: devuelve la original + nota si hay problemas.
    """

    def __init__(self, base_path: Path, min_score: int = 6, enabled: bool = True):
        self.base_path = Path(base_path)
        self.min_score = min_score
        self.enabled = enabled

    def _should_review(self, tool_name: str, response: str) -> bool:
        if not self.enabled:
            return False
        if tool_name not in _REVIEWABLE_TOOLS:
            return False
        return len((response or "").strip()) >= _MIN_REVIEW_LENGTH

    def review_sync(self, tool_name: str, task: str, response: str) -> Optional[dict]:
        """
        Realiza la revisión de forma síncrona usando AlbedoAgent.sentinel_review_sync().
        Retorna el resultado de revisión o None si no aplica/falla.
        """
        if not self._should_review(tool_name, response):
            return None
        try:
            from src.core.agents.panteon.albedo import AlbedoAgent

            albedo = AlbedoAgent()
            if not albedo.enabled:
                return None
            result = albedo.sentinel_review_sync(task[:500], response[:1000], tool_name)
            return result
        except Exception as e:
            logger.debug("review_chain: albedo error: %s", e)
            return None

    def annotate_if_low_quality(self, tool_name: str, task: str, response: str) -> str:
        """
        Revisa la respuesta y, si la calidad es baja, añade una nota al final.
        Retorna la respuesta (posiblemente con nota) o la original si no hay revisión.
        """
        review = self.review_sync(tool_name, task, response)
        if not review:
            return response
        score = int(review.get("score") or 10)
        notes = (review.get("notes") or "").strip()
        if score < self.min_score and notes:
            logger.info(
                "review_chain: %s score=%d/10 — %s", tool_name, score, notes[:80]
            )
            annotation = (
                f"\n\n---\n*[Nota de calidad — score {score}/10]: {notes[:200]}*"
            )
            return response + annotation
        return response


# ─── Singleton ────────────────────────────────────────────────────────────────

_review_chains: dict = {}


def get_review_chain(base_path: Path) -> ReviewChain:
    key = str(base_path)
    if key not in _review_chains:
        _review_chains[key] = ReviewChain(base_path)
    return _review_chains[key]
