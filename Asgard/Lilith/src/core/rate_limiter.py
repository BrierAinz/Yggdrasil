"""
Rate Limiter para Crystal - Control de límites de uso para usuarios públicos.
Implementa sliding window para mensajes por hora y tokens por día.
Persistencia en SQLite.
"""
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting."""

    max_messages_per_hour: int = 10
    max_tokens_per_day: int = 50000
    cooldown_seconds: int = 60
    block_message: str = "⏱️ Límite alcanzado. Espera {minutes} minutos."


@dataclass
class RateLimitStatus:
    """Estado de rate limit para un usuario."""

    user_id: str
    messages_used: int
    messages_remaining: int
    tokens_used: int
    tokens_remaining: int
    is_blocked: bool
    block_expires_at: Optional[float] = None
    next_reset: float = 0.0


class RateLimiter:
    """
    Rate Limiter con sliding window para usuarios públicos.
    - Mensajes por hora (sliding window de 60 min)
    - Tokens por día (sliding window de 24h)
    - Cooldown entre mensajes
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, base_path: Optional[Path] = None, db_name: str = "rate_limits.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, base_path: Optional[Path] = None, db_name: str = "rate_limits.db"
    ):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.db_path = self.base_path / "Data" / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._config = self._load_config()
        self._local_lock = threading.RLock()

        self._init_db()
        self._initialized = True

        logger.info(
            "[RateLimiter] Inicializado: %d msg/hr, %d tokens/day",
            self._config.max_messages_per_hour,
            self._config.max_tokens_per_day,
        )

    def _load_config(self) -> RateLimitConfig:
        """Carga configuración desde crystal.json."""
        try:
            crystal_path = self.base_path / "Config" / "crystal.json"
            if crystal_path.exists():
                data = json.loads(crystal_path.read_text(encoding="utf-8"))
                rl_config = data.get("rate_limit", {})
                return RateLimitConfig(
                    max_messages_per_hour=rl_config.get("max_messages_per_hour", 10),
                    max_tokens_per_day=rl_config.get("max_tokens_per_day", 50000),
                    cooldown_seconds=rl_config.get("cooldown_seconds", 60),
                    block_message=rl_config.get(
                        "block_message",
                        "⏱️ Límite alcanzado. Espera {minutes} minutos.",
                    ),
                )
        except Exception as e:
            logger.warning("[RateLimiter] Error cargando config: %s", e)
        return RateLimitConfig()

    def _init_db(self) -> None:
        """Inicializa tablas de rate limiting."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Tabla de mensajes (sliding window)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS message_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        guild_id TEXT,
                        timestamp REAL NOT NULL,
                        content_length INTEGER DEFAULT 0
                    )
                """
                )

                # Tabla de tokens usados
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS token_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        guild_id TEXT,
                        tokens INTEGER DEFAULT 0,
                        timestamp REAL NOT NULL
                    )
                """
                )

                # Tabla de bloqueos
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS blocks (
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
                    CREATE INDEX IF NOT EXISTS idx_msg_user_time
                    ON message_log(user_id, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_token_user_time
                    ON token_log(user_id, timestamp)
                """
                )

                conn.commit()
        except Exception as e:
            logger.error("[RateLimiter] Error inicializando DB: %s", e)

    def _cleanup_old_records(self) -> None:
        """Limpia registros antiguos (más de 24h)."""
        cutoff = time.time() - (24 * 60 * 60)
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute("DELETE FROM message_log WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM token_log WHERE timestamp < ?", (cutoff,))
                conn.execute(
                    "DELETE FROM blocks WHERE blocked_until < ?", (time.time(),)
                )
                conn.commit()
        except Exception as e:
            logger.debug("[RateLimiter] Error limpiando registros: %s", e)

    def check_rate_limit(
        self,
        user_id: str,
        guild_id: Optional[str] = None,
        estimated_tokens: int = 0,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica si un usuario puede enviar un mensaje.

        Args:
            user_id: ID del usuario Discord
            guild_id: ID del servidor (opcional)
            estimated_tokens: Estimación de tokens que usará

        Returns:
            Tuple (permitido, mensaje_bloqueo)
            Si permitido es True, mensaje_bloqueo es None
        """
        self._cleanup_old_records()

        with self._local_lock:
            # Verificar bloqueo activo
            is_blocked, block_reason, blocked_until = self._check_block(user_id)
            if is_blocked:
                minutes_left = max(1, int((blocked_until - time.time()) / 60))
                message = self._config.block_message.format(minutes=minutes_left)
                logger.info(
                    "[RateLimiter] User %s bloqueado hasta %.0f", user_id, blocked_until
                )
                return False, message

            # Verificar mensajes por hora (sliding window de 60 min)
            now = time.time()
            hour_ago = now - 3600

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM message_log WHERE user_id = ? AND timestamp > ?",
                    (user_id, hour_ago),
                )
                messages_last_hour = cursor.fetchone()[0]

                if messages_last_hour >= self._config.max_messages_per_hour:
                    # Bloquear por cooldown
                    self._set_block(
                        user_id, now + self._config.cooldown_seconds, "hourly_limit"
                    )
                    logger.warning(
                        "[RateLimiter] User %s alcanzó límite de %d mensajes/hora",
                        user_id,
                        self._config.max_messages_per_hour,
                    )
                    minutes = self._config.cooldown_seconds // 60
                    return False, self._config.block_message.format(minutes=minutes)

                # Verificar tokens por día (sliding window de 24h)
                day_ago = now - (24 * 60 * 60)
                cursor = conn.execute(
                    "SELECT COALESCE(SUM(tokens), 0) FROM token_log WHERE user_id = ? AND timestamp > ?",
                    (user_id, day_ago),
                )
                tokens_last_day = cursor.fetchone()[0]

                if tokens_last_day + estimated_tokens > self._config.max_tokens_per_day:
                    logger.warning(
                        "[RateLimiter] User %s alcanzó límite de %d tokens/día",
                        user_id,
                        self._config.max_tokens_per_day,
                    )
                    return (
                        False,
                        "⏱️ Has alcanzado el límite diario de tokens. Intenta mañana.",
                    )

            return True, None

    def _check_block(self, user_id: str) -> Tuple[bool, Optional[str], float]:
        """Verifica si el usuario está bloqueado."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    "SELECT blocked_until, reason FROM blocks WHERE user_id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()

                if row:
                    blocked_until, reason = row
                    if blocked_until > time.time():
                        return True, reason, blocked_until
                    else:
                        # Bloqueo expirado, limpiar
                        conn.execute("DELETE FROM blocks WHERE user_id = ?", (user_id,))
                        conn.commit()

                return False, None, 0.0
        except Exception as e:
            logger.error("[RateLimiter] Error verificando bloqueo: %s", e)
            return False, None, 0.0

    def _set_block(self, user_id: str, blocked_until: float, reason: str) -> None:
        """Establece un bloqueo para un usuario."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO blocks (user_id, blocked_until, reason, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, blocked_until, reason, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.error("[RateLimiter] Error estableciendo bloqueo: %s", e)

    def record_usage(
        self,
        user_id: str,
        content_length: int = 0,
        tokens_used: int = 0,
        guild_id: Optional[str] = None,
    ) -> None:
        """
        Registra uso de un mensaje.

        Args:
            user_id: ID del usuario
            content_length: Longitud del contenido
            tokens_used: Tokens consumidos
            guild_id: ID del servidor
        """
        now = time.time()

        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Registrar mensaje
                conn.execute(
                    "INSERT INTO message_log (user_id, guild_id, timestamp, content_length) VALUES (?, ?, ?, ?)",
                    (user_id, guild_id, now, content_length),
                )

                # Registrar tokens si hay
                if tokens_used > 0:
                    conn.execute(
                        "INSERT INTO token_log (user_id, guild_id, tokens, timestamp) VALUES (?, ?, ?, ?)",
                        (user_id, guild_id, tokens_used, now),
                    )

                conn.commit()

                logger.debug(
                    "[RateLimiter] Recorded usage for user %s: msg_len=%d, tokens=%d",
                    user_id,
                    content_length,
                    tokens_used,
                )
        except Exception as e:
            logger.error("[RateLimiter] Error registrando uso: %s", e)

    def get_status(self, user_id: str) -> RateLimitStatus:
        """Obtiene el estado actual de rate limit de un usuario."""
        self._cleanup_old_records()

        now = time.time()
        hour_ago = now - 3600
        day_ago = now - (24 * 60 * 60)

        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Mensajes usados
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM message_log WHERE user_id = ? AND timestamp > ?",
                    (user_id, hour_ago),
                )
                messages_used = cursor.fetchone()[0]

                # Tokens usados
                cursor = conn.execute(
                    "SELECT COALESCE(SUM(tokens), 0) FROM token_log WHERE user_id = ? AND timestamp > ?",
                    (user_id, day_ago),
                )
                tokens_used = cursor.fetchone()[0]

                # Bloqueo
                is_blocked, _, blocked_until = self._check_block(user_id)

                # Calcular próximo reset (cuando el mensaje más antiguo expire)
                cursor = conn.execute(
                    "SELECT MIN(timestamp) FROM message_log WHERE user_id = ? AND timestamp > ?",
                    (user_id, hour_ago),
                )
                oldest_msg = cursor.fetchone()[0]
                next_reset = (oldest_msg + 3600) if oldest_msg else now + 3600

                return RateLimitStatus(
                    user_id=user_id,
                    messages_used=messages_used,
                    messages_remaining=max(
                        0, self._config.max_messages_per_hour - messages_used
                    ),
                    tokens_used=tokens_used,
                    tokens_remaining=max(
                        0, self._config.max_tokens_per_day - tokens_used
                    ),
                    is_blocked=is_blocked,
                    block_expires_at=blocked_until if is_blocked else None,
                    next_reset=next_reset,
                )
        except Exception as e:
            logger.error("[RateLimiter] Error obteniendo status: %s", e)
            return RateLimitStatus(
                user_id=user_id,
                messages_used=0,
                messages_remaining=self._config.max_messages_per_hour,
                tokens_used=0,
                tokens_remaining=self._config.max_tokens_per_day,
                is_blocked=False,
                next_reset=now + 3600,
            )

    def manual_block(self, user_id: str, duration_seconds: int, reason: str) -> bool:
        """Bloquea manualmente a un usuario."""
        try:
            blocked_until = time.time() + duration_seconds
            self._set_block(user_id, blocked_until, reason)
            logger.info(
                "[RateLimiter] Manual block for user %s: %s (%ds)",
                user_id,
                reason,
                duration_seconds,
            )
            return True
        except Exception as e:
            logger.error("[RateLimiter] Error en bloqueo manual: %s", e)
            return False

    def unblock(self, user_id: str) -> bool:
        """Desbloquea a un usuario."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute("DELETE FROM blocks WHERE user_id = ?", (user_id,))
                conn.commit()
            logger.info("[RateLimiter] Unblocked user %s", user_id)
            return True
        except Exception as e:
            logger.error("[RateLimiter] Error desbloqueando: %s", e)
            return False


# Singleton global
_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter(base_path: Optional[Path] = None) -> RateLimiter:
    """Obtiene instancia singleton del RateLimiter."""
    global _limiter_instance
    if _limiter_instance is None:
        _limiter_instance = RateLimiter(base_path)
    return _limiter_instance


def check_user_rate_limit(
    user_id: str,
    guild_id: Optional[str] = None,
    estimated_tokens: int = 0,
    base_path: Optional[Path] = None,
) -> Tuple[bool, Optional[str]]:
    """Función conveniencia para verificar rate limit."""
    limiter = get_rate_limiter(base_path)
    return limiter.check_rate_limit(user_id, guild_id, estimated_tokens)


def record_message_usage(
    user_id: str,
    content_length: int = 0,
    tokens_used: int = 0,
    guild_id: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> None:
    """Función conveniencia para registrar uso."""
    limiter = get_rate_limiter(base_path)
    limiter.record_usage(user_id, content_length, tokens_used, guild_id)


__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitStatus",
    "get_rate_limiter",
    "check_user_rate_limit",
    "record_message_usage",
]
