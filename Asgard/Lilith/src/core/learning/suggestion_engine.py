"""
Suggestion Engine - Motor de sugerencias inteligentes

v5.0-Fase4B: Genera sugerencias proactivas basadas en patrones, contexto
y objetivos del usuario.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.learning.pattern_discovery import PatternConfidence, get_pattern_discovery

logger = logging.getLogger("lilith.learning.suggestions")


class SuggestionType(Enum):
    """Tipos de sugerencias."""

    WORKFLOW = "workflow"  # Crear workflow automatizado
    SHORTCUT = "shortcut"  # Atajo de teclado/comando
    OPTIMIZATION = "optimization"  # Optimizar proceso existente
    LEARNING = "learning"  # Recurso educativo
    INTEGRATION = "integration"  # Integrar con otro servicio
    SCHEDULE = "schedule"  # Programar tarea recurrente


class SuggestionPriority(Enum):
    """Prioridad de sugerencia."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Suggestion:
    """Sugerencia individual."""

    id: str
    type: SuggestionType
    title: str
    description: str
    priority: SuggestionPriority
    confidence: float  # 0-1
    user_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    action: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    dismissed: bool = False
    applied: bool = False
    applied_at: Optional[str] = None
    feedback: Optional[str] = None


class SuggestionEngine:
    """
    Motor de sugerencias inteligentes.

    Features:
    - Genera sugerencias basadas en patrones detectados
    - Prioriza según impacto y contexto
    - Aprende del feedback del usuario
    - Sugerencias contextuales en tiempo real
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.suggestions: Dict[str, Suggestion] = {}
        self.user_suggestions: Dict[str, List[str]] = {}  # user_id -> suggestion_ids
        self.user_feedback: Dict[str, Dict[str, Any]] = {}  # suggestion_id -> feedback
        self.storage_path = storage_path or Path("Data/learning")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        self._load_data()

    async def generate_suggestions(self, user_id: str) -> List[Suggestion]:
        """Genera sugerencias personalizadas para un usuario."""
        suggestions = []
        discovery = get_pattern_discovery()

        # 1. Sugerencias de workflow basadas en patrones
        workflow_suggestions = await self._generate_workflow_suggestions(
            user_id, discovery
        )
        suggestions.extend(workflow_suggestions)

        # 2. Sugerencias de optimización
        optimization_suggestions = await self._generate_optimization_suggestions(
            user_id, discovery
        )
        suggestions.extend(optimization_suggestions)

        # 3. Sugerencias de programación
        schedule_suggestions = await self._generate_schedule_suggestions(
            user_id, discovery
        )
        suggestions.extend(schedule_suggestions)

        # 4. Sugerencias de integración
        integration_suggestions = await self._generate_integration_suggestions(
            user_id, discovery
        )
        suggestions.extend(integration_suggestions)

        # Filtrar y almacenar nuevas sugerencias
        async with self.lock:
            new_suggestions = []
            for suggestion in suggestions:
                if suggestion.id not in self.suggestions:
                    self.suggestions[suggestion.id] = suggestion
                    if user_id not in self.user_suggestions:
                        self.user_suggestions[user_id] = []
                    self.user_suggestions[user_id].append(suggestion.id)
                    new_suggestions.append(suggestion)

            self._save_data()

        return new_suggestions

    async def _generate_workflow_suggestions(
        self, user_id: str, discovery
    ) -> List[Suggestion]:
        """Genera sugerencias de workflow basadas en patrones."""
        suggestions = []

        patterns = discovery.get_patterns_for_user(
            user_id, min_confidence=PatternConfidence.MEDIUM
        )

        for pattern in patterns[:3]:  # Top 3
            if pattern.suggested_automation:
                suggestion_id = f"sugg_workflow_{user_id}_{pattern.id}"

                # Calcular prioridad basada en frecuencia
                priority = SuggestionPriority.MEDIUM
                if pattern.frequency > 20:
                    priority = SuggestionPriority.HIGH
                elif pattern.frequency > 50:
                    priority = SuggestionPriority.CRITICAL

                suggestion = Suggestion(
                    id=suggestion_id,
                    type=SuggestionType.WORKFLOW,
                    title=f"Automatizar: {pattern.name}",
                    description=f"Detectamos que ejecutas esta secuencia {pattern.frequency} veces. "
                    f"Crear un workflow podría ahorrarte tiempo.",
                    priority=priority,
                    confidence=0.8
                    if pattern.confidence.value in ["high", "certain"]
                    else 0.6,
                    user_id=user_id,
                    context={
                        "pattern_id": pattern.id,
                        "pattern_type": pattern.type.value,
                        "frequency": pattern.frequency,
                    },
                    action={
                        "type": "create_workflow",
                        "template": pattern.suggested_automation,
                        "auto_fill": True,
                    },
                    expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat(),
                )

                suggestions.append(suggestion)

        return suggestions

    async def _generate_optimization_suggestions(
        self, user_id: str, discovery
    ) -> List[Suggestion]:
        """Genera sugerencias de optimización."""
        suggestions = []
        metrics = discovery.usage_metrics.get(user_id)

        if not metrics:
            return suggestions

        # Sugerencia: Acción muy repetida -> crear atajo
        if metrics.unique_actions and metrics.total_actions > 100:
            action_counts = defaultdict(int)
            for action in discovery.user_actions.get(user_id, []):
                action_counts[f"{action.type}:{action.name}"] += 1

            most_common = max(action_counts.items(), key=lambda x: x[1])
            if most_common[1] > 20:
                suggestion_id = f"sugg_shortcut_{user_id}_{hash(most_common[0])}"

                suggestion = Suggestion(
                    id=suggestion_id,
                    type=SuggestionType.SHORTCUT,
                    title=f"Crear atajo para '{most_common[0]}'",
                    description=f"Has usado esta acción {most_common[1]} veces. "
                    f"Un atajo de teclado podría acelerar tu flujo.",
                    priority=SuggestionPriority.MEDIUM,
                    confidence=0.75,
                    user_id=user_id,
                    context={"action": most_common[0], "usage_count": most_common[1]},
                    action={"type": "create_shortcut", "action": most_common[0]},
                )

                suggestions.append(suggestion)

        return suggestions

    async def _generate_schedule_suggestions(
        self, user_id: str, discovery
    ) -> List[Suggestion]:
        """Genera sugerencias de programación temporal."""
        suggestions = []
        metrics = discovery.usage_metrics.get(user_id)

        if not metrics:
            return suggestions

        # Detectar acciones recurrentes en horarios específicos
        patterns = discovery.get_patterns_for_user(
            user_id, pattern_type=PatternType.TEMPORAL
        )

        for pattern in patterns:
            if "peak_hours" in pattern.metadata:
                suggestion_id = f"sugg_schedule_{user_id}_{pattern.id}"

                peak_hours = pattern.metadata["peak_hours"]
                hours_str = ", ".join(f"{h}:00" for h in peak_hours[:3])

                suggestion = Suggestion(
                    id=suggestion_id,
                    type=SuggestionType.SCHEDULE,
                    title="Programar tareas para tus horas más activas",
                    description=f"Detectamos que eres más activo entre {hours_str}. "
                    f"¿Quieres programar tareas importantes para esos horarios?",
                    priority=SuggestionPriority.LOW,
                    confidence=0.7,
                    user_id=user_id,
                    context={"peak_hours": peak_hours, "pattern_id": pattern.id},
                    action={
                        "type": "schedule_recurring",
                        "recommended_hours": peak_hours,
                    },
                )

                suggestions.append(suggestion)

        return suggestions

    async def _generate_integration_suggestions(
        self, user_id: str, discovery
    ) -> List[Suggestion]:
        """Genera sugerencias de integración."""
        suggestions = []

        # Analizar acciones para detectar oportunidades de integración
        user_acts = discovery.user_actions.get(user_id, [])

        # Detectar uso de múltiples servicios
        services_used = set()
        for action in user_acts:
            if action.type == "tool":
                services_used.add(
                    action.name.split("_")[0] if "_" in action.name else action.name
                )

        # Si usa múltiples servicios, sugerir integraciones
        if len(services_used) >= 2:
            services_list = ", ".join(list(services_used)[:3])

            suggestion_id = f"sugg_integration_{user_id}_{len(services_used)}"

            suggestion = Suggestion(
                id=suggestion_id,
                type=SuggestionType.INTEGRATION,
                title=f"Integrar servicios: {services_list}",
                description=f"Usas {len(services_used)} servicios diferentes. "
                f"Podríamos automatizar flujos entre ellos.",
                priority=SuggestionPriority.MEDIUM,
                confidence=0.6,
                user_id=user_id,
                context={"services": list(services_used)},
                action={
                    "type": "explore_integrations",
                    "services": list(services_used),
                },
            )

            suggestions.append(suggestion)

        return suggestions

    async def get_contextual_suggestions(
        self, user_id: str, context: Dict[str, Any]
    ) -> List[Suggestion]:
        """Genera sugerencias contextuales en tiempo real."""
        suggestions = []
        current_action = context.get("current_action")
        current_resource = context.get("current_resource")

        # Sugerencia basada en acción actual
        if current_action:
            # Buscar patrones que empiecen con esta acción
            discovery = get_pattern_discovery()
            patterns = discovery.get_patterns_for_user(user_id)

            for pattern in patterns:
                if (
                    pattern.actions
                    and f"{pattern.actions[0].type}:{pattern.actions[0].name}"
                    == current_action
                ):
                    if len(pattern.actions) > 1:
                        next_action = pattern.actions[1]

                        suggestion_id = f"sugg_ctx_{user_id}_{pattern.id}_{datetime.utcnow().timestamp()}"

                        suggestion = Suggestion(
                            id=suggestion_id,
                            type=SuggestionType.WORKFLOW,
                            title=f"¿Quieres ejecutar '{next_action.name}'?",
                            description=f"Basado en tus patrones, sueles ejecutar esta acción a continuación.",
                            priority=SuggestionPriority.HIGH,
                            confidence=0.85,
                            user_id=user_id,
                            context={
                                "current_action": current_action,
                                "suggested_next": f"{next_action.type}:{next_action.name}",
                                "pattern_id": pattern.id,
                            },
                            action={
                                "type": "execute_action",
                                "action_type": next_action.type,
                                "action_name": next_action.name,
                            },
                            expires_at=(
                                datetime.utcnow() + timedelta(minutes=5)
                            ).isoformat(),
                        )

                        suggestions.append(suggestion)
                        break  # Solo la más relevante

        return suggestions

    def get_suggestions_for_user(
        self, user_id: str, include_dismissed: bool = False, limit: int = 10
    ) -> List[Suggestion]:
        """Obtiene sugerencias activas para un usuario."""
        suggestion_ids = self.user_suggestions.get(user_id, [])

        suggestions = []
        for sid in suggestion_ids:
            if sid in self.suggestions:
                s = self.suggestions[sid]

                # Filtrar expiradas
                if s.expires_at and datetime.utcnow().isoformat() > s.expires_at:
                    continue

                # Filtrar aplicadas/descartadas
                if s.applied:
                    continue
                if s.dismissed and not include_dismissed:
                    continue

                suggestions.append(s)

        # Ordenar por prioridad
        suggestions.sort(key=lambda s: (s.priority.value, s.confidence), reverse=True)

        return suggestions[:limit]

    async def dismiss_suggestion(
        self, suggestion_id: str, reason: Optional[str] = None
    ) -> bool:
        """Marca una sugerencia como descartada."""
        if suggestion_id not in self.suggestions:
            return False

        async with self.lock:
            self.suggestions[suggestion_id].dismissed = True
            self.suggestions[suggestion_id].feedback = reason
            self._save_data()

        return True

    async def apply_suggestion(self, suggestion_id: str) -> bool:
        """Marca una sugerencia como aplicada."""
        if suggestion_id not in self.suggestions:
            return False

        async with self.lock:
            self.suggestions[suggestion_id].applied = True
            self.suggestions[suggestion_id].applied_at = datetime.utcnow().isoformat()
            self._save_data()

        return True

    async def record_feedback(
        self, suggestion_id: str, helpful: bool, feedback: Optional[str] = None
    ):
        """Registra feedback sobre una sugerencia."""
        self.user_feedback[suggestion_id] = {
            "helpful": helpful,
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Aprender del feedback para mejorar futuras sugerencias
        if suggestion_id in self.suggestions:
            suggestion = self.suggestions[suggestion_id]
            # Ajustar confianza basada en feedback
            if not helpful:
                # Reducir confianza de patrones similares
                pass

        self._save_data()

    def get_suggestion_stats(self, user_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de sugerencias para un usuario."""
        suggestion_ids = self.user_suggestions.get(user_id, [])

        total = len(suggestion_ids)
        applied = sum(
            1 for sid in suggestion_ids if self.suggestions.get(sid, {}).applied
        )
        dismissed = sum(
            1 for sid in suggestion_ids if self.suggestions.get(sid, {}).dismissed
        )
        pending = total - applied - dismissed

        by_type = defaultdict(int)
        for sid in suggestion_ids:
            s = self.suggestions.get(sid)
            if s:
                by_type[s.type.value] += 1

        helpful_feedback = sum(
            1
            for sid, f in self.user_feedback.items()
            if f.get("helpful") and sid in suggestion_ids
        )

        return {
            "total": total,
            "applied": applied,
            "dismissed": dismissed,
            "pending": pending,
            "by_type": dict(by_type),
            "helpful_count": helpful_feedback,
            "conversion_rate": applied / total if total > 0 else 0,
        }

    def _save_data(self):
        """Guarda datos en disco."""
        try:
            data = {
                "suggestions": {
                    k: {
                        "id": v.id,
                        "type": v.type.value,
                        "title": v.title,
                        "description": v.description,
                        "priority": v.priority.value,
                        "confidence": v.confidence,
                        "user_id": v.user_id,
                        "context": v.context,
                        "action": v.action,
                        "created_at": v.created_at,
                        "expires_at": v.expires_at,
                        "dismissed": v.dismissed,
                        "applied": v.applied,
                        "applied_at": v.applied_at,
                        "feedback": v.feedback,
                    }
                    for k, v in self.suggestions.items()
                },
                "user_suggestions": self.user_suggestions,
                "user_feedback": self.user_feedback,
            }

            with open(self.storage_path / "suggestions.json", "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving suggestions: {e}")

    def _load_data(self):
        """Carga datos desde disco."""
        try:
            file_path = self.storage_path / "suggestions.json"
            if not file_path.exists():
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            for sid, sdata in data.get("suggestions", {}).items():
                suggestion = Suggestion(
                    id=sdata["id"],
                    type=SuggestionType(sdata["type"]),
                    title=sdata["title"],
                    description=sdata["description"],
                    priority=SuggestionPriority(sdata["priority"]),
                    confidence=sdata["confidence"],
                    user_id=sdata["user_id"],
                    context=sdata.get("context", {}),
                    action=sdata.get("action", {}),
                    created_at=sdata["created_at"],
                    expires_at=sdata.get("expires_at"),
                    dismissed=sdata.get("dismissed", False),
                    applied=sdata.get("applied", False),
                    applied_at=sdata.get("applied_at"),
                    feedback=sdata.get("feedback"),
                )
                self.suggestions[sid] = suggestion

            self.user_suggestions = data.get("user_suggestions", {})
            self.user_feedback = data.get("user_feedback", {})

        except Exception as e:
            logger.error(f"Error loading suggestions: {e}")


# Singleton
_engine_instance: Optional[SuggestionEngine] = None


def get_suggestion_engine() -> SuggestionEngine:
    """Obtiene el singleton de SuggestionEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SuggestionEngine()
    return _engine_instance
