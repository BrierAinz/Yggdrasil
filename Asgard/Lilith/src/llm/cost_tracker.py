"""
Cost Tracker para Crystal/OpenRouter.
Rastrea costos por usuario, modelo y tiempo.
Almacena en SQLite para persistencia.
"""
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.cost_tracker")


@dataclass
class UsageRecord:
    """Registro de uso de un modelo."""

    user_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: float
    guild_id: Optional[str] = None


class CostTracker:
    """
    Tracker de costes para Crystal/OpenRouter.
    Almacena uso en SQLite y provee endpoints de stats.
    """

    def __init__(
        self, base_path: Optional[Path] = None, db_name: str = "crystal_costs.db"
    ):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.db_path = self.base_path / "Data" / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pricing = self._load_pricing()
        self._init_db()

    def _load_pricing(self) -> Dict[str, Dict[str, float]]:
        """Carga pricing desde crystal.json."""
        try:
            crystal_path = self.base_path / "Config" / "crystal.json"
            if crystal_path.exists():
                data = json.loads(crystal_path.read_text(encoding="utf-8"))
                pricing = data.get("pricing", {})
                return {
                    model: {
                        "input": float(info.get("input", 0)),
                        "output": float(info.get("output", 0)),
                    }
                    for model, info in pricing.items()
                    if isinstance(info, dict)
                }
        except Exception as e:
            logger.warning("[CostTracker] Error cargando pricing: %s", e)
        # Pricing por defecto
        return {
            "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "meta-llama/llama-3-70b-instruct": {"input": 0.00059, "output": 0.00079},
        }

    def _init_db(self) -> None:
        """Inicializa la tabla de costos en SQLite."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usage_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        guild_id TEXT,
                        model TEXT NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        cost REAL DEFAULT 0.0,
                        timestamp REAL NOT NULL
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_timestamp
                    ON usage_records(user_id, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_model_timestamp
                    ON usage_records(model, timestamp)
                """
                )
                conn.commit()
        except Exception as e:
            logger.error("[CostTracker] Error inicializando DB: %s", e)

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calcula el costo en USD para una llamada.

        Args:
            model: Nombre del modelo (ej: anthropic/claude-3-haiku)
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida

        Returns:
            Costo total en USD
        """
        pricing = self._pricing.get(model, {})
        input_price = pricing.get("input", 0.0)  # Price per 1K tokens
        output_price = pricing.get("output", 0.0)

        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price

        return round(input_cost + output_cost, 6)

    def track_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        guild_id: Optional[str] = None,
    ) -> float:
        """
        Registra uso de un usuario y calcula costo.

        Args:
            user_id: ID del usuario Discord
            model: Modelo usado
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            guild_id: ID del servidor (opcional)

        Returns:
            Costo calculado
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        timestamp = time.time()

        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    INSERT INTO usage_records
                    (user_id, guild_id, model, input_tokens, output_tokens, cost, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        guild_id,
                        model,
                        input_tokens,
                        output_tokens,
                        cost,
                        timestamp,
                    ),
                )
                conn.commit()

            logger.info(
                "[CostTracker] User %s | Model %s | Input %d | Output %d | Cost $%.6f",
                user_id,
                model,
                input_tokens,
                output_tokens,
                cost,
            )
        except Exception as e:
            logger.error("[CostTracker] Error guardando uso: %s", e)

        return cost

    def get_user_stats(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict:
        """Obtiene estadísticas de uso de un usuario."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Total por modelo
                cursor = conn.execute(
                    """
                    SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cost), COUNT(*)
                    FROM usage_records
                    WHERE user_id = ? AND timestamp > ?
                    GROUP BY model
                    """,
                    (user_id, cutoff),
                )
                by_model = []
                total_cost = 0.0
                total_calls = 0
                total_input = 0
                total_output = 0

                for row in cursor:
                    by_model.append(
                        {
                            "model": row[0],
                            "input_tokens": row[1],
                            "output_tokens": row[2],
                            "cost": round(row[3], 6),
                            "calls": row[4],
                        }
                    )
                    total_cost += row[3]
                    total_calls += row[4]
                    total_input += row[1]
                    total_output += row[2]

                return {
                    "user_id": user_id,
                    "period_days": days,
                    "total_cost": round(total_cost, 6),
                    "total_calls": total_calls,
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "by_model": by_model,
                }
        except Exception as e:
            logger.error("[CostTracker] Error obteniendo stats: %s", e)
            return {
                "user_id": user_id,
                "period_days": days,
                "total_cost": 0.0,
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "by_model": [],
                "error": str(e),
            }

    def get_global_stats(self, days: int = 30) -> Dict:
        """Obtiene estadísticas globales."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(DISTINCT user_id),
                        SUM(input_tokens),
                        SUM(output_tokens),
                        SUM(cost),
                        COUNT(*)
                    FROM usage_records
                    WHERE timestamp > ?
                    """,
                    (cutoff,),
                )
                row = cursor.fetchone()

                # Top usuarios por costo
                top_users = []
                cursor = conn.execute(
                    """
                    SELECT user_id, SUM(cost), COUNT(*)
                    FROM usage_records
                    WHERE timestamp > ?
                    GROUP BY user_id
                    ORDER BY SUM(cost) DESC
                    LIMIT 10
                    """,
                    (cutoff,),
                )
                for r in cursor:
                    top_users.append(
                        {
                            "user_id": r[0],
                            "cost": round(r[1], 6),
                            "calls": r[2],
                        }
                    )

                return {
                    "period_days": days,
                    "unique_users": row[0] or 0,
                    "total_input_tokens": row[1] or 0,
                    "total_output_tokens": row[2] or 0,
                    "total_cost": round(row[3] or 0, 6),
                    "total_calls": row[4] or 0,
                    "top_users": top_users,
                }
        except Exception as e:
            logger.error("[CostTracker] Error obteniendo stats globales: %s", e)
            return {
                "period_days": days,
                "unique_users": 0,
                "total_cost": 0.0,
                "total_calls": 0,
                "error": str(e),
            }

    def get_daily_breakdown(self, days: int = 7) -> List[Dict]:
        """Obtiene desglose diario de costos."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        DATE(datetime(timestamp, 'unixepoch')) as day,
                        COUNT(*),
                        SUM(cost)
                    FROM usage_records
                    WHERE timestamp > ?
                    GROUP BY day
                    ORDER BY day DESC
                    """,
                    (cutoff,),
                )
                return [
                    {"date": row[0], "calls": row[1], "cost": round(row[2], 6)}
                    for row in cursor
                ]
        except Exception as e:
            logger.error("[CostTracker] Error obteniendo breakdown: %s", e)
            return []

    def cleanup_old_records(self, days: int = 90) -> int:
        """Limpia registros antiguos. Retorna número de filas eliminadas."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    "DELETE FROM usage_records WHERE timestamp < ?",
                    (cutoff,),
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error("[CostTracker] Error limpiando registros: %s", e)
            return 0


# Singleton global
_tracker_instance: Optional[CostTracker] = None


def get_cost_tracker(base_path: Optional[Path] = None) -> CostTracker:
    """Obtiene instancia singleton del CostTracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CostTracker(base_path)
    return _tracker_instance


def track_crystal_usage(
    user_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    guild_id: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> float:
    """Función conveniencia para trackear uso de Crystal."""
    tracker = get_cost_tracker(base_path)
    return tracker.track_usage(user_id, model, input_tokens, output_tokens, guild_id)


__all__ = [
    "CostTracker",
    "UsageRecord",
    "get_cost_tracker",
    "track_crystal_usage",
]
