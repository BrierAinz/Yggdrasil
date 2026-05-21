"""Bifrost integration — mount the Hermes Bridge onto the existing BifrostGateway.

This module provides TWO factory functions:

- ``create_bridge_router()`` — returns an APIRouter for embedding into
  existing FastAPI apps (Bifrost gateway, etc.).
- ``create_standalone_app()`` — returns a complete FastAPI application
  for running the bridge as a standalone server (port 9001).

All bridge logic lives HERE.  The ``app.py`` entry-point is just a thin
wrapper that calls ``create_standalone_app()`` and runs uvicorn.

Usage in ``bifrost/gateway.py``::

    from lilith_bridge.bifrost_integration import create_bridge_router

    bridge_router = create_bridge_router(engine=_engine, memory=_memory)
    app.include_router(bridge_router, prefix="/api/bridge")

Usage standalone::

    from lilith_bridge.bifrost_integration import create_standalone_app

    app = create_standalone_app()
    uvicorn.run(app, host="0.0.0.0", port=9001)
"""

from __future__ import annotations

# Import version without triggering circular import (don't use `from . import __version__`)
import importlib
import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import BridgeConfig, load_bridge_config
from .hermes_client import HermesClient
from .models import (
    BridgeChatRequest,
    BridgeChatResponse,
    BridgeHealth,
    BridgeMemoryStore,
    BridgeSkillSearch,
    HermesChatRequest,
    HermesChatResponse,
    HermesToolExecute,
    HermesToolResult,
)


try:
    _bridge_version = importlib.import_module("lilith_bridge").__version__
except (AttributeError, ImportError):
    _bridge_version = "1.0.0"


logger = logging.getLogger(__name__)

# ── Lazy Lilith state (used by standalone mode) ──────────────────────────


class _LilithState:
    """Holds lazily-initialised Lilith component references."""

    __slots__ = ("engine", "memory", "skills_ctx", "skills_loaded")

    def __init__(self) -> None:
        self.engine: Any = None
        self.memory: Any = None
        self.skills_ctx: Any = None
        self.skills_loaded: int = 0

    def ensure_engine(self, config: BridgeConfig) -> Any:
        """Lazy-initialise the LilithEngine, loading config and memory as needed."""
        if self.engine is None:
            try:
                from lilith_core.config import Config as LilithConfig
                from lilith_orchestrator.engine import LilithEngine

                lconfig = LilithConfig()
                if config.default_model != "auto":
                    object.__setattr__(lconfig, "model", config.default_model)
                self.engine = LilithEngine(lconfig, self.ensure_memory(config))
                logger.info("LilithEngine initialized")
            except ImportError:
                logger.warning("lilith_orchestrator not available — engine disabled")
                self.engine = None
        return self.engine

    def ensure_memory(self, config: BridgeConfig) -> Any:
        """Lazy-initialise the MemoryStore, creating the DB directory if needed."""
        if self.memory is None:
            try:
                from lilith_memory.store import MemoryStore

                db_path = config.resolve_memory_db()
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.memory = MemoryStore(str(db_path))
                logger.info("MemoryStore initialized: %s", db_path)
            except ImportError:
                logger.warning("lilith_memory not available — memory disabled")
                self.memory = None
        return self.memory

    def ensure_skills(self, config: BridgeConfig) -> tuple[Any, int]:
        """Lazy-initialise the SkillContext, loading skills from the repo."""
        if self.skills_ctx is None:
            try:
                from lilith_skills.context import SkillContext

                skills_dir = config.resolve_skills_dir()
                if skills_dir:
                    ctx = SkillContext.from_repo(str(skills_dir.parent.parent))
                    self.skills_ctx = ctx
                    self.skills_loaded = len(ctx.registry.skills)
                    logger.info(
                        "SkillContext loaded: %d skills from %s",
                        self.skills_loaded,
                        skills_dir,
                    )
                else:
                    logger.warning("Skills directory not found")
                    self.skills_ctx = None
                    self.skills_loaded = 0
            except ImportError:
                logger.warning("lilith_skills not available — skills disabled")
                self.skills_ctx = None
                self.skills_loaded = 0
        return self.skills_ctx, self.skills_loaded


# ── State singletons (module-level for standalone mode) ──────────────────

_bridge_config: BridgeConfig | None = None
_hermes_client: HermesClient | None = None
_lilith_state: _LilithState | None = None


def _validate_hermes_response(result: dict[str, Any]) -> dict[str, Any]:
    """Raise HTTPException if Hermes returned no choices."""
    if not result.get("choices"):
        raise HTTPException(status_code=502, detail="Hermes returned no choices")
    return result


def _get_bridge_config() -> BridgeConfig:
    """Lazy-load and cache the bridge configuration singleton."""
    global _bridge_config
    if _bridge_config is None:
        _bridge_config = load_bridge_config()
    return _bridge_config


def _get_hermes_client(config: BridgeConfig = Depends(_get_bridge_config)) -> HermesClient:
    """Lazy-load and cache the Hermes API client singleton."""
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

    Accepts:
      - Authorization: Bearer ***  (if auth_token configured)
      - X-Bridge-Token: <token>
      - ?token=<token>  (query parameter)
      - If no auth_token configured, allow all.
    """
    if not config.auth_token:
        return {"sub": "anonymous", "role": "admin"}

    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == config.auth_token:
        return {"sub": "bearer", "role": "admin"}

    bridge_token = request.headers.get("x-bridge-token")
    if bridge_token == config.auth_token:
        return {"sub": "bridge", "role": "admin"}

    query_token = request.query_params.get("token")
    if query_token == config.auth_token:
        return {"sub": "query", "role": "admin"}

    raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


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
        will try to lazy-load one (standalone mode).
    memory:
        Optional pre-initialised MemoryStore. If None, lazy-loads.
    skills_ctx:
        Optional pre-initialised SkillContext. If None, lazy-loads.

    """
    global _bridge_config
    _bridge_config = config or _get_bridge_config()

    # Use injected dependencies or lazy-load via _LilithState.
    state = _LilithState() if engine is None else None
    if state:
        state.engine = engine
        state.memory = memory
        state.skills_ctx = skills_ctx
        state.skills_loaded = len(skills_ctx.registry.skills) if skills_ctx else 0

    router = APIRouter(prefix="/bridge", tags=["Hermes Bridge"])

    # ── Health ─────────────────────────────────────────────────────

    @router.get("/health", response_model=BridgeHealth)
    async def bridge_health() -> BridgeHealth:
        """Return bridge health status including Hermes connection and loaded skills."""
        hermes = _get_hermes_client()
        hermes_info = await hermes.health()
        skills_count = (
            state.skills_loaded if state else (len(skills_ctx.registry.skills) if skills_ctx else 0)
        )

        return BridgeHealth(
            status="healthy",
            bridge_version=_bridge_version,
            lilith_engine=(state.engine if state else engine) is not None,
            hermes_connected=hermes_info.get("connected", False),
            memory_available=(state.memory if state else memory) is not None,
            skills_loaded=skills_count,
            uptime_seconds=0.0,
        )

    # ── Inbound: Hermes → Yggdrasil (Lilith) ──────────────────────

    @router.post("/chat", response_model=BridgeChatResponse)
    async def bridge_chat_inbound(
        req: BridgeChatRequest,
        _user: dict = Depends(_verify_bridge_token),
    ) -> BridgeChatResponse:
        """Receive a chat message from Hermes and process it through Lilith engine."""
        _engine = state.ensure_engine(_bridge_config) if state else engine
        if _engine is None:
            raise HTTPException(
                status_code=503,
                detail="Lilith engine not available (lilith-orchestrator not installed)",
            )

        start = time.time()
        session_id = req.session_id or str(uuid.uuid4())

        try:
            result = _engine.process(req.message)
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
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/memory")
    async def bridge_memory_recall(
        query: str = Query(...),
        k: int = Query(5),
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """Search Lilith memory for entries matching the query."""
        _memory = state.ensure_memory(_bridge_config) if state else memory
        if _memory is None:
            raise HTTPException(status_code=503, detail="Memory not available")

        try:
            results = _memory.search(query, k=k)
            return {"results": results, "count": len(results)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/memory")
    async def bridge_memory_store(
        req: BridgeMemoryStore,
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """Store a new memory entry in Lilith's vector store."""
        _memory = state.ensure_memory(_bridge_config) if state else memory
        if _memory is None:
            raise HTTPException(status_code=503, detail="Memory not available")

        try:
            _memory.store(req.text, req.metadata)
            return {"status": "stored", "text": req.text[:100]}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/skills")
    async def bridge_list_skills(
        category: str | None = Query(None),
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """List available skill categories or format skills by category."""
        _skills_ctx, _ = (
            state.ensure_skills(_bridge_config)
            if state
            else (skills_ctx, len(skills_ctx.registry.skills) if skills_ctx else 0)
        )
        if _skills_ctx is None:
            raise HTTPException(status_code=503, detail="Skills not available")

        if category:
            content = _skills_ctx.format_by_category(category)
            return {"category": category, "content": content}

        return {"categories": _skills_ctx.list_available()}

    @router.post("/skills/search")
    async def bridge_search_skills(
        req: BridgeSkillSearch,
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """Search skills by query string with optional result limit."""
        _skills_ctx, _ = (
            state.ensure_skills(_bridge_config)
            if state
            else (skills_ctx, len(skills_ctx.registry.skills) if skills_ctx else 0)
        )
        if _skills_ctx is None:
            raise HTTPException(status_code=503, detail="Skills not available")

        results = _skills_ctx.search(req.query, limit=req.limit)
        return {"query": req.query, "results": results, "count": len(results)}

    # ── Outbound: Yggdrasil → Hermes ──────────────────────────────

    @router.post("/hermes/chat", response_model=HermesChatResponse)
    async def bridge_chat_outbound(
        req: HermesChatRequest,
        _user: dict = Depends(_verify_bridge_token),
    ) -> HermesChatResponse:
        """Send a chat message to Hermes and relay the response back."""
        hermes = _get_hermes_client()

        messages: list[dict[str, Any]] = []
        if req.context:
            messages.append({"role": "system", "content": req.context})
        messages.append({"role": "user", "content": req.message})

        try:
            result = _validate_hermes_response(await hermes.chat(messages, model=req.model))

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
            raise HTTPException(status_code=502, detail=f"Hermes error: {exc}") from exc

    @router.get("/hermes/models")
    async def bridge_hermes_models(
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """List available models from the Hermes endpoint."""
        hermes = _get_hermes_client()
        models = await hermes.list_models()
        return {"models": models, "count": len(models)}

    @router.post("/hermes/execute", response_model=HermesToolResult)
    async def bridge_hermes_execute(
        req: HermesToolExecute,
        _user: dict = Depends(_verify_bridge_token),
    ) -> HermesToolResult:
        """Execute a tool on the Hermes side and return the result."""
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
        _user: dict = Depends(_verify_bridge_token),
    ) -> dict[str, Any]:
        """Check the health of the Hermes endpoint connection."""
        hermes = _get_hermes_client()
        return await hermes.health()

    return router


# ── Standalone app factory ─────────────────────────────────────────────


def create_standalone_app(config: BridgeConfig | None = None) -> FastAPI:
    """Create a standalone FastAPI app for the Hermes Bridge server.

    This includes:
    - CORS middleware
    - Startup/shutdown lifespan
    - Lazy initialization of Lilith components
    - All bridge endpoints

    Use this when running the bridge as its own server (port 9001).
    For embedding into Bifrost, use ``create_bridge_router()`` instead.
    """
    cfg = config or _get_bridge_config()
    _start_time = time.time()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        """Start lazy-init of all Lilith components and close Hermes client on shutdown."""
        logger.info("Hermes Bridge starting on %s:%d", cfg.host, cfg.port)
        logger.info("Hermes endpoint: %s", cfg.hermes_url)

        # Force lazy-init of all Lilith components.
        with _lilith_state_lock:
            assert _lilith_state is not None  # initialised at module level
            _lilith_state.ensure_memory(cfg)
            _lilith_state.ensure_engine(cfg)
            _lilith_state.ensure_skills(cfg)

        yield

        global _hermes_client
        if _hermes_client:
            await _hermes_client.close()
            _hermes_client = None

        logger.info("Hermes Bridge shut down")

    app = FastAPI(
        title="Hermes Bridge",
        description="Bidirectional gateway connecting Yggdrasil to Hermes Agent",
        version=_bridge_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the bridge router at /api/bridge (standalone mode).
    # In standalone mode, engine/memory/skills are lazily loaded
    # via _LilithState, so we don't pass pre-built instances.
    router = create_bridge_router(config=cfg, engine=None, memory=None, skills_ctx=None)
    app.include_router(router, prefix="/api")

    return app


# Module-level state for standalone mode
_lilith_state = _LilithState()


_lilith_state_lock = threading.Lock()
