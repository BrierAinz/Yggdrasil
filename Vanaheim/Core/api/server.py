"""Servidor FastAPI principal de Vanaheim.

Expone endpoints para:
- Registry de agentes
- Invocación de agentes individuales
- Health checks
"""

import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import uvicorn
from Agents.Adan.agent import AdanAgent
from Agents.Crystal.agent import CrystalAgent
from Agents.Eva.agent import EvaAgent
from Agents.Odin.agent import OdinAgent

# Importar agentes para registro automático
from Agents.Shalltear.agent import ShalltearAgent
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from Core.models import (
    AgentInfo,
    AgentState,
    HealthResponse,
    InvokeRequest,
    InvokeResponse,
    StreamRequest,
)
from Core.registry import get_registry


# Instancia global del registry
_registry = get_registry()


async def register_all_agents():
    """Registrar todos los agentes del Panteón en el registry."""
    from Core.models import AgentCapabilities, AgentConfig

    agents = [
        ShalltearAgent(
            AgentConfig(
                agent_id="shalltear",
                name="Shalltear",
                description="Clasificación rápida, parsing NL, triaje",
                model="llama-3.3-70b",
                provider="venice",
                capabilities=AgentCapabilities(
                    can_stream=True,
                    specialties=["classification", "parsing", "triage"],
                ),
            )
        ),
        AdanAgent(
            AgentConfig(
                agent_id="adan",
                name="Adán",
                description="Generación de código, tests, refactoring",
                model="qwen2.5-coder:7b",
                provider="ollama",
                base_url="http://localhost:11434",
                capabilities=AgentCapabilities(
                    can_stream=True,
                    supports_tools=True,
                    specialties=["code", "tests", "refactoring"],
                ),
            )
        ),
        EvaAgent(
            AgentConfig(
                agent_id="eva",
                name="Eva",
                description="Análisis de contexto largo, documentación",
                model="grok-4-fast-reasoning",
                provider="grok",
                capabilities=AgentCapabilities(
                    can_stream=True,
                    max_context_tokens=128000,
                    specialties=["analysis", "documentation", "insights"],
                ),
            )
        ),
        CrystalAgent(
            AgentConfig(
                agent_id="crystal",
                name="Crystal",
                description="Asistente público para Discord",
                model="kimi-for-coding",
                provider="kimi",
                capabilities=AgentCapabilities(
                    can_stream=True,
                    specialties=["conversation", "general_assistance"],
                ),
            )
        ),
        OdinAgent(
            AgentConfig(
                agent_id="odin",
                name="Odín",
                description="Análisis masivo, investigación profunda",
                model="kimi-for-coding",
                provider="kimi",
                capabilities=AgentCapabilities(
                    can_stream=True,
                    max_context_tokens=262000,
                    specialties=["deep_analysis", "research", "creative"],
                ),
            )
        ),
    ]

    for agent in agents:
        agent_info = AgentInfo(
            agent_id=agent.agent_id,
            name=agent.config.name,
            description=agent.config.description,
            config=agent.config,
            capabilities=agent.capabilities,
        )
        _registry.register(agent_info)
        print(f"[Vanaheim] Registered agent: {agent.agent_id}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Gestión del ciclo de vida del servidor."""
    # Startup
    print("[Vanaheim] Starting up...")
    await register_all_agents()
    print(f"[Vanaheim] {len(_registry.list_all())} agents registered")
    yield
    # Shutdown
    print("[Vanaheim] Shutting down...")


app = FastAPI(
    title="Vanaheim - Panteón de Agentes",
    description="Servicio independiente de agentes del Panteón",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== REGISTRY ENDPOINTS ==============


@app.get("/registry/agents")
async def list_agents():
    """Listar todos los agentes registrados."""
    agents = _registry.list_all()
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "state": a.state.value,
                "model": a.config.model,
                "provider": a.config.provider,
            }
            for a in agents
        ],
        "total": len(agents),
    }


@app.get("/registry/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Obtener información de un agente específico."""
    agent_info = _registry.get(agent_id)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent_info


@app.get("/registry/metrics")
async def get_metrics():
    """Obtener métricas del registry."""
    return _registry.get_metrics()


# ============== AGENT ENDPOINTS ==============


async def _get_agent_instance(agent_id: str):
    """Obtener instancia de un agente por ID."""
    # Mapa de IDs a clases de agentes
    agent_map = {
        "shalltear": ShalltearAgent,
        "adan": AdanAgent,
        "eva": EvaAgent,
        "crystal": CrystalAgent,
        "odin": OdinAgent,
    }

    agent_info = _registry.get(agent_id)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Crear instancia con su config
    agent_class = agent_map.get(agent_id)
    if not agent_class:
        raise HTTPException(status_code=500, detail=f"Agent class not found for {agent_id}")

    return agent_class(agent_info.config)


@app.get("/agents/{agent_id}/health", response_model=HealthResponse)
async def agent_health(agent_id: str):
    """Health check de un agente específico."""
    agent = await _get_agent_instance(agent_id)
    health = await agent.health()
    return HealthResponse(
        agent_id=health["agent_id"],
        name=health["name"],
        state=health["state"],
        available=health["available"],
        model=health["model"],
        provider=agent.config.provider,
    )


@app.post("/agents/{agent_id}/invoke", response_model=InvokeResponse)
async def agent_invoke(agent_id: str, request: InvokeRequest):
    """Invocar un agente de forma síncrona."""
    import time

    agent = await _get_agent_instance(agent_id)

    # Actualizar estado
    _registry.update_state(agent_id, AgentState.BUSY)

    start_time = time.time()
    try:
        result = await agent.execute(
            task=request.task,
            context={
                **request.context,
                "user_id": request.user_id,
                "channel": request.channel,
                "session_id": request.session_id,
                "conversation_history": request.conversation_history,
            },
        )

        execution_time = (time.time() - start_time) * 1000

        # Volver a idle
        _registry.update_state(agent_id, AgentState.IDLE)

        return InvokeResponse(
            agent_id=agent_id,
            result=result,
            execution_time_ms=execution_time,
        )

    except Exception as e:
        _registry.update_state(agent_id, AgentState.ERROR)
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.post("/agents/{agent_id}/stream")
async def agent_stream(agent_id: str, request: StreamRequest):
    """Invocar un agente con streaming de respuesta."""
    agent = await _get_agent_instance(agent_id)

    _registry.update_state(agent_id, AgentState.BUSY)

    async def event_generator():
        try:
            async for chunk in agent.stream(
                task=request.task,
                context={
                    **request.context,
                    "user_id": request.user_id,
                    "channel": request.channel,
                    "session_id": request.session_id,
                    "conversation_history": request.conversation_history,
                },
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e!s}\n\n"
        finally:
            _registry.update_state(agent_id, AgentState.IDLE)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ============== HEALTH ENDPOINTS ==============


@app.get("/health")
async def health_check():
    """Health check del servicio Vanaheim."""
    return {
        "status": "healthy",
        "service": "vanaheim",
        "version": "1.0.0",
        "agents_registered": len(_registry.list_all()),
        "agents_available": len(_registry.list_available()),
    }


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "service": "Vanaheim - Panteón de Agentes",
        "version": "1.0.0",
        "endpoints": {
            "registry": "/registry/agents",
            "health": "/health",
        },
    }


def main():
    """Punto de entrada para ejecutar el servidor."""
    port = int(os.getenv("VANAHEIM_PORT", "8001"))
    host = os.getenv("VANAHEIM_HOST", "0.0.0.0")

    print(f"[Vanaheim] Starting server on {host}:{port}")
    uvicorn.run(
        "Core.api.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
