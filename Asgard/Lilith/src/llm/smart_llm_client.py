"""
Smart LLM Client - D.12: Intelligent model selection with fallback and caching.

Features:
- Automatic complexity analysis
- Model selection based on role and optimization
- Fallback chain execution
- Response caching
- Cost tracking
"""
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityLevel,
    ComplexityResult,
    get_complexity_analyzer,
)
from src.llm.cost_tracker_extended import CostTrackerExtended, get_cost_tracker_v2
from src.llm.model_cache import (
    ModelCache,
    cache_response,
    get_cached_response,
    get_model_cache,
)
from src.llm.model_selector import ModelSelector, SelectionResult, get_model_selector

logger = logging.getLogger("lilith.smart_llm")


class SmartLLMClient:
    """
    Cliente LLM inteligente con selección automática de modelo.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )

        # Componentes
        self._complexity_analyzer = get_complexity_analyzer(self.base_path)
        self._model_selector = get_model_selector(self.base_path)
        self._cache = get_model_cache(self.base_path)
        self._cost_tracker = get_cost_tracker_v2(self.base_path)

        # Providers
        self._providers: Dict[str, Any] = {}

        logger.info("[SmartLLMClient] Inicializado")

    def _get_provider(self, provider_name: str):
        """Obtiene o inicializa un provider."""
        if provider_name not in self._providers:
            if provider_name == "anthropic":
                # Importar cliente Anthropic
                try:
                    from src.llm.anthropic_client import AnthropicClient

                    self._providers[provider_name] = AnthropicClient()
                except ImportError:
                    logger.error("[SmartLLMClient] Anthropic client not available")
                    return None
            elif provider_name == "openrouter":
                from src.llm.openrouter_client import OpenRouterClient

                self._providers[provider_name] = OpenRouterClient(
                    base_path=self.base_path
                )
            else:
                logger.error("[SmartLLMClient] Unknown provider: %s", provider_name)
                return None

        return self._providers[provider_name]

    async def chat(
        self,
        task: str,
        user_id: str = "anonymous",
        user_role: str = "public",
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None,
        optimization: str = "balanced",
        force_model: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Chat con selección inteligente de modelo.

        Args:
            task: Tarea/prompt
            user_id: ID del usuario
            user_role: Rol del usuario
            system_prompt: System prompt opcional
            context: Contexto adicional
            optimization: Estrategia de optimización
            force_model: Forzar modelo específico
            use_cache: Usar cache si está disponible

        Returns:
            Dict con respuesta y metadata
        """
        context = context or {}
        start_time = time.time()

        # 1. Estimar complejidad
        complexity_result = self._complexity_analyzer.estimate(task, context)

        # 2. Seleccionar modelo
        selection = self._model_selector.select(
            task=task,
            user_role=user_role,
            context={**context, "estimated_tokens": complexity_result.estimated_tokens},
            force_model=force_model,
            optimization=optimization,
        )

        # 3. Verificar cache
        if use_cache and not force_model:
            cached = self._cache.get(task, selection.model, context)
            if cached:
                logger.info("[SmartLLMClient] Cache hit for %s", selection.model)
                return {
                    "response": cached,
                    "model": selection.model,
                    "complexity": selection.complexity.value,
                    "cached": True,
                    "cost": 0.0,
                    "latency_ms": 0.0,
                }

        # 4. Ejecutar con fallback
        response, metadata = await self._execute_with_fallback(
            task=task, selection=selection, system_prompt=system_prompt, context=context
        )

        # 5. Calcular métricas
        latency_ms = (time.time() - start_time) * 1000

        # 6. Trackear costo
        cost_info = self._cost_tracker.track_usage(
            user_id=user_id,
            model=metadata.get("model_used", selection.model),
            complexity=selection.complexity,
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            latency_ms=latency_ms,
        )

        # 7. Guardar en cache
        if use_cache and response:
            self._cache.set(
                task=task,
                model=metadata.get("model_used", selection.model),
                response=response,
                complexity=selection.complexity,
                context=context,
            )

        return {
            "response": response,
            "model": metadata.get("model_used", selection.model),
            "complexity": selection.complexity.value,
            "confidence": selection.confidence,
            "estimated_cost": selection.estimated_cost,
            "actual_cost": cost_info.get("actual_cost", 0),
            "savings_vs_baseline": cost_info.get("savings", 0),
            "latency_ms": latency_ms,
            "cached": False,
            "fallback_used": metadata.get("fallback_used", False),
            "fallback_attempts": metadata.get("fallback_attempts", 0),
        }

    async def _execute_with_fallback(
        self,
        task: str,
        selection: SelectionResult,
        system_prompt: Optional[str],
        context: Dict,
    ) -> Tuple[str, Dict]:
        """Ejecuta con cadena de fallback."""
        models_to_try = [selection.model] + selection.fallback_chain

        last_error = None
        for attempt, model in enumerate(models_to_try, 1):
            try:
                logger.info("[SmartLLMClient] Attempt %d: %s", attempt, model)

                response, metadata = await self._call_model(
                    model=model, task=task, system_prompt=system_prompt, context=context
                )

                metadata["fallback_used"] = attempt > 1
                metadata["fallback_attempts"] = attempt - 1
                metadata["model_used"] = model

                return response, metadata

            except Exception as e:
                logger.warning("[SmartLLMClient] Model %s failed: %s", model, e)
                last_error = e
                continue

        # Todos los modelos fallaron
        logger.error("[SmartLLMClient] All models failed. Last error: %s", last_error)
        return "Lo siento, no puedo procesar tu solicitud en este momento. 🔧", {
            "error": str(last_error),
            "fallback_used": True,
            "fallback_attempts": len(models_to_try) - 1,
        }

    async def _call_model(
        self, model: str, task: str, system_prompt: Optional[str], context: Dict
    ) -> Tuple[str, Dict]:
        """Llama a un modelo específico."""
        # Determinar provider
        model_config = self._model_selector.get_model_info(model)
        if not model_config:
            raise ValueError(f"Model {model} not found")

        provider = model_config.provider
        provider_client = self._get_provider(provider)

        if not provider_client:
            raise RuntimeError(f"Provider {provider} not available")

        # Preparar mensajes
        messages = [{"role": "user", "content": task}]

        # Llamar al provider
        if provider == "anthropic":
            response = await provider_client.chat_async(
                messages=messages, system_prompt=system_prompt, model=model
            )
            # Simular metadata (el provider real debería retornar esto)
            metadata = {
                "input_tokens": len(task) // 4,
                "output_tokens": len(response) // 4,
            }
        elif provider == "openrouter":
            response = await provider_client.chat_async(
                messages=messages,
                system_prompt=system_prompt,
                model=model,
                user_id=context.get("user_id"),
            )
            # OpenRouter ya trackea uso
            metadata = {
                "input_tokens": len(task) // 4,
                "output_tokens": len(response) // 4,
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return response, metadata

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cliente."""
        return {
            "cache": self._cache.get_stats(),
            "savings": self._cache.get_savings_estimate(),
            "cost_report": self._cost_tracker.get_savings_report(days=7),
        }


# Instancia global
_smart_client: Optional[SmartLLMClient] = None


def get_smart_llm_client(base_path: Optional[Path] = None) -> SmartLLMClient:
    """Obtiene instancia global del SmartLLMClient."""
    global _smart_client
    if _smart_client is None:
        _smart_client = SmartLLMClient(base_path)
    return _smart_client


async def smart_chat(
    task: str, user_id: str = "anonymous", user_role: str = "public", **kwargs
) -> Dict[str, Any]:
    """Función conveniencia para chat inteligente."""
    client = get_smart_llm_client()
    return await client.chat(task, user_id, user_role, **kwargs)


__all__ = ["SmartLLMClient", "get_smart_llm_client", "smart_chat"]
