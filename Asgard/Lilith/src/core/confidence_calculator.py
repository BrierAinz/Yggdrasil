"""
Confidence Calculator - Cálculo de confianza en decisiones

Evalúa nivel de confianza basándose en:
- Calidad de memoria disponible
- Complejidad de la tarea
- Ambigüedad del mensaje
- Matched intent clarity
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Factores que afectan la confianza"""

    memory_quality: float  # 0.0-1.0
    task_complexity: float  # 0.0-1.0 (low complexity = high confidence)
    message_clarity: float  # 0.0-1.0
    intent_match_strength: float  # 0.0-1.0


class ConfidenceCalculator:
    """
    Calcula nivel de confianza en decisiones

    Confianza = promedio ponderado de:
    - memory_quality: 0.25
    - task_complexity: 0.30 (invertido)
    - message_clarity: 0.25
    - intent_match_strength: 0.20
    """

    # Pesos de cada factor
    WEIGHTS = {
        "memory_quality": 0.25,
        "task_complexity": 0.30,  # Se invierte: low complexity = high confidence
        "message_clarity": 0.25,
        "intent_match_strength": 0.20,
    }

    # Keywords de complejidad alta
    HIGH_COMPLEXITY_KEYWORDS = [
        "arquitectura",
        "diseña",
        "escalable",
        "distribuido",
        "complejo",
        "integra",
        "optimiza",
        "refactoriza",
        "migra",
        "implementa sistema",
        "completo",
    ]

    # Keywords de complejidad baja
    LOW_COMPLEXITY_KEYWORDS = [
        "lista",
        "muestra",
        "lee",
        "busca",
        "encuentra",
        "qué es",
        "explica",
        "define",
        "simple",
        "rápido",
    ]

    # Patterns de ambigüedad
    AMBIGUITY_PATTERNS = [
        r"\b(quizás|tal vez|no sé|creo que|supongo)\b",
        r"\b(o algo así|más o menos|aproximadamente)\b",
        r"\?.*\?",  # Múltiples preguntas
        r"\b(esto|eso|esa cosa|aquello)\b",  # Referencias vagas
    ]

    def calculate_confidence(
        self,
        message: str,
        memory_context: Optional[Dict[str, Any]] = None,
        matched_intent: Optional[str] = None,
        plan_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Calcular confianza de una decisión

        Args:
            message: Mensaje del usuario
            memory_context: Contexto de memoria disponible
            matched_intent: Intent que se matcheó (si hay)
            plan_steps: Pasos del plan generado (si hay)

        Returns:
            Dict con confidence (0.0-1.0), factors, y level (high/medium/low)
        """
        # Calcular factores individuales
        factors = ConfidenceFactors(
            memory_quality=self._assess_memory_quality(memory_context),
            task_complexity=self._assess_task_complexity(message, plan_steps),
            message_clarity=self._assess_message_clarity(message),
            intent_match_strength=self._assess_intent_match(matched_intent),
        )

        # Calcular confianza ponderada
        confidence = (
            self.WEIGHTS["memory_quality"] * factors.memory_quality
            + self.WEIGHTS["task_complexity"] * (1.0 - factors.task_complexity)
            + self.WEIGHTS["message_clarity"] * factors.message_clarity  # Invertir
            + self.WEIGHTS["intent_match_strength"] * factors.intent_match_strength
        )

        # Clamp a [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        # Determinar nivel
        if confidence >= 0.8:
            level = "high"
        elif confidence >= 0.5:
            level = "medium"
        else:
            level = "low"

        return {
            "confidence": round(confidence, 2),
            "level": level,
            "factors": {
                "memory_quality": round(factors.memory_quality, 2),
                "task_complexity": round(factors.task_complexity, 2),
                "message_clarity": round(factors.message_clarity, 2),
                "intent_match_strength": round(factors.intent_match_strength, 2),
            },
        }

    def _assess_memory_quality(self, memory_context: Optional[Dict[str, Any]]) -> float:
        """
        Evaluar calidad de la memoria disponible

        Args:
            memory_context: Contexto de memoria

        Returns:
            Score 0.0-1.0
        """
        if not memory_context:
            return 0.3  # Baja confianza sin memoria

        # Contar hechos relevantes
        facts = memory_context.get("facts", [])
        working_memory = memory_context.get("working_memory", [])

        total_items = len(facts) + len(working_memory)

        if total_items == 0:
            return 0.3
        elif total_items < 3:
            return 0.5
        elif total_items < 10:
            return 0.8
        else:
            return 1.0

    def _assess_task_complexity(
        self, message: str, plan_steps: Optional[List[Dict[str, Any]]]
    ) -> float:
        """
        Evaluar complejidad de la tarea

        Args:
            message: Mensaje del usuario
            plan_steps: Pasos del plan (si hay)

        Returns:
            Score 0.0-1.0 (0.0 = simple, 1.0 = muy complejo)
        """
        message_lower = message.lower()

        # Heurística 1: Keywords
        high_kw_count = sum(
            1 for kw in self.HIGH_COMPLEXITY_KEYWORDS if kw in message_lower
        )
        low_kw_count = sum(
            1 for kw in self.LOW_COMPLEXITY_KEYWORDS if kw in message_lower
        )

        # Heurística 2: Longitud del mensaje
        length_score = min(len(message) / 500, 1.0)  # Max a 500 chars

        # Heurística 3: Número de pasos en el plan
        steps_score = 0.0
        if plan_steps:
            num_steps = len(plan_steps)
            if num_steps <= 2:
                steps_score = 0.2
            elif num_steps <= 5:
                steps_score = 0.5
            else:
                steps_score = 0.8

        # Combinar
        keyword_score = 0.0
        if high_kw_count > low_kw_count:
            keyword_score = min(high_kw_count * 0.2, 1.0)
        elif low_kw_count > high_kw_count:
            keyword_score = max(0.0, 1.0 - low_kw_count * 0.2)
        else:
            keyword_score = 0.5

        # Promedio ponderado
        complexity = 0.4 * keyword_score + 0.3 * length_score + 0.3 * steps_score

        return complexity

    def _assess_message_clarity(self, message: str) -> float:
        """
        Evaluar claridad del mensaje

        Args:
            message: Mensaje del usuario

        Returns:
            Score 0.0-1.0 (1.0 = muy claro)
        """
        message_lower = message.lower()

        # Contar patterns de ambigüedad
        ambiguity_count = 0
        for pattern in self.AMBIGUITY_PATTERNS:
            ambiguity_count += len(re.findall(pattern, message_lower))

        # Heurística de longitud (muy corto o muy largo = menos claro)
        length = len(message)
        if length < 10:
            length_score = 0.3
        elif length < 30:
            length_score = 0.6
        elif length < 200:
            length_score = 1.0
        else:
            length_score = 0.8

        # Combinar
        if ambiguity_count == 0:
            ambiguity_score = 1.0
        elif ambiguity_count == 1:
            ambiguity_score = 0.7
        elif ambiguity_count == 2:
            ambiguity_score = 0.4
        else:
            ambiguity_score = 0.2

        clarity = (0.6 * ambiguity_score) + (0.4 * length_score)

        return clarity

    def _assess_intent_match(self, matched_intent: Optional[str]) -> float:
        """
        Evaluar fuerza del match de intent

        Args:
            matched_intent: Intent que se matcheó

        Returns:
            Score 0.0-1.0
        """
        if not matched_intent:
            return 0.4  # No match = confianza media-baja

        # Intents fuertes (muy específicos)
        strong_intents = [
            "read_file",
            "list_directory",
            "pc_list",
            "pc_exec",
            "delegate_eva",
            "delegate_odin",
            "delegate_adan",
        ]

        # Intents débiles (más ambiguos)
        weak_intents = ["fallback", "charla", "delegate_lucifer"]

        if matched_intent in strong_intents:
            return 0.9
        elif matched_intent in weak_intents:
            return 0.5
        else:
            return 0.7  # Default


# Singleton global
_confidence_calculator: Optional[ConfidenceCalculator] = None


def get_confidence_calculator() -> ConfidenceCalculator:
    """Obtener instancia singleton del calculator"""
    global _confidence_calculator
    if _confidence_calculator is None:
        _confidence_calculator = ConfidenceCalculator()
    return _confidence_calculator


def calculate_confidence(
    message: str,
    memory_context: Optional[Dict[str, Any]] = None,
    matched_intent: Optional[str] = None,
    plan_steps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para calcular confianza

    Returns:
        Dict con confidence, level, factors
    """
    calculator = get_confidence_calculator()
    return calculator.calculate_confidence(
        message=message,
        memory_context=memory_context,
        matched_intent=matched_intent,
        plan_steps=plan_steps,
    )
