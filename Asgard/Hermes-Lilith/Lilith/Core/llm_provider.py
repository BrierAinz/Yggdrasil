"""
LLM Provider System
===================
Sistema multi-provider para Lilith con fallback automatico.
Soporta LM Studio (local) y APIs remotas como Kimi (Moonshot).

Uso:
    from Lilith.Core.llm_provider import get_provider, LLMProvider

    # Obtener provider (auto-deteccion con fallback)
    provider = get_provider()
    response = provider.chat(messages=[...])

    # Forzar provider especifico
    provider = get_provider("kimi")
"""

import os
import time
from typing import Any, Dict, Iterator, List, Optional

import httpx

from .config import DEFAULT_MODEL, LLM_PROVIDER, LLM_PROVIDERS, LM_STUDIO_URL
from .resilience import CircuitBreaker, CircuitBreakerError, RetryConfig, retry_with_backoff
from .lilith_logger import get_logger

_logger = get_logger("lilith.llm_provider")


class LLMProvider:
    """Proveedor de LLM con interfaz OpenAI-compatible.

    Soporta cualquier endpoint que siga la API de OpenAI
    (LM Studio, Kimi/Moonshot, OpenAI, etc.)
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str = "auto",
        api_key: Optional[str] = None,
        provider_type: str = "local",
        chat_timeout: float = 120.0,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.provider_type = provider_type
        self._last_error: Optional[str] = None
        self._available: Optional[bool] = None
        self._checked_at: float = 0

        # ── Resilience ──
        self.chat_timeout = chat_timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        self.retry_config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
        )

        # Detectar modelo si es "auto"
        if self.model == "auto":
            self._auto_detect_model()

    def _auto_detect_model(self):
        """Detecta automaticamente el modelo disponible."""
        try:
            models = self.list_models()
            if models:
                self.model = models[0].get("id", "unknown")
            else:
                self.model = "local-model"
        except Exception:
            if self.provider_type == "local":
                self.model = "local-model"
            else:
                self.model = self.name  # fallback al nombre del provider

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers HTTP para el request."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def is_available(self, force_check: bool = False) -> bool:
        """Verifica si el provider esta disponible.

        Cachea el resultado por 30 segundos para no saturar.
        """
        now = time.time()
        if (
            not force_check
            and self._available is not None
            and (now - self._checked_at) < 30
        ):
            return self._available

        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=5.0,
            )
            self._available = response.status_code == 200
            self._last_error = None
        except Exception as e:
            self._available = False
            self._last_error = str(e)

        self._checked_at = now
        return self._available

    def list_models(self) -> List[Dict]:
        """Lista modelos disponibles en el provider."""
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            self._last_error = str(e)
            return []

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Envia mensaje al modelo y recibe respuesta completa.

        Protegido por circuit breaker y retry con backoff exponencial.
        Si el circuit breaker esta OPEN, lanza CircuitBreakerError inmediatamente.
        Retry en errores transitorios (429, 500, 502, 503, 504, timeouts, conexiones).
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        def _make_request():
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._get_headers(),
                timeout=self.chat_timeout,
            )
            response.raise_for_status()
            return response.json()

        try:
            result = retry_with_backoff(
                _make_request,
                retry_config=self.retry_config,
                circuit_breaker=self.circuit_breaker,
            )
            return result
        except CircuitBreakerError:
            raise
        except Exception as e:
            error_msg = f"HTTP error: {e}"
            self._last_error = error_msg
            return {"error": error_msg}

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """Streaming generator: yield chunks de texto.

        Protegido por circuit breaker. Si el circuito esta OPEN,
        emite un mensaje de error en vez de bloquear indefinidamente.
        """
        import json as _json

        # Verificar circuit breaker antes de iniciar stream
        if self.circuit_breaker.is_open:
            yield f"\n[Circuit breaker OPEN — provider '{self.name}' bloqueado por fallos consecutivos. Espera antes de reintentar.]\n"
            return

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._get_headers(),
                timeout=self.chat_timeout,
            ) as response:
                response.raise_for_status()
                self.circuit_breaker.record_success()
                for line in response.iter_lines():
                    if not line or not line.strip():
                        continue
                    line = line.strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = _json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (_json.JSONDecodeError, KeyError, IndexError):
                            continue
        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure()
            error_msg = f"HTTP {e.response.status_code}"
            self._last_error = error_msg
            yield f"\n[Error streaming desde {self.name}: {error_msg}]\n"
        except Exception as e:
            self.circuit_breaker.record_failure()
            self._last_error = str(e)
            yield f"\n[Error streaming desde {self.name}: {e}]\n"

    def get_status(self) -> Dict[str, Any]:
        """Retorna estado del provider incluyendo circuit breaker."""
        return {
            "name": self.name,
            "type": self.provider_type,
            "base_url": self.base_url,
            "model": self.model,
            "available": self.is_available(),
            "last_error": self._last_error,
            "has_api_key": bool(self.api_key),
            "circuit_breaker": self.circuit_breaker.stats,
        }

    def get_provider_info(self) -> Dict[str, Any]:
        """Retorna informacion completa del provider con estado del circuit breaker.

        Los Nords consultan las runas del Yggdrasil para conocer el estado
        de los caminos entre los nueve mundos.
        """
        return {
            "name": self.name,
            "model": self.model,
            "type": self.provider_type,
            "base_url": self.base_url,
            "available": self.is_available(),
            "circuit_breaker": self.circuit_breaker.stats,
            "last_error": self._last_error,
            "has_api_key": bool(self.api_key),
            "chat_timeout": self.chat_timeout,
        }

    def __repr__(self):
        status = "available" if self.is_available() else "unavailable"
        return f"LLMProvider({self.name}, model={self.model}, {status})"


# ──────────────────────────────────────────────────────────────────────────────
# Provider Registry & Fallback System
# ──────────────────────────────────────────────────────────────────────────────

_providers: Dict[str, LLMProvider] = {}
_active_provider: Optional[str] = None


def _init_providers():
    """Inicializa los providers desde la configuracion."""
    global _providers

    for cfg in LLM_PROVIDERS:
        name = cfg["name"]
        _providers[name] = LLMProvider(
            name=name,
            base_url=cfg["base_url"],
            model=cfg.get("model", "auto"),
            api_key=cfg.get("api_key"),
            provider_type=cfg.get("type", "local"),
        )


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """Obtiene un provider por nombre o con fallback automatico.

    Args:
        name: Nombre del provider ('lm_studio', 'kimi') o None para auto.

    Returns:
        LLMProvider conectado y disponible.

    Raises:
        ConnectionError: Si ningun provider esta disponible.
    """
    global _active_provider

    if not _providers:
        _init_providers()

    if name and name in _providers:
        provider = _providers[name]
        if provider.is_available():
            _active_provider = name
            return provider
        raise ConnectionError(
            f"Provider '{name}' no disponible: {provider._last_error}"
        )

    # Modo auto: intentar cada provider en orden
    if LLM_PROVIDER == "auto" or name is None:
        for prov_name, provider in _providers.items():
            if provider.is_available():
                _active_provider = prov_name
                return provider

        # Ninguno disponible - intentar de nuevo con force_check
        for prov_name, provider in _providers.items():
            if provider.is_available(force_check=True):
                _active_provider = prov_name
                return provider

        raise ConnectionError(
            f"Ningun provider disponible. Providers: "
            + ", ".join(
                f"{p.name}({p._last_error or 'unknown'})" for p in _providers.values()
            )
        )

    raise ValueError(f"Provider desconocido: {name}")


def get_active_provider_name() -> Optional[str]:
    """Retorna el nombre del provider activo."""
    return _active_provider


def list_providers() -> List[Dict[str, Any]]:
    """Lista todos los providers registrados con su estado."""
    if not _providers:
        _init_providers()

    return [p.get_status() for p in _providers.values()]


def switch_provider(name: str) -> LLMProvider:
    """Cambia al provider especificado.

    Returns:
        El nuevo provider activo.

    Raises:
        ConnectionError: Si el provider no esta disponible.
    """
    return get_provider(name)


def test_all_providers() -> Dict[str, Dict[str, Any]]:
    """Testea la conexion de todos los providers."""
    if not _providers:
        _init_providers()

    results = {}
    for name, provider in _providers.items():
        try:
            available = provider.is_available(force_check=True)
            models = provider.list_models() if available else []
            results[name] = {
                "available": available,
                "model": provider.model,
                "models_count": len(models),
                "error": provider._last_error,
            }
        except Exception as e:
            results[name] = {
                "available": False,
                "error": str(e),
            }
    return results


# Auto-init on import
try:
    _init_providers()
except Exception:
    pass
