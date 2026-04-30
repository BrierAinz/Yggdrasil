"""
Lilith 3.0 / 3.5 B.3 — Orquestador (refactor).
Coordina Planner, PlanExecutor y MemoryManager: planifica, ejecuta y persiste.
4.0 Fase 1: usa AgentRegistry para ejecutar pasos delegate_* cuando está disponible.
4.2: Integración con DagExecutor para ejecución paralela de planes con dependencias.
"""
import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .agent_caller import AgentCaller

# v4.2: Confidence and Context Enrichment
from .confidence_calculator import calculate_confidence

# 4.2: DAG Execution Engine
from .dag import DagExecutor, DagOptimizer, PlanDag
from .dag.vanaheim_node_executor import HybridNodeExecutor, VanaheimNodeExecutor
from .decision_auditor_v2 import log_decision
from .memory_store import MemoryStore
from .plan_executor import PlanExecutor
from .planner import Planner, Step

# v4.3: Modo Soberano - La Corona
from .sovereign_mode import (
    ExecutionMode,
    SovereignMode,
    get_sovereign_mode,
    try_delegate,
)
from .tools_v3.registry import ToolRegistryV3

if TYPE_CHECKING:
    from .agent_registry import AgentRegistry

logger = logging.getLogger("Orchestrator")


def _launch_scribe(
    user_message: str,
    response: str,
    agent: str,
    elapsed: float,
    channel: str = "discord",
    base_path=None,
) -> None:
    """Lanza la Escriba de Albedo en un hilo daemon (fire-and-forget). Nunca bloquea.
    channel: 'telegram' | 'discord_dm' | 'discord_public' — para tagging de fuente en episodios.
    """

    def _bg(
        _msg=user_message,
        _resp=response,
        _agent=agent,
        _elapsed=elapsed,
        _ch=channel,
        _bp=base_path,
    ):
        try:
            from .agents.albedo_agent import AlbedoAgent as _AlbedoAgent

            result = _AlbedoAgent().scribe_process_sync(_msg, _resp, _agent, _elapsed)
            if result:
                summary = (result.get("episode_summary") or "")[:100]
                logger.debug("[Albedo:Escriba] [%s] %s", _ch, summary)
                # Guardar episodio con source=channel para tagging de fuente
                if summary and _bp is not None:
                    try:
                        from .episode_builder import build_episode
                        from .episodic_store import EpisodicStore

                        tags = list(result.get("tags") or [])
                        if _ch and _ch not in tags:
                            tags.append(_ch)
                        episode = build_episode(
                            summary=summary,
                            outcome="success",
                            source=_ch,
                            channel_name=_ch,
                        )
                        EpisodicStore(_bp).append(episode)
                    except Exception as _ep_err:
                        logger.debug(
                            "[Albedo:Escriba] episodio no guardado: %s", _ep_err
                        )
        except Exception as _e:
            logger.warning("[Albedo:Escriba] Error en background: %s", _e)

    try:
        threading.Thread(target=_bg, daemon=True).start()
    except Exception as _e:
        logger.warning("[Albedo:Escriba] Error al lanzar hilo: %s", _e)


class Orchestrator:
    """
    Director de orquesta (3.5 B.3 refactor):
    - Obtiene el plan del Planner.
    - Delega la ejecuci?n al PlanExecutor.
    - Delega la persistencia al MemoryManager.post_interaction.
    """

    def __init__(
        self,
        planner: Planner,
        registry: ToolRegistryV3,
        memory_manager: Optional[Any] = None,
        *,
        plan_executor: Optional[PlanExecutor] = None,
        agent_caller: Optional[AgentCaller] = None,
        agent_registry: Optional["AgentRegistry"] = None,
    ):
        self.planner = planner
        self.registry = registry
        self.memory_manager = memory_manager
        self._last_executed_tool: Optional[str] = None
        base_path = (
            getattr(memory_manager, "base_path", None) if memory_manager else None
        )
        self.base_path = base_path
        # 4.0 Fase 1: AgentRegistry por defecto para delegate_eva/adan/lucifer/odin
        if agent_registry is None and base_path is not None:
            from .agent_registry import create_default_agent_registry

            agent_registry = create_default_agent_registry(base_path)
        self.agent_registry = agent_registry
        caller = agent_caller or AgentCaller(
            base_path=base_path, agent_registry=agent_registry
        )
        self._plan_executor = plan_executor or PlanExecutor(agent_caller=caller)

        # 4.2: DAG Executor para planes con dependencias
        self._dag_executor: Optional[DagExecutor] = None
        self._dag_optimizer = DagOptimizer()

        # 4.3: Vanaheim Node Executor para DAGs con agentes externos
        self._vanaheim_node_executor: Optional[VanaheimNodeExecutor] = None
        self._use_vanaheim_in_dag = True  # Configurable
        # v4.3: Modo Soberano
        self._sovereign_mode: Optional[SovereignMode] = None

    def _get_vanaheim_node_executor(self) -> Optional[VanaheimNodeExecutor]:
        """Obtiene instancia del executor de nodos Vanaheim (lazy init)."""
        if self._vanaheim_node_executor is None and self.base_path is not None:
            try:
                self._vanaheim_node_executor = VanaheimNodeExecutor(self.base_path)
            except Exception as e:
                logger.warning(
                    "[Orchestrator] Failed to initialize Vanaheim node executor: %s", e
                )
        return self._vanaheim_node_executor

    def _get_sovereign_mode(self) -> Optional[SovereignMode]:
        """Obtiene instancia del modo soberano (lazy init)."""
        if self._sovereign_mode is None and self.base_path is not None:
            try:
                self._sovereign_mode = get_sovereign_mode(self.base_path)
            except Exception as e:
                logger.warning(
                    "[Orchestrator] Failed to initialize sovereign mode: %s", e
                )
        return self._sovereign_mode

    def execute_plan(
        self,
        message: str,
        context: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: str = "",
        skip_cache: bool = False,
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        channel: str = "discord",
        session_id: Optional[str] = None,
    ) -> str:
        """
        Genera el plan para el mensaje, ejecuta todos los pasos (PlanExecutor) y devuelve
        la respuesta final. Si hay MemoryManager, guarda la interacci?n v?a post_interaction.
        C.3: si user_id se pasa, guarda last_plan para feedback posterior.
        3.7: skip_cache=True desactiva agent_response_cache para esta ejecución (ej. owner en DM).
        channel: fuente del mensaje ('telegram'|'discord_dm'|'discord_public') para tagging de episodios.
        4.0 UX: progress_callback(step_index, step_id, label) para feedback progresivo (Discord/WS).
        session_id: ID de sesión opcional para cargar attention stack.
        """
        _t0 = time.time()

        # ── v4.3: Modo Soberano ─────────────────────────────────────────────────
        sovereign = self._get_sovereign_mode()
        if sovereign and sovereign.enabled:
            try:
                mode, metadata = sovereign.decide_mode(message, context)
                if mode == ExecutionMode.DELEGATE:
                    # Intentar delegar a Vanaheim
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    delegate_response = loop.run_until_complete(
                        sovereign.execute_delegate(message, metadata, channel)
                    )

                    if delegate_response:
                        _launch_scribe(
                            message,
                            delegate_response,
                            metadata.get("agent", "vanaheim"),
                            time.time() - _t0,
                            channel=channel,
                            base_path=self.base_path,
                        )
                        return delegate_response
                    # Si falló, continuar con orquestación normal
                    logger.debug(
                        "[Orchestrator] DELEGATE failed, falling back to ORCHESTRATE"
                    )
            except Exception as e:
                logger.warning("[Orchestrator] Sovereign mode error: %s", e)
        # ─────────────────────────────────────────────────────────────────────────
