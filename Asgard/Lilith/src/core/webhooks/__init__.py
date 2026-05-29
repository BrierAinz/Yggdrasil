"""
Webhooks Module - Sistema de webhooks salientes con firma HMAC

v4.2.8: Sistema de webhooks para notificaciones externas
"""
from .delivery import DeliveryManager
from .manager import WebhookManager, get_webhook_manager
from .signer import WebhookSigner

__all__ = ["WebhookManager", "get_webhook_manager", "WebhookSigner", "DeliveryManager"]
