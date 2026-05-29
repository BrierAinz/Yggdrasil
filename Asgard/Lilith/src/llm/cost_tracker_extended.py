"""
Cost Tracker Extended - D.12: Enhanced cost tracking with complexity and savings.

Features:
- Cost tracking by complexity level
- Savings report vs "all Opus" baseline
- Model usage breakdown
- Latency tracking
"""
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.complexity_analyzer import ComplexityLevel
from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.cost_tracker_v2")


@dataclass
class ModelUsageRecord:
    """Registro de uso de modelo extendido."""

    user_id: str
    model: str
    complexity: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    timestamp: float


class CostTrackerExtended:
    """
    Cost tracker extendido con tracking por complejidad y ahorros.
    """

    _instance = None

    def __init__(self, base_path: Optional[Path] = None):
        if CostTrackerExtended._instance is not None:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )

        # DB path
        self.db_path = self.base_path / "Data" / "model_usage_v2.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Load pricing
        self._pricing = self._load_pricing()

        # Baseline cost (Opus)
        self._opus_cost_per_1k = 90.0  # input + output average

        self._init_db()

        logger.info("[CostTrackerExtended] Inicializado")
        CostTrackerExtended._instance = self

    def _load_pricing(self) -> Dict[str, Dict[str, float]]:
        """Carga pricing desde config."""
        config_path = self.base_path / "Config" / "model_selector.json"
        config = safe_load(config_path, default={})

        pricing = {}
        for name, data in config.get("models", {}).items():
            pricing[name] = {
                "input": data.get("cost_per_1k_input", 0.0),
                "output": data.get("cost_per_1k_output", 0.0),
            }

        return pricing

    def _init_db(self) -> None:
        """Inicializa base de datos."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        complexity TEXT NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        cost REAL DEFAULT 0.0,
                        latency_ms REAL DEFAULT 0.0,
                        timestamp REAL NOT NULL
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_usage_time
                    ON model_usage(timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_usage_model
                    ON model_usage(model, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_usage_complexity
                    ON model_usage(complexity, timestamp)
                """
                )
                conn.commit()
        except Exception as e:
            logger.error("[CostTrackerExtended] Error inicializando DB: %s", e)

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calcula costo en USD."""
        pricing = self._pricing.get(model, {"input": 3.0, "output": 15.0})

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def track_usage(
        self,
        user_id: str,
        model: str,
        complexity: ComplexityLevel,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ) -> Dict[str, float]:
        """
        Registra uso de modelo.

        Returns:
            Dict con costo actual y costo baseline (Opus)
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        baseline_cost = self.calculate_baseline_cost(input_tokens, output_tokens)

        timestamp = time.time()

        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    INSERT INTO model_usage
                    (user_id, model, complexity, input_tokens, output_tokens, cost, latency_ms, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        model,
                        complexity.value,
                        input_tokens,
                        output_tokens,
                        cost,
                        latency_ms,
                        timestamp,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error("[CostTrackerExtended] Error guardando uso: %s", e)

        savings = baseline_cost - cost

        logger.info(
            "[CostTrackerExtended] %s | %s | %s | Cost: $%.4f | Baseline: $%.4f | Saved: $%.4f",
            user_id,
            model,
            complexity.value,
            cost,
            baseline_cost,
            savings,
        )

        return {"actual_cost": cost, "baseline_cost": baseline_cost, "savings": savings}

    def calculate_baseline_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula costo si se hubiera usado Opus (baseline más caro)."""
        # Opus: $15 input, $75 output per 1K
        input_cost = (input_tokens / 1000) * 15.0
        output_cost = (output_tokens / 1000) * 75.0
        return round(input_cost + output_cost, 6)

    def get_savings_report(self, days: int = 30) -> Dict[str, Any]:
        """Genera reporte de ahorros."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Total actual
                cursor = conn.execute(
                    """
                    SELECT SUM(cost), SUM(input_tokens), SUM(output_tokens), COUNT(*)
                    FROM model_usage
                    WHERE timestamp > ?
                    """,
                    (cutoff,),
                )
                actual_cost, total_input, total_output, total_calls = cursor.fetchone()

                actual_cost = actual_cost or 0
                total_input = total_input or 0
                total_output = total_output or 0

                # Calcular baseline
                baseline_cost = self.calculate_baseline_cost(total_input, total_output)

                savings = baseline_cost - actual_cost
                savings_percentage = (
                    (savings / baseline_cost * 100) if baseline_cost > 0 else 0
                )

                # Por modelo
                cursor = conn.execute(
                    """
                    SELECT model, SUM(cost), SUM(input_tokens), SUM(output_tokens), COUNT(*), AVG(latency_ms)
                    FROM model_usage
                    WHERE timestamp > ?
                    GROUP BY model
                    """,
                    (cutoff,),
                )

                by_model = []
                for row in cursor:
                    by_model.append(
                        {
                            "model": row[0],
                            "cost": round(row[1], 4),
                            "input_tokens": row[2],
                            "output_tokens": row[3],
                            "calls": row[4],
                            "avg_latency_ms": round(row[5], 2) if row[5] else 0,
                        }
                    )

                # Por complejidad
                cursor = conn.execute(
                    """
                    SELECT complexity, SUM(cost), COUNT(*), AVG(latency_ms)
                    FROM model_usage
                    WHERE timestamp > ?
                    GROUP BY complexity
                    """,
                    (cutoff,),
                )

                by_complexity = {}
                for row in cursor:
                    by_complexity[row[0]] = {
                        "cost": round(row[1], 4),
                        "calls": row[2],
                        "avg_latency_ms": round(row[3], 2) if row[3] else 0,
                    }

                return {
                    "period_days": days,
                    "actual_cost": round(actual_cost, 4),
                    "baseline_cost": round(baseline_cost, 4),
                    "savings": round(savings, 4),
                    "savings_percentage": round(savings_percentage, 2),
                    "total_calls": total_calls,
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "by_model": sorted(by_model, key=lambda x: x["cost"], reverse=True),
                    "by_complexity": by_complexity,
                }

        except Exception as e:
            logger.error("[CostTrackerExtended] Error generando reporte: %s", e)
            return {"error": str(e)}

    def get_model_efficiency(self, days: int = 30) -> Dict[str, Any]:
        """Calcula eficiencia por modelo."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        model,
                        COUNT(*) as calls,
                        SUM(cost) as total_cost,
                        AVG(latency_ms) as avg_latency,
                        AVG(cost) as avg_cost_per_call
                    FROM model_usage
                    WHERE timestamp > ?
                    GROUP BY model
                    ORDER BY total_cost DESC
                    """,
                    (cutoff,),
                )

                models = []
                for row in cursor:
                    models.append(
                        {
                            "model": row[0],
                            "calls": row[1],
                            "total_cost": round(row[2], 4),
                            "avg_latency_ms": round(row[3], 2),
                            "avg_cost_per_call": round(row[4], 6),
                        }
                    )

                return {"period_days": days, "models": models}

        except Exception as e:
            logger.error("[CostTrackerExtended] Error calculando eficiencia: %s", e)
            return {"error": str(e)}

    def get_daily_costs(self, days: int = 7) -> List[Dict]:
        """Obtiene costos diarios."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        DATE(datetime(timestamp, 'unixepoch')) as day,
                        SUM(cost),
                        SUM(input_tokens),
                        SUM(output_tokens),
                        COUNT(*)
                    FROM model_usage
                    WHERE timestamp > ?
                    GROUP BY day
                    ORDER BY day DESC
                    """,
                    (cutoff,),
                )

                return [
                    {
                        "date": row[0],
                        "cost": round(row[1], 4),
                        "input_tokens": row[2],
                        "output_tokens": row[3],
                        "calls": row[4],
                    }
                    for row in cursor
                ]

        except Exception as e:
            logger.error("[CostTrackerExtended] Error obteniendo costos diarios: %s", e)
            return []


# Singleton
_cost_tracker_v2_instance: Optional[CostTrackerExtended] = None


def get_cost_tracker_v2(base_path: Optional[Path] = None) -> CostTrackerExtended:
    """Obtiene instancia singleton."""
    global _cost_tracker_v2_instance
    if _cost_tracker_v2_instance is None:
        _cost_tracker_v2_instance = CostTrackerExtended(base_path)
    return _cost_tracker_v2_instance


def track_model_usage(
    user_id: str,
    model: str,
    complexity: ComplexityLevel,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
) -> Dict[str, float]:
    """Función conveniencia."""
    tracker = get_cost_tracker_v2()
    return tracker.track_usage(
        user_id, model, complexity, input_tokens, output_tokens, latency_ms
    )


__all__ = [
    "CostTrackerExtended",
    "ModelUsageRecord",
    "get_cost_tracker_v2",
    "track_model_usage",
]
