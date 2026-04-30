"""
Pattern Discovery - Detección automática de patrones de uso

v5.0-Fase4B: Analiza comportamientos, detecta patrones recurrentes
y sugiere automatizaciones.
"""
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("lilith.learning.patterns")


class PatternType(Enum):
    """Tipos de patrones detectables."""

    SEQUENCE = "sequence"  # Secuencia de acciones
    TEMPORAL = "temporal"  # Patrón temporal (horario, día de semana)
    FREQUENCY = "frequency"  # Alta frecuencia de uso
    CONDITIONAL = "conditional"  # Patrón condicional (si X entonces Y)
    WORKFLOW = "workflow"  # Workflow completo sugerido


class PatternConfidence(Enum):
    """Nivel de confianza del patrón."""

    LOW = "low"  # 50-70%
    MEDIUM = "medium"  # 70-85%
    HIGH = "high"  # 85-95%
    CERTAIN = "certain"  # 95%+


@dataclass
class Action:
    """Acción individual en un patrón."""

    type: str  # tool, agent, workflow, api
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Pattern:
    """Patrón detectado."""

    id: str
    type: PatternType
    name: str
    description: str
    actions: List[Action]
    confidence: PatternConfidence
    frequency: int  # Cuántas veces se ha observado
    first_seen: str
    last_seen: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    suggested_automation: Optional[Dict[str, Any]] = None


@dataclass
class UsageMetrics:
    """Métricas de uso para análisis."""

    total_actions: int = 0
    unique_actions: Set[str] = field(default_factory=set)
    hourly_distribution: Dict[int, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    daily_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    action_sequences: List[List[str]] = field(default_factory=list)
    common_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class PatternDiscovery:
    """
    Motor de descubrimiento de patrones.

    Features:
    - Detección de secuencias frecuentes
    - Análisis temporal de uso
    - Identificación de workflows implícitos
    - Sugerencias de automatización
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.patterns: Dict[str, Pattern] = {}
        self.user_actions: Dict[str, List[Action]] = defaultdict(list)
        self.session_actions: Dict[str, List[Action]] = defaultdict(list)
        self.usage_metrics: Dict[str, UsageMetrics] = defaultdict(UsageMetrics)
        self.min_sequence_length = 3
        self.min_frequency = 3
        self.temporal_window_minutes = 30
        self.storage_path = storage_path or Path("Data/learning")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        self._load_data()

    async def record_action(
        self,
        user_id: str,
        action_type: str,
        action_name: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ):
        """Registra una acción para análisis."""
        action = Action(
            type=action_type,
            name=action_name,
            params=params or {},
            context=context or {},
        )

        async with self.lock:
            self.user_actions[user_id].append(action)

            if session_id:
                self.session_actions[session_id].append(action)

            # Actualizar métricas
            metrics = self.usage_metrics[user_id]
            metrics.total_actions += 1
            metrics.unique_actions.add(f"{action_type}:{action_name}")

            hour = datetime.utcnow().hour
            day = datetime.utcnow().strftime("%A")
            metrics.hourly_distribution[hour] += 1
            metrics.daily_distribution[day] += 1

            # Mantener solo últimas 1000 acciones por usuario
            if len(self.user_actions[user_id]) > 1000:
                self.user_actions[user_id] = self.user_actions[user_id][-1000:]

        # Ejecutar análisis periódico
        if metrics.total_actions % 50 == 0:
            await self.analyze_user_patterns(user_id)

        self._save_data()

    async def analyze_user_patterns(self, user_id: str) -> List[Pattern]:
        """Analiza patrones para un usuario específico."""
        actions = self.user_actions.get(user_id, [])
        if len(actions) < self.min_sequence_length:
            return []

        patterns = []

        # Detectar secuencias frecuentes
        sequence_patterns = await self._detect_sequences(user_id, actions)
        patterns.extend(sequence_patterns)

        # Detectar patrones temporales
        temporal_patterns = await self._detect_temporal_patterns(user_id, actions)
        patterns.extend(temporal_patterns)

        # Detectar patrones condicionales
        conditional_patterns = await self._detect_conditional_patterns(user_id, actions)
        patterns.extend(conditional_patterns)

        # Almacenar patrones detectados
        async with self.lock:
            for pattern in patterns:
                self.patterns[pattern.id] = pattern

        return patterns

    async def _detect_sequences(
        self, user_id: str, actions: List[Action]
    ) -> List[Pattern]:
        """Detecta secuencias de acciones frecuentes."""
        patterns = []

        # Encontrar secuencias de 3-5 acciones que se repiten
        for length in range(5, self.min_sequence_length - 1, -1):
            sequences = self._extract_sequences(actions, length)
            frequent = self._find_frequent_sequences(sequences)

            for seq, count in frequent.items():
                if count >= self.min_frequency:
                    pattern_id = f"seq_{user_id}_{hash(seq) % 10000}"

                    # Verificar si ya existe
                    if pattern_id in self.patterns:
                        # Actualizar frecuencia
                        self.patterns[pattern_id].frequency = count
                        self.patterns[
                            pattern_id
                        ].last_seen = datetime.utcnow().isoformat()
                        continue

                    # Crear nuevo patrón
                    seq_actions = [
                        Action(type=s.split(":")[0], name=s.split(":")[1]) for s in seq
                    ]

                    confidence = self._calculate_confidence(count, len(actions))

                    pattern = Pattern(
                        id=pattern_id,
                        type=PatternType.SEQUENCE,
                        name=f"Secuencia: {' → '.join(seq)}",
                        description=f"Secuencia de {length} acciones ejecutada {count} veces",
                        actions=seq_actions,
                        confidence=confidence,
                        frequency=count,
                        first_seen=datetime.utcnow().isoformat(),
                        last_seen=datetime.utcnow().isoformat(),
                        user_id=user_id,
                        suggested_automation={
                            "type": "workflow",
                            "actions": [
                                {"type": a.type, "name": a.name} for a in seq_actions
                            ],
                            "auto_trigger": False,
                        },
                    )

                    patterns.append(pattern)

        return patterns

    async def _detect_temporal_patterns(
        self, user_id: str, actions: List[Action]
    ) -> List[Pattern]:
        """Detecta patrones basados en tiempo."""
        patterns = []
        metrics = self.usage_metrics[user_id]

        # Detectar horas pico
        peak_hours = [
            hour
            for hour, count in metrics.hourly_distribution.items()
            if count > metrics.total_actions * 0.15  # Más del 15% del uso
        ]

        if len(peak_hours) >= 2:
            pattern_id = f"tmp_{user_id}_peak_hours"

            if pattern_id not in self.patterns:
                pattern = Pattern(
                    id=pattern_id,
                    type=PatternType.TEMPORAL,
                    name=f"Horas de actividad: {', '.join(map(str, peak_hours))}h",
                    description=f"Mayor actividad detectada entre las {min(peak_hours)}:00 y {max(peak_hours)}:00",
                    actions=[],
                    confidence=PatternConfidence.MEDIUM,
                    frequency=sum(metrics.hourly_distribution[h] for h in peak_hours),
                    first_seen=datetime.utcnow().isoformat(),
                    last_seen=datetime.utcnow().isoformat(),
                    user_id=user_id,
                    metadata={"peak_hours": peak_hours},
                )

                patterns.append(pattern)

        # Detectar día preferido
        if metrics.daily_distribution:
            peak_day = max(metrics.daily_distribution.items(), key=lambda x: x[1])
            if peak_day[1] > metrics.total_actions * 0.25:  # Más del 25% en un día
                pattern_id = f"tmp_{user_id}_peak_day"

                if pattern_id not in self.patterns:
                    pattern = Pattern(
                        id=pattern_id,
                        type=PatternType.TEMPORAL,
                        name=f"Día preferido: {peak_day[0]}",
                        description=f"Mayor actividad los {peak_day[0]} con {peak_day[1]} acciones",
                        actions=[],
                        confidence=PatternConfidence.MEDIUM,
                        frequency=peak_day[1],
                        first_seen=datetime.utcnow().isoformat(),
                        last_seen=datetime.utcnow().isoformat(),
                        user_id=user_id,
                        metadata={"peak_day": peak_day[0]},
                    )

                    patterns.append(pattern)

        return patterns

    async def _detect_conditional_patterns(
        self, user_id: str, actions: List[Action]
    ) -> List[Pattern]:
        """Detecta patrones condicionales (si X entonces Y)."""
        patterns = []

        # Buscar correlaciones entre acciones
        correlations = self._find_correlations(actions)

        for (trigger, result), confidence_score in correlations.items():
            if confidence_score >= 0.7:  # 70% de confianza mínima
                pattern_id = f"cond_{user_id}_{hash(trigger + result) % 10000}"

                if pattern_id not in self.patterns:
                    conf = (
                        PatternConfidence.MEDIUM
                        if confidence_score < 0.85
                        else PatternConfidence.HIGH
                    )

                    pattern = Pattern(
                        id=pattern_id,
                        type=PatternType.CONDITIONAL,
                        name=f"Si {trigger} → entonces {result}",
                        description=f"Cuando se ejecuta '{trigger}', el {confidence_score*100:.0f}% de las veces sigue '{result}'",
                        actions=[
                            Action(type="trigger", name=trigger),
                            Action(type="result", name=result),
                        ],
                        confidence=conf,
                        frequency=int(confidence_score * 100),
                        first_seen=datetime.utcnow().isoformat(),
                        last_seen=datetime.utcnow().isoformat(),
                        user_id=user_id,
                        suggested_automation={
                            "type": "conditional_workflow",
                            "trigger": trigger,
                            "action": result,
                            "confidence": confidence_score,
                        },
                    )

                    patterns.append(pattern)

        return patterns

    def _extract_sequences(
        self, actions: List[Action], length: int
    ) -> List[Tuple[str, ...]]:
        """Extrae todas las secuencias de longitud dada."""
        sequences = []
        for i in range(len(actions) - length + 1):
            seq = tuple(f"{a.type}:{a.name}" for a in actions[i : i + length])
            sequences.append(seq)
        return sequences

    def _find_frequent_sequences(
        self, sequences: List[Tuple[str, ...]]
    ) -> Dict[Tuple[str, ...], int]:
        """Encuentra secuencias que se repiten."""
        counts = defaultdict(int)
        for seq in sequences:
            counts[seq] += 1
        return {
            seq: count for seq, count in counts.items() if count >= self.min_frequency
        }

    def _find_correlations(self, actions: List[Action]) -> Dict[Tuple[str, str], float]:
        """Encuentra correlaciones entre acciones consecutivas."""
        correlations = defaultdict(lambda: {"count": 0, "total": 0})

        for i in range(len(actions) - 1):
            trigger = f"{actions[i].type}:{actions[i].name}"
            result = f"{actions[i+1].type}:{actions[i+1].name}"

            correlations[trigger]["total"] += 1
            correlations[(trigger, result)]["count"] += 1

        # Calcular confianza
        results = {}
        for (trigger, result), data in correlations.items():
            if isinstance(trigger, str) and isinstance(result, str):
                trigger_total = correlations[trigger]["total"]
                if trigger_total > 0:
                    confidence = data["count"] / trigger_total
                    if confidence >= 0.5:  # Mínimo 50%
                        results[(trigger, result)] = confidence

        return results

    def _calculate_confidence(
        self, frequency: int, total_actions: int
    ) -> PatternConfidence:
        """Calcula el nivel de confianza basado en frecuencia."""
        ratio = frequency / max(total_actions, 100)

        if ratio >= 0.95:
            return PatternConfidence.CERTAIN
        elif ratio >= 0.85:
            return PatternConfidence.HIGH
        elif ratio >= 0.70:
            return PatternConfidence.MEDIUM
        else:
            return PatternConfidence.LOW

    def get_patterns_for_user(
        self,
        user_id: str,
        pattern_type: Optional[PatternType] = None,
        min_confidence: Optional[PatternConfidence] = None,
    ) -> List[Pattern]:
        """Obtiene patrones detectados para un usuario."""
        user_patterns = [p for p in self.patterns.values() if p.user_id == user_id]

        if pattern_type:
            user_patterns = [p for p in user_patterns if p.type == pattern_type]

        if min_confidence:
            confidence_order = {
                PatternConfidence.CERTAIN: 4,
                PatternConfidence.HIGH: 3,
                PatternConfidence.MEDIUM: 2,
                PatternConfidence.LOW: 1,
            }
            min_level = confidence_order[min_confidence]
            user_patterns = [
                p for p in user_patterns if confidence_order[p.confidence] >= min_level
            ]

        # Ordenar por confianza y frecuencia
        user_patterns.sort(
            key=lambda p: (p.confidence.value, p.frequency), reverse=True
        )

        return user_patterns

    def get_suggested_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """Genera workflows sugeridos basados en patrones."""
        patterns = self.get_patterns_for_user(
            user_id,
            pattern_type=PatternType.SEQUENCE,
            min_confidence=PatternConfidence.MEDIUM,
        )

        suggestions = []
        for pattern in patterns[:5]:  # Top 5
            if pattern.suggested_automation:
                suggestions.append(
                    {
                        "pattern_id": pattern.id,
                        "name": pattern.name,
                        "description": pattern.description,
                        "confidence": pattern.confidence.value,
                        "frequency": pattern.frequency,
                        "automation": pattern.suggested_automation,
                        "estimated_time_saved": self._estimate_time_saved(pattern),
                    }
                )

        return suggestions

    def _estimate_time_saved(self, pattern: Pattern) -> str:
        """Estima el tiempo que se ahorraría automatizando el patrón."""
        if not pattern.actions:
            return "Desconocido"

        # Asumir ~30 segundos por acción manual
        seconds_per_action = 30
        total_seconds = len(pattern.actions) * seconds_per_action

        if pattern.frequency > 10:
            monthly_saves = (pattern.frequency / 30) * total_seconds
            if monthly_saves > 3600:
                return f"{monthly_saves/3600:.1f} horas/mes"
            else:
                return f"{monthly_saves/60:.0f} minutos/mes"
        else:
            return f"{total_seconds} segundos por ejecución"

    async def generate_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """Genera insights personalizados basados en patrones."""
        insights = []
        metrics = self.usage_metrics[user_id]

        if not metrics.total_actions:
            return insights

        # Insight: Acciones más usadas
        if metrics.unique_actions:
            top_actions = sorted(
                metrics.unique_actions,
                key=lambda a: sum(
                    1
                    for act in self.user_actions[user_id]
                    if f"{act.type}:{act.name}" == a
                ),
                reverse=True,
            )[:5]

            insights.append(
                {
                    "type": "top_actions",
                    "title": "Acciones más utilizadas",
                    "description": f"Tus top {len(top_actions)} acciones representan la mayoría de tu uso",
                    "data": top_actions,
                }
            )

        # Insight: Horario óptimo
        if metrics.hourly_distribution:
            peak_hour = max(metrics.hourly_distribution.items(), key=lambda x: x[1])
            insights.append(
                {
                    "type": "peak_time",
                    "title": "Momento más productivo",
                    "description": f"Tu hora más activa es las {peak_hour[0]}:00 con {peak_hour[1]} acciones",
                    "data": {"hour": peak_hour[0], "actions": peak_hour[1]},
                }
            )

        # Insight: Patrones detectados
        patterns = self.get_patterns_for_user(
            user_id, min_confidence=PatternConfidence.MEDIUM
        )
        if patterns:
            insights.append(
                {
                    "type": "detected_patterns",
                    "title": f"{len(patterns)} patrones detectados",
                    "description": "Hemos identificado patrones en tu forma de trabajar que podrían automatizarse",
                    "data": [p.name for p in patterns[:3]],
                }
            )

        # Insight: Oportunidades de automatización
        suggestions = self.get_suggested_workflows(user_id)
        if suggestions:
            total_saved = sum(
                int(s.get("estimated_time_saved", "0").split()[0] or 0)
                for s in suggestions
                if "minutos" in s.get("estimated_time_saved", "")
            )
            if total_saved > 0:
                insights.append(
                    {
                        "type": "automation_opportunity",
                        "title": "Oportunidad de automatización",
                        "description": f"Podrías ahorrar aproximadamente {total_saved} minutos al mes automatizando patrones comunes",
                        "data": {
                            "suggested_workflows": len(suggestions),
                            "estimated_savings": total_saved,
                        },
                    }
                )

        return insights

    def _save_data(self):
        """Guarda datos en disco."""
        try:
            data = {
                "patterns": {
                    k: {
                        "id": v.id,
                        "type": v.type.value,
                        "name": v.name,
                        "description": v.description,
                        "actions": [asdict(a) for a in v.actions],
                        "confidence": v.confidence.value,
                        "frequency": v.frequency,
                        "first_seen": v.first_seen,
                        "last_seen": v.last_seen,
                        "user_id": v.user_id,
                        "session_id": v.session_id,
                        "metadata": v.metadata,
                        "suggested_automation": v.suggested_automation,
                    }
                    for k, v in self.patterns.items()
                },
                "usage_metrics": {
                    k: {
                        "total_actions": v.total_actions,
                        "unique_actions": list(v.unique_actions),
                        "hourly_distribution": dict(v.hourly_distribution),
                        "daily_distribution": dict(v.daily_distribution),
                    }
                    for k, v in self.usage_metrics.items()
                },
            }

            with open(self.storage_path / "patterns.json", "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _load_data(self):
        """Carga datos desde disco."""
        try:
            file_path = self.storage_path / "patterns.json"
            if not file_path.exists():
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            for pid, pdata in data.get("patterns", {}).items():
                pattern = Pattern(
                    id=pdata["id"],
                    type=PatternType(pdata["type"]),
                    name=pdata["name"],
                    description=pdata["description"],
                    actions=[Action(**a) for a in pdata.get("actions", [])],
                    confidence=PatternConfidence(pdata["confidence"]),
                    frequency=pdata["frequency"],
                    first_seen=pdata["first_seen"],
                    last_seen=pdata["last_seen"],
                    user_id=pdata.get("user_id"),
                    session_id=pdata.get("session_id"),
                    metadata=pdata.get("metadata", {}),
                    suggested_automation=pdata.get("suggested_automation"),
                )
                self.patterns[pid] = pattern

        except Exception as e:
            logger.error(f"Error loading patterns: {e}")


# Singleton
_discovery_instance: Optional[PatternDiscovery] = None


def get_pattern_discovery() -> PatternDiscovery:
    """Obtiene el singleton de PatternDiscovery."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = PatternDiscovery()
    return _discovery_instance
