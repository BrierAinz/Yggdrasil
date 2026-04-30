"""
Bifrost - Canal de comunicación entre Asgard (Lilith) y Vanaheim.

Features:
- Abstracción de transporte (direct, http, websocket)
- Invocación de agentes de Vanaheim
- Ejecución de nodos DAG remotos
- Health checks y circuit breaker
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .json_safe import safe_load

logger = logging.getLogger("lilith.bifrost")


class BifrostTransport(Enum):
    """Tipos de transporte soportados."""

    DIRECT = "direct"  # Llamada directa en mismo proceso
    HTTP = "http"  # HTTP a servicio Vanaheim
    WEBSOCKET = "websocket"  # WebSocket para streaming


@dataclass
class BifrostResult:
    """Resultado de invocación vía Bifrost."""

    success: bool
    output: str
    agent_used: str
    latency_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class NodeResult:
    """Resultado de ejecución de nodo DAG."""

    success: bool
    output: Any
    tool_name: str
    agent_used: str
    latency_ms: float
    error: Optional[str] = None


class BifrostClient:
    """
    Cliente Bifrost para comunicación Asgard ↔ Vanaheim.
    Soporta múltiples transportes y gestiona la invocación de agentes.
    """

    def __init__(
        self, base_path: Optional[Path] = None, transport: Optional[str] = None
    ):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()

        # Configuración de transporte
        bifrost_config = self.config.get("bifrost", {})
        self.transport = BifrostTransport(
            transport or bifrost_config.get("transport", "direct")
        )
        self.timeout_seconds = bifrost_config.get("timeout_seconds", 30)
        self.http_endpoint = bifrost_config.get(
            "http_endpoint", "http://localhost:8765/vanaheim"
        )

        # Circuit breaker
        self._failure_count = 0
        self._max_failures = 5
        self._circuit_open = False
        self._last_failure_time = 0.0
        self._circuit_timeout = 60  # segundos

        # Cache de agentes
        self._agent_cache: Dict[str, Any] = {}

        # Handlers de transporte
        self._transport_handlers: Dict[BifrostTransport, Callable] = {
            BifrostTransport.DIRECT: self._direct_call,
            BifrostTransport.HTTP: self._http_call,
        }

        logger.info("[Bifrost] Inicializado con transporte: %s", self.transport.value)

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            return safe_load(config_path, default={})
        except Exception as e:
            logger.error("[Bifrost] Error cargando config: %s", e)
            return {"bifrost": {"transport": "direct", "timeout_seconds": 30}}

    def _check_circuit(self) -> bool:
        """Verifica si el circuit breaker está abierto."""
        if not self._circuit_open:
            return True

        # Verificar si podemos cerrar el circuito
        if time.time() - self._last_failure_time > self._circuit_timeout:
            logger.info("[Bifrost] Circuit breaker cerrado (timeout)")
            self._circuit_open = False
            self._failure_count = 0
            return True

        return False

    def _record_success(self):
        """Registra éxito y resetea contador de fallos."""
        self._failure_count = 0
        self._circuit_open = False

    def _record_failure(self):
        """Registra fallo y abre circuito si es necesario."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._max_failures:
            logger.warning(
                "[Bifrost] Circuit breaker ABIERTO (%d fallos)", self._failure_count
            )
            self._circuit_open = True

    def delegate_to_vanaheim(
        self,
        agent_name: str,
        task: str,
        complexity_level: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> BifrostResult:
        """
        Delega una tarea simple a un agente de Vanaheim.

        Args:
            agent_name: Nombre del agente (freya, heimdall, eir, balder)
            task: Descripción de la tarea
            complexity_level: Nivel de complejidad (trivial, simple, etc.)
            context: Contexto adicional

        Returns:
            BifrostResult con el resultado de la delegación
        """
        if not self._check_circuit():
            return BifrostResult(
                success=False,
                output="",
                agent_used=agent_name,
                latency_ms=0.0,
                error="Circuit breaker abierto - demasiados fallos",
            )

        start_time = time.time()

        try:
            payload = {
                "agent": agent_name,
                "task": task,
                "complexity_level": complexity_level,
                "context": context or {},
            }

            handler = self._transport_handlers.get(self.transport, self._direct_call)
            result = handler(payload)

            latency = (time.time() - start_time) * 1000
            self._record_success()

            return BifrostResult(
                success=result.get("success", False),
                output=result.get("output", ""),
                agent_used=agent_name,
                latency_ms=latency,
                metadata=result.get("metadata", {}),
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._record_failure()
            logger.error("[Bifrost] Error delegando a %s: %s", agent_name, e)

            return BifrostResult(
                success=False,
                output="",
                agent_used=agent_name,
                latency_ms=latency,
                error=str(e),
            )

    def execute_node(
        self,
        agent_name: str,
        tool_name: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> NodeResult:
        """
        Ejecuta un nodo DAG vía agente de Vanaheim.

        Args:
            agent_name: Agente de Vanaheim a usar
            tool_name: Tool/nodo a ejecutar
            params: Parámetros del nodo
            context: Contexto de ejecución

        Returns:
            NodeResult con el resultado
        """
        if not self._check_circuit():
            return NodeResult(
                success=False,
                output=None,
                tool_name=tool_name,
                agent_used=agent_name,
                latency_ms=0.0,
                error="Circuit breaker abierto",
            )

        start_time = time.time()

        try:
            payload = {
                "agent": agent_name,
                "tool": tool_name,
                "params": params,
                "context": context,
            }

            handler = self._transport_handlers.get(self.transport, self._direct_call)
            result = handler(payload, is_node=True)

            latency = (time.time() - start_time) * 1000
            self._record_success()

            return NodeResult(
                success=result.get("success", False),
                output=result.get("output"),
                tool_name=tool_name,
                agent_used=agent_name,
                latency_ms=latency,
                error=result.get("error"),
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self._record_failure()
            logger.error("[Bifrost] Error ejecutando nodo %s: %s", tool_name, e)

            return NodeResult(
                success=False,
                output=None,
                tool_name=tool_name,
                agent_used=agent_name,
                latency_ms=latency,
                error=str(e),
            )

    def _direct_call(self, payload: Dict, is_node: bool = False) -> Dict:
        """
        Llamada directa a agentes de Vanaheim (mismo proceso).
        """
        agent_name = payload.get("agent", "freya")

        # Importar dinámicamente el agente
        try:
            # Mapeo de nombres a módulos
            agent_modules = {
                "freya": "Vanaheim.Agents.freya_agent",
                "heimdall": "Vanaheim.Agents.heimdall_agent",
                "eir": "Vanaheim.Agents.eir_agent",
                "balder": "Vanaheim.Agents.balder_agent",
            }

            module_path = agent_modules.get(agent_name)
            if not module_path:
                raise ValueError(f"Agente desconocido: {agent_name}")

            # Importar módulo
            import importlib

            module = importlib.import_module(module_path)

            # Obtener clase del agente
            class_name = f"{agent_name.capitalize()}Agent"
            agent_class = getattr(module, class_name)

            # Instanciar o cachear
            if agent_name not in self._agent_cache:
                self._agent_cache[agent_name] = agent_class()

            agent = self._agent_cache[agent_name]

            # Ejecutar
            if is_node:
                result = agent.execute_node(
                    tool=payload.get("tool"),
                    params=payload.get("params", {}),
                    context=payload.get("context", {}),
                )
            else:
                result = agent.execute_task(
                    task=payload.get("task", ""),
                    complexity_level=payload.get("complexity_level"),
                    context=payload.get("context", {}),
                )

            return {
                "success": True,
                "output": result,
                "metadata": {"agent": agent_name, "transport": "direct"},
            }

        except ImportError as e:
            logger.warning("[Bifrost] Agente %s no disponible: %s", agent_name, e)
            # Fallback: simular respuesta para desarrollo
            return self._fallback_response(payload, agent_name)

        except Exception as e:
            logger.error("[Bifrost] Error en llamada directa: %s", e)
            raise

    def _http_call(self, payload: Dict, is_node: bool = False) -> Dict:
        """
        Llamada HTTP al servicio de Vanaheim.
        """
        import requests

        endpoint = f"{self.http_endpoint}/{'node' if is_node else 'task'}"

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout_seconds,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout:
            raise TimeoutError(f"Timeout en llamada HTTP a {endpoint}")
        except requests.RequestException as e:
            raise ConnectionError(f"Error HTTP: {e}")

    def _fallback_response(self, payload: Dict, agent_name: str) -> Dict:
        """
        Respuesta de fallback cuando el agente no está disponible.
        Usado para desarrollo/testing.
        """
        task = payload.get("task", payload.get("params", {}).get("task", ""))

        return {
            "success": True,
            "output": f"[FALLBACK BIFROST] Agente {agent_name} recibió: {task[:100]}...",
            "metadata": {
                "agent": agent_name,
                "transport": "fallback",
                "note": "Agente no implementado aún - respuesta simulada",
            },
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica salud de la conexión Bifrost.
        """
        try:
            if self.transport == BifrostTransport.DIRECT:
                # Verificar que podemos importar al menos un agente
                try:
                    import importlib

                    importlib.import_module("Vanaheim.Agents.freya_agent")
                    return {
                        "status": "healthy",
                        "transport": self.transport.value,
                        "agents_available": True,
                    }
                except ImportError:
                    return {
                        "status": "degraded",
                        "transport": self.transport.value,
                        "agents_available": False,
                    }

            elif self.transport == BifrostTransport.HTTP:
                import requests

                response = requests.get(f"{self.http_endpoint}/health", timeout=5)
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "transport": self.transport.value,
                    "http_status": response.status_code,
                }

        except Exception as e:
            return {
                "status": "error",
                "transport": self.transport.value,
                "error": str(e),
            }

    def get_available_agents(self) -> List[str]:
        """Retorna lista de agentes de Vanaheim disponibles."""
        vanaheim_config = self.config.get("vanaheim_agents", {})
        return [
            name
            for name, config in vanaheim_config.items()
            if config.get("enabled", True)
        ]


class BifrostBridge:
    """
    Bridge para recibir llamadas desde Vanaheim hacia Asgard.
    Usado cuando Vanaheim necesita consultar a Lilith.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )

    def query_lilith(self, query: str, context: Optional[Dict] = None) -> Dict:
        """
        Consulta a Lilith desde Vanaheim.
        """
        # Esta función sería llamada por el servicio Vanaheim
        # para escalar problemas a Lilith
        logger.info("[BifrostBridge] Consulta desde Vanaheim: %s", query[:100])

        # TODO: Implementar comunicación real con Lilith
        return {
            "success": True,
            "response": f"Lilith recibió: {query[:100]}...",
            "escalated": True,
        }


# Singleton
_bifrost_instance: Optional[BifrostClient] = None


def get_bifrost_client(
    base_path: Optional[Path] = None, transport: Optional[str] = None
) -> BifrostClient:
    """Obtiene instancia singleton de BifrostClient."""
    global _bifrost_instance
    if _bifrost_instance is None:
        _bifrost_instance = BifrostClient(base_path, transport)
    return _bifrost_instance


__all__ = [
    "BifrostTransport",
    "BifrostResult",
    "NodeResult",
    "BifrostClient",
    "BifrostBridge",
    "get_bifrost_client",
]
