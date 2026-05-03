"""Cliente HTTP para Lilith API."""

from typing import Any, Optional

import httpx


DEFAULT_URL = "http://localhost:8000"


class LilithClient:
    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def health(self) -> dict[str, Any]:
        r = self.client.get(f"{self.base_url}/health")
        r.raise_for_status()
        return r.json()

    def chat(self, message: str, model: Optional[str] = None) -> dict[str, Any]:
        payload = {"message": message}
        if model:
            payload["model"] = model
        r = self.client.post(f"{self.base_url}/chat", json=payload)
        r.raise_for_status()
        return r.json()

    def list_tools(self) -> dict[str, str]:
        r = self.client.get(f"{self.base_url}/tools")
        r.raise_for_status()
        return r.json()

    def execute_tool(self, tool: str, params: dict[str, Any]) -> Any:
        r = self.client.post(
            f"{self.base_url}/tools/execute", json={"tool": tool, "params": params}
        )
        r.raise_for_status()
        return r.json()

    def memory_recall(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        r = self.client.get(f"{self.base_url}/memory", params={"query": query, "k": k})
        r.raise_for_status()
        return r.json()

    def memory_store(self, text: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        payload = {"text": text, "metadata": metadata or {}}
        r = self.client.post(f"{self.base_url}/memory", json=payload)
        r.raise_for_status()
        return r.json()
