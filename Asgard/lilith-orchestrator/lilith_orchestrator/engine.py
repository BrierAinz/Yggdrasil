"""
LilithEngine — Motor de orquestación multi-agente de Lilith

Este módulo es el punto de entrada principal de lilith-orchestrator.
LilithEngine conecta la configuración de Lilith con el sistema swarm
para producir respuestas orquestadas por múltiples agentes.

Uso:
    from lilith_orchestrator.engine import LilithEngine
    engine = LilithEngine(config, memory)
    result = engine.process("Hola, ¿cómo estás?")
    # result = {"response": "...", "usage": {...}, "tool_call": None}

Cuando el swarm no está disponible o no tiene agentes registrados,
LilithEngine realiza un fallback a una llamada LLM directa usando la
configuración proporcionada.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


logger = logging.getLogger("lilith.engine")

# ── Tipos de resultado ────────────────────────────────────────────────────────


@dataclass
class EngineUsage:
    """Uso de tokens y métricas de una llamada al engine."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    agents_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert usage stats to a plain dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "agents_used": self.agents_used,
        }


# ── LilithEngine ──────────────────────────────────────────────────────────────


class LilithEngine:
    """
    Motor central de orquestación de Lilith.

    Conecta la configuración de Lilith (LilithConfig) y el almacén de
    memoria (MemoryStore opcional) con el sistema swarm para producir
    respuestas orquestadas.

    Flujo:
        1. Recibe mensaje del usuario.
        2. Intenta usar el sistema swarm (Coordinator + Swarm + TaskPlanner).
        3. Si el swarm no está disponible, falla a una llamada LLM directa.
        4. Retorna resultado con response, usage y tool_call.

    El engine es async-compatible:
        - ``process()`` se puede llamar desde código síncrono.
        - ``process_stream()`` es un async generator para respuestas streaming.
    """

    def __init__(self, config: Any, memory: Any = None) -> None:
        """
        Inicializa LilithEngine.

        Args:
            config: Instancia de LilithConfig con la configuración del modelo.
                     Se accede a ``config.model``, ``config.base_url``,
                     ``config.api_key``, etc.
            memory: Instancia opcional de MemoryStore para consulta de contexto.
        """
        self.config = config
        self.memory = memory

        # Componentes del swarm (lazy init)
        self._swarm: Any = None
        self._coordinator: Any = None

        # Métricas
        self._request_count: int = 0
        self._error_count: int = 0
        self._total_latency_ms: float = 0.0

        logger.info("LilithEngine initialized (model=%s)", getattr(config, "model", "unknown"))

    # ── Inicialización lazy ───────────────────────────────────────────────

    def _init_swarm(self) -> bool:
        """
        Intenta inicializar el sistema swarm.

        Returns:
            True si el swarm se inicializó con al menos un agente, False si no.
        """
        if self._swarm is not None:
            # Ya inicializado — verificar que tenga agentes
            return len(self._swarm.list_agents()) > 0

        try:
            from lilith_core.agents.swarm import get_swarm
            from lilith_core.agents.swarm.coordinator import get_coordinator

            self._swarm = get_swarm()
            self._coordinator = get_coordinator()

            # Verificar que haya agentes registrados
            agents = self._swarm.list_agents()
            if agents:
                logger.info(
                    "Swarm initialized with %d agents: %s",
                    len(agents),
                    [a["name"] for a in agents],
                )
                return True
            logger.warning("Swarm initialized but no agents registered — will use LLM fallback")
            return False

        except ImportError:
            logger.debug("lilith_core swarm not available — using LLM fallback")
            return False
        except Exception as exc:
            logger.warning("Failed to init swarm: %s — using LLM fallback", exc)
            return False

    def _ensure_coordinator(self) -> Any:
        """Retorna el coordinator, creando si es necesario."""
        if self._coordinator is None:
            try:
                from lilith_core.agents.swarm.coordinator import get_coordinator

                self._coordinator = get_coordinator()
            except ImportError:
                pass
        return self._coordinator

    # ── Procesamiento principal ───────────────────────────────────────────

    def process(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Procesa un mensaje del usuario y retorna la respuesta.

        Este método se puede llamar desde código síncrono. Internamente,
        crea o reutiliza un event loop para correr el procesamiento async.

        Args:
            message: Mensaje del usuario.
            context: Contexto adicional (opcional).

        Returns:
            Diccionario con:
                - response: str — Texto de respuesta.
                - usage: dict — Métricas de uso.
                - tool_call: dict | None — Tool call detectado, si lo hay.
        """
        start = time.time()
        self._request_count += 1

        # Intentar procesar con el swarm
        has_swarm = self._init_swarm()

        if has_swarm and self._coordinator is not None:
            result = self._process_swarm_sync(message, context or {})
        else:
            result = self._process_llm_fallback(message, context or {})

        # Registrar métricas
        elapsed_ms = (time.time() - start) * 1000
        self._total_latency_ms += elapsed_ms

        # Asegurar estructura de resultado
        return self._normalize_result(result, elapsed_ms)

    async def process_stream(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Procesa un mensaje en modo streaming, yieldando fragmentos.

        Este es un async generator — se usa con ``async for``:
            async for chunk in engine.process_stream(message):
                print(chunk["response"])

        Args:
            message: Mensaje del usuario.
            context: Contexto adicional (opcional).

        Yields:
            Diccionarios parciales con:
                - response: str — Fragmento de texto.
                - usage: dict | None — Métricas (solo en el último chunk).
                - tool_call: dict | None — Tool call (solo si se detecta).
                - done: bool — True en el último fragmento.
        """
        self._request_count += 1
        start = time.time()
        has_swarm = self._init_swarm()

        if has_swarm and self._coordinator is not None:
            async for chunk in self._process_swarm_stream(message, context or {}):
                yield chunk
        else:
            async for chunk in self._process_llm_stream(message, context or {}):
                yield chunk

        elapsed_ms = (time.time() - start) * 1000
        self._total_latency_ms += elapsed_ms

        # Yield métricas finales
        yield {
            "response": "",
            "usage": {"latency_ms": round(elapsed_ms, 2)},
            "tool_call": None,
            "done": True,
        }

    # ── Procesamiento swarm ────────────────────────────────────────────────

    def _process_swarm_sync(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta el procesamiento víaCoordinator (swarm multi-agente) de forma síncrona.

        Internamente corre el event loop para ejecutar la coroutine del Coordinator.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async def _run() -> dict[str, Any]:
            return await self._process_swarm_async(message, context)

        if loop and loop.is_running():
            # Ya estamos en un event loop — crear tarea y esperar resultado
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _run())
                return future.result(timeout=120)
        else:
            return asyncio.run(_run())

    async def _process_swarm_async(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta procesamiento vía swarm de forma asíncrona."""
        try:
            result = await self._coordinator.execute(
                task_description=message,
                context=context,
            )

            # Reconstruir respuesta del CoordinationResult
            agents_used = getattr(result, "agents_used", [])
            response_text = getattr(result, "final_output", "")
            if not response_text:
                response_text = str(getattr(result, "error", "Sin respuesta del swarm"))

            return {
                "response": response_text,
                "usage": EngineUsage(
                    agents_used=agents_used,
                    latency_ms=getattr(result, "execution_time_ms", 0),
                ),
                "tool_call": None,
            }

        except Exception as exc:
            logger.error("Swarm processing failed: %s", exc, exc_info=True)
            self._error_count += 1
            # Fallback a LLM directo
            return self._process_llm_fallback(message, context)

    async def _process_swarm_stream(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming vía swarm — por ahora delega al async y yieldea el resultado completo."""
        try:
            result = await self._coordinator.execute(
                task_description=message,
                context=context,
            )

            agents_used = getattr(result, "agents_used", [])
            response_text = getattr(result, "final_output", "")
            if not response_text:
                response_text = str(getattr(result, "error", "Sin respuesta del swarm"))

            yield {
                "response": response_text,
                "usage": EngineUsage(
                    agents_used=agents_used,
                    latency_ms=getattr(result, "execution_time_ms", 0),
                ),
                "tool_call": None,
                "done": False,
            }

        except Exception as exc:
            logger.error("Swarm stream failed: %s", exc, exc_info=True)
            self._error_count += 1
            async for chunk in self._process_llm_stream(message, context):
                yield chunk

    # ── Fallback: llamada LLM directa ──────────────────────────────────────

    def _process_llm_fallback(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Fallback cuando el swarm no está disponible.

        Usa la configuración del engine para hacer una llamada directa al LLM.
        """
        logger.debug("Using LLM fallback for message: %s", message[:80])

        # Intentar usar el cliente LLM de la configuración
        try:
            client = self._get_llm_client()
            if client is not None:
                response_text = self._call_llm(client, message, context)
                return {
                    "response": response_text,
                    "usage": EngineUsage(agents_used=["llm_fallback"]),
                    "tool_call": None,
                }
        except Exception as exc:
            logger.exception("LLM fallback call failed: %s", exc)
            self._error_count += 1

        # Último recurso: respuesta de error friendly
        return {
            "response": "[Lilith] No pude procesar tu mensaje en este momento. "
            "El sistema swarm y el LLM directo no están disponibles.",
            "usage": EngineUsage(),
            "tool_call": None,
        }

    async def _process_llm_stream(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Fallback streaming vía LLM directo."""
        result = self._process_llm_fallback(message, context)
        yield {
            "response": result["response"],
            "usage": result["usage"].to_dict()
            if isinstance(result["usage"], EngineUsage)
            else result["usage"],
            "tool_call": None,
            "done": False,
        }

    def _get_llm_client(self) -> Any:
        """
        Obtiene un cliente LLM a partir de la configuración.

        Intenta importar y configurar el cliente HTTP para llamadas API
        usando los parámetros de LilithConfig.
        """
        config = self.config

        # Intentar usar LLMClient de lilith_core si está disponible
        try:
            from lilith_core.llm import LLMClient

            return LLMClient(
                model=getattr(config, "model", "gpt-4"),
                base_url=getattr(config, "base_url", None),
                api_key=getattr(config, "api_key", None),
            )
        except ImportError:
            pass

        # Intentar usar el cliente directo de la configuración
        if hasattr(config, "llm_client") and config.llm_client is not None:
            return config.llm_client

        return None

    def _call_llm(self, client: Any, message: str, context: dict[str, Any]) -> str:
        """Realiza una llamada al LLM y retorna la respuesta como texto."""
        import httpx

        # Construir messages
        messages = []
        system_prompt = getattr(self.config, "system_prompt", None) or self._get_system_prompt()

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Inyectar contexto de memoria si está disponible
        if self.memory is not None:
            try:
                recent = self.memory.search(message, limit=5)
                if recent:
                    memory_context = "\n".join(f"- {m.get('content', '')}" for m in recent[:5])
                    messages.append(
                        {
                            "role": "system",
                            "content": f"Contexto relevante de memoria:\n{memory_context}",
                        },
                    )
            except Exception as exc:
                logger.debug("Memory lookup failed (non-fatal): %s", exc)

        # Contexto adicional del caller
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            messages.append(
                {
                    "role": "system",
                    "content": f"Contexto adicional:\n{context_str}",
                },
            )

        messages.append({"role": "user", "content": message})

        model = getattr(self.config, "model", "gpt-4")
        base_url = getattr(self.config, "base_url", "http://localhost:1234/v1")
        api_key = getattr(self.config, "api_key", "lm-studio")
        max_tokens = getattr(self.config, "max_tokens", 2048)
        temperature = getattr(self.config, "temperature", 0.7)

        # Si el cliente tiene un método chat, usarlo
        if hasattr(client, "chat"):
            return client.chat(message)

        # Si tiene un método generate, usarlo
        if hasattr(client, "generate"):
            return client.generate(message)

        # Fallback: llamada HTTP directa (estilo OpenAI-compatible)
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            resp = httpx.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # Extraer respuesta
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return content or "(sin respuesta del modelo)"
            return "(sin respuesta del modelo)"

        except Exception as exc:
            logger.exception("Direct LLM call failed: %s", exc)
            raise

    def _get_system_prompt(self) -> str:
        """Obtiene el system prompt por defecto."""
        try:
            from lilith_core.config import SYSTEM_PROMPT

            return SYSTEM_PROMPT
        except ImportError:
            pass

        return (
            "Eres Lilith, una asistente inteligente y versátil. "
            "Respondes en el idioma del usuario con claridad y precisión."
        )

    # ── Normalización de resultados ───────────────────────────────────────

    def _normalize_result(self, result: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
        """Asegura que el resultado siempre tenga la estructura esperada."""
        if not isinstance(result, dict):
            result = {"response": str(result)}

        # response
        response = result.get("response", "")
        if response is None:
            response = "(sin respuesta)"
        result["response"] = str(response)

        # usage
        raw_usage = result.get("usage", {})
        if isinstance(raw_usage, EngineUsage):
            result["usage"] = raw_usage.to_dict()
        elif isinstance(raw_usage, dict):
            raw_usage.setdefault("latency_ms", round(elapsed_ms, 2))
            result["usage"] = raw_usage
        else:
            result["usage"] = {"latency_ms": round(elapsed_ms, 2)}

        # tool_call
        result.setdefault("tool_call", None)

        # context (para compatibilidad con lilith-api)
        result.setdefault("context", [])

        return result

    # ── Utilidades ──────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas del engine."""
        avg_latency = self._total_latency_ms / self._request_count if self._request_count > 0 else 0
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "swarm_available": self._swarm is not None,
            "memory_available": self.memory is not None,
            "model": getattr(self.config, "model", "unknown"),
        }

    def reset_stats(self) -> None:
        """Reinicia contadores de métricas."""
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0
