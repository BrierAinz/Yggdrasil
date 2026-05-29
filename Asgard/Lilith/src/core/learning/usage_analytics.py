"""
Usage Analytics - Análisis detallado de uso del sistema

v5.0-Fase4B: Métricas, visualizaciones y reportes de uso.
"""
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.learning.analytics")


@dataclass
class DailyStats:
    """Estadísticas diarias."""

    date: str
    total_actions: int = 0
    unique_users: set = field(default_factory=set)
    action_breakdown: Dict[str, int] = field(default_factory=dict)
    peak_hour: Optional[int] = None
    average_session_duration: float = 0.0


@dataclass
class UserJourney:
    """Journey de un usuario."""

    user_id: str
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    common_paths: List[List[str]] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    satisfaction_score: Optional[float] = None


class UsageAnalytics:
    """
    Sistema de analytics de uso.

    Features:
    - Métricas de engagement
    - Funnels de conversión
    - Retención de usuarios
    - Reportes automáticos
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.daily_stats: Dict[str, DailyStats] = {}
        self.user_journeys: Dict[str, UserJourney] = {}
        self.events: List[Dict[str, Any]] = []
        self.storage_path = storage_path or Path("Data/analytics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_data()

    def record_event(
        self, event_type: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Registra un evento para análisis."""
        event = {
            "type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        self.events.append(event)

        # Actualizar estadísticas diarias
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(date=today)

        stats = self.daily_stats[today]
        stats.total_actions += 1
        stats.unique_users.add(user_id)

        # Breakdown por tipo
        if event_type not in stats.action_breakdown:
            stats.action_breakdown[event_type] = 0
        stats.action_breakdown[event_type] += 1

        # Mantener solo últimos 30 días de eventos
        if len(self.events) > 10000:
            self.events = self.events[-5000:]

        self._save_data()

    def get_daily_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """Obtiene resumen de los últimos N días."""
        results = []

        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            stats = self.daily_stats.get(date)

            if stats:
                results.append(
                    {
                        "date": date,
                        "total_actions": stats.total_actions,
                        "unique_users": len(stats.unique_users),
                        "action_breakdown": stats.action_breakdown,
                        "peak_hour": stats.peak_hour,
                    }
                )
            else:
                results.append(
                    {
                        "date": date,
                        "total_actions": 0,
                        "unique_users": 0,
                        "action_breakdown": {},
                        "peak_hour": None,
                    }
                )

        return list(reversed(results))

    def get_user_engagement(self, user_id: str) -> Dict[str, Any]:
        """Obtiene métricas de engagement de un usuario."""
        user_events = [e for e in self.events if e["user_id"] == user_id]

        if not user_events:
            return {
                "user_id": user_id,
                "total_actions": 0,
                "first_seen": None,
                "last_seen": None,
                "active_days": 0,
            }

        dates = set()
        for event in user_events:
            date = event["timestamp"][:10]
            dates.add(date)

        return {
            "user_id": user_id,
            "total_actions": len(user_events),
            "first_seen": user_events[0]["timestamp"],
            "last_seen": user_events[-1]["timestamp"],
            "active_days": len(dates),
            "actions_per_day": len(user_events) / max(len(dates), 1),
        }

    def generate_report(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Genera un reporte de analytics."""
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        total_actions = 0
        all_users = set()
        action_types = defaultdict(int)

        for date_str, stats in self.daily_stats.items():
            if start_date <= date_str <= end_date:
                total_actions += stats.total_actions
                all_users.update(stats.unique_users)

                for action_type, count in stats.action_breakdown.items():
                    action_types[action_type] += count

        return {
            "period": {"start": start_date, "end": end_date},
            "summary": {
                "total_actions": total_actions,
                "unique_users": len(all_users),
                "actions_per_user": total_actions / max(len(all_users), 1),
            },
            "action_breakdown": dict(action_types),
            "top_actions": sorted(
                action_types.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _save_data(self):
        """Guarda datos en disco."""
        try:
            data = {
                "daily_stats": {
                    k: {
                        "date": v.date,
                        "total_actions": v.total_actions,
                        "unique_users": list(v.unique_users),
                        "action_breakdown": v.action_breakdown,
                        "peak_hour": v.peak_hour,
                    }
                    for k, v in self.daily_stats.items()
                },
                "events": self.events[-5000:],  # Solo últimos 5000
            }

            with open(self.storage_path / "usage_analytics.json", "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving analytics: {e}")

    def _load_data(self):
        """Carga datos desde disco."""
        try:
            file_path = self.storage_path / "usage_analytics.json"
            if not file_path.exists():
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            for date, stats_data in data.get("daily_stats", {}).items():
                self.daily_stats[date] = DailyStats(
                    date=stats_data["date"],
                    total_actions=stats_data["total_actions"],
                    unique_users=set(stats_data.get("unique_users", [])),
                    action_breakdown=stats_data.get("action_breakdown", {}),
                    peak_hour=stats_data.get("peak_hour"),
                )

            self.events = data.get("events", [])

        except Exception as e:
            logger.error(f"Error loading analytics: {e}")


# Singleton
_analytics_instance: Optional[UsageAnalytics] = None


def get_analytics() -> UsageAnalytics:
    """Obtiene el singleton de UsageAnalytics."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = UsageAnalytics()
    return _analytics_instance
