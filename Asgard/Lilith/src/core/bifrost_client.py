"""BifrostClient - Cliente para comunicación Asgard ↔ Vanaheim.

Este módulo permite a Lilith delegar tareas directamente a agentes
en Vanaheim sin pasar por el orquestador completo.

Uso:
    client = get_bifrost_client(base_path)
    result = await client.execute(agent="adan", task="refactor this code")
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("lilith.bifrost")


class CircuitBreaker:
    """
    Circuit breaker para proteger contra fallos en cascada.
    Estados: closed (normal), open (fallando), half-open (probando)
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"

    def can_execute(self) -> bool:
        """Determina si se puede ejecutar una llamada."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed > self.recovery_timeout:
                    logger.info("[Bifrost] Circuit breaker transitioning to half-open")
                    self.state = "half-open"
                    return True
            logger.debug("[Bifrost] Circuit breaker is OPEN, fast-failing")
            return False

        return True  # half-open

    def record_success(self):
        """Registra un éxito."""
        if self.state == "half-open":
            logger.info("[Bifrost] Circuit breaker closing (recovery successful)")
        self.failures = 0
        self.state = "closed"

    def record_failure(self):
        """Registra un fallo."""
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.failures >= self.failure_threshold and self.state != "open":
            logger.warning(
                f"[Bifrost] Circuit breaker OPEN after {self.failures} failures"
            )
            self.state = "open"

    def get_status(self) -> dict:
        """Retorna estado actual."""
        return {
            "state": self.state,
            "failures": self.failures,
            "threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
        }


class BifrostClient:
    """Cliente para llamar a agentes en Vanaheim."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config = self._load_config()

        self.enabled = self.config.get("enabled", False)
        self.vanaheim_url = self.config.get("url", "http://localhost:9000").rstrip("/")
        self.token = self.config.get("token", "")
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 2)

        # Circuit breakers por agente
        cb_config = self.config.get("circuit_breaker", {})
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            "adan": CircuitBreaker(
                cb_config.get("failure_threshold", 3),
                cb_config.get("recovery_timeout_seconds", 30),
            ),
            "eva": CircuitBreaker(
                cb_config.get("failure_threshold", 3),
                cb_config.get("recovery_timeout_seconds", 30),
            ),
            "odin": CircuitBreaker(
                cb_config.get("failure_threshold", 3),
                cb_config.get("recovery_timeout_seconds", 30),
            ),
        }

        if self.enabled:
            logger.info(f"[BifrostClient] Initialized with URL: {self.vanaheim_url}")
        else:
            logger.info("[BifrostClient] Disabled in config")

    def _load_config(self) -> dict:
        """Carga configuración desde Config/bifrost.json."""
        config_path = self.base_path / "Config" / "bifrost.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"[BifrostClient] Config not found at {config_path}")
            return {"enabled": False}
        except json.JSONDecodeError as e:
            logger.error(f"[BifrostClient] Invalid JSON in config: {e}")
            return {"enabled": False}

    async def execute(
        self,
        agent: str,  # adan, eva, odin
        task: str,
        context: Optional[str] = None,
        streaming: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta tarea en agente de Vanaheim con retry y circuit breaker.

        Args:
            agent: Nombre del agente (adan, eva, odin)
            task: Tarea a ejecutar
            context: Contexto adicional opcional
            streaming: Si se debe usar streaming (no implementado aún)

        Returns:
            Dict con respuesta o None si falló
        """
        if not self.enabled:
            logger.debug("[BifrostClient] Disabled, skipping")
            return None

        if agent not in self.circuit_breakers:
            logger.warning(f"[BifrostClient] Unknown agent: {agent}")
            return None

        cb = self.circuit_breakers[agent]
        if not cb.can_execute():
            logger.warning(f"[BifrostClient] Circuit breaker OPEN for {agent}")
            return None

        payload = {
            "agent": agent,
            "task": task,
            "context": context or "",
            "streaming": streaming,
        }

        headers = {"X-Bifrost-Token": self.token} if self.token else {}

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.vanaheim_url}/api/bifrost/execute",
                        json=payload,
                        headers=headers,
                    )

                    if resp.status_code == 200:
                        cb.record_success()
                        data = resp.json()
                        logger.info(
                            f"[BifrostClient] Success from {agent} in {data.get('latency_ms', 0):.0f}ms"
                        )
                        return data

                    if resp.status_code == 401:
                        logger.error(
                            "[BifrostClient] Authentication failed - check token"
                        )
                        # Don't retry auth failures
                        cb.record_failure()
                        return None

                    logger.warning(
                        f"[BifrostClient] HTTP {resp.status_code} from {agent}"
                    )

            except httpx.TimeoutException:
                logger.warning(
                    f"[BifrostClient] Timeout calling {agent} (attempt {attempt+1}/{self.max_retries})"
                )
            except httpx.ConnectError as e:
                logger.warning(
                    f"[BifrostClient] Connection error: {e} (attempt {attempt+1}/{self.max_retries})"
                )
            except Exception as e:
                logger.error(f"[BifrostClient] Error calling {agent}: {e}")

        # All retries failed
        cb.record_failure()
        logger.error(f"[BifrostClient] All retries failed for {agent}")
        return None

    async def health_check(self) -> Dict[str, Any]:
        """Verifica salud de Vanaheim."""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.vanaheim_url}/api/bifrost/health")
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "unreachable", "code": resp.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def should_use_vanaheim(self, classification: dict) -> bool:
        """
        Determina si se debe usar Vanaheim basado en clasificación de Albedo.

        Args:
            classification: Dict retornado por Albedo:Sombra

        Returns:
            True si se debe delegar a Vanaheim
        """
        if not self.enabled:
            return False

        route = classification.get("route", "asgard")
        confidence = classification.get("confidence", 0.0)
        agent = classification.get("recommended_agent", "")

        # Solo usar Vanaheim si:
        # 1. Route es "vanaheim"
        # 2. Confianza es suficiente
        # 3. El agente recomendado está en Vanaheim
        threshold = self.config.get("routing_rules", {}).get(
            "confidence_threshold", 0.7
        )
        vanaheim_agents = self.config.get("routing_rules", {}).get(
            "vanaheim_agents", ["adan", "eva", "odin"]
        )

        if route != "vanaheim":
            return False

        if confidence < threshold:
            logger.debug(
                f"[BifrostClient] Confidence {confidence} below threshold {threshold}"
            )
            return False

        if agent not in vanaheim_agents:
            logger.debug(f"[BifrostClient] Agent {agent} not in Vanaheim")
            return False

        # Verificar circuit breaker
        cb = self.circuit_breakers.get(agent)
        if cb and not cb.can_execute():
            logger.warning(
                f"[BifrostClient] Circuit open for {agent}, won't use Vanaheim"
            )
            return False

        return True

    def get_circuit_status(self) -> Dict[str, dict]:
        """Retorna estado de todos los circuit breakers."""
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}


# Singleton instance
_bifrost_client: Optional[BifrostClient] = None


def get_bifrost_client(base_path: Optional[Path] = None) -> BifrostClient:
    """Obtiene instancia singleton de BifrostClient."""
    global _bifrost_client

    if _bifrost_client is None:
        if base_path is None:
            # Inferir base_path desde ubicación de este archivo
            base_path = Path(__file__).resolve().parent.parent.parent
        _bifrost_client = BifrostClient(base_path)

    return _bifrost_client


async def execute_on_vanaheim(
    agent: str,
    task: str,
    context: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> Optional[str]:
    """
    Función helper para ejecutar tarea en Vanaheim y retornar solo la respuesta.

    Returns:
        String con la respuesta o None si falló
    """
    client = get_bifrost_client(base_path)
    result = await client.execute(agent, task, context)

    if result and "response" in result:
        return result["response"]

    return None
