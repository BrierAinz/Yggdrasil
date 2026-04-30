"""
Discord Rich Notifier - Sistema de notificaciones con embeds ricos
Templates de embeds con colores, botones y agrupación
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import discord
from discord.ui import Button, View

logger = logging.getLogger("lilith.discord_rich_notifier")


class NotificationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationTemplate(Enum):
    HEALTH_CHECK_FAILED = "health_check_failed"
    BACKUP_COMPLETED = "backup_completed"
    PATTERN_DETECTED = "pattern_detected"
    TASK_COMPLETED = "task_completed"
    SYSTEM_ALERT = "system_alert"
    AUTO_LEARN_SUGGESTION = "auto_learn_suggestion"


# Configuración de colores para embeds
EMBED_COLORS = {
    NotificationSeverity.INFO: 0x3498DB,  # Azul
    NotificationSeverity.WARNING: 0xFF9900,  # Naranja
    NotificationSeverity.ERROR: 0xFF0000,  # Rojo
    NotificationSeverity.SUCCESS: 0x00FF00,  # Verde
    "lilith_purple": 0x7C6AF7,  # Morado Lilith
}

# Templates de notificaciones
EMBED_TEMPLATES = {
    NotificationTemplate.HEALTH_CHECK_FAILED: {
        "title": "⚠️ Subsistema falló",
        "severity": NotificationSeverity.WARNING,
        "fields": [
            {"name": "Subsistema", "value": "{subsystem}", "inline": True},
            {"name": "Razón", "value": "{reason}", "inline": True},
            {"name": "Timestamp", "value": "{timestamp}", "inline": True},
        ],
        "footer": "Auto-recuperación en progreso...",
        "buttons": [
            {
                "label": "🔄 Reintentar",
                "style": "primary",
                "custom_id": "retry_recovery",
            },
            {"label": "📋 Ver logs", "style": "secondary", "custom_id": "view_logs"},
        ],
    },
    NotificationTemplate.BACKUP_COMPLETED: {
        "title": "✅ Backup completado",
        "severity": NotificationSeverity.SUCCESS,
        "fields": [
            {"name": "Archivo", "value": "{filename}", "inline": True},
            {"name": "Tamaño", "value": "{size_mb} MB", "inline": True},
            {"name": "Duración", "value": "{duration}s", "inline": True},
        ],
        "footer": "Backup automático",
        "timestamp": True,
        "buttons": [
            {"label": "✓ OK", "style": "success", "custom_id": "dismiss"},
            {"label": "📋 Detalles", "style": "secondary", "custom_id": "view_details"},
        ],
    },
    NotificationTemplate.PATTERN_DETECTED: {
        "title": "🔍 Sugerencia de automatización",
        "severity": NotificationSeverity.INFO,
        "color": "lilith_purple",
        "description": "{suggestion_text}",
        "fields": [
            {"name": "Pattern", "value": "{pattern_name}", "inline": True},
            {"name": "Confianza", "value": "{confidence}%", "inline": True},
        ],
        "footer": "Responde 'sí' o usa los botones",
        "buttons": [
            {"label": "✅ Crear", "style": "success", "custom_id": "create_automation"},
            {"label": "❌ Ignorar", "style": "secondary", "custom_id": "ignore_pattern"},
        ],
    },
    NotificationTemplate.TASK_COMPLETED: {
        "title": "✓ Task completada",
        "severity": NotificationSeverity.SUCCESS,
        "fields": [
            {"name": "Task", "value": "{task_name}", "inline": True},
            {"name": "Estado", "value": "{status}", "inline": True},
        ],
        "timestamp": True,
    },
    NotificationTemplate.SYSTEM_ALERT: {
        "title": "🚨 Alerta del sistema",
        "severity": NotificationSeverity.ERROR,
        "fields": [
            {"name": "Tipo", "value": "{alert_type}", "inline": True},
            {"name": "Severidad", "value": "{severity}", "inline": True},
        ],
        "description": "{message}",
        "buttons": [
            {"label": "🔧 Acción", "style": "primary", "custom_id": "take_action"},
            {"label": "✓ Entendido", "style": "secondary", "custom_id": "acknowledge"},
        ],
    },
    NotificationTemplate.AUTO_LEARN_SUGGESTION: {
        "title": "📚 Sugerencia de auto-aprendizaje",
        "severity": NotificationSeverity.INFO,
        "color": "lilith_purple",
        "description": "{description}",
        "fields": [
            {"name": "Fuente", "value": "{source}", "inline": True},
            {"name": "Relevancia", "value": "{relevance}/10", "inline": True},
        ],
        "buttons": [
            {"label": "✅ Añadir", "style": "success", "custom_id": "add_to_notebook"},
            {"label": "📝 Editar", "style": "primary", "custom_id": "edit_entry"},
            {"label": "❌ Descartar", "style": "secondary", "custom_id": "discard"},
        ],
    },
}


@dataclass
class NotificationContext:
    """Contexto de una notificación para persistencia"""

    id: str
    template: str
    params: Dict[str, Any]
    severity: str
    created_at: float
    user_id: Optional[str] = None
    guild_id: Optional[str] = None
    resolved: bool = False
    resolution: Optional[str] = None


class NotificationButtonView(View):
    """Vista con botones para notificaciones"""

    def __init__(
        self,
        buttons: List[Dict],
        context: NotificationContext,
        callback: Optional[Callable] = None,
    ):
        super().__init__(timeout=3600)  # 1 hora timeout
        self.context = context
        self.callback = callback

        for btn_config in buttons:
            style = getattr(discord.ButtonStyle, btn_config.get("style", "secondary"))
            button = Button(
                label=btn_config["label"],
                style=style,
                custom_id=f"{context.id}:{btn_config['custom_id']}",
            )
            button.callback = self._create_callback(btn_config["custom_id"])
            self.add_item(button)

    def _create_callback(self, action: str):
        async def callback(interaction: discord.Interaction):
            logger.info(
                f"[Notification] User {interaction.user.id} clicked {action} on {self.context.id}"
            )

            if self.callback:
                await self.callback(self.context, action, interaction)

            # Feedback visual
            await interaction.response.send_message(
                f"✅ Acción '{action}' registrada", ephemeral=True
            )

        return callback


class RichDiscordNotifier:
    """
    Notificador de Discord con embeds ricos y botones
    """

    def __init__(self, bot: Optional[discord.Client] = None):
        self.bot = bot
        self._grouping_buffer: Dict[str, List[Dict]] = {}
        self._grouping_timers: Dict[str, float] = {}
        self._context_store: Dict[str, NotificationContext] = {}
        self._button_callbacks: Dict[str, Callable] = {}

        # Configuración de agrupación
        self.grouping_enabled = True
        self.grouping_threshold = 3
        self.grouping_window_seconds = 300  # 5 minutos

    def register_button_callback(self, action: str, callback: Callable):
        """Registra un callback para un tipo de acción de botón"""
        self._button_callbacks[action] = callback

    async def send_rich_notification(
        self,
        channel: discord.TextChannel,
        template: NotificationTemplate,
        params: Dict[str, Any],
        severity: Optional[NotificationSeverity] = None,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
    ) -> Optional[discord.Message]:
        """
        Envía una notificación rica con embed

        Args:
            channel: Canal de Discord
            template: Template a usar
            params: Parámetros para el template
            severity: Severidad (override del template)
            user_id: ID de usuario relacionado
            guild_id: ID del servidor

        Returns:
            Mensaje enviado o None si se agrupó
        """
        template_config = EMBED_TEMPLATES.get(template, {})

        # Verificar agrupación
        if self.grouping_enabled:
            group_key = f"{channel.id}:{template.value}"
            should_group = self._check_grouping(group_key, template_config)
            if should_group:
                return None

        # Construir embed
        embed = self._build_embed(template_config, params, severity)

        # Crear contexto
        context = NotificationContext(
            id=f"{int(time.time())}_{hash(str(params))}",
            template=template.value,
            params=params,
            severity=(
                severity or template_config.get("severity", NotificationSeverity.INFO)
            ).value,
            created_at=time.time(),
            user_id=str(user_id) if user_id else None,
            guild_id=str(guild_id) if guild_id else None,
        )
        self._context_store[context.id] = context

        # Botones
        buttons_config = template_config.get("buttons", [])
        view = None
        if buttons_config:
            view = NotificationButtonView(
                buttons=buttons_config,
                context=context,
                callback=self._handle_button_click,
            )

        try:
            message = await channel.send(embed=embed, view=view)
            logger.info(f"[RichNotifier] Sent {template.value} to channel {channel.id}")
            return message
        except Exception as e:
            logger.error(f"[RichNotifier] Error sending notification: {e}")
            return None

    def _build_embed(
        self,
        template_config: Dict,
        params: Dict[str, Any],
        severity_override: Optional[NotificationSeverity] = None,
    ) -> discord.Embed:
        """Construye un embed desde template"""

        # Determinar color
        severity = severity_override or template_config.get(
            "severity", NotificationSeverity.INFO
        )
        color_key = template_config.get("color", severity)
        color = EMBED_COLORS.get(color_key, EMBED_COLORS[NotificationSeverity.INFO])

        # Título y descripción con formato
        title = template_config.get("title", "Notificación")
        title = title.format(**params)

        description = template_config.get("description", "")
        if description:
            description = description.format(**params)

        embed = discord.Embed(
            title=title,
            description=description if description else None,
            color=color,
            timestamp=datetime.now(timezone.utc)
            if template_config.get("timestamp")
            else None,
        )

        # Campos
        for field in template_config.get("fields", []):
            value = field["value"].format(**params)
            embed.add_field(
                name=field["name"], value=value, inline=field.get("inline", False)
            )

        # Footer
        footer = template_config.get("footer", "")
        if footer:
            embed.set_footer(text=footer)

        return embed

    def _check_grouping(self, group_key: str, template_config: Dict) -> bool:
        """Verifica si debe agrupar la notificación"""
        now = time.time()

        # Limpiar buffer antiguo
        if group_key in self._grouping_timers:
            if now - self._grouping_timers[group_key] > self.grouping_window_seconds:
                self._grouping_buffer.pop(group_key, None)

        # Agregar al buffer
        if group_key not in self._grouping_buffer:
            self._grouping_buffer[group_key] = []
            self._grouping_timers[group_key] = now

        self._grouping_buffer[group_key].append(template_config)

        # Verificar si alcanzó el umbral
        if len(self._grouping_buffer[group_key]) >= self.grouping_threshold:
            return True

        return False

    async def send_grouped_notification(
        self,
        channel: discord.TextChannel,
        group_key: str,
    ):
        """Envía una notificación agrupada"""
        notifications = self._grouping_buffer.get(group_key, [])
        if not notifications:
            return

        count = len(notifications)

        embed = discord.Embed(
            title=f"📦 {count} notificaciones agrupadas",
            description=f"Se recibieron {count} notificaciones similares en los últimos 5 minutos.",
            color=EMBED_COLORS[NotificationSeverity.WARNING],
        )

        # Resumen por tipo
        type_counts = {}
        for n in notifications:
            title = n.get("title", "Unknown")
            type_counts[title] = type_counts.get(title, 0) + 1

        for title, count in type_counts.items():
            embed.add_field(name=title, value=f"{count} veces", inline=True)

        # Botón para ver detalles
        view = View()
        view.add_item(
            Button(
                label="Ver detalles",
                style=discord.ButtonStyle.secondary,
                custom_id=f"grouped:{group_key}:details",
            )
        )

        try:
            await channel.send(embed=embed, view=view)
            # Limpiar buffer
            self._grouping_buffer.pop(group_key, None)
            self._grouping_timers.pop(group_key, None)
        except Exception as e:
            logger.error(f"[RichNotifier] Error sending grouped notification: {e}")

    async def _handle_button_click(
        self,
        context: NotificationContext,
        action: str,
        interaction: discord.Interaction,
    ):
        """Maneja clicks en botones"""
        # Actualizar contexto
        context.resolved = True
        context.resolution = action

        # Llamar callback registrado
        callback = self._button_callbacks.get(action)
        if callback:
            try:
                await callback(context, interaction)
            except Exception as e:
                logger.error(f"[RichNotifier] Button callback error: {e}")

    def get_context(self, notification_id: str) -> Optional[NotificationContext]:
        """Obtiene el contexto de una notificación"""
        return self._context_store.get(notification_id)

    def get_pending_notifications(
        self, user_id: Optional[str] = None
    ) -> List[NotificationContext]:
        """Obtiene notificaciones pendientes"""
        pending = [ctx for ctx in self._context_store.values() if not ctx.resolved]
        if user_id:
            pending = [ctx for ctx in pending if ctx.user_id == user_id]
        return pending


# Funciones de conveniencia para uso simple


async def send_health_check_failed(
    channel: discord.TextChannel,
    subsystem: str,
    reason: str,
    notifier: Optional[RichDiscordNotifier] = None,
):
    """Envía notificación de health check fallido"""
    if notifier is None:
        notifier = RichDiscordNotifier()

    await notifier.send_rich_notification(
        channel=channel,
        template=NotificationTemplate.HEALTH_CHECK_FAILED,
        params={
            "subsystem": subsystem,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


async def send_backup_completed(
    channel: discord.TextChannel,
    filename: str,
    size_mb: float,
    duration: int,
    notifier: Optional[RichDiscordNotifier] = None,
):
    """Envía notificación de backup completado"""
    if notifier is None:
        notifier = RichDiscordNotifier()

    await notifier.send_rich_notification(
        channel=channel,
        template=NotificationTemplate.BACKUP_COMPLETED,
        params={
            "filename": filename,
            "size_mb": round(size_mb, 2),
            "duration": duration,
        },
        severity=NotificationSeverity.SUCCESS,
    )


async def send_pattern_detected(
    channel: discord.TextChannel,
    suggestion_text: str,
    pattern_name: str,
    confidence: float,
    notifier: Optional[RichDiscordNotifier] = None,
):
    """Envía notificación de pattern detectado"""
    if notifier is None:
        notifier = RichDiscordNotifier()

    await notifier.send_rich_notification(
        channel=channel,
        template=NotificationTemplate.PATTERN_DETECTED,
        params={
            "suggestion_text": suggestion_text,
            "pattern_name": pattern_name,
            "confidence": int(confidence * 100),
        },
    )


__all__ = [
    "RichDiscordNotifier",
    "NotificationTemplate",
    "NotificationSeverity",
    "NotificationContext",
    "NotificationButtonView",
    "send_health_check_failed",
    "send_backup_completed",
    "send_pattern_detected",
]
