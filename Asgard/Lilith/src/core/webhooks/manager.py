"""
Webhook Manager - Gestión de webhooks configurados

v4.2.8: Sistema completo de webhooks salientes
"""
import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.json_safe import safe_load

from .delivery import DeliveryManager, DeliveryStatus, RetryConfig
from .signer import WebhookSigner

logger = logging.getLogger("lilith.webhooks")


class WebhookEventType(Enum):
    """Eventos soportados para webhooks."""

    HEALTH_STATUS_CHANGED = "health.status_changed"
    WORKFLOW_EXECUTED = "workflow.executed"
    TOOL_EXECUTION_FINISHED = "tool.execution_finished"
    ALERT_TRIGGERED = "alert.triggered"
    ANALYTICS_THRESHOLD_REACHED = "analytics.threshold_reached"
    AGENT_MESSAGE = "agent.message"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


@dataclass
class Webhook:
    """Configuración de un webhook."""

    id: str
    name: str
    url: str
    secret: str
    events: List[str]
    enabled: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_triggered: Optional[str] = None
    trigger_count: int = 0

    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "enabled": self.enabled,
            "retry_config": {
                "max_retries": self.retry_config.max_retries,
                "backoff_base": self.retry_config.backoff_base,
                "backoff_max": self.retry_config.backoff_max,
                "timeout_seconds": self.retry_config.timeout_seconds,
            },
            "custom_headers": self.custom_headers,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
        }
        if include_secret:
            result["secret"] = self.secret
        else:
            result["secret_masked"] = "***"
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Webhook":
        """Crea Webhook desde dict."""
        retry_data = data.get("retry_config", {})
        return cls(
            id=data["id"],
            name=data["name"],
            url=data["url"],
            secret=data["secret"],
            events=data.get("events", []),
            enabled=data.get("enabled", True),
            retry_config=RetryConfig(
                max_retries=retry_data.get("max_retries", 3),
                backoff_base=retry_data.get("backoff_base", 2.0),
                backoff_max=retry_data.get("backoff_max", 60.0),
                timeout_seconds=retry_data.get("timeout_seconds", 30.0),
            ),
            custom_headers=data.get("custom_headers", {}),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            last_triggered=data.get("last_triggered"),
            trigger_count=data.get("trigger_count", 0),
        )


class WebhookManager:
    """
    Gestor de webhooks para Lilith.

    Features:
    - CRUD de webhooks
    - Envío de eventos a múltiples suscriptores
    - Firma HMAC-SHA256
    - Retry con backoff
    - Cola async para performance
    """

    _instance: Optional["WebhookManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
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
        self.config_path = self.base_path / "Config" / "webhooks.json"
        self.storage_path = self.base_path / "Data" / "webhooks"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Cargar webhooks
        self._webhooks: Dict[str, Webhook] = {}
        self._load_webhooks()

        # Delivery manager
        self._delivery = DeliveryManager()

        # Callbacks de eventos
        self._event_callbacks: Dict[str, List[Callable]] = {}

        self._initialized = True
        logger.info("WebhookManager: Inicializado con %d webhooks", len(self._webhooks))

    async def start(self):
        """Inicia el sistema de webhooks."""
        await self._delivery.start()
        logger.info("WebhookManager: Sistema iniciado")

    async def stop(self):
        """Detiene el sistema de webhooks."""
        await self._delivery.stop()
        logger.info("WebhookManager: Sistema detenido")

    # CRUD Operations

    def create_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
        description: str = "",
        custom_headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> Webhook:
        """
        Crea un nuevo webhook.

        Args:
            name: Nombre descriptivo
            url: URL endpoint
            events: Lista de eventos a suscribir
            description: Descripción opcional
            custom_headers: Headers HTTP adicionales
            retry_config: Configuración de retry

        Returns:
            Webhook creado
        """
        # Validar eventos
        valid_events = [e.value for e in WebhookEventType]
        invalid_events = [e for e in events if e not in valid_events]
        if invalid_events:
            raise ValueError(f"Eventos inválidos: {invalid_events}")

        # Generar secreto único
        secret = secrets.token_urlsafe(32)

        webhook = Webhook(
            id=secrets.token_hex(8),
            name=name,
            url=url,
            secret=secret,
            events=events,
            description=description,
            custom_headers=custom_headers or {},
            retry_config=retry_config or RetryConfig(),
        )

        self._webhooks[webhook.id] = webhook
        self._save_webhooks()

        logger.info("WebhookManager: Creado webhook %s (%s)", webhook.id, name)
        return webhook

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Obtiene un webhook por ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self, event_type: Optional[str] = None) -> List[Webhook]:
        """
        Lista webhooks.

        Args:
            event_type: Filtrar por tipo de evento (opcional)

        Returns:
            Lista de webhooks
        """
        webhooks = list(self._webhooks.values())

        if event_type:
            webhooks = [w for w in webhooks if event_type in w.events]

        return sorted(webhooks, key=lambda w: w.created_at, reverse=True)

    def update_webhook(self, webhook_id: str, **kwargs) -> Optional[Webhook]:
        """
        Actualiza un webhook.

        Args:
            webhook_id: ID del webhook
            **kwargs: Campos a actualizar

        Returns:
            Webhook actualizado o None
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        allowed_fields = [
            "name",
            "url",
            "events",
            "enabled",
            "description",
            "custom_headers",
        ]
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(webhook, field, value)

        webhook.updated_at = datetime.utcnow().isoformat()
        self._save_webhooks()

        logger.info("WebhookManager: Actualizado webhook %s", webhook_id)
        return webhook

    def delete_webhook(self, webhook_id: str) -> bool:
        """Elimina un webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            self._save_webhooks()
            logger.info("WebhookManager: Eliminado webhook %s", webhook_id)
            return True
        return False

    def regenerate_secret(self, webhook_id: str) -> Optional[str]:
        """Regenera el secreto de un webhook."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        webhook.secret = secrets.token_urlsafe(32)
        webhook.updated_at = datetime.utcnow().isoformat()
        self._save_webhooks()

        logger.info("WebhookManager: Secreto regenerado para %s", webhook_id)
        return webhook.secret

    # Event Triggering

    async def trigger_event(
        self, event_type: str, payload: Dict[str, Any], source: str = "system"
    ) -> List[str]:
        """
        Dispara un evento a todos los webhooks suscritos.

        Args:
            event_type: Tipo de evento
            payload: Datos del evento
            source: Fuente del evento

        Returns:
            Lista de IDs de entrega
        """
        webhooks = self.list_webhooks(event_type)
        delivery_ids = []

        for webhook in webhooks:
            if not webhook.enabled:
                continue

            delivery_id = await self._delivery.enqueue_delivery(
                webhook_id=webhook.id,
                url=webhook.url,
                secret=webhook.secret,
                event_type=event_type,
                payload={"source": source, **payload},
                retry_config=webhook.retry_config,
                custom_headers=webhook.custom_headers,
            )
            delivery_ids.append(delivery_id)

            # Actualizar métricas del webhook
            webhook.last_triggered = datetime.utcnow().isoformat()
            webhook.trigger_count += 1

        if delivery_ids:
            self._save_webhooks()
            logger.info(
                "WebhookManager: Evento %s enviado a %d webhooks",
                event_type,
                len(delivery_ids),
            )

        # Ejecutar callbacks registrados
        await self._execute_callbacks(event_type, payload)

        return delivery_ids

    async def test_webhook(self, webhook_id: str) -> Optional[str]:
        """
        Envía un evento de prueba a un webhook.

        Args:
            webhook_id: ID del webhook

        Returns:
            ID de la entrega o None
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        test_payload = {
            "test": True,
            "message": "Este es un evento de prueba de Lilith",
            "timestamp": datetime.utcnow().isoformat(),
        }

        delivery_id = await self._delivery.enqueue_delivery(
            webhook_id=webhook.id,
            url=webhook.url,
            secret=webhook.secret,
            event_type="webhook.test",
            payload=test_payload,
            retry_config=RetryConfig(max_retries=0),  # No retry para tests
        )

        logger.info("WebhookManager: Test enviado a %s", webhook_id)
        return delivery_id

    # Delivery Records

    def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una entrega."""
        record = self._delivery.get_delivery_record(delivery_id)
        if record:
            return record.to_dict()
        return None

    def get_webhook_deliveries(
        self, webhook_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtiene historial de entregas para un webhook."""
        records = self._delivery.get_records_for_webhook(webhook_id, limit)
        return [r.to_dict() for r in records]

    # Persistence

    def _load_webhooks(self):
        """Carga webhooks desde disco."""
        config = safe_load(self.config_path, default={"webhooks": []})

        for data in config.get("webhooks", []):
            try:
                webhook = Webhook.from_dict(data)
                self._webhooks[webhook.id] = webhook
            except Exception as e:
                logger.warning("Error cargando webhook: %s", e)

    def _save_webhooks(self):
        """Guarda webhooks a disco."""
        config = {
            "webhooks": [
                w.to_dict(include_secret=True) for w in self._webhooks.values()
            ],
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Error guardando webhooks: %s", e)

    # Callbacks

    def register_callback(self, event_type: str, callback: Callable):
        """Registra un callback para un tipo de evento."""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    async def _execute_callbacks(self, event_type: str, payload: Dict[str, Any]):
        """Ejecuta callbacks registrados."""
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.debug("Error en callback: %s", e)


# Singleton
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager(base_path: Optional[Path] = None) -> WebhookManager:
    """Obtiene instancia del WebhookManager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager(base_path)
    return _webhook_manager
