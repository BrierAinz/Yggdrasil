"""BifrostGateway - API Gateway con LilithEngine real, JWT, Streaming y Hermes Bridge."""
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Paths para imports de Asgard
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Asgard" / "lilith-core"))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "Asgard" / "lilith-memory")
)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Asgard" / "lilith-tools"))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "Asgard" / "lilith-orchestrator")
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "Asgard" / "lilith-bridge")
)

from bifrost.auth import create_access_token, verify_token
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bifrost.gateway")

app = FastAPI(title="Bifrost Gateway", version="2.0.0")
security = HTTPBearer(auto_error=False)

# Singletons
_config = Config()
_memory = MemoryStore(str(_config.root / "bifrost_memory.db"))
_engine = LilithEngine(_config, _memory)

# Tokens legacy (compatibilidad)
VALID_TOKENS = set()


def load_tokens():
    global VALID_TOKENS
    try:
        config_path = Path(__file__).parent.parent / "config" / "bifrost.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        VALID_TOKENS = set(cfg.get("auth", {}).get("tokens", []))
        logger.info(f"Loaded {len(VALID_TOKENS)} legacy tokens")
    except Exception as e:
        logger.warning(f"Could not load tokens: {e}")
        VALID_TOKENS = set()


load_tokens()


def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    if token in VALID_TOKENS:
        return {"sub": "legacy", "role": "admin"}
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


class ChatRequest(BaseModel):
    message: str
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    latency_ms: float
    usage: Optional[Dict[str, Any]] = None


@app.get("/api/bifrost/health")
async def health_check():
    return {
        "status": "healthy",
        "gateway": "bifrost-v2",
        "engine": "lilith",
        "version": "2.0.0",
        "timestamp": time.time(),
    }


@app.post("/api/bifrost/auth/token")
async def login_token(request: Request):
    """Endpoint simple para generar un token JWT (en produccion usar OAuth2PasswordRequestForm)."""
    body = await request.json()
    username = body.get("username", "anon")
    password = body.get("password", "")
    # En produccion verificar contra DB/hash; aqui generamos libremente para facilitar testing
    token = create_access_token({"sub": username, "role": "user"})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/bifrost/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: dict = Depends(_get_current_user)):
    start = time.time()
    try:
        result = _engine.process(req.message)
        latency = round((time.time() - start) * 1000, 2)
        return ChatResponse(
            response=result.get("response", ""),
            latency_ms=latency,
            usage=result.get("usage"),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bifrost/chat/stream")
async def chat_stream(req: ChatRequest, user: dict = Depends(_get_current_user)):
    async def event_generator():
        try:
            for chunk in _engine.process_stream(req.message):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Legacy endpoint (mantiene compatibilidad)
class ExecuteRequest(BaseModel):
    agent: str
    task: str
    context: Optional[str] = ""
    streaming: bool = False
    metadata: Optional[Dict[str, Any]] = None


@app.post("/api/bifrost/execute")
async def execute_legacy(
    req: ExecuteRequest,
    x_bifrost_token: Optional[str] = Header(None),
    user: dict = Depends(_get_current_user),
):
    start = time.time()
    if req.agent.lower() != "lilith":
        raise HTTPException(
            status_code=400, detail=f"Agent {req.agent} no disponible. Use 'lilith'."
        )
    try:
        result = _engine.process(req.task)
        latency = round((time.time() - start) * 1000, 2)
        return {
            "agent": "lilith",
            "response": result.get("response", ""),
            "latency_ms": latency,
            "usage": result.get("usage"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Hermes Bridge — mount bidirectional gateway to Hermes Agent
# ---------------------------------------------------------------------------
try:
    from lilith_bridge.bifrost_integration import create_bridge_router

    _bridge_router = create_bridge_router(
        engine=_engine,
        memory=_memory,
        skills_ctx=None,  # skills loaded lazily by the router
    )
    app.include_router(_bridge_router, prefix="/api/bridge")
    logger.info("Hermes Bridge router mounted at /api/bridge")
except ImportError:
    logger.warning("lilith-bridge not installed — Hermes Bridge routes not available")
