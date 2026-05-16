"""
ConflictResolver — Resolución de conflictos entre agentes

FASE 3 del sistema swarm: cuando múltiples agentes producen resultados
contradictorios, este módulo determina la respuesta consensuada.

Estrategias:
- VOTE:      Mayoría gana (cada agente = 1 voto).
- PRIORITY:  El agente con mayor prioridad (según rol/config) gana.
- MERGE:     Combina los outputs en una respuesta unificada.
- LLM_JUDGE: Usa un LLM para seleccionar la mejor respuesta.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.agents.conflict_resolver")


# ── Enums y dataclasses ───────────────────────────────────────────────────────


class ResolutionStrategy(Enum):
    """Estrategias de resolución de conflictos."""

    VOTE = "vote"          # Mayoría gana
    PRIORITY = "priority"  # Mayor prioridad gana
    MERGE = "merge"        # Combinar outputs
    LLM_JUDGE = "llm_judge"  # LLM como juez


@dataclass
class ConflictConfig:
    """Configuración del ConflictResolver.

    Attributes:
        default_strategy: Estrategia por defecto cuando no se especifica.
        llm_model: Modelo LLM a usar para la estrategia LLM_JUDGE.
        llm_base_url: URL base del endpoint LLM (estilo OpenAI-compatible).
        llm_api_key: API key para el endpoint LLM.
        merge_separator: Separador al combinar outputs con estrategia MERGE.
        min_confidence: Confianza mínima para aceptar una resolución.
        max_history: Número máximo de conflictos en el historial.
        priority_order: Orden de prioridad de roles (de mayor a menor).
    """

    default_strategy: ResolutionStrategy = ResolutionStrategy.VOTE
    llm_model: str = "gpt-4"
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = ""
    merge_separator: str = "\n\n---\n\n"
    min_confidence: float = 0.5
    max_history: int = 100
    priority_order: List[str] = field(default_factory=lambda: [
        "orchestrator",
        "coordinator",
        "planner",
        "researcher",
        "reviewer",
        "executor",
        "specialist",
    ])


@dataclass
class ConflictResolution:
    """Resultado de una resolución de conflicto.

    Attributes:
        winner_agent: Nombre del agente ganador (o del agente líder en MERGE).
        consensus_output: Output consensuado después de la resolución.
        confidence: Nivel de confianza de la resolución (0.0 - 1.0).
        dissenting_agents: Lista de agentes cuyos outputs fueron descartados.
        resolution_strategy: Estrategia utilizada para resolver el conflicto.
        metadata: Metadatos adicionales de la resolución.
    """

    winner_agent: str
    consensus_output: Any
    confidence: float
    dissenting_agents: List[str]
    resolution_strategy: ResolutionStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la resolución a diccionario."""
        return {
            "winner_agent": self.winner_agent,
            "consensus_output": str(self.consensus_output),
            "confidence": round(self.confidence, 3),
            "dissenting_agents": self.dissenting_agents,
            "resolution_strategy": self.resolution_strategy.value,
            "metadata": self.metadata,
        }


# ── ConflictResolver ──────────────────────────────────────────────────────────


class ConflictResolver:
    """
    Resuelve conflictos entre agentes cuando múltiples agentes producen
    resultados contradictorios.

    Uso:
        resolver = ConflictResolver(swarm)
        resolution = resolver.resolve(agent_results, context, strategy="vote")
        print(resolution.winner_agent, resolution.consensus_output)
    """

    def __init__(
        self,
        swarm: Any,
        config: ConflictConfig | None = None,
    ) -> None:
        """
        Inicializa el ConflictResolver.

        Args:
            swarm: Instancia de Swarm para consultar información de agentes.
            config: Configuración opcional. Si es None, usa ConflictConfig por defecto.
        """
        self.swarm = swarm
        self.config = config or ConflictConfig()
        self._history: List[Dict[str, Any]] = []

    def resolve(
        self,
        results: List[Any],
        context: Dict[str, Any] | None = None,
        strategy: str | ResolutionStrategy | None = None,
    ) -> ConflictResolution:
        """
        Resuelve un conflicto entre múltiples AgentResults.

        Args:
            results: Lista de AgentResult producidos por diferentes agentes.
            context: Contexto adicional para la resolución (opcional).
            strategy: Estrategia a usar. Si es None, usa la configuración por defecto.

        Returns:
            ConflictResolution con el resultado de la resolución.
        """
        if not results:
            return ConflictResolution(
                winner_agent="none",
                consensus_output="(sin resultados para resolver)",
                confidence=0.0,
                dissenting_agents=[],
                resolution_strategy=ResolutionStrategy.VOTE,
                metadata={"error": "empty_results"},
            )

        # Si solo hay un resultado, no hay conflicto
        if len(results) == 1:
            result = results[0]
            return ConflictResolution(
                winner_agent=getattr(result, "agent_name", "unknown"),
                consensus_output=getattr(result, "output", str(result)),
                confidence=1.0,
                dissenting_agents=[],
                resolution_strategy=ResolutionStrategy.VOTE,
            )

        # Resolver estrategia
        if isinstance(strategy, str):
            strategy = ResolutionStrategy(strategy.lower())
        elif strategy is None:
            strategy = self.config.default_strategy

        # Filtrar resultados fallidos
        successful = [r for r in results if getattr(r, "success", True)]
        if not successful:
            # Todos fallaron — retornar el primero con su error
            result = results[0]
            return ConflictResolution(
                winner_agent=getattr(result, "agent_name", "unknown"),
                consensus_output=f"[Error] {getattr(result, 'error', 'Todos los agentes fallaron')}",
                confidence=0.0,
                dissenting_agents=[getattr(r, "agent_name", "unknown") for r in results[1:]],
                resolution_strategy=strategy,
                metadata={"all_failed": True},
            )

        # Ejecutar estrategia de resolución
        resolution = self._resolve_by_strategy(successful, context or {}, strategy)

        # Registrar en historial
        self._record_conflict(results, resolution, strategy)

        return resolution

    def _resolve_by_strategy(
        self,
        results: List[Any],
        context: Dict[str, Any],
        strategy: ResolutionStrategy,
    ) -> ConflictResolution:
        """Despacha a la estrategia de resolución apropiada."""
        if strategy == ResolutionStrategy.VOTE:
            return self._resolve_vote(results, context)
        elif strategy == ResolutionStrategy.PRIORITY:
            return self._resolve_priority(results, context)
        elif strategy == ResolutionStrategy.MERGE:
            return self._resolve_merge(results, context)
        elif strategy == ResolutionStrategy.LLM_JUDGE:
            return self._resolve_llm_judge(results, context)
        else:
            logger.warning("Estrategia desconocida: %s — usando VOTE", strategy)
            return self._resolve_vote(results, context)

    # ── Estrategia VOTE ─────────────────────────────────────────────────────

    def _resolve_vote(
        self, results: List[Any], context: Dict[str, Any]
    ) -> ConflictResolution:
        """
        Mayoría gana: agrupa outputs idénticos o similares y selecciona
        el grupo más grande.
        """
        # Agrupar por similitud de output
        groups: Dict[str, List[Any]] = {}
        for r in results:
            output_key = self._output_fingerprint(getattr(r, "output", ""))
            if output_key not in groups:
                groups[output_key] = []
            groups[output_key].append(r)

        # Encontrar el grupo más grande
        largest_group_key = max(groups, key=lambda k: len(groups[k]))
        largest_group = groups[largest_group_key]
        total = len(results)

        # El ganador es el primer agente del grupo más grande
        winner = largest_group[0]
        winner_name = getattr(winner, "agent_name", "unknown")

        # Agentes disidentes
        dissenting = [
            getattr(r, "agent_name", "unknown")
            for r in results
            if self._output_fingerprint(getattr(r, "output", "")) != largest_group_key
        ]

        # Confianza basada en la proporción de votos
        confidence = len(largest_group) / total if total > 0 else 0.5

        return ConflictResolution(
            winner_agent=winner_name,
            consensus_output=getattr(winner, "output", ""),
            confidence=confidence,
            dissenting_agents=dissenting,
            resolution_strategy=ResolutionStrategy.VOTE,
            metadata={"vote_counts": {k: len(v) for k, v in groups.items()}},
        )

    # ── Estrategia PRIORITY ────────────────────────────────────────────────

    def _resolve_priority(
        self, results: List[Any], context: Dict[str, Any]
    ) -> ConflictResolution:
        """
        El agente con mayor prioridad gana. La prioridad se basa en el rol
        del agente según ``config.priority_order``.
        """
        priority_map = {
            role: idx
            for idx, role in enumerate(self.config.priority_order)
        }

        # Valor por defecto para roles no listados
        default_priority = len(self.config.priority_order)

        def get_priority(result: Any) -> int:
            """Obtiene prioridad de un resultado basándose en el rol del agente."""
            agent_name = getattr(result, "agent_name", "unknown")
            # Intentar obtener el agente del swarm y su rol
            if self.swarm is not None:
                agent = self.swarm.get_agent(agent_name)
                if agent is not None:
                    role_value = getattr(agent.config, "role", None)
                    if role_value is not None:
                        role_str = role_value.value if hasattr(role_value, "value") else str(role_value)
                        return priority_map.get(role_str, default_priority)
            return default_priority

        # Ordenar por prioridad (menor número = mayor prioridad)
        sorted_results = sorted(results, key=get_priority)
        winner = sorted_results[0]
        winner_name = getattr(winner, "agent_name", "unknown")

        dissenting = [
            getattr(r, "agent_name", "unknown")
            for r in results
            if getattr(r, "agent_name", "") != winner_name
        ]

        # Confianza: mayor cuando el ganador tiene alta prioridad
        winner_priority = get_priority(winner)
        max_priority = len(self.config.priority_order)
        confidence = 1.0 - (winner_priority / (max_priority + 1))

        return ConflictResolution(
            winner_agent=winner_name,
            consensus_output=getattr(winner, "output", ""),
            confidence=confidence,
            dissenting_agents=dissenting,
            resolution_strategy=ResolutionStrategy.PRIORITY,
            metadata={
                "priorities": {
                    getattr(r, "agent_name", "unknown"): get_priority(r)
                    for r in results
                },
            },
        )

    # ── Estrategia MERGE ────────────────────────────────────────────────────

    def _resolve_merge(
        self, results: List[Any], context: Dict[str, Any]
    ) -> ConflictResolution:
        """
        Combina los outputs de todos los agentes en una respuesta unificada.
        El primer agente (o el de mayor prioridad) es el líder del merge.
        """
        # Ordenar por prioridad si tenemos swarm
        if self.swarm is not None:
            priority_map = {
                role: idx
                for idx, role in enumerate(self.config.priority_order)
            }
            default_priority = len(self.config.priority_order)

            def get_priority(r: Any) -> int:
                agent_name = getattr(r, "agent_name", "unknown")
                agent = self.swarm.get_agent(agent_name)
                if agent is not None:
                    role_value = getattr(agent.config, "role", None)
                    if role_value is not None:
                        role_str = role_value.value if hasattr(role_value, "value") else str(role_value)
                        return priority_map.get(role_str, default_priority)
                return default_priority

            sorted_results = sorted(results, key=get_priority)
        else:
            sorted_results = results

        # Combinar outputs
        parts = []
        for r in sorted_results:
            agent_name = getattr(r, "agent_name", "unknown")
            output = getattr(r, "output", "")
            parts.append(f"**{agent_name}**: {output}")

        merged_output = self.config.merge_separator.join(parts)

        winner_name = getattr(sorted_results[0], "agent_name", "unknown")
        dissenting = []  # En MERGE, todos contribuyen, no hay disidentes

        # Confianza: basada en cuántos agentes contribuyeron
        confidence = min(1.0, len(sorted_results) / 3.0)  # Máximo con 3+ agentes

        return ConflictResolution(
            winner_agent=winner_name,
            consensus_output=merged_output,
            confidence=confidence,
            dissenting_agents=dissenting,
            resolution_strategy=ResolutionStrategy.MERGE,
            metadata={
                "merged_agents": [
                    getattr(r, "agent_name", "unknown") for r in sorted_results
                ],
            },
        )

    # ── Estrategia LLM_JUDGE ──────────────────────────────────────────────

    def _resolve_llm_judge(
        self, results: List[Any], context: Dict[str, Any]
    ) -> ConflictResolution:
        """
        Usa un LLM para juzgar y seleccionar la mejor respuesta entre
        los resultados contradictorios.
        """
        # Construir prompt para el juez
        candidates = []
        for idx, r in enumerate(results, 1):
            agent_name = getattr(r, "agent_name", f"agent_{idx}")
            output = getattr(r, "output", "")
            candidates.append(f"[Agente {idx}: {agent_name}]\n{output}")

        candidates_text = "\n\n".join(candidates)
        context_text = "\n".join(f"- {k}: {v}" for k, v in context.items()) if context else "(sin contexto)"

        prompt = (
            "Eres un juez imparcial. Se te presentan varias respuestas de diferentes agentes "
            "a la misma consulta. Selecciona la mejor respuesta basándote en exactitud, "
            "completitud y relevancia.\n\n"
            f"Contexto de la consulta:\n{context_text}\n\n"
            f"Candidatos:\n{candidates_text}\n\n"
            "Responde SOLO con el número del agente ganador (1, 2, 3, etc.) "
            "seguido de una breve justificación en una línea."
        )

        llm_output = self._call_llm(prompt)

        # Parsear la respuesta del LLM para encontrar el ganador
        winner_idx = 0  # Default al primero
        try:
            # Buscar un número al inicio de la respuesta
            import re
            match = re.search(r"^\s*(\d+)", llm_output.strip())
            if match:
                winner_idx = int(match.group(1)) - 1
                winner_idx = max(0, min(winner_idx, len(results) - 1))
        except (ValueError, IndexError):
            logger.debug("No se pudo parsear la respuesta del juez LLM: %s", llm_output[:100])

        winner = results[winner_idx]
        winner_name = getattr(winner, "agent_name", "unknown")

        dissenting = [
            getattr(r, "agent_name", "unknown")
            for r in results
            if r is not winner
        ]

        # Confianza: moderada dado que el LLM podría equivocarse
        confidence = 0.7

        return ConflictResolution(
            winner_agent=winner_name,
            consensus_output=getattr(winner, "output", ""),
            confidence=confidence,
            dissenting_agents=dissenting,
            resolution_strategy=ResolutionStrategy.LLM_JUDGE,
            metadata={
                "llm_judge_response": llm_output[:500],
                "winner_index": winner_idx,
            },
        )

    # ── Historial de conflictos ────────────────────────────────────────────

    def _record_conflict(
        self,
        results: List[Any],
        resolution: ConflictResolution,
        strategy: ResolutionStrategy,
    ) -> None:
        """Registra un conflicto resuelto en el historial."""
        entry = {
            "agents": [getattr(r, "agent_name", "unknown") for r in results],
            "strategy": strategy.value,
            "winner": resolution.winner_agent,
            "confidence": resolution.confidence,
            "dissenting_count": len(resolution.dissenting_agents),
        }

        self._history.append(entry)

        # Limitar tamaño del historial
        if len(self._history) > self.config.max_history:
            self._history = self._history[-self.config.max_history :]

    def get_conflict_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de conflictos resueltos.

        Args:
            limit: Número máximo de entradas a retornar.

        Returns:
            Lista de diccionarios con el historial de conflictos.
        """
        return self._history[-limit:]

    def get_conflict_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de conflictos resueltos."""
        if not self._history:
            return {
                "total_conflicts": 0,
                "by_strategy": {},
                "avg_confidence": 0.0,
            }

        by_strategy: Dict[str, int] = {}
        total_confidence = 0.0

        for entry in self._history:
            strategy = entry.get("strategy", "unknown")
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
            total_confidence += entry.get("confidence", 0.0)

        return {
            "total_conflicts": len(self._history),
            "by_strategy": by_strategy,
            "avg_confidence": round(total_confidence / len(self._history), 3),
            "most_common_winner": self._most_common_winner(),
        }

    def _most_common_winner(self) -> str:
        """Encuentra el agente que más frecuentemente gana conflictos."""
        from collections import Counter

        winners = [e.get("winner", "unknown") for e in self._history]
        if not winners:
            return "none"
        return Counter(winners).most_common(1)[0][0]

    # ── Utilidades ──────────────────────────────────────────────────────────

    @staticmethod
    def _output_fingerprint(output: Any) -> str:
        """
        Genera una huella digital (fingerprint) del output para agrupamiento.

        Usa un hash del output normalizado para comparar similitudes.
        """
        text = str(output).strip().lower()
        # Normalizar espacios en blanco
        text = " ".join(text.split())
        # Hash para comparación rápida
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    def _call_llm(self, prompt: str) -> str:
        """
        Realiza una llamada al LLM para la estrategia LLM_JUDGE.

        Usa la configuración del ConflictConfig para el endpoint.
        """
        import httpx

        try:
            headers = {"Content-Type": "application/json"}
            if self.config.llm_api_key:
                headers["Authorization"] = f"Bearer {self.config.llm_api_key}"

            payload = {
                "model": self.config.llm_model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 256,
                "temperature": 0.1,  # Baja temperatura para respuestas deterministas del juez
            }

            resp = httpx.post(
                f"{self.config.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

        except Exception as exc:
            logger.error("LLM judge call failed: %s", exc)
            return ""


# ── Singleton ──────────────────────────────────────────────────────────────────

_conflict_resolver: Optional[ConflictResolver] = None


def get_conflict_resolver(swarm: Any = None, config: ConflictConfig | None = None) -> ConflictResolver:
    """Obtiene instancia singleton del ConflictResolver."""
    global _conflict_resolver
    if _conflict_resolver is None:
        if swarm is None:
            try:
                from .swarm import get_swarm
                swarm = get_swarm()
            except ImportError:
                logger.warning("Swarm not available for ConflictResolver")
                swarm = None
        _conflict_resolver = ConflictResolver(swarm, config)
    return _conflict_resolver