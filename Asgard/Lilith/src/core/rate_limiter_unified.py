"""
Lilith Unified Rate Limiter
============================

Sistema unificado de rate limiting para todos los transportes y APIs.

Features:
- Sliding window algorithm
- Per-role limits (owner, trusted, public)
- Per-transport tracking (discord, telegram, api)
- Token and request tracking
- SQLite persistence
- FastAPI middleware support
- Response headers (X-RateLimit-Limit, X-RateLimit-Remaining, etc.)

Migration path:
    from src.core.rate_limiter_unified import get_rate_limiter, RateLimiterUnified

    # Reemplaza llamadas antiguas:
    # OLD: check_user_rate_limit(user_id, guild_id, tokens)
    # NEW: limiter.is_allowed(user_id, transport="discord", estimated_tokens=tokens)
"""

import json
import logging
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("lilith.rate_limiter_unified")


class TransportType(str, Enum):
    """Tipos de transporte para tracking separado."""

    DISCORD = "discord"
    TELEGRAM = "telegram"
    API = "api"
    WEB = "web"


class UserRole(str, Enum):
    """Roles de usuario con límites diferentes."""

    OWNER = "owner"
    TRUSTED = "trusted"
    PUBLIC = "public"
    SYSTEM = "system"  # Para llamadas internas


@dataclass
class RateLimitRule:
    """Regla de rate limiting para un rol."""

    max_requests_per_hour: int = 100
    max_requests_per_minute: int = 10
    max_tokens_per_day: int = 50000
    cooldown_seconds: int = 60
    bypass_rate_limit: bool = False
    description: str = ""
    expires_at: Optional[str] = None  # ISO format para overrides temporales

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitRule":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RateLimitStatus:
    """Estado completo de rate limit para un usuario."""

    user_id: str
    transport: str
    role: str
    requests_used_hour: int = 0
    requests_remaining_hour: int = 0
    requests_used_minute: int = 0
    requests_remaining_minute: int = 0
    tokens_used_day: int = 0
    tokens_remaining_day: int = 0
    is_blocked: bool = False
    block_expires_at: Optional[float] = None
    block_reason: Optional[str] = None
    retry_after_seconds: int = 0
    reset_timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RateLimitResult:
    """Resultado de una verificación de rate limit."""

    allowed: bool
    status: RateLimitStatus
    headers: Dict[str, str] = field(default_factory=dict)
    message: Optional[str] = None


class RateLimiterUnified:
    """
    Rate Limiter Unificado para todos los transportes.

    Features:
    - Sliding window para requests (por hora/minuto)
    - Tracking de tokens (por día)
    - Separación por transporte (discord, telegram, api)
    - Reglas por rol (owner, trusted, public)
    - Overrides por usuario
    - SQLite persistence
    - Response headers estándar
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
        self.default_role = self.config.get("global", {}).get("default_role", "public")

        # Setup DB
        db_path = self.config.get("storage", {}).get(
            "path", "Data/rate_limits_unified.db"
        )
        self.db_path = self.base_path / db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache de requests recientes (sliding window)
        # Estructura: {user_id: {transport: [timestamps]}}
        self._requests_cache: Dict[str, Dict[str, List[float]]] = {}
        self._tokens_cache: Dict[str, Dict[str, List[Tuple[float, int]]]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = 3600  # 1 hora

        self._init_db()
        self._initialized = True

        logger.info(
            "[RateLimiterUnified] Inicializado. Roles: %d, Transports: %s",
            len(self.config.get("by_role", {})),
            ", ".join(self.config.get("transports", {}).keys()),
        )

    def _load_config(self) -> dict:
        """Carga configuración desde rate_limits_unified.json."""
        config_path = self.base_path / "Config" / "rate_limits_unified.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("[RateLimiterUnified] Error cargando config: %s", e)

        # Config por defecto
        return {
            "global": {"enabled": True, "default_role": "public"},
            "by_role": {
                "owner": {
                    "max_requests_per_hour": 1000,
                    "max_requests_per_minute": 60,
                    "max_tokens_per_day": 500000,
                    "cooldown_seconds": 0,
                    "bypass_rate_limit": True,
                },
                "trusted": {
                    "max_requests_per_hour": 500,
                    "max_requests_per_minute": 30,
                    "max_tokens_per_day": 100000,
                    "cooldown_seconds": 30,
                },
                "public": {
                    "max_requests_per_hour": 30,
                    "max_requests_per_minute": 5,
                    "max_tokens_per_day": 20000,
                    "cooldown_seconds": 60,
                },
                "system": {
                    "max_requests_per_hour": 10000,
                    "max_requests_per_minute": 200,
                    "max_tokens_per_day": 1000000,
                    "bypass_rate_limit": True,
                },
            },
            "transports": {
                "discord": {"enabled": True, "track_tokens": True},
                "telegram": {"enabled": True, "track_tokens": True},
                "api": {"enabled": True, "track_tokens": True},
                "web": {"enabled": True, "track_tokens": False},
            },
            "user_overrides": {},
            "storage": {"path": "Data/rate_limits_unified.db"},
        }

    def _init_db(self) -> None:
        """Inicializa tablas de rate limiting unificado."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Tabla de requests (sliding window por transporte)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        transport TEXT NOT NULL,
                        role TEXT NOT NULL,
                        endpoint TEXT,
                        timestamp REAL NOT NULL,
                        blocked BOOLEAN DEFAULT 0,
                        metadata TEXT  -- JSON
                    )
                """
                )

                # Tabla de tokens usados
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        transport TEXT NOT NULL,
                        tokens INTEGER DEFAULT 0,
                        timestamp REAL NOT NULL
                    )
                """
                )

                # Tabla de bloqueos
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_blocks (
                        user_id TEXT NOT NULL,
                        transport TEXT NOT NULL,
                        blocked_until REAL NOT NULL,
                        reason TEXT,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (user_id, transport)
                    )
                """
                )

                # Tabla de overrides persistentes
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_user_overrides (
                        user_id TEXT PRIMARY KEY,
                        rule_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL
                    )
                """
                )

                # Índices
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_requests_user_transport_time
                    ON rate_requests(user_id, transport, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_tokens_user_transport_time
                    ON rate_tokens(user_id, transport, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_requests_endpoint
                    ON rate_requests(endpoint, timestamp)
                """
                )

                conn.commit()
        except Exception as e:
            logger.error("[RateLimiterUnified] Error inicializando DB: %s", e)

    def _get_rule(self, user_id: str, role: Optional[str] = None) -> RateLimitRule:
        """Obtiene la regla aplicable para un usuario (con override si existe)."""
        # Verificar override en DB
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                cursor = conn.execute(
                    "SELECT rule_json, expires_at FROM rate_user_overrides WHERE user_id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()
                if row:
                    rule_json, expires_at = row
                    if expires_at and time.time() > expires_at:
                        logger.debug(
                            "[RateLimiterUnified] Override expirado para %s", user_id
                        )
                        # Eliminar override expirado de la DB
                        conn.execute(
                            "DELETE FROM rate_user_overrides WHERE user_id = ?",
                            (user_id,),
                        )
                        conn.commit()
                    else:
                        return RateLimitRule.from_dict(json.loads(rule_json))
        except Exception as e:
            logger.debug("[RateLimiterUnified] Error leyendo override: %s", e)

        # Verificar override en config
        overrides = self.config.get("user_overrides", {})
        if user_id in overrides:
            override = overrides[user_id]
            expires_at = override.get("expires_at")
            if expires_at:
                try:
                    exp_ts = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    ).timestamp()
                    if time.time() <= exp_ts:
                        return RateLimitRule.from_dict(override)
                except:
                    pass
            else:
                return RateLimitRule.from_dict(override)

        # Usar regla por rol
        return self._get_role_rule(role or self.default_role)

    def _get_role_rule(self, role: str) -> RateLimitRule:
        """Obtiene regla para un rol."""
        by_role = self.config.get("by_role", {})
        role_config = by_role.get(role, by_role.get("public", {}))
        return RateLimitRule.from_dict(role_config)

    def is_allowed(
        self,
        user_id: str,
        transport: Union[str, TransportType] = TransportType.API,
        role: Optional[str] = None,
        endpoint: str = "",
        estimated_tokens: int = 0,
    ) -> RateLimitResult:
        """
        Verifica si un usuario puede hacer una request.

        Args:
            user_id: ID del usuario
            transport: Tipo de transporte (discord, telegram, api, web)
            role: Rol del usuario (owner, trusted, public, system)
            endpoint: Endpoint API opcional
            estimated_tokens: Tokens estimados que usará

        Returns:
            RateLimitResult con allowed, status y headers
        """
        transport_str = (
            transport.value if isinstance(transport, TransportType) else transport
        )

        if not self.enabled:
            return RateLimitResult(
                allowed=True,
                status=RateLimitStatus(
                    user_id=user_id, transport=transport_str, role=role or "public"
                ),
                headers={"X-RateLimit-Limit": "0", "X-RateLimit-Remaining": "0"},
            )

        # Verificar si transport está habilitado
        transports_config = self.config.get("transports", {})
        if transport_str not in transports_config:
            logger.warning(
                "[RateLimiterUnified] Transport desconocido: %s", transport_str
            )
            transport_str = "api"

        if not transports_config.get(transport_str, {}).get("enabled", True):
            return RateLimitResult(
                allowed=True,
                status=RateLimitStatus(
                    user_id=user_id, transport=transport_str, role=role or "public"
                ),
                headers={},
            )

        rule = self._get_rule(user_id, role)

        if rule.bypass_rate_limit:
            return RateLimitResult(
                allowed=True,
                status=RateLimitStatus(
                    user_id=user_id,
                    transport=transport_str,
                    role=role or "public",
                    requests_remaining_hour=-1,
                    requests_remaining_minute=-1,
                    tokens_remaining_day=-1,
                ),
                headers={"X-RateLimit-Limit": "-1", "X-RateLimit-Remaining": "-1"},
            )

        now = time.time()
        hour_ago = now - 3600
        minute_ago = now - 60
        day_ago = now - 86400

        with self._cache_lock:
            # Inicializar cache para este usuario/transporte
            if user_id not in self._requests_cache:
                self._requests_cache[user_id] = {}
            if transport_str not in self._requests_cache[user_id]:
                self._requests_cache[user_id][transport_str] = []

            # Limpiar cache antiguo
            self._requests_cache[user_id][transport_str] = [
                ts
                for ts in self._requests_cache[user_id][transport_str]
                if ts > hour_ago
            ]

            # Contar requests en ventanas
            requests_list = self._requests_cache[user_id][transport_str]
            requests_last_hour = len(requests_list)
            requests_last_minute = len([ts for ts in requests_list if ts > minute_ago])

            # Calcular tokens usados hoy
            if user_id not in self._tokens_cache:
                self._tokens_cache[user_id] = {}
            if transport_str not in self._tokens_cache[user_id]:
                self._tokens_cache[user_id][transport_str] = []

            # Limpiar tokens antiguos
            self._tokens_cache[user_id][transport_str] = [
                (ts, tokens)
                for ts, tokens in self._tokens_cache[user_id][transport_str]
                if ts > day_ago
            ]

            tokens_last_day = sum(
                tokens for _, tokens in self._tokens_cache[user_id][transport_str]
            )

            # Verificar bloqueo activo
            is_blocked, block_reason, block_expires = self._check_block(
                user_id, transport_str
            )

            if is_blocked:
                retry_after = max(1, int(block_expires - now))
                status = RateLimitStatus(
                    user_id=user_id,
                    transport=transport_str,
                    role=role or "public",
                    requests_used_hour=requests_last_hour,
                    requests_remaining_hour=0,
                    requests_used_minute=requests_last_minute,
                    requests_remaining_minute=0,
                    tokens_used_day=tokens_last_day,
                    tokens_remaining_day=max(
                        0, rule.max_tokens_per_day - tokens_last_day
                    ),
                    is_blocked=True,
                    block_expires_at=block_expires,
                    block_reason=block_reason,
                    retry_after_seconds=retry_after,
                    reset_timestamp=block_expires,
                )
                return RateLimitResult(
                    allowed=False,
                    status=status,
                    headers=self._build_headers(status, rule),
                    message=f"Rate limit exceeded. Retry after {retry_after}s",
                )

            # Verificar límites de requests
            if requests_last_hour >= rule.max_requests_per_hour:
                retry_after = self._calculate_retry_after(
                    requests_list, rule.max_requests_per_hour, 3600
                )
                self._set_block(
                    user_id, transport_str, now + retry_after, "hourly_limit"
                )
                status = RateLimitStatus(
                    user_id=user_id,
                    transport=transport_str,
                    role=role or "public",
                    requests_used_hour=requests_last_hour,
                    requests_remaining_hour=0,
                    requests_used_minute=requests_last_minute,
                    requests_remaining_minute=0,
                    tokens_used_day=tokens_last_day,
                    tokens_remaining_day=max(
                        0, rule.max_tokens_per_day - tokens_last_day
                    ),
                    is_blocked=True,
                    block_expires_at=now + retry_after,
                    block_reason="hourly_limit",
                    retry_after_seconds=retry_after,
                    reset_timestamp=now + 3600,
                )
                self._log_blocked(user_id, transport_str, role or "public", endpoint)
                return RateLimitResult(
                    allowed=False,
                    status=status,
                    headers=self._build_headers(status, rule),
                    message=f"Hourly rate limit exceeded. Retry after {retry_after}s",
                )

            if requests_last_minute >= rule.max_requests_per_minute:
                retry_after = 60 - int(now - minute_ago) % 60
                self._set_block(
                    user_id, transport_str, now + retry_after, "minute_limit"
                )
                status = RateLimitStatus(
                    user_id=user_id,
                    transport=transport_str,
                    role=role or "public",
                    requests_used_hour=requests_last_hour,
                    requests_remaining_hour=max(
                        0, rule.max_requests_per_hour - requests_last_hour
                    ),
                    requests_used_minute=requests_last_minute,
                    requests_remaining_minute=0,
                    tokens_used_day=tokens_last_day,
                    tokens_remaining_day=max(
                        0, rule.max_tokens_per_day - tokens_last_day
                    ),
                    is_blocked=True,
                    block_expires_at=now + retry_after,
                    block_reason="minute_limit",
                    retry_after_seconds=retry_after,
                    reset_timestamp=now + 60,
                )
                self._log_blocked(user_id, transport_str, role or "public", endpoint)
                return RateLimitResult(
                    allowed=False,
                    status=status,
                    headers=self._build_headers(status, rule),
                    message=f"Minute rate limit exceeded. Retry after {retry_after}s",
                )

            # Verificar límite de tokens
            if tokens_last_day + estimated_tokens > rule.max_tokens_per_day:
                retry_after = int(day_ago + 86400 - now)
                status = RateLimitStatus(
                    user_id=user_id,
                    transport=transport_str,
                    role=role or "public",
                    requests_used_hour=requests_last_hour,
                    requests_remaining_hour=max(
                        0, rule.max_requests_per_hour - requests_last_hour - 1
                    ),
                    requests_used_minute=requests_last_minute,
                    requests_remaining_minute=max(
                        0, rule.max_requests_per_minute - requests_last_minute - 1
                    ),
                    tokens_used_day=tokens_last_day,
                    tokens_remaining_day=0,
                    is_blocked=True,
                    block_expires_at=now + retry_after,
                    block_reason="daily_tokens",
                    retry_after_seconds=retry_after,
                    reset_timestamp=now + 86400,
                )
                return RateLimitResult(
                    allowed=False,
                    status=status,
                    headers=self._build_headers(status, rule),
                    message="Daily token limit exceeded. Try again tomorrow.",
                )

            # Registrar request
            self._requests_cache[user_id][transport_str].append(now)
            if estimated_tokens > 0:
                self._tokens_cache[user_id][transport_str].append(
                    (now, estimated_tokens)
                )
            self._persist_request(user_id, transport_str, role or "public", endpoint)

            # Calcular reset timestamp
            reset_ts = now + 3600
            if requests_list:
                oldest = min(requests_list)
                reset_ts = oldest + 3600

            status = RateLimitStatus(
                user_id=user_id,
                transport=transport_str,
                role=role or "public",
                requests_used_hour=requests_last_hour + 1,
                requests_remaining_hour=max(
                    0, rule.max_requests_per_hour - requests_last_hour - 1
                ),
                requests_used_minute=requests_last_minute + 1,
                requests_remaining_minute=max(
                    0, rule.max_requests_per_minute - requests_last_minute - 1
                ),
                tokens_used_day=tokens_last_day + estimated_tokens,
                tokens_remaining_day=max(
                    0, rule.max_tokens_per_day - tokens_last_day - estimated_tokens
                ),
                is_blocked=False,
                reset_timestamp=reset_ts,
            )

            return RateLimitResult(
                allowed=True, status=status, headers=self._build_headers(status, rule)
            )

    def record_usage(
        self,
        user_id: str,
        transport: Union[str, TransportType],
        tokens_used: int = 0,
        role: Optional[str] = None,
    ) -> None:
        """
        Registra uso de tokens después de una request.

        Args:
            user_id: ID del usuario
            transport: Tipo de transporte
            tokens_used: Tokens consumidos
            role: Rol del usuario
        """
        if tokens_used <= 0:
            return

        transport_str = (
            transport.value if isinstance(transport, TransportType) else transport
        )
        now = time.time()

        with self._cache_lock:
            if user_id not in self._tokens_cache:
                self._tokens_cache[user_id] = {}
            if transport_str not in self._tokens_cache[user_id]:
                self._tokens_cache[user_id][transport_str] = []

            self._tokens_cache[user_id][transport_str].append((now, tokens_used))

        # Persistir
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    "INSERT INTO rate_tokens (user_id, transport, tokens, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, transport_str, tokens_used, now),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiterUnified] Error persistiendo tokens: %s", e)

    def _calculate_retry_after(
        self, timestamps: List[float], limit: int, window: int
    ) -> int:
        """Calcula cuándo expirará el bloqueo basado en el request más antiguo."""
        if len(timestamps) < limit:
            return window
        oldest = min(timestamps)
        return max(1, int(oldest + window - time.time()))

    def _build_headers(
        self, status: RateLimitStatus, rule: RateLimitRule
    ) -> Dict[str, str]:
        """Construye headers estándar de rate limit."""
        if rule.bypass_rate_limit:
            return {"X-RateLimit-Limit": "-1", "X-RateLimit-Remaining": "-1"}

        headers = {
            "X-RateLimit-Limit": str(rule.max_requests_per_hour),
            "X-RateLimit-Remaining": str(status.requests_remaining_hour),
            "X-RateLimit-Reset": str(int(status.reset_timestamp)),
            "X-RateLimit-Limit-Minute": str(rule.max_requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(status.requests_remaining_minute),
        }

        if status.is_blocked:
            headers["Retry-After"] = str(status.retry_after_seconds)

        return headers

    def _check_block(
        self, user_id: str, transport: str
    ) -> Tuple[bool, Optional[str], float]:
        """Verifica si el usuario está bloqueado para un transporte."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                cursor = conn.execute(
                    "SELECT blocked_until, reason FROM rate_blocks WHERE user_id = ? AND transport = ?",
                    (user_id, transport),
                )
                row = cursor.fetchone()

                if row:
                    blocked_until, reason = row
                    if blocked_until > time.time():
                        return True, reason, blocked_until
                    else:
                        # Bloqueo expirado, limpiar
                        conn.execute(
                            "DELETE FROM rate_blocks WHERE user_id = ? AND transport = ?",
                            (user_id, transport),
                        )
                        conn.commit()

                return False, None, 0.0
        except Exception as e:
            logger.error("[RateLimiterUnified] Error verificando bloqueo: %s", e)
            return False, None, 0.0

    def _set_block(
        self, user_id: str, transport: str, blocked_until: float, reason: str
    ) -> None:
        """Establece un bloqueo para un usuario/transporte."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rate_blocks (user_id, transport, blocked_until, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, transport, blocked_until, reason, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.error("[RateLimiterUnified] Error estableciendo bloqueo: %s", e)

    def _persist_request(
        self, user_id: str, transport: str, role: str, endpoint: str
    ) -> None:
        """Persiste request en SQLite (fire-and-forget)."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO rate_requests (user_id, transport, role, endpoint, timestamp, blocked)
                    VALUES (?, ?, ?, ?, ?, 0)
                    """,
                    (user_id, transport, role, endpoint, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiterUnified] Error persistiendo request: %s", e)

    def _log_blocked(
        self, user_id: str, transport: str, role: str, endpoint: str
    ) -> None:
        """Log de request bloqueada."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO rate_requests (user_id, transport, role, endpoint, timestamp, blocked)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (user_id, transport, role, endpoint, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiterUnified] Error logueando bloqueo: %s", e)

    def get_status(
        self,
        user_id: str,
        transport: Union[str, TransportType] = TransportType.API,
        role: Optional[str] = None,
    ) -> RateLimitStatus:
        """Obtiene estado completo de rate limit para un usuario."""
        transport_str = (
            transport.value if isinstance(transport, TransportType) else transport
        )
        rule = self._get_rule(user_id, role)
        now = time.time()
        hour_ago = now - 3600
        minute_ago = now - 60
        day_ago = now - 86400

        with self._cache_lock:
            requests = self._requests_cache.get(user_id, {}).get(transport_str, [])
            requests_last_hour = len([ts for ts in requests if ts > hour_ago])
            requests_last_minute = len([ts for ts in requests if ts > minute_ago])

            tokens = self._tokens_cache.get(user_id, {}).get(transport_str, [])
            tokens_last_day = sum(toks for ts, toks in tokens if ts > day_ago)

        # Calcular reset timestamp
        reset_ts = now + 3600
        if requests:
            oldest = min(requests)
            reset_ts = oldest + 3600

        # Verificar bloqueo
        is_blocked, block_reason, block_expires = self._check_block(
            user_id, transport_str
        )

        return RateLimitStatus(
            user_id=user_id,
            transport=transport_str,
            role=role or "public",
            requests_used_hour=requests_last_hour,
            requests_remaining_hour=max(
                0, rule.max_requests_per_hour - requests_last_hour
            ),
            requests_used_minute=requests_last_minute,
            requests_remaining_minute=max(
                0, rule.max_requests_per_minute - requests_last_minute
            ),
            tokens_used_day=tokens_last_day,
            tokens_remaining_day=max(0, rule.max_tokens_per_day - tokens_last_day),
            is_blocked=is_blocked,
            block_expires_at=block_expires if is_blocked else None,
            block_reason=block_reason,
            retry_after_seconds=max(0, int(block_expires - now)) if is_blocked else 0,
            reset_timestamp=reset_ts,
        )

    def manual_block(
        self,
        user_id: str,
        transport: Union[str, TransportType],
        duration_seconds: int,
        reason: str,
    ) -> bool:
        """Bloquea manualmente a un usuario."""
        transport_str = (
            transport.value if isinstance(transport, TransportType) else transport
        )
        try:
            blocked_until = time.time() + duration_seconds
            self._set_block(user_id, transport_str, blocked_until, reason)
            logger.info(
                "[RateLimiterUnified] Bloqueo manual para %s/%s: %s (%ds)",
                user_id,
                transport_str,
                reason,
                duration_seconds,
            )
            return True
        except Exception as e:
            logger.error("[RateLimiterUnified] Error en bloqueo manual: %s", e)
            return False

    def unblock(
        self, user_id: str, transport: Optional[Union[str, TransportType]] = None
    ) -> bool:
        """Desbloquea a un usuario (de un transporte o todos)."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                if transport:
                    transport_str = (
                        transport.value
                        if isinstance(transport, TransportType)
                        else transport
                    )
                    conn.execute(
                        "DELETE FROM rate_blocks WHERE user_id = ? AND transport = ?",
                        (user_id, transport_str),
                    )
                else:
                    conn.execute(
                        "DELETE FROM rate_blocks WHERE user_id = ?", (user_id,)
                    )
                conn.commit()
            logger.info("[RateLimiterUnified] Desbloqueado: %s", user_id)
            return True
        except Exception as e:
            logger.error("[RateLimiterUnified] Error desbloqueando: %s", e)
            return False

    def create_override(
        self,
        user_id: str,
        max_requests_per_hour: int,
        max_requests_per_minute: int = 10,
        max_tokens_per_day: int = 50000,
        reason: str = "",
        duration_hours: Optional[float] = None,
    ) -> bool:
        """Crea un override temporal para un usuario."""
        try:
            rule = RateLimitRule(
                max_requests_per_hour=max_requests_per_hour,
                max_requests_per_minute=max_requests_per_minute,
                max_tokens_per_day=max_tokens_per_day,
                description=reason,
            )

            if duration_hours:
                expires_dt = datetime.now(timezone.utc) + timedelta(
                    hours=duration_hours
                )
                rule.expires_at = expires_dt.isoformat().replace("+00:00", "Z")

            # Guardar en DB
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rate_user_overrides
                    (user_id, rule_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        json.dumps(rule.to_dict()),
                        time.time(),
                        datetime.now(timezone.utc).timestamp() + (duration_hours * 3600)
                        if duration_hours
                        else None,
                    ),
                )
                conn.commit()

            logger.info(
                "[RateLimiterUnified] Override creado para %s: %d req/hr",
                user_id,
                max_requests_per_hour,
            )
            return True
        except Exception as e:
            logger.error("[RateLimiterUnified] Error creando override: %s", e)
            return False

    def remove_override(self, user_id: str) -> bool:
        """Elimina un override de usuario."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    "DELETE FROM rate_user_overrides WHERE user_id = ?", (user_id,)
                )
                conn.commit()

            # También de config en memoria
            overrides = self.config.get("user_overrides", {})
            if user_id in overrides:
                del overrides[user_id]

            logger.info("[RateLimiterUnified] Override eliminado para %s", user_id)
            return True
        except Exception as e:
            logger.error("[RateLimiterUnified] Error eliminando override: %s", e)
            return False

    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Estadísticas globales de rate limiting."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cutoff = time.time() - (hours * 3600)

                # Total requests por transporte
                cursor = conn.execute(
                    """
                    SELECT transport, COUNT(*), SUM(blocked)
                    FROM rate_requests
                    WHERE timestamp > ?
                    GROUP BY transport
                    """,
                    (cutoff,),
                )
                by_transport = {
                    row[0]: {"requests": row[1], "blocked": row[2] or 0}
                    for row in cursor.fetchall()
                }

                # Top usuarios bloqueados
                cursor = conn.execute(
                    """
                    SELECT user_id, transport, COUNT(*) as count
                    FROM rate_requests
                    WHERE timestamp > ? AND blocked = 1
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    (cutoff,),
                )
                top_blocked = [
                    {"user_id": r[0], "transport": r[1], "blocked_count": r[2]}
                    for r in cursor.fetchall()
                ]

                # Por rol
                cursor = conn.execute(
                    "SELECT role, COUNT(*) FROM rate_requests WHERE timestamp > ? GROUP BY role",
                    (cutoff,),
                )
                by_role = {r[0]: r[1] for r in cursor.fetchall()}

                return {
                    "period_hours": hours,
                    "by_transport": by_transport,
                    "by_role": by_role,
                    "top_blocked": top_blocked,
                }
        except Exception as e:
            logger.error("[RateLimiterUnified] Error obteniendo stats: %s", e)
            return {}


# Singleton global
_rate_limiter_unified_instance: Optional[RateLimiterUnified] = None


def get_rate_limiter(base_path: Optional[Path] = None) -> RateLimiterUnified:
    """Obtiene instancia singleton del RateLimiterUnified."""
    global _rate_limiter_unified_instance
    if _rate_limiter_unified_instance is None:
        _rate_limiter_unified_instance = RateLimiterUnified(base_path)
    return _rate_limiter_unified_instance


def check_rate_limit(
    user_id: str,
    transport: Union[str, TransportType] = "api",
    role: Optional[str] = None,
    estimated_tokens: int = 0,
) -> Tuple[bool, Optional[str]]:
    """Función conveniencia para verificar rate limit. Retorna (permitido, mensaje)."""
    limiter = get_rate_limiter()
    result = limiter.is_allowed(
        user_id, transport, role, estimated_tokens=estimated_tokens
    )
    return result.allowed, result.message


def record_message_usage(
    user_id: str,
    transport: str = "discord",
    tokens_used: int = 0,
    role: Optional[str] = None,
) -> None:
    """Función conveniencia para registrar uso (compatible con rate_limiter.py antiguo)."""
    limiter = get_rate_limiter()
    limiter.record_usage(user_id, transport, tokens_used, role)


# Backwards compatibility con rate_limiter.py
class RateLimiter:
    """Wrapper para compatibilidad con código antiguo que usaba RateLimiter."""

    def __init__(self, base_path: Optional[Path] = None):
        self._limiter = get_rate_limiter(base_path)

    def check_rate_limit(
        self, user_id: str, guild_id: Optional[str] = None, estimated_tokens: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """Compatibilidad con API antigua."""
        result = self._limiter.is_allowed(
            user_id=user_id,
            transport=TransportType.DISCORD,
            estimated_tokens=estimated_tokens,
        )
        return result.allowed, result.message

    def record_usage(
        self,
        user_id: str,
        content_length: int = 0,
        tokens_used: int = 0,
        guild_id: Optional[str] = None,
    ) -> None:
        """Compatibilidad con API antigua."""
        self._limiter.record_usage(user_id, TransportType.DISCORD, tokens_used)

    def get_status(self, user_id: str) -> Any:
        """Compatibilidad con API antigua."""
        return self._limiter.get_status(user_id, TransportType.DISCORD)

    def manual_block(self, user_id: str, duration_seconds: int, reason: str) -> bool:
        """Compatibilidad con API antigua."""
        return self._limiter.manual_block(
            user_id, TransportType.DISCORD, duration_seconds, reason
        )

    def unblock(self, user_id: str) -> bool:
        """Compatibilidad con API antigua."""
        return self._limiter.unblock(user_id, TransportType.DISCORD)


__all__ = [
    "RateLimiterUnified",
    "RateLimiter",  # Backwards compatibility
    "RateLimitRule",
    "RateLimitStatus",
    "RateLimitResult",
    "TransportType",
    "UserRole",
    "get_rate_limiter",
    "check_rate_limit",
    "record_message_usage",
]
