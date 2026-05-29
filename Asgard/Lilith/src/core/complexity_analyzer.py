"""
Complexity Analyzer - D.12: Task complexity estimation with confidence scoring.

Features:
- Heuristic-based complexity estimation
- Confidence scoring
- Context-aware analysis
- Token estimation
- Tool complexity scoring
"""
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .json_safe import safe_load

logger = logging.getLogger("lilith.complexity")


class ComplexityLevel(Enum):
    """Niveles de complejidad de tareas."""

    TRIVIAL = "trivial"  # Haiku/GPT-4o-mini
    SIMPLE = "simple"  # Sonnet
    MODERATE = "moderate"  # Sonnet
    COMPLEX = "complex"  # Opus
    EXPERT = "expert"  # Opus

    @property
    def estimated_cost_factor(self) -> float:
        """Factor de costo relativo vs Haiku."""
        return {
            ComplexityLevel.TRIVIAL: 1.0,
            ComplexityLevel.SIMPLE: 12.0,
            ComplexityLevel.MODERATE: 12.0,
            ComplexityLevel.COMPLEX: 60.0,
            ComplexityLevel.EXPERT: 60.0,
        }[self]


@dataclass
class ComplexityResult:
    """Resultado del análisis de complejidad."""

    level: ComplexityLevel
    confidence: float
    estimated_tokens: int
    factors: Dict[str, Any] = field(default_factory=dict)
    reasoning: List[str] = field(default_factory=list)


@dataclass
class ComplexityFeatures:
    """Features extraídos (para compatibilidad con tests)."""

    input_length: int = 0
    word_count: int = 0
    has_trivial_keywords: bool = False
    has_complex_keywords: bool = False
    has_expert_keywords: bool = False
    tool_complexity_score: int = 0
    context_size: int = 0
    question_marks: int = 0
    code_blocks: int = 0
    sentence_count: int = 0


class ComplexityAnalyzer:
    """
    Analizador de complejidad de tareas LLM.
    Usa heurísticas y ML opcional para estimar complejidad.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()

        # Keywords heurísticas
        self._trivial_keywords = set(
            self.config.get(
                "trivial_keywords",
                [
                    "sí",
                    "no",
                    "ok",
                    "bien",
                    "gracias",
                    "hola",
                    "adiós",
                    "confirm",
                    "yes",
                    "no",
                    "ok",
                    "thanks",
                    "hello",
                    "bye",
                    "confirma",
                    "confirmas",
                    "vale",
                    "sí/no",
                    "yes/no",
                ],
            )
        )

        self._simple_keywords = set(
            self.config.get(
                "simple_keywords",
                [
                    "explica",
                    "qué es",
                    "cómo",
                    "define",
                    "cuándo",
                    "dónde",
                    "explain",
                    "what is",
                    "how to",
                    "define",
                    "when",
                    "where",
                    "read",
                    "list",
                    "get",
                    "search",
                ],
            )
        )

        self._complex_keywords = set(
            self.config.get(
                "complex_keywords",
                [
                    "diseña",
                    "arquitectura",
                    "evalúa",
                    "compara",
                    "analiza",
                    "optimiza",
                    "refactoriza",
                    "debug",
                    "implementa",
                    "design",
                    "architecture",
                    "evaluate",
                    "compare",
                    "analyze",
                    "optimize",
                    "refactor",
                    "debug",
                    "implement",
                    "trade-offs",
                    "tradeoffs",
                    "mejora",
                    "improve",
                ],
            )
        )

        self._expert_keywords = set(
            self.config.get(
                "expert_keywords",
                [
                    "depura",
                    "troubleshoot",
                    "root cause",
                    "performance tuning",
                    "distributed system",
                    "microservices",
                    "kubernetes",
                    "scale",
                    "seguridad",
                    "security",
                    "vulnerabilidad",
                    "vulnerability",
                    "exploit",
                    "crypto",
                    "machine learning",
                    "ml model",
                    "deep debugging",
                    "debugging profundo",
                    "critical",
                ],
            )
        )

        # Tools que requieren nivel experto
        self._expert_tools = set(
            self.config.get(
                "expert_tools",
                [
                    "delegate_odin",
                    "delegate_adan",
                    "execute_code",
                    "file_system_write",
                    "database_migration",
                    "security_audit",
                ],
            )
        )

        # Tools complejas
        self._complex_tools = set(
            self.config.get(
                "complex_tools",
                [
                    "delegate_eva",
                    "delegate_lucifer",
                    "multi_step_plan",
                    "code_generation",
                    "refactor",
                ],
            )
        )

        # Thresholds
        thresholds = self.config.get("thresholds", {})
        self._max_trivial_length = thresholds.get("max_input_length_trivial", 100)
        self._min_complex_length = thresholds.get("min_input_length_complex", 400)
        self._min_expert_length = thresholds.get("min_input_length_expert", 1000)

        logger.info("[ComplexityAnalyzer] Inicializado. Config: %s", len(self.config))

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde model_selector.json."""
        config_path = self.base_path / "Config" / "model_selector.json"

        try:
            full_config = safe_load(config_path, default={})
            return full_config.get("complexity_rules", {})
        except Exception as e:
            logger.error("[ComplexityAnalyzer] Error cargando config: %s", e)
            return {}

    def estimate(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> ComplexityResult:
        """
        Estima complejidad de una tarea.

        Args:
            task: Texto de la tarea
            context: Contexto adicional (tools, historial, etc.)

        Returns:
            ComplexityResult con nivel y confianza
        """
        context = context or {}
        factors: Dict[str, Any] = {}
        reasoning: List[str] = []

        # 1. Análisis de longitud
        length_score = self._analyze_length(task)
        factors["length"] = length_score
        if length_score["is_trivial"]:
            reasoning.append(f"Input muy corto ({length_score['length']} chars)")
        elif length_score["is_expert"]:
            reasoning.append(f"Input muy largo ({length_score['length']} chars)")
        elif length_score["is_complex"]:
            reasoning.append(f"Input largo ({length_score['length']} chars)")

        # 2. Análisis de keywords
        keyword_score = self._analyze_keywords(task)
        factors["keywords"] = keyword_score
        if keyword_score["max_level"]:
            reasoning.append(f"Keywords indican nivel: {keyword_score['max_level']}")

        # 3. Análisis de tools
        tools_score = self._analyze_tools(context.get("tools", []))
        factors["tools"] = tools_score
        if tools_score["is_expert"]:
            reasoning.append("Tools requieren nivel experto")
        elif tools_score["is_complex"]:
            reasoning.append("Tools indican tarea compleja")

        # 4. Análisis de bloques de código
        code_score = self._analyze_code_blocks(task)
        factors["code"] = code_score
        if code_score["is_complex"]:
            reasoning.append(f"Múltiples bloques de código ({code_score['count']})")

        # 5. Análisis de historial
        history_score = self._analyze_history(context.get("history", []))
        factors["history"] = history_score
        if history_score["is_complex"]:
            reasoning.append(
                f"Historial largo ({history_score['message_count']} mensajes)"
            )

        # Calcular nivel final
        level, confidence = self._compute_level(factors)

        # Estimar tokens
        estimated_tokens = self._estimate_tokens(task, level)

        return ComplexityResult(
            level=level,
            confidence=confidence,
            estimated_tokens=estimated_tokens,
            factors=factors,
            reasoning=reasoning or ["Default analysis"],
        )

    def estimate_with_features(
        self, task: str, context: Optional[Dict] = None
    ) -> tuple[ComplexityResult, ComplexityFeatures]:
        """
        Estima complejidad y retorna también los features extraídos.

        Returns:
            Tuple de (ComplexityResult, ComplexityFeatures)
        """
        result = self.estimate(task, context)
        features = self._extract_features(task, context)
        return result, features

    def _analyze_length(self, task: str) -> Dict[str, Any]:
        """Analiza longitud del input."""
        length = len(task)
        return {
            "length": length,
            "is_trivial": length < self._max_trivial_length,
            "is_complex": length > self._min_complex_length,
            "is_expert": length > self._min_expert_length,
            "score": -2
            if length < self._max_trivial_length
            else 4
            if length > self._min_expert_length
            else 3
            if length > self._min_complex_length
            else 0,
        }

    def _analyze_keywords(self, task: str) -> Dict[str, Any]:
        """Analiza keywords presentes."""
        task_lower = task.lower()

        trivial = sum(1 for kw in self._trivial_keywords if kw in task_lower)
        simple = sum(1 for kw in self._simple_keywords if kw in task_lower)
        complex_kw = sum(1 for kw in self._complex_keywords if kw in task_lower)
        expert = sum(1 for kw in self._expert_keywords if kw in task_lower)

        # Determinar nivel máximo
        max_level = None
        if expert > 0:
            max_level = "EXPERT"
        elif complex_kw > 0:
            max_level = "COMPLEX"
        elif simple > 0:
            max_level = "SIMPLE"
        elif trivial > 0:
            max_level = "TRIVIAL"

        score = (-2 * trivial) + simple + (4 * complex_kw) + (5 * expert)

        return {
            "trivial": trivial,
            "simple": simple,
            "complex": complex_kw,
            "expert": expert,
            "max_level": max_level,
            "score": score,
        }

    def _analyze_tools(self, tools: List[str]) -> Dict[str, Any]:
        """Analiza tools solicitados."""
        expert_tools = [t for t in tools if t in self._expert_tools]
        complex_tools = [t for t in tools if t in self._complex_tools]
        return {
            "requested": tools,
            "expert_tools": expert_tools,
            "complex_tools": complex_tools,
            "is_expert": len(expert_tools) > 0,
            "is_complex": len(complex_tools) > 0,
            "score": 5 if expert_tools else (3 if complex_tools else 0),
        }

    def _analyze_code_blocks(self, task: str) -> Dict[str, Any]:
        """Analiza bloques de código."""
        count = task.count("```") // 2
        return {
            "count": count,
            "is_complex": count >= 2,
            "score": 2 if count >= 2 else (1 if count >= 1 else 0),
        }

    def _analyze_history(self, history: List[Dict]) -> Dict[str, Any]:
        """Analiza historial de conversación."""
        count = len(history)
        return {
            "message_count": count,
            "is_complex": count > 10,
            "score": 1 if count > 10 else 0,
        }

    def _compute_level(self, factors: Dict[str, Any]) -> tuple[ComplexityLevel, float]:
        """Computa nivel final basado en factores."""
        # Sumar scores
        total_score = (
            factors["length"].get("score", 0)
            + factors["keywords"].get("score", 0)
            + factors["tools"].get("score", 0)
            + factors.get("code", {}).get("score", 0)
            + factors["history"].get("score", 0)
        )

        # Mapear a nivel
        if total_score <= -2:
            level = ComplexityLevel.TRIVIAL
        elif total_score <= 0:
            level = ComplexityLevel.SIMPLE
        elif total_score <= 2:
            level = ComplexityLevel.MODERATE
        elif total_score <= 4:
            level = ComplexityLevel.COMPLEX
        else:
            level = ComplexityLevel.EXPERT

        # Calcular confianza basada en consistencia de factores
        confidence = self._calculate_confidence(factors, level)

        return level, confidence

    def _calculate_confidence(
        self, factors: Dict[str, Any], level: ComplexityLevel
    ) -> float:
        """Calcula confianza del análisis."""
        # Más factores alineados = mayor confianza
        confidence = 0.5  # Base

        # Length alignment
        if level == ComplexityLevel.TRIVIAL and factors["length"]["is_trivial"]:
            confidence += 0.2
        elif level == ComplexityLevel.EXPERT and factors["length"].get("is_expert"):
            confidence += 0.2
        elif (
            level in [ComplexityLevel.COMPLEX, ComplexityLevel.EXPERT]
            and factors["length"]["is_complex"]
        ):
            confidence += 0.15

        # Keywords alignment
        kw_max = factors["keywords"].get("max_level")
        if kw_max == level.value.upper():
            confidence += 0.2

        # Tools alignment
        if level == ComplexityLevel.EXPERT and factors["tools"]["is_expert"]:
            confidence += 0.15
        elif level == ComplexityLevel.COMPLEX and factors["tools"].get("is_complex"):
            confidence += 0.1

        return min(confidence, 0.95)

    def _estimate_tokens(self, task: str, level: ComplexityLevel) -> int:
        """Estima tokens necesarios para el response."""
        # Token estimado aproximado: ~4 chars por token
        input_tokens = len(task) // 4

        # Output tokens estimados por nivel
        output_tokens = {
            ComplexityLevel.TRIVIAL: 50,
            ComplexityLevel.SIMPLE: 200,
            ComplexityLevel.MODERATE: 500,
            ComplexityLevel.COMPLEX: 1500,
            ComplexityLevel.EXPERT: 2500,
        }[level]

        return input_tokens + output_tokens

    def _extract_features(
        self, task: str, context: Optional[Dict] = None
    ) -> ComplexityFeatures:
        """Extrae features de una tarea para compatibilidad con tests."""
        import re

        task_lower = task.lower()
        words = task.split()
        sentences = re.split(r"[.!?]+", task)

        # Keywords check
        has_trivial = any(kw in task_lower for kw in self._trivial_keywords)
        has_complex = any(kw in task_lower for kw in self._complex_keywords)
        has_expert = any(kw in task_lower for kw in self._expert_keywords)

        # Tools
        tools = context.get("tools", []) if context else []
        tool_score = 0
        if any(t in self._expert_tools for t in tools):
            tool_score = 4
        elif any(t in self._complex_tools for t in tools):
            tool_score = 2

        return ComplexityFeatures(
            input_length=len(task),
            word_count=len(words),
            has_trivial_keywords=has_trivial,
            has_complex_keywords=has_complex,
            has_expert_keywords=has_expert,
            tool_complexity_score=tool_score,
            context_size=len(str(context)) if context else 0,
            question_marks=task.count("?"),
            code_blocks=task.count("```") // 2,
            sentence_count=len([s for s in sentences if s.strip()]),
        )


# Singleton
_analyzer_instance: Optional[ComplexityAnalyzer] = None


def get_complexity_analyzer(base_path: Optional[Path] = None) -> ComplexityAnalyzer:
    """Obtiene instancia singleton del ComplexityAnalyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ComplexityAnalyzer(base_path)
    return _analyzer_instance


def estimate_complexity(task: str, context: Optional[Dict] = None) -> ComplexityResult:
    """Función conveniencia para estimar complejidad."""
    analyzer = get_complexity_analyzer()
    return analyzer.estimate(task, context)


__all__ = [
    "ComplexityLevel",
    "ComplexityResult",
    "ComplexityFeatures",
    "ComplexityAnalyzer",
    "get_complexity_analyzer",
    "estimate_complexity",
]
