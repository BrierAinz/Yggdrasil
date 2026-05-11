"""Hermes Bridge — FastAPI application.

Bidirectional gateway connecting Yggdrasil (Lilith) to Hermes Agent.

Architecture:
    Hermes Agent  ◄════════►  HermesBridge  ◄════════►  LilithEngine / Memory / Skills
         │                           │                           │
    (external LLM,          (FastAPI server @ :9001)    (Yggdrasil internal)
     powerful tools,
     MCP server)
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
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

# ── Global state ──────────────────────────────────────────────────────

_config: BridgeConfig | None = None
_hermes_client: HermesClient | None = None
_start_time: float = time.time()

# Lazy singletons for Lilith components (same pattern as lilith-api).
_lock = threading.Lock()


class _LilithState:
    """Holds lazily-initialised Lilith component references."""

    __slots__ = ("engine", "memory", "skills_ctx", "skills_loaded")

    def __init__(self) -> None:
        self.engine: Any = None
        self.memory: Any = None
        self.skills_ctx: Any = None
        self.skills_loaded: int = 0

    def _ensure_engine(self, config: BridgeConfig) -> Any:
        if self.engine is None:
            try:
                from lilith_core.config import Config as LilithConfig
                from lilith_orchestrator.engine import LilithEngine

                lconfig = LilithConfig()
                # Override model if specified in bridge config.
                if config.default_model != "auto":
                    # LilithConfig fields can be set directly.
                    object.__setattr__(lconfig, "model", config.default_model)
                self.engine = LilithEngine(lconfig, self._ensure_memory(config))
                logger.info("LilithEngine initialized")
            except ImportError:
                logger.warning("lilith_orchestrator not available — engine disabled")
                self.engine = None
        return self.engine

    def _ensure_memory(self, config: BridgeConfig) -> Any:
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

    def _ensure_skills(self, config: BridgeConfig) -> tuple[Any, int]:
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


_state = _LilithState()


# ── Dependency injection ──────────────────────────────────────────────


def get_config() -> BridgeConfig:
    global _config
    if _config is None:
        _config = load_bridge_config()
    return _config


def get_hermes_client(config: BridgeConfig = Depends(get_config)) -> HermesClient:
    global _hermes_client
    if _hermes_client is None:
        _hermes_client = HermesClient(
            base_url=config.hermes_url,
            api_key=config.hermes_api_key,
            timeout=config.hermes_timeout,
            max_retries=config.hermes_max_retries,
        )
    return _hermes_client


def get_memory(config: BridgeConfig = Depends(get_config)) -> Any:
    with _lock:
        return _state._ensure_memory(config)


def get_engine(config: BridgeConfig = Depends(get_config)) -> Any:
    with _lock:
        return _state._ensure_engine(config)


def get_skills(config: BridgeConfig = Depends(get_config)) -> tuple[Any, int]:
    with _lock:
        return _state._ensure_skills(config)


# ── Auth ──────────────────────────────────────────────────────────────


def _verify_token(
    request: Request,
    config: BridgeConfig = Depends(get_config),
) -> dict[str, str]:
    """Verify authentication token (header or query parameter).

    Accepts:
      - Authorization: Bearer <token>
      - X-Bridge-Token: <token>
      - ?token=<token> (query parameter)
    """
    if not config.auth_token:
        # No auth configured — allow all.
        return {"sub": "anonymous", "role": "admin"}

    # Check Authorization header.
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if token == config.auth_token:
            return {"sub": "bearer", "role": "admin"}

    # Check X-Bridge-Token header.
    bridge_token = request.headers.get("x-bridge-token")
    if bridge_token == config.auth_token:
        return {"sub": "bridge", "role": "admin"}

    # Check query parameter.
    query_token = request.query_params.get("token")
    if query_token == config.auth_token:
        return {"sub": "query", "role": "admin"}

    raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


# ── Lifespan ──────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize connections. Shutdown: clean up."""
    config = get_config()
    logger.info("Hermes Bridge starting on %s:%d", config.host, config.port)
    logger.info("Hermes endpoint: %s", config.hermes_url)

    # Pre-initialize Lilith components.
    with _lock:
        _state._ensure_memory(config)
        _ = get_engine(config)  # noqa: F841
        _ = get_skills(config)  # noqa: F841

    yield

    # Shutdown: close Hermes client.
    global _hermes_client
    if _hermes_client:
        await _hermes_client.close()
        _hermes_client = None

    logger.info("Hermes Bridge shut down")


# ── App factory ───────────────────────────────────────────────────────


def create_app(config: BridgeConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    global _config
    if config:
        _config = config

    _cfg = config or get_config()

    app = FastAPI(
        title="Hermes Bridge",
        description="Bidirectional gateway connecting Yggdrasil to Hermes Agent",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health ─────────────────────────────────────────────────────

    @app.get("/api/bridge/health", response_model=BridgeHealth)
    async def health(config: BridgeConfig = Depends(get_config)):
        hermes = get_hermes_client(config)
        hermes_health = await hermes.health()
        skills_ctx, skills_count = get_skills(config)

        return BridgeHealth(
            status="healthy",
            bridge_version="1.0.0",
            lilith_engine=_state.engine is not None,
            hermes_connected=hermes_health.get("connected", False),
            memory_available=_state.memory is not None,
            skills_loaded=skills_count,
            uptime_seconds=round(time.time() - _start_time, 1),
        )

    # ── Inbound: Hermes → Yggdrasil ───────────────────────────────

    @app.post("/api/bridge/chat", response_model=BridgeChatResponse)
    async def chat_inbound(
        req: BridgeChatRequest,
        user: dict = Depends(_verify_token),
        config: BridgeConfig = Depends(get_config),
    ):
        """Hermes sends a message to Lilith."""
        import uuid

        start = time.time()
        engine = get_engine(config)

        if engine is None:
            raise HTTPException(
                status_code=503,
                detail="Lilith engine not available (lilith-orchestrator not installed)",
            )

        session_id = req.session_id or str(uuid.uuid4())

        try:
            result = engine.process(req.message)
            latency = round((time.time() - start) * 1000, 2)

            tools_used = []
            if isinstance(result, dict) and result.get("tool_call"):
                tc = result["tool_call"]
                tools_used.append(tc.get("name", "unknown"))

            return BridgeChatResponse(
                response=result.get("response", "") if isinstance(result, dict) else str(result),
                session_id=session_id,
                latency_ms=latency,
                tools_used=tools_used,
                usage=result.get("usage") if isinstance(result, dict) else None,
            )
        except Exception as exc:
            logger.exception("Lilith chat error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/bridge/memory")
    async def memory_recall(
        query: str = Query(...),
        k: int = Query(5),
        user: dict = Depends(_verify_token),
        memory: Any = Depends(get_memory),
    ):
        """Query Lilith's memory store."""
        if memory is None:
            raise HTTPException(
                status_code=503, detail="Memory store not available"
            )
        try:
            results = memory.search(query, k=k)
            return {"results": results, "count": len(results)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/bridge/memory")
    async def memory_store(
        req: BridgeMemoryStore,
        user: dict = Depends(_verify_token),
        memory: Any = Depends(get_memory),
    ):
        """Store data in Lilith's memory."""
        if memory is None:
            raise HTTPException(
                status_code=503, detail="Memory store not available"
            )
        try:
            memory.store(req.text, req.metadata)
            return {"status": "stored", "text": req.text[:100]}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/bridge/skills")
    async def list_skills(
        category: str | None = Query(None),
        user: dict = Depends(_verify_token),
        skills: tuple = Depends(get_skills),
    ):
        """List available skills in the knowledge base."""
        skills_ctx, _ = skills
        if skills_ctx is None:
            raise HTTPException(
                status_code=503, detail="Skills not available (lilith-skills not installed)"
            )

        if category:
            result = skills_ctx.format_by_category(category)
            return {"category": category, "content": result}

        return {"categories": skills_ctx.list_available()}

    @app.post("/api/bridge/skills/search")
    async def search_skills(
        req: BridgeSkillSearch,
        user: dict = Depends(_verify_token),
        skills: tuple = Depends(get_skills),
    ):
        """Search skills by keyword."""
        skills_ctx, _ = skills
        if skills_ctx is None:
            raise HTTPException(
                status_code=503, detail="Skills not available"
            )

        results = skills_ctx.search(req.query, limit=req.limit)
        return {"query": req.query, "results": results, "count": len(results)}

    # ── Outbound: Yggdrasil → Hermes ───────────────────────────────

    @app.post("/api/bridge/hermes/chat", response_model=HermesChatResponse)
    async def chat_outbound(
        req: HermesChatRequest,
        user: dict = Depends(_verify_token),
        config: BridgeConfig = Depends(get_config),
    ):
        """Delegate a message to Hermes Agent (powerful external LLM)."""
        hermes = get_hermes_client(config)
        start = time.time()

        # Build the messages list.
        messages: list[dict[str, Any]] = []
        if req.context:
            messages.append({"role": "system", "content": req.context})
        messages.append({"role": "user", "content": req.message})

        try:
            result = await hermes.chat(
                messages,
                model=req.model,
            )

            if not result.get("choices"):
                raise HTTPException(
                    status_code=502, detail="Hermes returned no choices"
                )

            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "")
            usage = result.get("usage", {})
            model_used = result.get("model", "")

            latency = round((time.time() - start) * 1000, 2)

            # Parse tool calls if any.
            tools_used: list[str] = []
            tool_calls = choice.get("message", {}).get("tool_calls", [])
            for tc in tool_calls:
                func = tc.get("function", {})
                tools_used.append(func.get("name", "unknown"))

            return HermesChatResponse(
                response=content,
                model=model_used,
                usage=usage,
                tools_used=tools_used,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Hermes chat error: %s", exc)
            raise HTTPException(status_code=502, detail=f"Hermes error: {exc}")

    @app.get("/api/bridge/hermes/models")
    async def list_hermes_models(
        user: dict = Depends(_verify_token),
        config: BridgeConfig = Depends(get_config),
    ):
        """List models available on the Hermes side."""
        hermes = get_hermes_client(config)
        models = await hermes.list_models()
        return {"models": models, "count": len(models)}

    @app.post("/api/bridge/hermes/execute", response_model=HermesToolResult)
    async def execute_hermes_tool(
        req: HermesToolExecute,
        user: dict = Depends(_verify_token),
        config: BridgeConfig = Depends(get_config),
    ):
        """Execute a tool via Hermes Agent."""
        hermes = get_hermes_client(config)

        try:
            result = await hermes.execute_tool(req.tool, req.params)

            # Parse the result.
            if isinstance(result, dict):
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return HermesToolResult(
                        tool=req.tool,
                        success=True,
                        result=content,
                    )

            return HermesToolResult(
                tool=req.tool,
                success=True,
                result=result,
            )
        except Exception as exc:
            return HermesToolResult(
                tool=req.tool,
                success=False,
                error=str(exc),
            )

    @app.get("/api/bridge/hermes/health")
    async def hermes_health(
        user: dict = Depends(_verify_token),
        config: BridgeConfig = Depends(get_config),
    ):
        """Check Hermes Agent connectivity."""
        hermes = get_hermes_client(config)
        return await hermes.health()

    return app