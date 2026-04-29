from typing import Any, Dict, List

from fastapi import FastAPI
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine
from lilith_tools.registry import ToolRegistry
from pydantic import BaseModel

app = FastAPI(title="Lilith API", version="2.0.0")

config = Config()
memory = MemoryStore(config.root / "memory.db")
engine = LilithEngine(config, memory)


class ChatRequest(BaseModel):
    message: str
    model: str = None


class ChatResponse(BaseModel):
    response: str
    context_used: List[str]
    tool_call: Dict[str, Any]


class ToolCallRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = engine.process(req.message)
    # Simulacion de respuesta hasta integrar LLM real
    response_text = f"Recibido: {req.message}"
    if result["tool_call"]:
        response_text += f" (tool detectado: {result['tool_call']})"
    return ChatResponse(
        response=response_text,
        context_used=[c["content"] for c in result["context"]],
        tool_call=result["tool_call"],
    )


@app.post("/tools/execute")
async def execute_tool(req: ToolCallRequest):
    result = engine.execute_tool(req.tool, req.params)
    return result


@app.get("/tools")
async def list_tools() -> Dict[str, str]:
    return ToolRegistry.list_tools()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "tools": len(ToolRegistry.list_tools())}
