from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine
from lilith_tools.registry import ToolRegistry
from pydantic import BaseModel

app = FastAPI(title="Lilith API", version="2.1.0")

config = Config()
memory = MemoryStore(config.root / "memory.db")
engine = LilithEngine(config, memory)


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    context_used: List[str]
    tool_call: Dict[str, Any]


class ToolCallRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


class MemoryStoreRequest(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = engine.process(req.message)
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
    return engine.execute_tool(req.tool, req.params)


@app.get("/tools")
async def list_tools() -> Dict[str, str]:
    return ToolRegistry.list_tools()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.1.0",
        "tools": len(ToolRegistry.list_tools()),
        "model": config.get("model", "auto"),
    }


@app.get("/status")
async def status():
    return {
        "version": "2.1.0",
        "model": config.get("model", "auto"),
        "tools_available": len(ToolRegistry.list_tools()),
        "memory_entries": memory.count_entries(),
    }


@app.get("/memory")
async def memory_recall(query: str = Query(...), k: int = 5):
    return memory.search(query, k=k)


@app.post("/memory")
async def memory_store(req: MemoryStoreRequest):
    memory.store(req.text, req.metadata)
    return {"status": "stored", "text": req.text[:100]}
