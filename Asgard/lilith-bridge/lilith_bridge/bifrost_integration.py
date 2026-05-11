"""Bifrost integration — mount the Hermes Bridge onto the existing BifrostGateway.

This module provides a FastAPI router that can be included in the
BifrostGateway app to add Hermes Bridge endpoints. This way the
Bifrost server can also act as a bridge to Hermes Agent without
running a separate server.

Usage in ``bifrost/gateway.py``::

    from lilith_bridge.bifrost_integration import create_bridge_router

    bridge_router = create_bridge_router()
    app.include_router(bridge_router, prefix="/api/bridge")

This adds all the /api/bridge/* endpoints to the Bifrost server.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from .config import BridgeConfig, load_bridge_config
from .hermes_client import HermesClient
from .models import (
    BridgeChatRequest,
    BridgeChatResponse,
    BridgeHealth,
    BridgeMemoryQuery,
    BridgeMemoryStore,
    BridgeSkillSearch,
    HermesChatRequest,
    HermesChatResponse,
    HermesToolExecute,
    HermesToolResult,
)

logger = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────────────────

_bridge_config: BridgeConfig | None = None
_hermes_client: HermesClient | None = None


def _get_bridge_config() -> BridgeConfig:
    global _bridge_config
    if _bridge_config is None:
        _bridge_config = load_bridge_config()
    return _bridge_config


def _get_hermes_client(config: BridgeConfig = Depends(_get_bridge_config)) -> HermesClient:
    global _hermes_client
    if _hermes_client is None:
        _hermes_client = HermesClient(
            base_url=config.hermes_url,
            api_key=config.hermes_api_key,
            timeout=config.hermes_timeout,
            max_retries=config.hermes_max_retries,
        )
    return _hermes_client


def _verify_bridge_token(
    request: Request,
    config: BridgeConfig = Depends(_get_bridge_config),
) -> dict[str, str]:
    """Verify authentication for bridge endpoints.

    If BifrostGateway already authenticated the user via its own JWT
    middleware, the request will have a valid user. This adds an
    additional layer: if ``auth_token`` is configured in bridge config,
    it must match. If not configured, BifrostGateway's own auth is
    sufficient.
    """
    if not config.auth_token:
        return {"sub": "bifrost-user", "role": "admin"}

    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        if auth[7:] == config.auth_token:
            return {"sub": "bearer", "role": "admin"}

    bridge_token = request.headers.get("x-bridge-token")
    if bridge_token == config.auth_token:
        return {"sub": "bridge", "role": "admin"}

    raise HTTPException(status_code=401, detail="Invalid bridge token")


# ── Router factory ──────────────────────────────────────────────────────


def create_bridge_router(
    config: BridgeConfig | None = None,
    engine: Any = None,
    memory: Any = None,
    skills_ctx: Any = None,
) -> APIRouter:
    """Create a FastAPI router with Hermes Bridge endpoints.

    This router can be included in any existing FastAPI app (Bifrost,
    lilith-api, etc.) to add bidirectional bridge functionality.

    Parameters
    ----------
    config:
        Optional pre-built config. Falls back to loading from YAML.
    engine:
        Optional pre-initialised LilithEngine. If None, the bridge
        will try to lazy-load one.
    memory:
        Optional pre-initialised MemoryStore. If None, lazy-loads.
    skills_ctx:
        Optional pre-initialised SkillContext. If None, lazy-loads.
    """
    global _bridge_config
    if config:
        _bridge_config = config
    else:
        _bridge_config = _get_bridge_config()

    router = APIRouter(prefix="/bridge", tags=["Hermes Bridge"])

    # ── Health ─────────────────────────────────────────────────────

    @router.get("/health", response_model=BridgeHealth)
    async def bridge_health():
        hermes = _get_hermes_client()
        hermes_info = await hermes.health()
        skills_count = len(skills_ctx.registry.skills) if skills_ctx else 0

        return BridgeHealth(
            status="healthy",
            bridge_version="1.0.0",
            lilith_engine=engine is not None,
            hermes_connected=hermes_info.get("connected", False),
            memory_available=memory is not None,
            skills_loaded=skills_count,
            uptime_seconds=0.0,  # Bifrost tracks its own uptime
        )

    # ── Inbound: Hermes → Yggdrasil (Lilith) ──────────────────────

    @router.post("/chat", response_model=BridgeChatResponse)
    async def bridge_chat_inbound(
        req: BridgeChatRequest,
        user: dict = Depends(_verify_bridge_token),
    ):
        if engine is None:
            raise HTTPException(
                status_code=503,
                detail="Lilith engine not available",
            )

        import uuid

        start = time.time()
        session_id = req.session_id or str(uuid.uuid4())

        try:
            result = engine.process(req.message)
            latency = round((time.time() - start) * 1000, 2)

            tools_used: list[str] = []
            if isinstance(result, dict) and result.get("tool_call"):
                tc = result["tool_call"]
                tools_used.append(tc.get("name", "unknown") if isinstance(tc, dict) else str(tc))

            return BridgeChatResponse(
                response=result.get("response", "") if isinstance(result, dict) else str(result),
                session_id=session_id,
                latency_ms=latency,
                tools_used=tools_used,
                usage=result.get("usage") if isinstance(result, dict) else None,
            )
        except Exception as exc:
            logger.exception("Bridge chat inbound error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/memory")
    async def bridge_memory_recall(
        query: str = Query(...),
        k: int = Query(5),
        user: dict = Depends(_verify_bridge_token),
    ):
        if memory is None:
            raise HTTPException(status_code=503, detail="Memory not available")

        try:
            results = memory.search(query, k=k)
            return {"results": results, "count": len(results)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @router.post("/memory")
    async def bridge_memory_store(
        req: BridgeMemoryStore,
        user: dict = Depends(_verify_bridge_token),
    ):
        if memory is None:
            raise HTTPException(status_code=503, detail="Memory not available")

        try:
            memory.store(req.text, req.metadata)
            return {"status": "stored", "text": req.text[:100]}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/skills")
    async def bridge_list_skills(
        category: str | None = Query(None),
        user: dict = Depends(_verify_bridge_token),
    ):
        if skills_ctx is None:
            raise HTTPException(status_code=503, detail="Skills not available")

        if category:
            content = skills_ctx.format_by_category(category)
            return {"category": category, "content": content}

        return {"categories": skills_ctx.list_available()}

    @router.post("/skills/search")
    async def bridge_search_skills(
        req: BridgeSkillSearch,
        user: dict = Depends(_verify_bridge_token),
    ):
        if skills_ctx is None:
            raise HTTPException(status_code=503, detail="Skills not available")

        results = skills_ctx.search(req.query, limit=req.limit)
        return {"query": req.query, "results": results, "count": len(results)}

    # ── Outbound: Yggdrasil → Hermes ──────────────────────────────

    @router.post("/hermes/chat", response_model=HermesChatResponse)
    async def bridge_chat_outbound(
        req: HermesChatRequest,
        user: dict = Depends(_verify_bridge_token),
    ):
        hermes = _get_hermes_client()
        start = time.time()

        messages: list[dict[str, Any]] = []
        if req.context:
            messages.append({"role": "system", "content": req.context})
        messages.append({"role": "user", "content": req.message})

        try:
            result = await hermes.chat(messages, model=req.model)

            if not result.get("choices"):
                raise HTTPException(status_code=502, detail="Hermes returned no choices")

            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "")

            tools_used: list[str] = []
            for tc in choice.get("message", {}).get("tool_calls", []):
                func = tc.get("function", {})
                tools_used.append(func.get("name", "unknown"))

            return HermesChatResponse(
                response=content,
                model=result.get("model", ""),
                usage=result.get("usage"),
                tools_used=tools_used,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Hermes outbound error: %s", exc)
            raise HTTPException(status_code=502, detail=f"Hermes error: {exc}")

    @router.get("/hermes/models")
    async def bridge_hermes_models(
        user: dict = Depends(_verify_bridge_token),
    ):
        hermes = _get_hermes_client()
        models = await hermes.list_models()
        return {"models": models, "count": len(models)}

    @router.post("/hermes/execute", response_model=HermesToolResult)
    async def bridge_hermes_execute(
        req: HermesToolExecute,
        user: dict = Depends(_verify_bridge_token),
    ):
        hermes = _get_hermes_client()

        try:
            result = await hermes.execute_tool(req.tool, req.params)

            if isinstance(result, dict):
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return HermesToolResult(tool=req.tool, success=True, result=content)

            return HermesToolResult(tool=req.tool, success=True, result=result)
        except Exception as exc:
            return HermesToolResult(tool=req.tool, success=False, error=str(exc))

    @router.get("/hermes/health")
    async def bridge_hermes_health(
        user: dict = Depends(_verify_bridge_token),
    ):
        hermes = _get_hermes_client()
        return await hermes.health()

    return router