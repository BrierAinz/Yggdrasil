"""
Tests for Webhooks

v4.2.8: Tests unitarios para el sistema de webhooks.
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.webhooks.delivery import DeliveryManager, DeliveryStatus, RetryConfig
from src.core.webhooks.manager import Webhook, WebhookEventType, WebhookManager
from src.core.webhooks.signer import WebhookSigner


class TestWebhookSigner:
    """Tests para firma de webhooks."""

    def setup_method(self):
        """Setup."""
        self.signer = WebhookSigner()
        self.secret = "test_secret_key"

    def test_sign_payload(self):
        """Test firma de payload."""
        payload = b'{"event": "test"}'

        signature = self.signer.sign_payload(payload, self.secret)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex

    def test_verify_signature_valid(self):
        """Test verificación de firma válida."""
        payload = b'{"event": "test"}'
        signature = self.signer.sign_payload(payload, self.secret)

        is_valid = self.signer.verify_signature(payload, signature, self.secret)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test verificación de firma inválida."""
        payload = b'{"event": "test"}'

        is_valid = self.signer.verify_signature(
            payload, "invalid_signature", self.secret
        )

        assert is_valid is False

    def test_create_signature_header(self):
        """Test creación de header de firma."""
        payload = b'{"event": "test"}'

        header = self.signer.create_signature_header(payload, self.secret)

        assert header.startswith("sha256=")


class TestDeliveryManager:
    """Tests para el manager de delivery."""

    def setup_method(self):
        """Setup."""
        self.retry_config = RetryConfig(
            max_retries=3,
            backoff_base=0.1,  # Rápido para tests
            backoff_max=1.0,
            timeout_seconds=5.0,
        )
        self.delivery = DeliveryManager(self.retry_config)

    @pytest.mark.asyncio
    async def test_calculate_backoff(self):
        """Test cálculo de backoff."""
        # Primer reintento: 0.1 * 2^0 = 0.1
        delay1 = self.delivery._calculate_backoff(0)
        assert delay1 == 0.1

        # Segundo reintento: 0.1 * 2^1 = 0.2
        delay2 = self.delivery._calculate_backoff(1)
        assert delay2 == 0.2

        # Verificar max
        delay_max = self.delivery._calculate_backoff(10)
        assert delay_max == 1.0  # No excede backoff_max

    def test_should_retry(self):
        """Test decisión de reintento."""
        # Error 5xx - debería reintentar
        assert self.delivery._should_retry(500) is True
        assert self.delivery._should_retry(503) is True

        # Error 4xx - no debería reintentar (excepto 429)
        assert self.delivery._should_retry(400) is False
        assert self.delivery._should_retry(404) is False

        # Error 429 (rate limit) - debería reintentar
        assert self.delivery._should_retry(429) is True

    @pytest.mark.asyncio
    async def test_successful_delivery(self):
        """Test delivery exitoso."""
        # Mock de httpx
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await self.delivery.deliver(
                url="https://example.com/webhook",
                payload={"event": "test"},
                secret="secret",
                headers={},
            )

            assert result.success is True
            assert result.status_code == 200
            assert result.attempts == 1


class TestWebhookManager:
    """Tests para el manager de webhooks."""

    def setup_method(self):
        """Setup con mocks."""
        with patch("Backend.core.webhooks.manager.Path"):
            self.manager = WebhookManager.__new__(WebhookManager)
            self.manager._webhooks = {}
            self.manager._delivery_log = []

    def test_create_webhook(self):
        """Test creación de webhook."""
        webhook = self.manager.create_webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["test.event"],
        )

        assert webhook.id in self.manager._webhooks
        assert webhook.name == "Test Webhook"
        assert webhook.enabled is True
        assert len(webhook.secret) > 0  # Auto-generado

    def test_get_webhook(self):
        """Test obtención de webhook."""
        created = self.manager.create_webhook(
            name="Test", url="https://example.com", events=["test"]
        )

        retrieved = self.manager.get_webhook(created.id)

        assert retrieved == created

    def test_update_webhook(self):
        """Test actualización de webhook."""
        webhook = self.manager.create_webhook(
            name="Original", url="https://old.com", events=["old"]
        )

        updated = self.manager.update_webhook(
            webhook.id, name="Updated", url="https://new.com"
        )

        assert updated.name == "Updated"
        assert updated.url == "https://new.com"

    def test_delete_webhook(self):
        """Test eliminación de webhook."""
        webhook = self.manager.create_webhook(
            name="To Delete", url="https://example.com", events=["test"]
        )

        result = self.manager.delete_webhook(webhook.id)

        assert result is True
        assert webhook.id not in self.manager._webhooks

    def test_list_webhooks(self):
        """Test listado de webhooks."""
        self.manager.create_webhook("Webhook 1", "https://1.com", ["e1"])
        self.manager.create_webhook("Webhook 2", "https://2.com", ["e2"])

        webhooks = self.manager.list_webhooks()

        assert len(webhooks) == 2

    def test_get_webhooks_for_event(self):
        """Test obtención de webhooks para un evento."""
        wh1 = self.manager.create_webhook(
            "WH1", "https://1.com", ["event.a", "event.b"]
        )
        wh2 = self.manager.create_webhook("WH2", "https://2.com", ["event.b"])
        wh3 = self.manager.create_webhook("WH3", "https://3.com", ["event.c"])

        result = self.manager.get_webhooks_for_event("event.b")

        assert len(result) == 2
        assert wh1 in result
        assert wh2 in result
        assert wh3 not in result

    def test_webhook_to_dict(self):
        """Test serialización de webhook."""
        webhook = Webhook(
            id="wh_123",
            name="Test",
            url="https://example.com",
            secret="secret_key",
            events=["test.event"],
        )

        data = webhook.to_dict()

        assert data["id"] == "wh_123"
        assert data["name"] == "Test"
        assert data["url"] == "https://example.com"
        assert "secret_masked" in data
        assert data["secret_masked"] == "***"
        assert "secret" not in data  # No incluir secret en respuesta

    def test_webhook_to_dict_with_secret(self):
        """Test serialización incluyendo secret."""
        webhook = Webhook(
            id="wh_123",
            name="Test",
            url="https://example.com",
            secret="secret_key",
            events=["test.event"],
        )

        data = webhook.to_dict(include_secret=True)

        assert data["secret"] == "secret_key"


class TestWebhookEventTypes:
    """Tests para tipos de eventos de webhook."""

    def test_event_type_values(self):
        """Test valores de tipos de eventos."""
        assert WebhookEventType.HEALTH_STATUS_CHANGED.value == "health.status_changed"
        assert WebhookEventType.WORKFLOW_EXECUTED.value == "workflow.executed"
        assert (
            WebhookEventType.TOOL_EXECUTION_FINISHED.value == "tool.execution_finished"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
