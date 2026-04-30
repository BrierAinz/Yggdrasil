"""
Lilith v5.2 — MacroLearner
==========================

Sistema de aprendizaje de macros que detecta patrones de uso
automáticamente desde el historial de operaciones PC.

Features:
- Análisis de episodios recientes
- Detección de secuencias repetidas
- Generación de sugerencias de macros
- Nombres automáticos inteligentes
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.pattern_detector import Operation, Pattern, PatternDetector

logger = logging.getLogger("lilith.macro.learner")


@dataclass
class MacroSuggestion:
    """Sugerencia de macro generada desde un patrón."""

    name: str
    description: str
    operations: List[Dict[str, Any]]
    params: Dict[str, Dict[str, Any]]
    frequency: int
    last_seen: float
    confidence: float
    source_pattern: Optional[Pattern] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            "name": self.name,
            "description": self.description,
            "operations": self.operations,
            "params": self.params,
            "frequency": self.frequency,
            "last_seen": self.last_seen,
            "confidence": self.confidence,
        }


@dataclass
class Episode:
    """Episodio de operación PC (simplificado para learning)."""

    id: str
    user_id: str
    tool: str  # 'pc_operation', 'pc_operation_batch'
    operation: str
    params: Dict[str, Any]
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


class MacroLearner:
    """
    Aprende macros desde patrones de uso detectados en el historial.

    Estrategias de detección:
    1. Temporal: Secuencias ejecutadas en ventana de tiempo
    2. Structural: Operaciones con estructura similar
    3. Frequency: Comandos ejecutados N+ veces
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        min_frequency: int = 3,
        window_hours: int = 168,  # 1 semana
    ):
        """
        Inicializa el learner.

        Args:
            similarity_threshold: Umbral de similitud para clustering
            min_frequency: Mínimo de ocurrencias para sugerir macro
            window_hours: Ventana de tiempo para análisis
        """
        self.similarity_threshold = similarity_threshold
        self.min_frequency = min_frequency
        self.window_hours = window_hours
        self.pattern_detector = PatternDetector(similarity_threshold)

    async def analyze_recent_history(
        self,
        episodes: List[Episode],
        user_id: Optional[str] = None,
    ) -> List[MacroSuggestion]:
        """
        Analiza historial de episodios y sugiere macros.

        Args:
            episodes: Lista de episodios recientes
            user_id: Filtrar por usuario específico (None = todos)

        Returns:
            Lista de sugerencias ordenadas por confianza
        """
        # Filtrar episodios relevantes
        filtered = self._filter_episodes(episodes, user_id)
        logger.info("[MacroLearner] Analizando %d episodios", len(filtered))

        if len(filtered) < self.min_frequency:
            logger.debug("[MacroLearner] Insuficientes episodios para análisis")
            return []

        # Extraer secuencias de operaciones
        sequences = self._extract_sequences(filtered)
        logger.debug("[MacroLearner] Extraídas %d secuencias", len(sequences))

        if not sequences:
            return []

        # Detectar patrones
        patterns = self.pattern_detector.find_patterns(
            sequences,
            min_frequency=self.min_frequency,
        )

        # Convertir patrones a sugerencias
        suggestions = []
        for pattern in patterns:
            suggestion = self._pattern_to_suggestion(pattern)
            if suggestion:
                suggestions.append(suggestion)

        # Ordenar por confianza
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        logger.info("[MacroLearner] Generadas %d sugerencias", len(suggestions))
        return suggestions

    def _filter_episodes(
        self,
        episodes: List[Episode],
        user_id: Optional[str] = None,
    ) -> List[Episode]:
        """
        Filtra episodios por tiempo y tipo.

        Args:
            episodes: Lista de episodios
            user_id: Filtrar por usuario

        Returns:
            Episodios filtrados
        """
        cutoff_time = time.time() - (self.window_hours * 3600)
        relevant_tools = {"pc_operation", "pc_operation_batch", "pc_agent"}

        filtered = []
        for ep in episodes:
            # Filtrar por tiempo
            if ep.timestamp < cutoff_time:
                continue

            # Filtrar por usuario
            if user_id and ep.user_id != user_id:
                continue

            # Filtrar por tipo de tool
            if ep.tool not in relevant_tools:
                continue

            filtered.append(ep)

        return filtered

    def _extract_sequences(
        self,
        episodes: List[Episode],
        time_gap_seconds: float = 300.0,  # 5 minutos
    ) -> List[List[Operation]]:
        """
        Extrae secuencias de operaciones agrupadas temporalmente.

        Args:
            episodes: Episodios filtrados
            time_gap_seconds: Gap máximo entre operaciones de una secuencia

        Returns:
            Lista de secuencias (cada secuencia es lista de operaciones)
        """
        if not episodes:
            return []

        # Ordenar por timestamp
        sorted_eps = sorted(episodes, key=lambda e: e.timestamp)

        sequences = []
        current_sequence = []
        last_timestamp = 0.0

        for ep in sorted_eps:
            # Nueva secuencia si hay gap grande
            if current_sequence and (ep.timestamp - last_timestamp) > time_gap_seconds:
                if len(current_sequence) >= 2:  # Mínimo 2 operaciones
                    sequences.append(current_sequence)
                current_sequence = []

            # Crear operación
            op = Operation(
                operation=ep.operation,
                params=ep.params.copy(),
                timestamp=ep.timestamp,
            )
            current_sequence.append(op)
            last_timestamp = ep.timestamp

        # Agregar última secuencia
        if len(current_sequence) >= 2:
            sequences.append(current_sequence)

        return sequences

    def _pattern_to_suggestion(self, pattern: Pattern) -> Optional[MacroSuggestion]:
        """
        Convierte un patrón detectado en una sugerencia de macro.
        """
        if not pattern.operations:
            return None

        # Generar nombre
        name = self._generate_macro_name(pattern)

        # Generar descripción
        description = self._generate_description(pattern)

        # Extraer parámetros
        params = pattern.estimate_params()

        # Crear operaciones template
        operations = []
        for op in pattern.operations:
            op_template = {
                "operation": op.operation,
            }
            # Parámetros con placeholders para variables
            for key, value in op.params.items():
                param_key = f"{op.operation}_{key}"
                if param_key in params:
                    op_template[key] = f"{{{param_key}}}"
                else:
                    op_template[key] = value
            operations.append(op_template)

        return MacroSuggestion(
            name=name,
            description=description,
            operations=operations,
            params=params,
            frequency=pattern.count,
            last_seen=pattern.last_timestamp,
            confidence=pattern.confidence,
            source_pattern=pattern,
        )

    def _generate_macro_name(self, pattern: Pattern) -> str:
        """
        Genera nombre automático para macro basado en operaciones.
        """
        if not pattern.operations:
            return "macro_custom"

        # Contar tipos de operaciones
        op_counts: Dict[str, int] = {}
        for op in pattern.operations:
            op_counts[op.operation] = op_counts.get(op.operation, 0) + 1

        # Construir nombre descriptivo
        parts = []

        # Operación principal (la más frecuente)
        main_op = max(op_counts.items(), key=lambda x: x[1])[0]
        op_names = {
            "mkdir": "setup",
            "copy": "backup",
            "move": "organize",
            "delete": "cleanup",
            "exec": "run",
            "write_file": "create",
        }
        parts.append(op_names.get(main_op, main_op))

        # Agregar contexto si hay operaciones secundarias
        if len(op_counts) > 1:
            secondary_ops = [op for op in op_counts.keys() if op != main_op]
            if secondary_ops:
                parts.append(op_names.get(secondary_ops[0], secondary_ops[0]))

        # Agregar timestamp único si hay colisión potencial
        name = "_".join(parts)

        # Si es muy genérico, agregar identificador único
        if name in ("setup", "backup", "run"):
            name = f"{name}_auto_{int(time.time()) % 10000}"

        return name

    def _generate_description(self, pattern: Pattern) -> str:
        """
        Genera descripción legible para el patrón.
        """
        if not pattern.operations:
            return "Macro automática generada desde uso frecuente"

        op_descriptions = {
            "mkdir": "crear carpetas",
            "copy": "copiar archivos",
            "move": "mover archivos",
            "delete": "eliminar archivos",
            "exec": "ejecutar comandos",
            "write_file": "crear archivos",
        }

        # Contar operaciones
        op_counts: Dict[str, int] = {}
        for op in pattern.operations:
            op_counts[op.operation] = op_counts.get(op.operation, 0) + 1

        # Construir descripción
        desc_parts = []
        for op, count in op_counts.items():
            desc = op_descriptions.get(op, f"operaciones {op}")
            if count > 1:
                desc_parts.append(f"{count}x {desc}")
            else:
                desc_parts.append(desc)

        return f"Automatiza: {', '.join(desc_parts)}"

    def get_suggestion_by_name(
        self,
        suggestions: List[MacroSuggestion],
        name: str,
    ) -> Optional[MacroSuggestion]:
        """
        Busca una sugerencia por nombre.
        """
        for suggestion in suggestions:
            if suggestion.name == name:
                return suggestion
        return None

    def filter_high_confidence(
        self,
        suggestions: List[MacroSuggestion],
        threshold: float = 0.7,
    ) -> List[MacroSuggestion]:
        """
        Filtra sugerencias por confianza mínima.
        """
        return [s for s in suggestions if s.confidence >= threshold]


class EpisodeStore:
    """
    Store simplificado para episodios de PC operations.
    (Wrapper sobre el sistema de memoria existente)
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.episodes: List[Episode] = []

    def add_episode(
        self,
        user_id: str,
        tool: str,
        operation: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Agrega un nuevo episodio."""
        episode = Episode(
            id=f"ep_{int(time.time() * 1000)}",
            user_id=user_id,
            tool=tool,
            operation=operation,
            params=params.copy(),
            timestamp=time.time(),
            context=context or {},
        )
        self.episodes.append(episode)
        return episode

    def get_recent(
        self,
        user_id: Optional[str] = None,
        hours: int = 168,
        tool_filter: Optional[Set[str]] = None,
    ) -> List[Episode]:
        """Obtiene episodios recientes."""
        cutoff = time.time() - (hours * 3600)

        filtered = []
        for ep in self.episodes:
            if ep.timestamp < cutoff:
                continue
            if user_id and ep.user_id != user_id:
                continue
            if tool_filter and ep.tool not in tool_filter:
                continue
            filtered.append(ep)

        return sorted(filtered, key=lambda e: e.timestamp)

    def clear_old(self, hours: int = 720) -> int:  # 30 días por defecto
        """Limpia episodios antiguos. Retorna cantidad eliminada."""
        cutoff = time.time() - (hours * 3600)
        old_count = len(self.episodes)
        self.episodes = [ep for ep in self.episodes if ep.timestamp >= cutoff]
        return old_count - len(self.episodes)


# Singleton
def create_macro_learner(
    similarity_threshold: float = 0.8,
    min_frequency: int = 3,
) -> MacroLearner:
    """Factory para crear MacroLearner con configuración por defecto."""
    return MacroLearner(
        similarity_threshold=similarity_threshold,
        min_frequency=min_frequency,
    )
