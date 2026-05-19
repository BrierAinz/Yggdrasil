"""Cliente HTTP para MuninnDB en Asgard.

Reemplaza las importaciones directas de muninn_memory con
llamadas HTTP al API de Lilith.
"""

import asyncio
import os
from typing import Any

import httpx


class MuninnClient:
    """Cliente HTTP para comunicarse con MuninnDB en Asgard."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("MUNINN_URL", "http://localhost:8000")
        self.timeout = 30.0

    async def get_memory(self, agent_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recuperar memorias relevantes para un agente.

        Args:
            agent_id: ID del agente
            query: Consulta para búsqueda semántica
            limit: Número máximo de resultados

        Returns:
            Lista de memorias relevantes
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/memory/retrieve",
                    json={
                        "agent_id": agent_id,
                        "query": query,
                        "limit": limit,
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("memories", [])
                return []
        except Exception:
            return []

    async def write_memory(
        self, agent_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Escribir una memoria para un agente (fire-and-forget).

        Args:
            agent_id: ID del agente
            content: Contenido de la memoria
            metadata: Metadatos adicionales

        Returns:
            True si se escribió exitosamente
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/memory/write",
                    json={
                        "agent_id": agent_id,
                        "content": content,
                        "metadata": metadata or {},
                    },
                )
                return resp.status_code == 200
        except Exception:
            return False

    def write_memory_sync(
        self, agent_id: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Escribir memoria de forma síncrona (fire-and-forget).

        Usar en contextos donde no se puede usar async.
        """
        try:
            _task = asyncio.create_task(self.write_memory(agent_id, content, metadata))  # noqa: RUF006
        except Exception:
            pass

    async def get_agent_context(self, agent_id: str, user_id: str | None = None) -> dict[str, Any]:
        """Obtener contexto completo para un agente.

        Args:
            agent_id: ID del agente
            user_id: ID del usuario (opcional)

        Returns:
            Contexto agregado (memorias, preferencias, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/memory/context",
                    params={"agent_id": agent_id, "user_id": user_id},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {}
        except Exception:
            return {}


def get_muninn_client() -> MuninnClient:
    """Obtener instancia del cliente Muninn."""
    return MuninnClient()
