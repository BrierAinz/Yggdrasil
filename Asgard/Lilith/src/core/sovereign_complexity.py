"""
Sovereign Complexity Analyzer - Extensión para modo Soberano de Lilith.

Features:
- Análisis de complejidad para decisión DELEGATE vs ORCHESTRATE
- Umbrales configurables
- Detección de dependencias y multi-agente
- Scoring soberano (0-100)
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .complexity_analyzer import ComplexityAnalyzer, ComplexityLevel, ComplexityResult
from .json_safe import safe_load

logger = logging.getLogger("lilith.sovereign")


class ExecutionMode(Enum):
    """Modos de ejecución soberana."""

    DELEGATE = "delegate"  # Forwarding simple a Vanaheim
    ORCHESTRATE = "orchestrate"  # DAG completo con Lilith
    AUTO = "auto"  # Decisión automática


@dataclass
class SovereignComplexityResult:
    """Resultado del análisis de complejidad soberana."""

    level: ComplexityLevel
    sovereign_score: int  # 0-100
    should_delegate: bool
    should_orchestrate: bool
    confidence: float
    factors: Dict[str, Any] = field(default_factory=dict)
    recommended_mode: ExecutionMode = ExecutionMode.AUTO
    reasoning: List[str] = field(default_factory=list)


class SovereignComplexityAnalyzer:
    """
    Analizador de complejidad para modo Soberano.
    Extiende ComplexityAnalyzer con criterios de decisión DELEGATE vs ORCHESTRATE.
    """

    # Puntuación por nivel base
    LEVEL_SCORES = {
        ComplexityLevel.TRIVIAL: 10,
        ComplexityLevel.SIMPLE: 30,
        ComplexityLevel.MODERATE: 50,
        ComplexityLevel.COMPLEX: 75,
        ComplexityLevel.EXPERT: 90,
    }

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()
        self.base_analyzer = ComplexityAnalyzer(base_path)

        # Thresholds configurables
        thresholds = self.config.get("thresholds", {})
        self.delegate_max_score = thresholds.get("delegate_max_score", 40)
        self.orchestrate_min_score = thresholds.get("orchestrate_min_score", 60)
        self.confidence_min = thresholds.get("confidence_min", 0.7)

        # Scoring weights
        weights = self.config.get("scoring", {}).get("weights", {})
        self.weights = {
            "complexity_level": weights.get("complexity_level", 30),
            "estimated_steps": weights.get("estimated_steps", 25),
            "has_dependencies": weights.get("has_dependencies", 20),
            "multi_agent_required": weights.get("multi_agent_required", 15),
            "context_size": weights.get("context_size", 10),
        }

        logger.info(
            "[SovereignComplexity] Inicializado. Delegate: <%d, Orchestrate: >%d",
            self.delegate_max_score,
            self.orchestrate_min_score,
        )

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"

        try:
            config = safe_load(config_path, default={})
            return config
        except Exception as e:
            logger.error("[SovereignComplexity] Error cargando config: %s", e)
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto."""
        return {
            "enabled": True,
            "thresholds": {
                "delegate_max_score": 40,
                "orchestrate_min_score": 60,
                "confidence_min": 0.7,
            },
            "scoring": {
                "weights": {
                    "complexity_level": 30,
                    "estimated_steps": 25,
                    "has_dependencies": 20,
                    "multi_agent_required": 15,
                    "context_size": 10,
                }
            },
        }

    def analyze_for_sovereign(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> SovereignComplexityResult:
        """
        Analiza complejidad para decisión soberana DELEGATE vs ORCHESTRATE.

        Args:
            task: Texto de la tarea
            context: Contexto adicional (tools, historial, etc.)

        Returns:
            SovereignComplexityResult con decisión de modo
        """
        context = context or {}

        # 1. Análisis base
        base_result = self.base_analyzer.estimate(task, context)

        # 2. Factores adicionales para modo soberano
        factors = self._analyze_sovereign_factors(task, context, base_result)

        # 3. Calcular score soberano (0-100)
        sovereign_score = self._calculate_sovereign_score(base_result.level, factors)

        # 4. Decidir modo
        should_delegate, should_orchestrate, reasoning = self._decide_mode(
            sovereign_score, base_result.confidence, factors
        )

        # 5. Determinar modo recomendado
        if should_delegate:
            recommended_mode = ExecutionMode.DELEGATE
        elif should_orchestrate:
            recommended_mode = ExecutionMode.ORCHESTRATE
        else:
            recommended_mode = ExecutionMode.AUTO

        return SovereignComplexityResult(
            level=base_result.level,
            sovereign_score=sovereign_score,
            should_delegate=should_delegate,
            should_orchestrate=should_orchestrate,
            confidence=base_result.confidence,
            factors=factors,
            recommended_mode=recommended_mode,
            reasoning=reasoning,
        )

    def _analyze_sovereign_factors(
        self, task: str, context: Dict, base_result: ComplexityResult
    ) -> Dict[str, Any]:
        """Analiza factores adicionales para decisión soberana."""
        factors = dict(base_result.factors)

        # Detectar dependencias explícitas
        factors["has_dependencies"] = self._detect_dependencies(task)

        # Detectar necesidad de múltiples agentes
        factors["requires_multiple_agents"] = self._detect_multi_agent_need(task)

        # Detectar estructura de tarea
        factors["is_structured_task"] = self._detect_structure(task)

        # Estimar pasos necesarios
        factors["estimated_steps"] = self._estimate_steps(task, base_result.level)

        # Tamaño del contexto
        factors["context_size"] = len(str(context))

        return factors

    def _detect_dependencies(self, task: str) -> bool:
        """Detecta si la tarea tiene dependencias implícitas."""
        dependency_indicators = [
            "después de",
            "luego de",
            "una vez que",
            "seguido de",
            "after",
            "once",
            "then",
            "followed by",
            "depende de",
            "requires",
            "prerequisite",
            "primero",
            "first",
            "antes de",
            "before",
        ]
        task_lower = task.lower()
        return any(indicator in task_lower for indicator in dependency_indicators)

    def _detect_multi_agent_need(self, task: str) -> bool:
        """Detecta si la tarea requiere múltiples agentes."""
        multi_indicators = [
            "investiga y",
            "busca y",
            "analiza y",
            "research and",
            "search and",
            "analyze and",
            "múltiples",
            "varios",
            "diferentes",
            "multiple",
            "various",
            "different",
            "código y documentación",
            "code and docs",
            "diseña e implementa",
            "design and implement",
        ]
        task_lower = task.lower()
        return any(indicator in task_lower for indicator in multi_indicators)

    def _detect_structure(self, task: str) -> bool:
        """Detecta si la tarea tiene estructura clara de pasos."""
        structure_indicators = [
            "paso",
            "step",
            "fase",
            "phase",
            "1.",
            "2.",
            "3.",
            "primero",
            "segundo",
            "tercero",
            "first",
            "second",
            "third",
        ]
        task_lower = task.lower()
        return any(indicator in task_lower for indicator in structure_indicators)

    def _estimate_steps(self, task: str, level: ComplexityLevel) -> int:
        """Estima número de pasos necesarios."""
        base_steps = {
            ComplexityLevel.TRIVIAL: 1,
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MODERATE: 2,
            ComplexityLevel.COMPLEX: 4,
            ComplexityLevel.EXPERT: 6,
        }

        steps = base_steps.get(level, 1)

        # Ajustar por indicadores de estructura
        if self._detect_structure(task):
            steps += 1
        if self._detect_dependencies(task):
            steps += 1

        return min(steps, 10)

    def _calculate_sovereign_score(
        self, level: ComplexityLevel, factors: Dict[str, Any]
    ) -> int:
        """Calcula score soberano (0-100) basado en factores."""
        # Score base por nivel
        base_score = self.LEVEL_SCORES.get(level, 50)

        # Aplicar pesos adicionales
        score = base_score

        # Ajustar por pasos estimados
        steps = factors.get("estimated_steps", 1)
        if steps > 1:
            score += min((steps - 1) * 5, self.weights["estimated_steps"])

        # Ajustar por dependencias
        if factors.get("has_dependencies", False):
            score += self.weights["has_dependencies"]

        # Ajustar por múltiples agentes
        if factors.get("requires_multiple_agents", False):
            score += self.weights["multi_agent_required"]

        # Ajustar por contexto grande
        context_size = factors.get("context_size", 0)
        if context_size > 5000:
            score += self.weights["context_size"]

        return max(0, min(100, score))

    def _decide_mode(
        self, score: int, confidence: float, factors: Dict[str, Any]
    ) -> tuple[bool, bool, List[str]]:
        """Decide modo basado en score y confianza."""
        reasoning = []

        # Zona clara de DELEGATE
        if score <= self.delegate_max_score:
            reasoning.append(
                f"Score {score} <= {self.delegate_max_score} (umbral DELEGATE)"
            )
            return True, False, reasoning

        # Zona clara de ORCHESTRATE
        if score >= self.orchestrate_min_score:
            reasoning.append(
                f"Score {score} >= {self.orchestrate_min_score} (umbral ORCHESTRATE)"
            )
            return False, True, reasoning

        # Zona gris (40-60): usar confianza
        reasoning.append(
            f"Score {score} en zona gris ({self.delegate_max_score}-{self.orchestrate_min_score})"
        )

        if confidence >= self.confidence_min:
            # Confianza alta: usar punto medio
            if score < 50:
                reasoning.append(
                    f"Confianza {confidence:.2f} >= {self.confidence_min}, score < 50 → DELEGATE"
                )
                return True, False, reasoning
            else:
                reasoning.append(
                    f"Confianza {confidence:.2f} >= {self.confidence_min}, score >= 50 → ORCHESTRATE"
                )
                return False, True, reasoning
        else:
            # Confianza baja: default a DELEGATE (mejor under-orchestrate)
            reasoning.append(
                f"Confianza {confidence:.2f} < {self.confidence_min}, default DELEGATE"
            )
            return True, False, reasoning

    def quick_analyze(self, task: str) -> ExecutionMode:
        """
        Análisis rápido para decisiones de baja latencia.
        Retorna solo el modo recomendado.
        """
        result = self.analyze_for_sovereign(task)
        return result.recommended_mode


# Singleton
_sovereign_analyzer_instance: Optional[SovereignComplexityAnalyzer] = None


def get_sovereign_analyzer(
    base_path: Optional[Path] = None,
) -> SovereignComplexityAnalyzer:
    """Obtiene instancia singleton del SovereignComplexityAnalyzer."""
    global _sovereign_analyzer_instance
    if _sovereign_analyzer_instance is None:
        _sovereign_analyzer_instance = SovereignComplexityAnalyzer(base_path)
    return _sovereign_analyzer_instance


def analyze_for_sovereign(
    task: str, context: Optional[Dict] = None
) -> SovereignComplexityResult:
    """Función conveniencia para análisis soberano."""
    analyzer = get_sovereign_analyzer()
    return analyzer.analyze_for_sovereign(task, context)


__all__ = [
    "ExecutionMode",
    "SovereignComplexityResult",
    "SovereignComplexityAnalyzer",
    "get_sovereign_analyzer",
    "analyze_for_sovereign",
]
