"""
Webhook Signer - Firma y verificación HMAC-SHA256

v4.2.8: Sistema de firma para webhooks
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


class WebhookSigner:
    """
    Maneja la firma HMAC-SHA256 de payloads de webhook.

    Formato de firma:
    - Header: X-Webhook-Signature: sha256=<hex_signature>
    - Payload: timestamp + body JSON
    """

    SIGNATURE_HEADER = "X-Webhook-Signature"
    TIMESTAMP_HEADER = "X-Webhook-Timestamp"

    def __init__(self, secret: str):
        """
        Args:
            secret: Secreto compartido para firmar/verificar
        """
        self.secret = secret.encode("utf-8")

    def sign_payload(
        self, payload: Dict[str, Any], timestamp: Optional[int] = None
    ) -> tuple[str, int]:
        """
        Firma un payload con HMAC-SHA256.

        Args:
            payload: Datos a firmar
            timestamp: Timestamp opcional (default: now)

        Returns:
            Tupla de (signature_hex, timestamp)
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Crear string to sign: timestamp.body_json
        body_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        string_to_sign = f"{timestamp}.{body_json}"

        # Generar HMAC-SHA256
        signature = hmac.new(
            self.secret, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def verify_payload(
        self,
        signature: str,
        payload: Dict[str, Any],
        timestamp: int,
        tolerance_seconds: int = 300,
    ) -> bool:
        """
        Verifica la firma de un payload.

        Args:
            signature: Firma recibida (hex)
            payload: Datos recibidos
            timestamp: Timestamp recibido
            tolerance_seconds: Tolerancia de tiempo para replay attacks

        Returns:
            True si la firma es válida
        """
        # Verificar timestamp (evitar replay attacks)
        now = int(time.time())
        if abs(now - timestamp) > tolerance_seconds:
            return False

        # Recalcular firma esperada
        expected_signature, _ = self.sign_payload(payload, timestamp)

        # Comparación timing-safe
        return hmac.compare_digest(signature, expected_signature)

    def get_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Genera headers de firma para un request.

        Args:
            payload: Datos a enviar

        Returns:
            Dict con headers de firma
        """
        signature, timestamp = self.sign_payload(payload)

        return {
            self.SIGNATURE_HEADER: f"sha256={signature}",
            self.TIMESTAMP_HEADER: str(timestamp),
            "Content-Type": "application/json",
        }


class WebhookVerifier:
    """
    Verifica webhooks entrantes firmados con HMAC-SHA256.

    Útil para endpoints que reciben webhooks de Lilith
    y quieren verificar la autenticidad.
    """

    def __init__(self, secret: str):
        self.signer = WebhookSigner(secret)

    def verify_request(
        self, headers: Dict[str, str], body: bytes
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verifica un request de webhook.

        Args:
            headers: Headers HTTP recibidos
            body: Body raw del request

        Returns:
            Tupla (es_válido, payload_parseado_o_None)
        """
        # Extraer firma
        signature_header = headers.get(WebhookSigner.SIGNATURE_HEADER, "")
        if not signature_header.startswith("sha256="):
            return False, None

        signature = signature_header[7:]  # Quitar "sha256="

        # Extraer timestamp
        try:
            timestamp = int(headers.get(WebhookSigner.TIMESTAMP_HEADER, "0"))
        except ValueError:
            return False, None

        # Parsear body
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return False, None

        # Verificar
        is_valid = self.signer.verify_payload(signature, payload, timestamp)
        return is_valid, payload if is_valid else None
