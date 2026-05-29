"""Cliente HTTP para Vanaheim - El Éxodo del Panteón.

Permite a Asgard (Lilith) delegar tareas a agentes que corren en Vanaheim
como servicios independientes.
"""
import os
from typing import Any, AsyncGenerator, Dict, Optional

import httpx


class VanaheimClient:
    """Cliente para comunicarse con el servicio Vanaheim."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("VANAHEIM_URL", "http://localhost:8001")
        self.timeout = 300.0  # Odín puede tardar

    async def health(self) -> Dict[str, Any]:
        """Health check del servicio Vanaheim."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return (
                    resp.json()
                    if resp.status_code == 200
                    else {"status": "unavailable"}
                )
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def list_agents(self) -> list:
        """Listar agentes registrados en Vanaheim."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/registry/agents")
                if resp.status_code == 200:
                    return resp.json().get("agents", [])
                return []
        except Exception:
            return []

    async def agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Health check de un agente específico."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/agents/{agent_id}/health")
                return resp.json() if resp.status_code == 200 else {"available": False}
        except Exception:
            return {"available": False}

    async def invoke(
        self,
        agent_id: str,
        task: str,
        context: str = "",
        conversation_history: Optional[list] = None,
        user_id: Optional[str] = None,
        channel: str = "discord",
    ) -> str:
        """Invocar un agente de forma síncrona.

        Args:
            agent_id: ID del agente (eva, adan, odin, shalltear, crystal)
            task: Tarea a ejecutar
            context: Contexto adicional
            conversation_history: Historial de conversación
            user_id: ID del usuario
            channel: Canal de origen

        Returns:
            Resultado de la ejecución
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/agents/{agent_id}/invoke",
                json={
                    "task": task,
                    "context": {"context": context} if context else {},
                    "conversation_history": conversation_history or [],
                    "user_id": user_id,
                    "channel": channel,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", "")

    async def stream(
        self,
        agent_id: str,
        task: str,
        context: str = "",
        conversation_history: Optional[list] = None,
        user_id: Optional[str] = None,
        channel: str = "discord",
    ) -> AsyncGenerator[str, None]:
        """Invocar un agente con streaming.

        Yields chunks de la respuesta.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/agents/{agent_id}/stream",
                json={
                    "task": task,
                    "context": {"context": context} if context else {},
                    "conversation_history": conversation_history or [],
                    "user_id": user_id,
                    "channel": channel,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        if data.startswith("[ERROR]"):
                            yield data
                            break
                        yield data

    def is_available(self) -> bool:
        """Verificar si Vanaheim está disponible (síncrono)."""
        try:
            import asyncio

            result = asyncio.run(self.health())
            return result.get("status") == "healthy"
        except Exception:
            return False


# Singleton para uso global
_vanaheim_client: Optional[VanaheimClient] = None


def get_vanaheim_client() -> VanaheimClient:
    """Obtener instancia singleton del cliente Vanaheim."""
    global _vanaheim_client
    if _vanaheim_client is None:
        _vanaheim_client = VanaheimClient()
    return _vanaheim_client


def invoke_agent_sync(
    agent_id: str,
    task: str,
    context: str = "",
    conversation_history: Optional[list] = None,
) -> str:
    """Invocar agente de forma síncrona (para uso desde tools sync).

    Fallback a agente local si Vanaheim no está disponible.
    """
    import asyncio

    client = get_vanaheim_client()

    try:
        return asyncio.run(
            client.invoke(
                agent_id=agent_id,
                task=task,
                context=context,
                conversation_history=conversation_history,
            )
        )
    except Exception as e:
        # Fallback: retornar error para que el caller decida
        return f"[Vanaheim {agent_id} unavailable: {e}]"
