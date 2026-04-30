"""
Retrospective Generator - D.12: Generación automática de retrospectivas de proyecto.
"""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.retrospective")


class RetrospectiveGenerator:
    """
    Genera retrospectivas automáticas basadas en episodios del proyecto.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.episodic_store = None  # Lazy load

    def _get_store(self):
        """Lazy load del EpisodicStore"""
        if self.episodic_store is None:
            from src.core.memory.legacy_adapter import EpisodicStore

            self.episodic_store = EpisodicStore(self.base_path)
        return self.episodic_store

    def generate(self, project_id: str, period: str = "last_week") -> Dict[str, Any]:
        """
        Genera retrospectiva para un proyecto y período.

        Args:
            project_id: ID del proyecto
            period: Período ("last_week", "last_month", "last_2_weeks")

        Returns:
            Dict con stats e insights
        """
        # Calcular fechas del período
        start_date, end_date = self._parse_period(period)

        # Obtener episodios del período
        episodes = self._get_store().query_by_project(
            project_id,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            limit=1000,
        )

        if not episodes:
            return {
                "project_id": project_id,
                "period": period,
                "total_episodes": 0,
                "message": "No hay episodios en el período seleccionado",
            }

        # Calcular estadísticas
        stats = self._calculate_stats(episodes)

        # Generar insights
        insights = self._generate_insights(stats, episodes)

        return {
            "project_id": project_id,
            "period": period,
            "period_dates": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "total_episodes": len(episodes),
            "stats": stats,
            "insights": insights,
            "highlights": self._extract_highlights(episodes),
            "recommendations": self._generate_recommendations(stats),
        }

    def _parse_period(self, period: str) -> tuple:
        """
        Parsea string de período a fechas.

        Returns:
            (start_date, end_date) como datetime objects
        """
        end_date = datetime.now(timezone.utc)

        period_mapping = {
            "last_day": timedelta(days=1),
            "last_week": timedelta(weeks=1),
            "last_2_weeks": timedelta(weeks=2),
            "last_month": timedelta(days=30),
            "last_3_months": timedelta(days=90),
        }

        delta = period_mapping.get(period, timedelta(weeks=1))
        start_date = end_date - delta

        return start_date, end_date

    def _calculate_stats(self, episodes: List[Dict]) -> Dict[str, Any]:
        """Calcula estadísticas de episodios."""
        # Contar outcomes
        outcomes = Counter()
        emotions = Counter()
        all_tags = Counter()
        tools_used = Counter()
        sources = Counter()

        for ep in episodes:
            # Outcome
            outcomes[ep.get("outcome", "unknown")] += 1

            # Emotional tag
            emotion = ep.get("emotional_tag")
            if emotion:
                emotions[emotion] += 1

            # Tags
            for tag in ep.get("tags", []):
                all_tags[tag] += 1

            # Tool used
            tool = ep.get("tool_used")
            if tool:
                tools_used[tool] += 1

            # Source
            sources[ep.get("source", "unknown")] += 1

        total = len(episodes)

        return {
            "total": total,
            "outcomes": dict(outcomes),
            "outcome_percentages": {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in outcomes.items()
            },
            "success_rate": round(outcomes.get("success", 0) / total * 100, 1)
            if total > 0
            else 0,
            "failure_rate": round(outcomes.get("failure", 0) / total * 100, 1)
            if total > 0
            else 0,
            "emotional_breakdown": dict(emotions),
            "most_common_tags": all_tags.most_common(10),
            "tools_used": dict(tools_used),
            "sources": dict(sources),
        }

    def _generate_insights(self, stats: Dict, episodes: List[Dict]) -> List[str]:
        """Genera insights basados en estadísticas."""
        insights = []

        # Insight sobre success rate
        success_rate = stats.get("success_rate", 0)
        if success_rate >= 80:
            insights.append(f"🟢 Excelente tasa de éxito: {success_rate}%")
        elif success_rate >= 60:
            insights.append(f"🟡 Buena tasa de éxito: {success_rate}%")
        elif success_rate >= 40:
            insights.append(
                f"🟠 Tasa de éxito moderada: {success_rate}% - hay margen de mejora"
            )
        else:
            insights.append(f"🔴 Tasa de éxito baja: {success_rate}% - revisar procesos")

        # Insight sobre emociones
        emotions = stats.get("emotional_breakdown", {})
        frustrating = emotions.get("frustrating", 0)
        exciting = emotions.get("exciting", 0)

        if frustrating > len(episodes) * 0.3:
            insights.append(
                f"😤 Alta frustación detectada ({frustrating} episodios) - considerar refactor"
            )
        if exciting > 0:
            insights.append(f"🎉 {exciting} momentos exitosos celebrados")

        # Insight sobre tags
        top_tags = stats.get("most_common_tags", [])
        if top_tags:
            tag_names = [t[0] for t in top_tags[:3]]
            insights.append(f"🏷️ Tags más frecuentes: {', '.join(tag_names)}")

        # Insight sobre bug fixes
        bug_fixes = sum(1 for ep in episodes if "bug_fix" in ep.get("tags", []))
        if bug_fixes > len(episodes) * 0.3:
            insights.append(
                f"🐻‍❄️ Muchos bug fixes ({bug_fixes}) - considerar más testing"
            )

        return insights

    def _extract_highlights(self, episodes: List[Dict]) -> List[Dict]:
        """Extrae episodios destacados."""
        highlights = []

        # Episodios exitosos emocionantes
        exciting_success = [
            ep
            for ep in episodes
            if ep.get("emotional_tag") == "exciting" and ep.get("outcome") == "success"
        ]

        # Últimos 3 éxitos emocionantes
        for ep in exciting_success[:3]:
            highlights.append(
                {
                    "type": "exciting_success",
                    "timestamp": ep.get("timestamp"),
                    "summary": ep.get("summary", "")[:100],
                    "tags": ep.get("tags", []),
                }
            )

        # Episodios con fallos importantes
        failures = [ep for ep in episodes if ep.get("outcome") == "failure"]
        for ep in failures[:2]:
            highlights.append(
                {
                    "type": "failure_learn",
                    "timestamp": ep.get("timestamp"),
                    "summary": ep.get("summary", "")[:100],
                    "lesson": "Revisar para evitar repetir",
                }
            )

        return highlights

    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Genera recomendaciones basadas en stats."""
        recommendations = []

        success_rate = stats.get("success_rate", 0)
        failure_rate = stats.get("failure_rate", 0)

        if success_rate < 50:
            recommendations.append("Considerar revisar procesos de desarrollo")
            recommendations.append("Aumentar cobertura de tests antes de deploys")

        if failure_rate > 30:
            recommendations.append("Implementar más validaciones pre-commit")

        # Verificar testing
        tools = stats.get("tools_used", {})
        if "testing" not in str(tools).lower():
            recommendations.append("Incrementar tiempo dedicado a testing")

        return recommendations

    def format_for_discord(self, retrospective: Dict) -> Dict[str, Any]:
        """
        Formatea retrospectiva para enviar como embed de Discord.

        Returns:
            Dict compatible con discord.Embed
        """
        stats = retrospective.get("stats", {})

        embed = {
            "title": f"📊 Retrospectiva: {retrospective['project_id']}",
            "description": f"Período: {retrospective['period']}\nTotal episodios: {retrospective['total_episodes']}",
            "color": 0x3498DB,
            "fields": [],
            "footer": {"text": "Lilith Memory System"},
        }

        # Outcomes
        outcomes = stats.get("outcomes", {})
        outcomes_str = "\n".join([f"{k}: {v}" for k, v in outcomes.items()])
        embed["fields"].append(
            {"name": "📈 Outcomes", "value": outcomes_str or "N/A", "inline": True}
        )

        # Success rate
        embed["fields"].append(
            {
                "name": "✅ Tasa de Éxito",
                "value": f"{stats.get('success_rate', 0)}%",
                "inline": True,
            }
        )

        # Top tags
        top_tags = stats.get("most_common_tags", [])
        tags_str = ", ".join([f"{t[0]} ({t[1]})" for t in top_tags[:5]])
        embed["fields"].append(
            {"name": "🏷️ Tags Principales", "value": tags_str or "N/A", "inline": False}
        )

        # Insights
        insights = retrospective.get("insights", [])
        if insights:
            insights_str = "\n".join(insights[:5])
            embed["fields"].append(
                {"name": "💡 Insights", "value": insights_str, "inline": False}
            )

        return embed


# Funciones de conveniencia
def generate_retrospective(
    project_id: str, period: str = "last_week", base_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Genera retrospectiva (función conveniencia)"""
    path = base_path or Path(__file__).resolve().parents[2]
    generator = RetrospectiveGenerator(path)
    return generator.generate(project_id, period)
