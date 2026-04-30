"""
Sovereign Mode - Modo Soberano de Lilith (La Corona).

Integra:
- SovereignComplexityAnalyzer: decide DELEGATE vs ORCHESTRATE
- SovereignState: tracking de busy state
- BifrostClient existente: comunicación con Vanaheim
- VanaheimRouter: selección de agente

Este módulo es el punto de entrada único para el modo soberano.
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .bifrost_client import get_bifrost_client
from .sovereign_complexity import (
    ExecutionMode,
    SovereignComplexityAnalyzer,
    get_sovereign_analyzer,
)
from .sovereign_metrics import SovereignMetrics, get_sovereign_metrics
from .sovereign_state import SovereignState, get_sovereign_state
from .vanaheim_router import VanaheimRouter, get_vanaheim_router

logger = logging.getLogger("lilith.sovereign_mode")


class SovereignMode:
    """
    Modo Soberano de Lilith.

    Decide entre:
    - DELEGATE: Forwarding simple a Vanaheim (70% del tráfico)
    - ORCHESTRATE: DAG completo con Lilith (30% del tráfico)
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )

        # Componentes
        self.complexity_analyzer = get_sovereign_analyzer(self.base_path)
        self.sovereign_state = get_sovereign_state(self.base_path)
        self.vanaheim_router = get_vanaheim_router(self.base_path)
        self.bifrost_client = get_bifrost_client(self.base_path)
        self.metrics = get_sovereign_metrics(self.base_path)

        # Configuración
        self.config = self._load_config()
        self.enabled = self.config.get("enabled", True)

        # Métricas
        self._delegate_count = 0
        self._orchestrate_count = 0

        logger.info("[SovereignMode] Inicializado. Enabled: %s", self.enabled)

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        from .json_safe import safe_load

        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            return safe_load(config_path, default={})
        except Exception as e:
            logger.error("[SovereignMode] Error cargando config: %s", e)
            return {"enabled": True}

    def decide_mode(
        self,
        message: str,
        context: Optional[Dict] = None,
        force_mode: Optional[ExecutionMode] = None,
    ) -> Tuple[ExecutionMode, Dict[str, Any]]:
        """
        Decide el modo de ejecución para un mensaje.

        Args:
            message: Mensaje del usuario
            context: Contexto adicional
            force_mode: Forzar un modo específico (para testing)

        Returns:
            Tuple de (modo, metadatos)
        """
        if not self.enabled:
            return ExecutionMode.ORCHESTRATE, {"reason": "Sovereign mode disabled"}

        if force_mode:
            return force_mode, {"reason": "Forced mode"}

        # 1. Verificar patrones forzados
        force_patterns = self.config.get("force_patterns", {})
        message_lower = message.lower()

        for pattern in force_patterns.get("delegate", []):
            if self._matches_pattern(message_lower, pattern):
                return ExecutionMode.DELEGATE, {"reason": "Force pattern (delegate)"}

        for pattern in force_patterns.get("orchestrate", []):
            if self._matches_pattern(message_lower, pattern):
                return ExecutionMode.ORCHESTRATE, {
                    "reason": "Force pattern (orchestrate)"
                }

        # 2. Analizar complejidad
        complexity_result = self.complexity_analyzer.analyze_for_sovereign(
            message, context
        )

        # 3. Verificar si Lilith está busy
        is_busy = self.sovereign_state.is_lilith_busy(complexity_result.sovereign_score)

        # 4. Decidir modo
        if is_busy and complexity_result.should_delegate:
            mode = ExecutionMode.DELEGATE
            reason = f"Lilith busy + low complexity (score: {complexity_result.sovereign_score})"
        elif complexity_result.should_delegate:
            mode = ExecutionMode.DELEGATE
            reason = f"Low complexity (score: {complexity_result.sovereign_score})"
        elif complexity_result.should_orchestrate:
            mode = ExecutionMode.ORCHESTRATE
            reason = f"High complexity (score: {complexity_result.sovereign_score})"
        else:
            # Zona gris - usar confianza
            if complexity_result.confidence >= 0.7:
                mode = (
                    ExecutionMode.DELEGATE
                    if complexity_result.sovereign_score < 50
                    else ExecutionMode.ORCHESTRATE
                )
                reason = f"Gray zone with confidence {complexity_result.confidence:.2f}"
            else:
                # Default a DELEGATE para ser conservador
                mode = ExecutionMode.DELEGATE
                reason = f"Gray zone with low confidence {complexity_result.confidence:.2f}, defaulting to DELEGATE"

        metadata = {
            "reason": reason,
            "complexity_score": complexity_result.sovereign_score,
            "complexity_level": complexity_result.level.value,
            "confidence": complexity_result.confidence,
            "is_lilith_busy": is_busy,
            "factors": complexity_result.factors,
        }

        # Registrar métrica de decisión
        self.metrics.record_execution(
            mode=mode.value,
            latency_ms=0,  # Se actualizará después de la ejecución
            success=True,
            complexity_score=complexity_result.sovereign_score,
            channel="unknown",
        )

        return mode, metadata

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Verifica si el texto coincide con un patrón."""
        import re

        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            # Si no es regex válido, tratar como substring
            return pattern.lower() in text

    async def execute_delegate(
        self, message: str, metadata: Dict[str, Any], channel: str = "discord"
    ) -> Optional[str]:
        """
        Ejecuta en modo DELEGATE (Vanaheim).

        Args:
            message: Mensaje del usuario
            metadata: Metadatos de la decisión
            channel: Canal de origen

        Returns:
            Respuesta de Vanaheim o None si falló
        """
        start_time = time.time()

        # 1. Seleccionar agente
        agent, confidence = self.vanaheim_router.select_agent(
            message, complexity_level=metadata.get("complexity_level")
        )

        logger.info(
            "[SovereignMode] DELEGATE to %s (confidence: %.2f)", agent, confidence
        )

        # 2. Intentar delegar vía Bifrost existente
        try:
            # Mapear agentes de Vanaheim a agentes conocidos por Bifrost
            bifrost_agent_map = {
                "freya": "eva",  # Freya -> Eva (conversación)
                "heimdall": "odin",  # Heimdall -> Odín (búsqueda)
                "eir": "adan",  # Eir -> Adán (código)
                "balder": "eva",  # Balder -> Eva (análisis)
            }

            bifrost_agent = bifrost_agent_map.get(agent, "eva")

            # Crear clasificación compatible con BifrostClient
            classification = {
                "route": "vanaheim",
                "recommended_agent": bifrost_agent,
                "confidence": confidence,
                "complexity": metadata.get("complexity_level", "simple"),
                "compressed_context": "",
            }

            # Verificar si Bifrost acepta esta clasificación
            if self.bifrost_client.should_use_vanaheim(classification):
                result = await self.bifrost_client.execute(
                    agent=bifrost_agent, task=message, context=""
                )

                if result:
                    latency = (time.time() - start_time) * 1000
                    self._delegate_count += 1
                    self.sovereign_state.record_metric(
                        "delegate_success",
                        {"agent": agent, "latency_ms": latency, "channel": channel},
                    )
                    logger.info("[SovereignMode] DELEGATE success in %.2fms", latency)
                    return result.get("response", "")

            # Si Bifrost no funcionó, usar agentes locales
            logger.debug("[SovereignMode] Bifrost unavailable, using direct agent")
            return await self._execute_direct_agent(agent, message)

        except Exception as e:
            logger.error("[SovereignMode] DELEGATE failed: %s", e)
            # Registrar fallo
            self.metrics.record_execution(
                mode="delegate",
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                agent=agent,
                complexity_score=metadata.get("complexity_score"),
                channel=channel,
            )
            # Fallback a ejecución directa
            return await self._execute_direct_agent(agent, message)

    async def _execute_direct_agent(self, agent: str, message: str) -> Optional[str]:
        """Ejecuta agente de Vanaheim directamente (in-process)."""
        try:
            if agent == "freya":
                from Workspace.Yggdrasil.Vanaheim.Agents.freya_agent import (
                    get_freya_agent,
                )

                agent_instance = get_freya_agent()
                return agent_instance.execute_task(message)
            elif agent == "heimdall":
                from Workspace.Yggdrasil.Vanaheim.Agents.heimdall_agent import (
                    get_heimdall_agent,
                )

                agent_instance = get_heimdall_agent()
                return agent_instance.execute_task(message)
            elif agent == "eir":
                from Workspace.Yggdrasil.Vanaheim.Agents.eir_agent import get_eir_agent

                agent_instance = get_eir_agent()
                return agent_instance.execute_task(message)
            elif agent == "balder":
                from Workspace.Yggdrasil.Vanaheim.Agents.balder_agent import (
                    get_balder_agent,
                )

                agent_instance = get_balder_agent()
                return agent_instance.execute_task(message)
            else:
                logger.warning("[SovereignMode] Unknown agent: %s", agent)
                return None
        except Exception as e:
            logger.error("[SovereignMode] Direct agent execution failed: %s", e)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del modo soberano."""
        total = self._delegate_count + self._orchestrate_count
        current_metrics = self.metrics.get_current_ratio()
        health = self.metrics.get_health_report()

        return {
            "enabled": self.enabled,
            "delegate_count": self._delegate_count,
            "orchestrate_count": self._orchestrate_count,
            "delegate_ratio": self._delegate_count / total if total > 0 else 0,
            "orchestrate_ratio": self._orchestrate_count / total if total > 0 else 0,
            "target_ratio": 0.7,
            "state": self.sovereign_state.get_snapshot().status.value,
            "today_metrics": current_metrics,
            "health": health["status"],
            "recommendations": self.metrics.get_recommendations(),
        }


# Singleton
_sovereign_mode_instance: Optional[SovereignMode] = None


def get_sovereign_mode(base_path: Optional[Path] = None) -> SovereignMode:
    """Obtiene instancia singleton de SovereignMode."""
    global _sovereign_mode_instance
    if _sovereign_mode_instance is None:
        _sovereign_mode_instance = SovereignMode(base_path)
    return _sovereign_mode_instance


async def try_delegate(
    message: str, context: Optional[Dict] = None, channel: str = "discord"
) -> Optional[str]:
    """
    Intenta delegar a Vanaheim si el modo soberano lo recomienda.

    Returns:
        Respuesta de Vanaheim o None si debe ir a orquestación
    """
    sovereign = get_sovereign_mode()
    mode, metadata = sovereign.decide_mode(message, context)

    if mode == ExecutionMode.DELEGATE:
        return await sovereign.execute_delegate(message, metadata, channel)

    return None


__all__ = ["SovereignMode", "get_sovereign_mode", "try_delegate"]
