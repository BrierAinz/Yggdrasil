"""
Rate Limiter V2 - B.4: Rate limiting por usuario/rol con sliding window.

Features:
- Sliding window algorithm
- Per-role limits (owner, trusted, public)
- Per-user overrides
- SQLite persistence
- FastAPI middleware support
- Response headers
"""
import json
import logging
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.rate_limiter_v2")


@dataclass
class RateLimitRule:
    """Regla de rate limiting para un rol o usuario."""

    max_requests_per_hour: int = 100
    max_requests_per_minute: int = 10
    bypass_rate_limit: bool = False
    description: str = ""
    expires_at: Optional[str] = None  # ISO format para overrides temporales


@dataclass
class RateLimitStatus:
    """Estado de rate limit para un usuario."""

    user_id: str
    role: str
    requests_used_hour: int
    requests_remaining_hour: int
    requests_used_minute: int
    requests_remaining_minute: int
    is_blocked: bool
    block_expires_at: Optional[float]
    retry_after_seconds: int = 0
    limit: int = 0
    remaining: int = 0
    reset_timestamp: float = 0.0


class RateLimiterV2:
    """
    Rate Limiter V2 con soporte por rol y overrides por usuario.
    Sliding window + persistencia SQLite.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, base_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )

        # Cargar configuración
        self.config = self._load_config()
        self.enabled = self.config.get("global", {}).get("enabled", True)

        # Setup DB
        db_config = self.config.get("storage", {})
        db_path = db_config.get("path", "Data/rate_limit_history.db")
        self.db_path = self.base_path / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache de requests recientes (sliding window)
        self._requests_cache: Dict[str, List[float]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = 3600  # 1 hora

        self._init_db()
        self._initialized = True

        logger.info(
            "[RateLimiterV2] Inicializado. Roles: %d",
            len(self.config.get("by_role", {})),
        )

    def _load_config(self) -> dict:
        """Carga configuración desde rate_limits.json."""
        config_path = self.base_path / "Config" / "rate_limits.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("[RateLimiterV2] Error cargando config: %s", e)

        # Config por defecto
        return {
            "global": {"enabled": True},
            "by_role": {
                "owner": {"max_requests_per_hour": 1000, "max_requests_per_minute": 60},
                "trusted": {
                    "max_requests_per_hour": 100,
                    "max_requests_per_minute": 10,
                },
                "public": {"max_requests_per_hour": 10, "max_requests_per_minute": 2},
            },
            "user_overrides": {},
        }

    def _init_db(self) -> None:
        """Inicializa tablas de rate limiting."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Tabla de requests (sliding window)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limit_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        endpoint TEXT,
                        timestamp REAL NOT NULL,
                        blocked BOOLEAN DEFAULT 0
                    )
                """
                )

                # Tabla de bloqueos
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limit_blocks (
                        user_id TEXT PRIMARY KEY,
                        blocked_until REAL NOT NULL,
                        reason TEXT,
                        created_at REAL NOT NULL
                    )
                """
                )

                # Índices
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rate_user_time
                    ON rate_limit_history(user_id, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_rate_endpoint
                    ON rate_limit_history(endpoint, timestamp)
                """
                )

                conn.commit()
        except Exception as e:
            logger.error("[RateLimiterV2] Error inicializando DB: %s", e)

    def _get_rule(self, user_id: str, role: str = "public") -> RateLimitRule:
        """Obtiene la regla aplicable para un usuario (con override si existe)."""
        # Verificar override por usuario
        overrides = self.config.get("user_overrides", {})
        if user_id in overrides:
            override = overrides[user_id]
            # Verificar expiración
            expires_at = override.get("expires_at")
            if expires_at:
                try:
                    exp_ts = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    ).timestamp()
                    if time.time() > exp_ts:
                        logger.debug(
                            "[RateLimiterV2] Override expirado para %s", user_id
                        )
                        return self._get_role_rule(role)
                except:
                    pass

            logger.debug("[RateLimiterV2] Usando override para %s", user_id)
            return RateLimitRule(**override)

        return self._get_role_rule(role)

    def _get_role_rule(self, role: str) -> RateLimitRule:
        """Obtiene regla para un rol."""
        by_role = self.config.get("by_role", {})
        role_config = by_role.get(role, by_role.get("public", {}))
        return RateLimitRule(**role_config)

    def is_allowed(
        self, user_id: str, role: str = "public", endpoint: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si un usuario puede hacer una request.

        Returns:
            Tuple[bool, dict]: (permitido, metadata con headers)
        """
        if not self.enabled:
            return True, {"limit": 0, "remaining": 0, "reset": 0}

        rule = self._get_rule(user_id, role)

        if rule.bypass_rate_limit:
            return True, {"limit": -1, "remaining": -1, "reset": 0}

        now = time.time()
        hour_ago = now - 3600
        minute_ago = now - 60

        with self._cache_lock:
            # Limpiar cache antiguo
            if user_id in self._requests_cache:
                self._requests_cache[user_id] = [
                    ts for ts in self._requests_cache[user_id] if ts > hour_ago
                ]
            else:
                self._requests_cache[user_id] = []

            # Contar requests en ventanas
            requests_last_hour = len(self._requests_cache[user_id])
            requests_last_minute = len(
                [ts for ts in self._requests_cache[user_id] if ts > minute_ago]
            )

            # Verificar límites
            if requests_last_hour >= rule.max_requests_per_hour:
                retry_after = int(self._requests_cache[user_id][0] + 3600 - now)
                logger.warning(
                    "[RateLimiterV2] User %s blocked: hourly limit (%d/%d)",
                    user_id,
                    requests_last_hour,
                    rule.max_requests_per_hour,
                )
                self._log_blocked(user_id, role, endpoint)
                return False, {
                    "limit": rule.max_requests_per_hour,
                    "remaining": 0,
                    "reset": int(now + 3600),
                    "retry_after": max(1, retry_after),
                }

            if requests_last_minute >= rule.max_requests_per_minute:
                retry_after = int(60 - (now - minute_ago))
                logger.warning(
                    "[RateLimiterV2] User %s blocked: minute limit (%d/%d)",
                    user_id,
                    requests_last_minute,
                    rule.max_requests_per_minute,
                )
                self._log_blocked(user_id, role, endpoint)
                return False, {
                    "limit": rule.max_requests_per_minute,
                    "remaining": 0,
                    "reset": int(now + 60),
                    "retry_after": max(1, retry_after),
                }

            # Registrar request
            self._requests_cache[user_id].append(now)
            self._persist_request(user_id, role, endpoint)

            remaining_hour = rule.max_requests_per_hour - requests_last_hour - 1
            remaining_minute = rule.max_requests_per_minute - requests_last_minute - 1

            return True, {
                "limit": rule.max_requests_per_hour,
                "remaining": max(0, remaining_hour),
                "reset": int(now + 3600),
                "limit_minute": rule.max_requests_per_minute,
                "remaining_minute": max(0, remaining_minute),
            }

    def _persist_request(self, user_id: str, role: str, endpoint: str) -> None:
        """Persiste request en SQLite (fire-and-forget)."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    "INSERT INTO rate_limit_history (user_id, role, endpoint, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, role, endpoint, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiterV2] Error persistiendo request: %s", e)

    def _log_blocked(self, user_id: str, role: str, endpoint: str) -> None:
        """Log de request bloqueada."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    "INSERT INTO rate_limit_history (user_id, role, endpoint, timestamp, blocked) VALUES (?, ?, ?, ?, 1)",
                    (user_id, role, endpoint, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiterV2] Error logueando bloqueo: %s", e)

    def get_status(self, user_id: str, role: str = "public") -> RateLimitStatus:
        """Obtiene estado completo de rate limit para un usuario."""
        rule = self._get_rule(user_id, role)
        now = time.time()
        hour_ago = now - 3600
        minute_ago = now - 60

        with self._cache_lock:
            requests = self._requests_cache.get(user_id, [])
            requests_last_hour = len([ts for ts in requests if ts > hour_ago])
            requests_last_minute = len([ts for ts in requests if ts > minute_ago])

        remaining_hour = max(0, rule.max_requests_per_hour - requests_last_hour)
        remaining_minute = max(0, rule.max_requests_per_minute - requests_last_minute)

        # Calcular reset timestamp (cuando el request más antiguo expire)
        reset_ts = now + 3600
        if requests:
            oldest = min(requests)
            reset_ts = oldest + 3600

        return RateLimitStatus(
            user_id=user_id,
            role=role,
            requests_used_hour=requests_last_hour,
            requests_remaining_hour=remaining_hour,
            requests_used_minute=requests_last_minute,
            requests_remaining_minute=remaining_minute,
            is_blocked=remaining_hour == 0 or remaining_minute == 0,
            block_expires_at=None,
            limit=rule.max_requests_per_hour,
            remaining=remaining_hour,
            reset_timestamp=reset_ts,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas globales de rate limiting."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Total requests en última hora
                hour_ago = time.time() - 3600
                cursor = conn.execute(
                    "SELECT COUNT(*), SUM(blocked) FROM rate_limit_history WHERE timestamp > ?",
                    (hour_ago,),
                )
                total, blocked = cursor.fetchone()

                # Top usuarios por requests
                cursor = conn.execute(
                    """SELECT user_id, role, COUNT(*) as count
                       FROM rate_limit_history
                       WHERE timestamp > ?
                       GROUP BY user_id
                       ORDER BY count DESC
                       LIMIT 10""",
                    (hour_ago,),
                )
                top_users = [
                    {"user_id": r[0], "role": r[1], "requests": r[2]}
                    for r in cursor.fetchall()
                ]

                # Por rol
                cursor = conn.execute(
                    "SELECT role, COUNT(*) FROM rate_limit_history WHERE timestamp > ? GROUP BY role",
                    (hour_ago,),
                )
                by_role = {r[0]: r[1] for r in cursor.fetchall()}

                return {
                    "total_requests_last_hour": total or 0,
                    "blocked_requests_last_hour": blocked or 0,
                    "top_users": top_users,
                    "by_role": by_role,
                }
        except Exception as e:
            logger.error("[RateLimiterV2] Error obteniendo stats: %s", e)
            return {}

    def create_override(
        self,
        user_id: str,
        max_requests_per_hour: int,
        max_requests_per_minute: int = None,
        reason: str = "",
        duration_hours: int = None,
    ) -> bool:
        """Crea un override temporal para un usuario."""
        try:
            overrides = self.config.get("user_overrides", {})

            override = {
                "max_requests_per_hour": max_requests_per_hour,
                "reason": reason,
            }

            if max_requests_per_minute:
                override["max_requests_per_minute"] = max_requests_per_minute

            if duration_hours:
                expires_at = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                # Add duration
                from datetime import timedelta

                expires_dt = datetime.now(timezone.utc) + timedelta(
                    hours=duration_hours
                )
                override["expires_at"] = expires_dt.isoformat().replace("+00:00", "Z")

            overrides[user_id] = override

            # Guardar en config
            config_path = self.base_path / "Config" / "rate_limits.json"
            self.config["user_overrides"] = overrides

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logger.info(
                "[RateLimiterV2] Override created for %s: %d req/hr",
                user_id,
                max_requests_per_hour,
            )
            return True
        except Exception as e:
            logger.error("[RateLimiterV2] Error creando override: %s", e)
            return False

    def remove_override(self, user_id: str) -> bool:
        """Elimina un override."""
        try:
            overrides = self.config.get("user_overrides", {})
            if user_id in overrides:
                del overrides[user_id]

                config_path = self.base_path / "Config" / "rate_limits.json"
                self.config["user_overrides"] = overrides

                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)

                logger.info("[RateLimiterV2] Override removed for %s", user_id)
                return True
            return False
        except Exception as e:
            logger.error("[RateLimiterV2] Error eliminando override: %s", e)
            return False


# Singleton
_rate_limiter_v2_instance: Optional[RateLimiterV2] = None


def get_rate_limiter_v2(base_path: Optional[Path] = None) -> RateLimiterV2:
    """Obtiene instancia singleton del RateLimiterV2."""
    global _rate_limiter_v2_instance
    if _rate_limiter_v2_instance is None:
        _rate_limiter_v2_instance = RateLimiterV2(base_path)
    return _rate_limiter_v2_instance


def check_rate_limit(
    user_id: str, role: str = "public", endpoint: str = ""
) -> Tuple[bool, Dict[str, Any]]:
    """Función conveniencia para verificar rate limit."""
    limiter = get_rate_limiter_v2()
    return limiter.is_allowed(user_id, role, endpoint)


__all__ = [
    "RateLimiterV2",
    "RateLimitRule",
    "RateLimitStatus",
    "get_rate_limiter_v2",
    "check_rate_limit",
]
