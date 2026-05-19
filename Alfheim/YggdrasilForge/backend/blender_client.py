"""Async client for Blender MCP addon — HTTP bridge to Blender 3D.

The Blender MCP addon exposes tools via JSON-RPC on port 9897 (not default 9876).
On WSL2, the addon must be configured with host=0.0.0.0 to accept connections.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger("forge.blender")


class BlenderMCPError(Exception):
    """Error from a Blender MCP tool call."""

    def __init__(
        self, code: int = -1, message: str = "Unknown Blender MCP error", data: Any = None
    ):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(self.message)


class BlenderMCPClient:
    """Async HTTP client for Blender MCP addon.

    Sends JSON-RPC requests to the MCP server running inside Blender
    and wraps all MCP tool calls into convenient Python async methods.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 120.0):
        self.base_url = base_url or settings.BLENDER_MCP_URL
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._request_id = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call a Blender MCP tool via JSON-RPC 2.0 over HTTP.

        The Blender MCP addon exposes a JSON-RPC endpoint that implements
        the Model Context Protocol. We send a 'tools/call' method request
        and return the result content.

        Returns the parsed result content (typically a dict or string).

        Raises BlenderMCPError on JSON-RPC errors or connection failures.
        """
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
            "id": self._next_id(),
        }

        try:
            response = await client.post("/", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise BlenderMCPError(
                code=-32001,
                message=(
                    f"Cannot connect to Blender MCP at {self.base_url}. "
                    "Is Blender running with the MCP addon enabled?"
                ),
                data=str(exc),
            ) from exc
        except httpx.TimeoutException as exc:
            raise BlenderMCPError(
                code=-32002,
                message=f"Blender MCP timed out after {self.timeout}s",
                data=str(exc),
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise BlenderMCPError(
                code=exc.response.status_code,
                message=f"Blender MCP returned HTTP {exc.response.status_code}",
                data=exc.response.text[:500],
            ) from exc

        data = response.json()

        # JSON-RPC error response
        if "error" in data:
            err = data["error"]
            raise BlenderMCPError(
                code=err.get("code", -1),
                message=err.get("message", "Unknown JSON-RPC error"),
                data=err.get("data"),
            )

        # Extract result content
        result = data.get("result")

        # MCP tool results are typically {content: [{type: "text", text: "..."}]}
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")
                # Try to parse as JSON, fall back to raw text
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return text
            return content

        return result

    # ── Health Check ────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check if Blender MCP addon is reachable."""
        try:
            await self._get_client()
            # Try a lightweight call — get scene info
            result = await self._call_tool("get_scene_info", {"user_prompt": "health_check"})
            return result is not None
        except BlenderMCPError:
            return False
        except Exception:
            return False

    # ── Scene Operations ────────────────────────────────────────────────

    async def get_scene_info(self) -> dict:
        """Get detailed information about the current Blender scene."""
        return await self._call_tool("get_scene_info", {"user_prompt": "forge_scene_info"})

    async def get_object_info(self, object_name: str) -> dict:
        """Get detailed information about a specific object in the scene."""
        return await self._call_tool(
            "get_object_info",
            {
                "object_name": object_name,
            },
        )

    async def get_viewport_screenshot(self, max_size: int = 1000) -> Any:
        """Capture a screenshot of the current Blender 3D viewport."""
        return await self._call_tool(
            "get_viewport_screenshot",
            {
                "max_size": max_size,
                "user_prompt": "forge_screenshot",
            },
        )

    # ── Hunyuan3D ───────────────────────────────────────────────────────

    async def generate_hunyuan3d(
        self,
        text_prompt: str | None = None,
        image_url: str | None = None,
    ) -> dict:
        """Generate a 3D model using Hunyuan3D (text and/or image)."""
        args: dict[str, Any] = {"user_prompt": text_prompt or "forge_generation"}
        if text_prompt:
            args["text_prompt"] = text_prompt
        if image_url:
            args["input_image_url"] = image_url
        return await self._call_tool("generate_hunyuan3d_model", args)

    async def poll_hunyuan_status(self, job_id: str) -> dict:
        """Check if a Hunyuan3D generation task is completed."""
        return await self._call_tool("poll_hunyuan_job_status", {"job_id": job_id})

    async def import_hunyuan_asset(self, name: str, zip_file_url: str) -> dict:
        """Import a completed Hunyuan3D model into Blender."""
        return await self._call_tool(
            "import_generated_asset_hunyuan",
            {
                "name": name,
                "zip_file_url": zip_file_url,
            },
        )

    # ── Hyper3D Rodin ──────────────────────────────────────────────────

    async def generate_rodin_text(
        self,
        text_prompt: str,
        bbox_condition: list[float] | None = None,
    ) -> dict:
        """Generate a 3D model from text using Hyper3D Rodin."""
        args: dict[str, Any] = {"text_prompt": text_prompt, "user_prompt": text_prompt}
        if bbox_condition:
            args["bbox_condition"] = bbox_condition
        return await self._call_tool("generate_hyper3d_model_via_text", args)

    async def generate_rodin_image(
        self,
        image_paths: list[str] | None = None,
        image_urls: list[str] | None = None,
        bbox_condition: list[float] | None = None,
    ) -> dict:
        """Generate a 3D model from images using Hyper3D Rodin."""
        args: dict[str, Any] = {"user_prompt": "forge_image_to_3d"}
        if image_paths:
            args["input_image_paths"] = image_paths
        if image_urls:
            args["input_image_urls"] = image_urls
        if bbox_condition:
            args["bbox_condition"] = bbox_condition
        return await self._call_tool("generate_hyper3d_model_via_images", args)

    async def poll_rodin_status(
        self,
        subscription_key: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        """Check if a Hyper3D Rodin generation task is completed."""
        args: dict[str, str] = {}
        if subscription_key:
            args["subscription_key"] = subscription_key
        if request_id:
            args["request_id"] = request_id
        return await self._call_tool("poll_rodin_job_status", args)

    async def import_rodin_asset(
        self,
        name: str,
        task_uuid: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        """Import a completed Rodin model into Blender."""
        args: dict[str, str] = {"name": name}
        if task_uuid:
            args["task_uuid"] = task_uuid
        if request_id:
            args["request_id"] = request_id
        return await self._call_tool("import_generated_asset", args)

    # ── PolyHaven ───────────────────────────────────────────────────────

    async def get_polyhaven_status(self) -> dict:
        """Check if PolyHaven integration is enabled."""
        return await self._call_tool("get_polyhaven_status", {})

    async def get_polyhaven_categories(self, asset_type: str = "hdris") -> dict:
        """Get categories for a specific asset type on PolyHaven."""
        return await self._call_tool(
            "get_polyhaven_categories",
            {
                "asset_type": asset_type,
            },
        )

    async def search_polyhaven(
        self,
        asset_type: str = "all",
        categories: str | None = None,
    ) -> dict:
        """Search PolyHaven assets with optional filtering."""
        args: dict[str, Any] = {
            "asset_type": asset_type,
            "user_prompt": "forge_search",
        }
        if categories:
            args["categories"] = categories
        return await self._call_tool("search_polyhaven_assets", args)

    async def download_polyhaven(
        self,
        asset_id: str,
        asset_type: str,
        resolution: str = "1k",
        file_format: str | None = None,
    ) -> dict:
        """Download and import a PolyHaven asset into Blender."""
        args: dict[str, Any] = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "resolution": resolution,
            "user_prompt": f"forge_download_{asset_id}",
        }
        if file_format:
            args["file_format"] = file_format
        return await self._call_tool("download_polyhaven_asset", args)

    async def set_texture(self, object_name: str, texture_id: str) -> dict:
        """Apply a previously downloaded PolyHaven texture to an object."""
        return await self._call_tool(
            "set_texture",
            {
                "object_name": object_name,
                "texture_id": texture_id,
                "user_prompt": f"forge_texture_{texture_id}",
            },
        )

    # ── Sketchfab ───────────────────────────────────────────────────────

    async def get_sketchfab_status(self) -> dict:
        """Check if Sketchfab integration is enabled."""
        return await self._call_tool("get_sketchfab_status", {})

    async def search_sketchfab(
        self,
        query: str,
        categories: str | None = None,
        count: int = 10,
        downloadable: bool = True,
    ) -> dict:
        """Search Sketchfab models with optional filtering."""
        args: dict[str, Any] = {
            "query": query,
            "count": count,
            "downloadable": downloadable,
            "user_prompt": f"forge_search_{query}",
        }
        if categories:
            args["categories"] = categories
        return await self._call_tool("search_sketchfab_models", args)

    async def download_sketchfab(self, uid: str, target_size: float = 1.0) -> dict:
        """Download and import a Sketchfab model into Blender."""
        return await self._call_tool(
            "download_sketchfab_model",
            {
                "uid": uid,
                "target_size": target_size,
                "user_prompt": f"forge_download_{uid}",
            },
        )

    async def preview_sketchfab(self, uid: str) -> dict:
        """Get a preview thumbnail of a Sketchfab model."""
        return await self._call_tool("get_sketchfab_model_preview", {"uid": uid})

    # ── Blender Code Execution ──────────────────────────────────────────

    async def execute_blender_code(self, code: str) -> dict:
        """Execute arbitrary Python code in Blender.

        WARNING: This is powerful and dangerous in production. Add auth.
        """
        return await self._call_tool(
            "execute_blender_code",
            {
                "code": code,
                "user_prompt": "forge_execute",
            },
        )


# ── Singleton client instance ────────────────────────────────────────────

blender_client = BlenderMCPClient()
