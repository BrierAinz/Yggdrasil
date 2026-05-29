"""
Lilith v5.1 — TelegramProgressStreamer
Sistema de progress streaming para operaciones PC en Telegram.

Features:
- Rate limiting (max 1 edit/segundo)
- Buffer de actualizaciones rápidas
- Progress bars visuales
- Emoji status indicators
- Fallback a mensajes nuevos si falla el edit
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.telegram.progress_streamer")


class StepStatus(Enum):
    """Estados posibles de un paso."""

    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class ProgressUpdate:
    """Representa una actualización de progreso."""

    step_index: int
    total_steps: int
    step_id: str
    status: StepStatus
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressConfig:
    """Configuración para el progress streamer."""

    rate_limit_seconds: float = 1.0
    buffer_max_size: int = 10
    enable_progress_bar: bool = True
    enable_time_estimate: bool = True
    emoji_set: str = "default"
    max_message_length: int = 4000


class TelegramProgressStreamer:
    """
    Streamer de progreso para Telegram con rate limiting y buffering.

    Maneja la visualización de progreso en tiempo real durante la ejecución
    de planes de PC Agent, respetando los límites de la API de Telegram.
    """

    # Emoji sets
    EMOJI_SETS = {
        "default": {
            StepStatus.PENDING: "⏸️",
            StepStatus.WORKING: "⏳",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
        },
        "minimal": {
            StepStatus.PENDING: "○",
            StepStatus.WORKING: "◐",
            StepStatus.COMPLETED: "●",
            StepStatus.FAILED: "✕",
        },
        "fun": {
            StepStatus.PENDING: "🌑",
            StepStatus.WORKING: "🌕",
            StepStatus.COMPLETED: "🎉",
            StepStatus.FAILED: "💥",
        },
    }

    def __init__(
        self,
        bot_token: str,
        chat_id: int,
        message_id: int,
        config: Optional[ProgressConfig] = None,
        http_client: Optional[Any] = None,
    ):
        """
        Inicializa el streamer.

        Args:
            bot_token: Token del bot de Telegram
            chat_id: ID del chat
            message_id: ID del mensaje a editar
            config: Configuración opcional
            http_client: Cliente HTTP opcional (httpx.AsyncClient)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.message_id = message_id
        self.config = config or ProgressConfig()
        self.http_client = http_client

        # Rate limiting
        self._last_update = 0.0
        self._buffer: List[ProgressUpdate] = []
        self._buffer_lock = asyncio.Lock()

        # Estado
        self._current_step = 0
        self._total_steps = 0
        self._step_states: Dict[str, StepStatus] = {}
        self._step_messages: Dict[str, str] = {}
        self._start_time = time.time()
        self._completed = False

        # Callback para tests
        self._on_update: Optional[Callable[[ProgressUpdate], None]] = None

    def set_update_callback(self, callback: Callable[[ProgressUpdate], None]):
        """Establece callback para recibir actualizaciones (para tests)."""
        self._on_update = callback

    def _get_emoji(self, status: StepStatus) -> str:
        """Obtiene el emoji correspondiente al estado."""
        emoji_set = self.EMOJI_SETS.get(
            self.config.emoji_set, self.EMOJI_SETS["default"]
        )
        return emoji_set.get(status, "•")

    def _build_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Construye una barra de progreso visual."""
        if not self.config.enable_progress_bar or total <= 0:
            return ""

        filled = int(width * current / total)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        percentage = int(100 * current / total)

        return f"[{bar}] {percentage}%"

    def _format_time_estimate(self, current: int, total: int) -> str:
        """Calcula y formatea tiempo estimado restante."""
        if not self.config.enable_time_estimate or current <= 0 or total <= 0:
            return ""

        elapsed = time.time() - self._start_time
        avg_time_per_step = elapsed / current
        remaining_steps = total - current
        estimated_remaining = avg_time_per_step * remaining_steps

        if estimated_remaining < 60:
            return f"~{int(estimated_remaining)}s restantes"
        elif estimated_remaining < 3600:
            return f"~{int(estimated_remaining / 60)}m restantes"
        else:
            return f"~{int(estimated_remaining / 3600)}h {int((estimated_remaining % 3600) / 60)}m restantes"

    def _build_message(self, current_update: Optional[ProgressUpdate] = None) -> str:
        """Construye el mensaje de progreso completo."""
        lines = ["📊 **Ejecutando operaciones PC**", ""]

        # Barra de progreso principal
        if self._total_steps > 0:
            progress_bar = self._build_progress_bar(
                self._current_step, self._total_steps
            )
            lines.append(f"{progress_bar}")
            lines.append(f"Paso {self._current_step}/{self._total_steps}")

            # Tiempo estimado
            time_est = self._format_time_estimate(self._current_step, self._total_steps)
            if time_est:
                lines.append(f"⏱️ {time_est}")
            lines.append("")

        # Lista de pasos (últimos 5 para no hacer el mensaje muy largo)
        if self._step_states:
            lines.append("**Pasos:**")

            # Mostrar pasos relevantes
            step_items = list(self._step_states.items())

            # Si hay muchos pasos, mostrar solo los recientes
            if len(step_items) > 5:
                lines.append("...")
                step_items = step_items[-5:]

            for step_id, status in step_items:
                emoji = self._get_emoji(status)
                msg = self._step_messages.get(step_id, "")

                # Truncar mensaje largo
                if len(msg) > 40:
                    msg = msg[:37] + "..."

                if status == StepStatus.WORKING:
                    lines.append(f"{emoji} **{step_id}**: {msg}")
                elif status == StepStatus.FAILED:
                    lines.append(f"{emoji} ~~{step_id}~~: {msg}")
                else:
                    lines.append(f"{emoji} {step_id}: {msg}")

        # Estado actual
        if current_update and current_update.status == StepStatus.WORKING:
            lines.append("")
            lines.append(f"_⏳ {current_update.message}_")

        message = "\n".join(lines)

        # Truncar si es necesario
        if len(message) > self.config.max_message_length:
            message = message[: self.config.max_message_length - 3] + "..."

        return message

    async def update_progress(
        self,
        step_index: int,
        total_steps: int,
        step_id: str,
        status: str,
        message: str,
    ) -> bool:
        """
        Actualiza el progreso. Puede ser llamado frecuentemente;
        maneja rate limiting internamente.

        Args:
            step_index: Índice del paso actual (1-based)
            total_steps: Total de pasos
            step_id: ID del paso
            status: Estado ('working', 'completed', 'failed', 'pending')
            message: Mensaje descriptivo

        Returns:
            True si se envió la actualización, False si se bufferizó
        """
        # Convertir string status a enum
        try:
            status_enum = StepStatus(status)
        except ValueError:
            status_enum = StepStatus.WORKING

        # Actualizar estado interno
        self._current_step = step_index
        self._total_steps = total_steps
        self._step_states[step_id] = status_enum
        self._step_messages[step_id] = message

        # Crear objeto de actualización
        update = ProgressUpdate(
            step_index=step_index,
            total_steps=total_steps,
            step_id=step_id,
            status=status_enum,
            message=message,
        )

        # Notificar callback si existe
        if self._on_update:
            try:
                self._on_update(update)
            except Exception:
                pass

        # Verificar rate limiting
        now = time.time()
        time_since_last = now - self._last_update

        async with self._buffer_lock:
            # Si estamos en rate limit, agregar al buffer
            if time_since_last < self.config.rate_limit_seconds:
                self._buffer.append(update)

                # Limitar tamaño del buffer
                if len(self._buffer) > self.config.buffer_max_size:
                    self._buffer = self._buffer[-self.config.buffer_max_size :]

                return False

            # Enviar actualización
            success = await self._send_update(update)

            if success:
                self._last_update = now

                # Programar procesamiento del buffer
                if self._buffer:
                    asyncio.create_task(self._process_buffer())

            return success

    async def _send_update(self, update: ProgressUpdate) -> bool:
        """Envía actualización a Telegram editando el mensaje."""
        message = self._build_message(update)

        try:
            # Usar http_client si está disponible, sino crear uno
            if self.http_client:
                return await self._edit_message(message)
            else:
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    self.http_client = client
                    return await self._edit_message(message)
        except Exception as e:
            logger.warning("[TelegramProgressStreamer] Error enviando update: %s", e)
            return False

    async def _edit_message(self, text: str) -> bool:
        """Edita el mensaje en Telegram."""
        import httpx

        url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        payload = {
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        try:
            if isinstance(self.http_client, httpx.AsyncClient):
                resp = await self.http_client.post(url, json=payload)
            else:
                # Crear cliente temporal
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)

            if resp.status_code == 200:
                return True

            # Si el mensaje no cambió, no es error
            data = resp.json()
            if (
                not data.get("ok")
                and "message is not modified"
                in str(data.get("description", "")).lower()
            ):
                return True

            logger.debug("[TelegramProgressStreamer] Edit falló: %s", data)
            return False

        except Exception as e:
            logger.warning("[TelegramProgressStreamer] Error editando mensaje: %s", e)
            return False

    async def _process_buffer(self):
        """Procesa actualizaciones bufferizadas después del rate limit."""
        await asyncio.sleep(self.config.rate_limit_seconds)

        async with self._buffer_lock:
            if not self._buffer:
                return

            # Tomar la última actualización (más reciente)
            last_update = self._buffer[-1]
            self._buffer.clear()

        # Enviar última actualización
        success = await self._send_update(last_update)
        if success:
            self._last_update = time.time()

    async def finalize(self, success: bool = True, final_message: Optional[str] = None):
        """
        Finaliza el stream de progreso.

        Args:
            success: Si la operación fue exitosa
            final_message: Mensaje final opcional
        """
        self._completed = True

        # Construir mensaje final
        if final_message:
            message = final_message
        else:
            emoji = "✅" if success else "❌"
            status = "Completado" if success else "Fallido"
            message = f"{emoji} **Operación {status}**\n\n"
            message += f"{self._current_step}/{self._total_steps} pasos ejecutados"

            elapsed = time.time() - self._start_time
            if elapsed < 60:
                message += f"\n⏱️ {int(elapsed)}s"
            else:
                message += f"\n⏱️ {int(elapsed / 60)}m {int(elapsed % 60)}s"

        # Enviar mensaje final
        await self._edit_message(message)

        logger.info(
            "[TelegramProgressStreamer] Finalizado: %s pasos en %.1fs",
            self._current_step,
            time.time() - self._start_time,
        )

    async def send_error(self, error_message: str):
        """Envía mensaje de error."""
        message = f"❌ **Error durante la ejecución**\n\n{error_message}"
        await self._edit_message(message)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del streaming."""
        elapsed = time.time() - self._start_time

        completed = sum(
            1 for s in self._step_states.values() if s == StepStatus.COMPLETED
        )
        failed = sum(1 for s in self._step_states.values() if s == StepStatus.FAILED)

        return {
            "total_steps": self._total_steps,
            "completed_steps": completed,
            "failed_steps": failed,
            "elapsed_seconds": elapsed,
            "average_step_time": elapsed / max(completed, 1),
        }


class BufferedProgressStreamer:
    """
    Versión bufferizada del streamer que acumula actualizaciones
    y las envía en intervalos regulares.

    Útil para operaciones muy rápidas donde se generan muchas
    actualizaciones en poco tiempo.
    """

    def __init__(
        self,
        streamer: TelegramProgressStreamer,
        buffer_interval: float = 2.0,
    ):
        self.streamer = streamer
        self.buffer_interval = buffer_interval
        self._buffer: List[ProgressUpdate] = []
        self._lock = asyncio.Lock()
        self._timer: Optional[asyncio.Task] = None
        self._closed = False

    async def update_progress(
        self,
        step_index: int,
        total_steps: int,
        step_id: str,
        status: str,
        message: str,
    ) -> bool:
        """Agrega actualización al buffer."""
        if self._closed:
            return False

        try:
            status_enum = StepStatus(status)
        except ValueError:
            status_enum = StepStatus.WORKING

        update = ProgressUpdate(
            step_index=step_index,
            total_steps=total_steps,
            step_id=step_id,
            status=status_enum,
            message=message,
        )

        async with self._lock:
            self._buffer.append(update)

            # Iniciar timer si no está corriendo
            if self._timer is None or self._timer.done():
                self._timer = asyncio.create_task(self._flush_after_delay())

        return True

    async def _flush_after_delay(self):
        """Espera el intervalo y flushea el buffer."""
        await asyncio.sleep(self.buffer_interval)
        await self.flush()

    async def flush(self):
        """Envía la última actualización del buffer."""
        async with self._lock:
            if not self._buffer:
                return

            last_update = self._buffer[-1]
            self._buffer.clear()

        await self.streamer.update_progress(
            step_index=last_update.step_index,
            total_steps=last_update.total_steps,
            step_id=last_update.step_id,
            status=last_update.status.value,
            message=last_update.message,
        )

    async def close(self):
        """Cierra el buffer y flushea pendientes."""
        self._closed = True

        if self._timer and not self._timer.done():
            self._timer.cancel()
            try:
                await self._timer
            except asyncio.CancelledError:
                pass

        await self.flush()


# Factory function para crear el streamer adecuado
def create_progress_streamer(
    bot_token: str,
    chat_id: int,
    message_id: int,
    use_buffer: bool = True,
    config: Optional[ProgressConfig] = None,
) -> TelegramProgressStreamer | BufferedProgressStreamer:
    """
    Factory para crear un streamer de progreso.

    Args:
        bot_token: Token del bot de Telegram
        chat_id: ID del chat
        message_id: ID del mensaje a editar
        use_buffer: Si usar buffering de actualizaciones
        config: Configuración opcional

    Returns:
        Instancia de TelegramProgressStreamer o BufferedProgressStreamer
    """
    base_streamer = TelegramProgressStreamer(
        bot_token=bot_token,
        chat_id=chat_id,
        message_id=message_id,
        config=config,
    )

    if use_buffer:
        return BufferedProgressStreamer(
            streamer=base_streamer,
            buffer_interval=config.rate_limit_seconds if config else 1.0,
        )

    return base_streamer
