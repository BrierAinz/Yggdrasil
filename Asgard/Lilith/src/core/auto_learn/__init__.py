"""
Fase 4.3 — Modo auto-aprendizaje: job periódico, clasificación en dos fases, cuaderno y confirmación por Discord.
"""
from .classifier import classify_items, heuristic_important
from .job import run_auto_learn_job

__all__ = ["run_auto_learn_job", "classify_items", "heuristic_important"]
