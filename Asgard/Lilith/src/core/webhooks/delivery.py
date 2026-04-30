"""
Webhook Delivery - Sistema de entrega con retry y backoff

v4.2.8: Delivery confiable de webhooks
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .signer import WebhookSigner

logger = logging.getLogger("lilith.webhooks")


class DeliveryStatus(Enum):
    """Estado de una entrega."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class DeliveryAttempt:
    """Registro de un intento de entrega."""

    timestamp: datetime
    status_code: Optional[int]
    response_body: Optional[str]
    error: Optional[str]
    duration_ms: float


@dataclass
class DeliveryRecord:
    """Registro completo de una entrega."""

    webhook_id: str
    event_type: str
    payload: Dict[str, Any]
    status: DeliveryStatus
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    final_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "event_type": self.event_type,
            "status": self.status.value,
            "attempts": [
                {
                    "timestamp": a.timestamp.isoformat(),
                    "status_code": a.status_code,
                    "error": a.error,
                    "duration_ms": round(a.duration_ms, 2),
                }
                for a in self.attempts
            ],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "attempt_count": len(self.attempts),
        }


@dataclass
class RetryConfig:
    """Configuración de retry para webhooks."""

    max_retries: int = 3
    backoff_base: float = 2.0  # Segundos
    backoff_max: float = 60.0
    timeout_seconds: float = 30.0

    def get_delay(self, attempt: int) -> float:
        """Calcula el delay para un intento dado (exponential backoff)."""
        delay = self.backoff_base * (2**attempt)
        return min(delay, self.backoff_max)


class DeliveryManager:
    """
    Gestiona la entrega de webhooks con retry y backoff.

    Features:
    - Retry exponencial con jitter
    - Timeout configurable
    - Registro detallado de intentos
    - Cola async para alta performance
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._records: Dict[str, DeliveryRecord] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Inicia el worker de entregas."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=False,  # No seguir redirects por seguridad
                limits=httpx.Limits(max_connections=100),
            )

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._delivery_worker())
            logger.info("DeliveryManager: Worker iniciado")

    async def stop(self):
        """Detiene el worker de entregas."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.aclose()
            self._client = None

        logger.info("DeliveryManager: Worker detenido")

    async def enqueue_delivery(
        self,
        webhook_id: str,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
        retry_config: Optional[RetryConfig] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Encola una entrega de webhook.

        Args:
            webhook_id: ID del webhook
            url: URL destino
            secret: Secreto para firma
            event_type: Tipo de evento
            payload: Datos del evento
            retry_config: Config de retry (default: 3 retries)
            custom_headers: Headers adicionales

        Returns:
            ID de la entrega
        """
        delivery_id = f"{webhook_id}:{int(time.time() * 1000)}"

        record = DeliveryRecord(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status=DeliveryStatus.PENDING,
        )
        self._records[delivery_id] = record

        await self._queue.put(
            {
                "delivery_id": delivery_id,
                "url": url,
                "secret": secret,
                "event_type": event_type,
                "payload": payload,
                "retry_config": retry_config or RetryConfig(),
                "custom_headers": custom_headers or {},
            }
        )

        return delivery_id

    async def _delivery_worker(self):
        """Worker que procesa la cola de entregas."""
        while True:
            try:
                item = await self._queue.get()
                await self._process_delivery(item)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("DeliveryManager: Error en worker: %s", e)

    async def _process_delivery(self, item: Dict[str, Any]):
        """Procesa una entrega con retry."""
        delivery_id = item["delivery_id"]
        record = self._records[delivery_id]
        retry_config: RetryConfig = item["retry_config"]

        signer = WebhookSigner(item["secret"])

        # Preparar payload
        payload = {
            "event": item["event_type"],
            "timestamp": datetime.utcnow().isoformat(),
            "data": item["payload"],
            "webhook_id": item["webhook_id"],
        }

        # Headers de firma + custom
        headers = signer.get_headers(payload)
        headers.update(item["custom_headers"])
        headers["X-Webhook-Event"] = item["event_type"]
        headers["X-Webhook-ID"] = item["webhook_id"]

        # Intentar entrega con retry
        for attempt in range(retry_config.max_retries + 1):
            attempt_record = await self._attempt_delivery(
                item["url"], payload, headers, retry_config.timeout_seconds
            )
            record.attempts.append(attempt_record)

            if attempt_record.status_code and 200 <= attempt_record.status_code < 300:
                # Éxito
                record.status = DeliveryStatus.DELIVERED
                record.completed_at = datetime.now()
                logger.info(
                    "Webhook %s entregado en %d intentos (%dms)",
                    delivery_id,
                    len(record.attempts),
                    attempt_record.duration_ms,
                )
                return

            # Falló, calcular retry
            if attempt < retry_config.max_retries:
                delay = retry_config.get_delay(attempt)
                # Agregar jitter (±10%)
                jitter = delay * 0.1 * (2 * (time.time() % 1) - 1)
                await asyncio.sleep(delay + jitter)
                record.status = DeliveryStatus.RETRYING

        # Agotados los retries
        record.status = DeliveryStatus.FAILED
        record.completed_at = datetime.now()
        record.final_error = f"Failed after {len(record.attempts)} attempts"
        logger.warning(
            "Webhook %s falló después de %d intentos", delivery_id, len(record.attempts)
        )

    async def _attempt_delivery(
        self, url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float
    ) -> DeliveryAttempt:
        """Realiza un intento de entrega."""
        start = time.time()

        try:
            response = await self._client.post(
                url, json=payload, headers=headers, timeout=timeout
            )
            duration = (time.time() - start) * 1000

            # Leer body de respuesta (limitado)
            try:
                response_body = response.text[:1000]  # Max 1KB
            except:
                response_body = None

            return DeliveryAttempt(
                timestamp=datetime.now(),
                status_code=response.status_code,
                response_body=response_body,
                error=None,
                duration_ms=duration,
            )

        except httpx.TimeoutException as e:
            duration = (time.time() - start) * 1000
            return DeliveryAttempt(
                timestamp=datetime.now(),
                status_code=None,
                response_body=None,
                error=f"Timeout after {timeout}s",
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return DeliveryAttempt(
                timestamp=datetime.now(),
                status_code=None,
                response_body=None,
                error=str(e)[:200],
                duration_ms=duration,
            )

    def get_delivery_record(self, delivery_id: str) -> Optional[DeliveryRecord]:
        """Obtiene el registro de una entrega."""
        return self._records.get(delivery_id)

    def get_records_for_webhook(
        self, webhook_id: str, limit: int = 50
    ) -> List[DeliveryRecord]:
        """Obtiene registros de entregas para un webhook."""
        records = [r for r in self._records.values() if r.webhook_id == webhook_id]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def cleanup_old_records(self, max_age_hours: int = 24):
        """Limpia registros antiguos."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = [
            k for k, v in self._records.items() if v.created_at.timestamp() < cutoff
        ]
        for k in to_remove:
            del self._records[k]
        return len(to_remove)
