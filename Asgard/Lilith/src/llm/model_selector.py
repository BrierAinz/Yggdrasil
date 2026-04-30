"""
Model Selector - Selección automática de modelos según complejidad y rol
Estrategias por rol con fallback chains
"""
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityLevel,
    ComplexityResult,
)

logger = logging.getLogger("lilith.model_selector")


@dataclass
class ModelConfig:
    """Configuración de un modelo LLM"""

    name: str
    provider: str  # "anthropic" | "openrouter" | "other"
    cost_per_1k_input: float  # USD
    cost_per_1k_output: float  # USD
    avg_latency_ms: int
    max_tokens: int
    description: str


@dataclass
class SelectionResult:
    """Resultado de la selección de modelo"""

    model: str
    complexity: ComplexityLevel
    confidence: float
    estimated_cost: float
    fallback_chain: List[str] = field(default_factory=list)
    provider: str = "unknown"
    reasoning: str = ""


# Configuraciones de modelos conocidos
KNOWN_MODELS = {
    # Anthropic
    "claude-opus-4-20250514": ModelConfig(
        name="claude-opus-4-20250514",
        provider="anthropic",
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        avg_latency_ms=2500,
        max_tokens=200000,
        description="Claude Opus 4 - Máxima capacidad de razonamiento",
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        name="claude-3-5-sonnet-20241022",
        provider="anthropic",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        avg_latency_ms=1500,
        max_tokens=200000,
        description="Claude 3.5 Sonnet - Equilibrio capacidad/coste",
    ),
    "claude-3-haiku-20240307": ModelConfig(
        name="claude-3-haiku-20240307",
        provider="anthropic",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        avg_latency_ms=800,
        max_tokens=200000,
        description="Claude 3 Haiku - Rápido y económico",
    ),
    # OpenRouter
    "anthropic/claude-3-haiku": ModelConfig(
        name="anthropic/claude-3-haiku",
        provider="openrouter",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        avg_latency_ms=1000,
        max_tokens=200000,
        description="Claude Haiku via OpenRouter",
    ),
    "anthropic/claude-3-5-sonnet": ModelConfig(
        name="anthropic/claude-3-5-sonnet",
        provider="openrouter",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        avg_latency_ms=1800,
        max_tokens=200000,
        description="Claude Sonnet via OpenRouter",
    ),
    "openai/gpt-4o-mini": ModelConfig(
        name="openai/gpt-4o-mini",
        provider="openrouter",
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        avg_latency_ms=900,
        max_tokens=128000,
        description="GPT-4o Mini - Económico",
    ),
}


class ModelSelector:
    """
    Selector de modelos basado en complejidad y rol de usuario.
    Implementa estrategias con fallback chains.
    """

    # Estrategias por defecto
    DEFAULT_STRATEGY = {
        ComplexityLevel.TRIVIAL: ["claude-3-haiku-20240307", "openai/gpt-4o-mini"],
        ComplexityLevel.SIMPLE: [
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
        ComplexityLevel.MODERATE: [
            "claude-3-5-sonnet-20241022",
            "claude-opus-4-20250514",
        ],
        ComplexityLevel.COMPLEX: [
            "claude-opus-4-20250514",
            "claude-3-5-sonnet-20241022",
        ],
        ComplexityLevel.EXPERT: [
            "claude-opus-4-20250514",
            "claude-3-5-sonnet-20241022",
        ],
    }

    PUBLIC_STRATEGY = {
        # Público usa OpenRouter (Crystal)
        ComplexityLevel.TRIVIAL: ["anthropic/claude-3-haiku", "openai/gpt-4o-mini"],
        ComplexityLevel.SIMPLE: ["anthropic/claude-3-haiku", "openai/gpt-4o-mini"],
        ComplexityLevel.MODERATE: ["anthropic/claude-3-5-sonnet"],
        ComplexityLevel.COMPLEX: ["anthropic/claude-3-5-sonnet"],
        ComplexityLevel.EXPERT: ["anthropic/claude-3-5-sonnet"],
    }

    TRUSTED_STRATEGY = {
        # Trusted igual que owner pero con fallback a OpenRouter
        ComplexityLevel.TRIVIAL: [
            "claude-3-haiku-20240307",
            "anthropic/claude-3-haiku",
        ],
        ComplexityLevel.SIMPLE: [
            "claude-3-5-sonnet-20241022",
            "anthropic/claude-3-5-sonnet",
        ],
        ComplexityLevel.MODERATE: [
            "claude-3-5-sonnet-20241022",
            "claude-opus-4-20250514",
        ],
        ComplexityLevel.COMPLEX: [
            "claude-opus-4-20250514",
            "claude-3-5-sonnet-20241022",
        ],
        ComplexityLevel.EXPERT: [
            "claude-opus-4-20250514",
            "claude-3-5-sonnet-20241022",
        ],
    }

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()
        self.strategies = self._load_strategies()
        self.known_models = {**KNOWN_MODELS}

        # Tracking de fallbacks
        self._fallback_stats: Dict[str, int] = {}
        self._model_usage: Dict[str, int] = {}

    def _load_config(self) -> Dict:
        """Carga configuración desde model_selector.json"""
        try:
            config_path = self.base_path / "Config" / "model_selector.json"
            if config_path.exists():
                return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[ModelSelector] Error cargando config: {e}")

        return {
            "fallback_enabled": True,
            "max_fallback_attempts": 3,
        }

    def _load_strategies(self) -> Dict[str, Dict[ComplexityLevel, List[str]]]:
        """Carga estrategias desde config o usa defaults"""
        strategies_config = self.config.get("strategies", {})

        strategies = {
            "owner": self.DEFAULT_STRATEGY,
            "trusted": self.TRUSTED_STRATEGY,
            "public": self.PUBLIC_STRATEGY,
        }

        # Override con config si existe
        for role in ["owner", "trusted", "public"]:
            if role in strategies_config:
                role_config = strategies_config[role]
                parsed_strategy = {}
                for level_name, models in role_config.items():
                    try:
                        level = ComplexityLevel(level_name.lower())
                        parsed_strategy[level] = models
                    except ValueError:
                        logger.warning(
                            f"[ModelSelector] Unknown complexity level: {level_name}"
                        )
                if parsed_strategy:
                    strategies[role] = parsed_strategy

        return strategies

    def select(
        self,
        task: str,
        user_role: str,
        context: Optional[Dict] = None,
        force_model: Optional[str] = None,
        optimization: str = "balanced",
    ) -> SelectionResult:
        """
        Selecciona el modelo óptimo según complejidad y rol.

        Args:
            task: Tarea/prompt a procesar
            user_role: Rol del usuario (owner/trusted/public)
            context: Contexto adicional con estimated_tokens, etc.
            force_model: Forzar modelo específico
            optimization: Estrategia de optimización (speed/cost/quality/balanced)

        Returns:
            SelectionResult con modelo seleccionado y metadata
        """
        role = user_role.lower()
        if role not in self.strategies:
            role = "owner"  # Default

        # Si se fuerza un modelo específico
        if force_model:
            model_config = self.known_models.get(force_model)
            if model_config:
                estimated_tokens = (
                    context.get("estimated_tokens", 1000) if context else 1000
                )
                estimated_cost = self.estimate_cost(
                    model_config, estimated_tokens, estimated_tokens // 2
                )
                return SelectionResult(
                    model=force_model,
                    complexity=ComplexityLevel.COMPLEX,  # Asumir complejo si se fuerza
                    confidence=1.0,
                    estimated_cost=estimated_cost,
                    fallback_chain=[],
                    provider=model_config.provider,
                    reasoning="Model forced by user",
                )
            else:
                # Modelo forzado no está en known_models, crear config básica
                estimated_tokens = (
                    context.get("estimated_tokens", 1000) if context else 1000
                )
                estimated_cost = (estimated_tokens / 1000) * 0.01 + (
                    estimated_tokens / 2 / 1000
                ) * 0.03
                return SelectionResult(
                    model=force_model,
                    complexity=ComplexityLevel.COMPLEX,
                    confidence=1.0,
                    estimated_cost=round(estimated_cost, 6),
                    fallback_chain=[],
                    provider="unknown",
                    reasoning="Model forced by user (unknown model)",
                )

        # Obtener complejidad del contexto o estimar
        if context and "complexity_result" in context:
            complexity_result = context["complexity_result"]
            complexity = (
                complexity_result.level
                if isinstance(complexity_result, ComplexityResult)
                else complexity_result
            )
        else:
            # Estimar complejidad
            analyzer = ComplexityAnalyzer(self.base_path)
            complexity_result = analyzer.estimate(task, context)
            complexity = complexity_result.level

        strategy = self.strategies[role]
        model_chain = strategy.get(complexity, strategy[ComplexityLevel.SIMPLE])

        if not model_chain:
            model_chain = ["claude-3-5-sonnet-20241022"]  # Default seguro

        selected_name = model_chain[0]
        fallback_chain = model_chain[1:] if len(model_chain) > 1 else []

        # Obtener config del modelo
        model_config = self.known_models.get(selected_name)
        if not model_config:
            # Modelo desconocido, crear config básica
            model_config = ModelConfig(
                name=selected_name,
                provider="unknown",
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                avg_latency_ms=1500,
                max_tokens=100000,
                description=f"Model {selected_name}",
            )

        # Estimar costo
        estimated_tokens = context.get("estimated_tokens", 1000) if context else 1000
        estimated_output = estimated_tokens // 2  # Asumir input:output 2:1
        estimated_cost = self.estimate_cost(
            model_config, estimated_tokens, estimated_output
        )

        # Tracking
        self._model_usage[selected_name] = self._model_usage.get(selected_name, 0) + 1

        logger.info(
            f"[ModelSelector] Selected: {selected_name} "
            f"({complexity.value} task, {user_role} role, "
            f"est. cost: ${estimated_cost:.4f})"
        )

        return SelectionResult(
            model=selected_name,
            complexity=complexity,
            confidence=0.9,
            estimated_cost=estimated_cost,
            fallback_chain=fallback_chain,
            provider=model_config.provider,
            reasoning=f"Complexity: {complexity.value}, Role: {role}, Optimization: {optimization}",
        )

    def get_fallback_chain(
        self, complexity: ComplexityLevel, user_role: str
    ) -> List[ModelConfig]:
        """Obtiene toda la cadena de fallback para una complejidad/rol"""
        role = user_role.lower()
        if role not in self.strategies:
            role = "owner"

        strategy = self.strategies[role]
        model_names = strategy.get(complexity, [])

        return [
            self.known_models.get(name)
            or ModelConfig(
                name=name,
                provider="unknown",
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                avg_latency_ms=1500,
                max_tokens=100000,
                description=f"Model {name}",
            )
            for name in model_names
        ]

    def get_model_info(self, model_name: str) -> Optional[ModelConfig]:
        """Obtiene información de un modelo"""
        return self.known_models.get(model_name)

    def record_fallback(self, from_model: str, to_model: str, reason: str):
        """Registra un evento de fallback"""
        key = f"{from_model}->{to_model}"
        self._fallback_stats[key] = self._fallback_stats.get(key, 0) + 1

        logger.warning(
            f"[ModelSelector] Fallback recorded: {from_model} -> {to_model} "
            f"(reason: {reason})"
        )

    def get_stats(self) -> Dict:
        """Obtiene estadísticas de uso del selector"""
        return {
            "model_usage": self._model_usage.copy(),
            "fallback_stats": self._fallback_stats.copy(),
            "total_calls": sum(self._model_usage.values()),
        }

    def estimate_cost(
        self, model: ModelConfig, input_tokens: int, output_tokens: int
    ) -> float:
        """Estima el costo de una llamada"""
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def get_savings_vs_baseline(
        self,
        actual_cost: float,
        baseline_model: str = "claude-opus-4-20250514",
        total_tokens: int = 1000,
    ) -> Dict:
        """Calcula ahorros vs usar siempre el modelo baseline"""
        if baseline_model not in self.known_models:
            return {"error": f"Unknown baseline model: {baseline_model}"}

        baseline = self.known_models[baseline_model]
        baseline_cost = (total_tokens / 1000) * (
            baseline.cost_per_1k_input + baseline.cost_per_1k_output
        )

        savings = baseline_cost - actual_cost
        savings_pct = (savings / baseline_cost) * 100 if baseline_cost > 0 else 0

        return {
            "baseline_cost": round(baseline_cost, 6),
            "actual_cost": round(actual_cost, 6),
            "savings": round(savings, 6),
            "savings_percentage": round(savings_pct, 2),
            "baseline_model": baseline_model,
        }


# Singleton global
_selector_instance: Optional[ModelSelector] = None


def get_model_selector(base_path: Optional[Path] = None) -> ModelSelector:
    """Obtiene instancia singleton del ModelSelector"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = ModelSelector(base_path)
    return _selector_instance


def select_model(
    task: str,
    user_role: str,
    context: Optional[Dict] = None,
    force_model: Optional[str] = None,
    optimization: str = "balanced",
    base_path: Optional[Path] = None,
) -> SelectionResult:
    """Función conveniencia para seleccionar modelo"""
    selector = get_model_selector(base_path)
    return selector.select(task, user_role, context, force_model, optimization)


__all__ = [
    "ModelConfig",
    "SelectionResult",
    "ModelSelector",
    "KNOWN_MODELS",
    "get_model_selector",
    "select_model",
]
