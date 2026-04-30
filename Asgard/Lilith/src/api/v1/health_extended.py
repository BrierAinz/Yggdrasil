"""
Health Check Extendido - Verifica estado de todas las APIs y servicios.
Endpoints:
- GET /api/health/full    - Health check completo con APIs externas
- GET /api/health/apis    - Estado de APIs de LLM
"""
import asyncio
import os
from datetime import datetime
from typing import Dict, List

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


async def check_kimi_api() -> Dict:
    """Verifica API de Kimi (Moonshot AI)."""
    api_key = os.getenv("KIMI_API_KEY") or os.getenv("CRYSTAL_KIMI_API_KEY")
    if not api_key:
        return {"status": "no_key", "message": "KIMI_API_KEY no configurada"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.moonshot.cn/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "kimi-k2.5",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
            if response.status_code == 200:
                return {
                    "status": "online",
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code,
                    "message": response.text[:100],
                }
    except Exception as e:
        return {"status": "offline", "message": str(e)}


async def check_grok_api() -> Dict:
    """Verifica API de Grok (xAI)."""
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        return {"status": "no_key", "message": "GROK_API_KEY no configurada"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "grok-2-latest",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
            if response.status_code == 200:
                return {
                    "status": "online",
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code,
                    "message": response.text[:100],
                }
    except Exception as e:
        return {"status": "offline", "message": str(e)}


async def check_venice_api() -> Dict:
    """Verifica API de Venice."""
    api_key = os.getenv("VENICE_API_KEY")
    if not api_key:
        return {"status": "no_key", "message": "VENICE_API_KEY no configurada"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.venice.ai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if response.status_code == 200:
                return {
                    "status": "online",
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {"status": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "offline", "message": str(e)}


async def check_muninn() -> Dict:
    """Verifica conexión a MuninnDB."""
    token = os.getenv("MUNINN_TOKEN")
    if not token:
        return {"status": "no_key", "message": "MUNINN_TOKEN no configurado"}

    try:
        from src.core.memory.muninn_memory import MuninnMemory

        muninn = MuninnMemory()
        # Intentar una operación simple
        return {"status": "online", "message": "MuninnDB disponible"}
    except Exception as e:
        return {"status": "offline", "message": str(e)}


async def check_archivero() -> Dict:
    """Verifica que el agente Archivero funcione."""
    try:
        from src.core.agents.panteon.archivero import ArchiveroAgent

        agent = ArchiveroAgent()
        return {
            "status": "online",
            "vault": agent.muninn_docs.active_vault
            if hasattr(agent.muninn_docs, "active_vault")
            else "unknown",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/full")
async def health_check_full():
    """
    Health check completo incluyendo APIs externas.
    """
    start_time = datetime.now()

    # Verificar todas las APIs en paralelo
    results = await asyncio.gather(
        check_kimi_api(),
        check_grok_api(),
        check_venice_api(),
        check_muninn(),
        check_archivero(),
        return_exceptions=True,
    )

    kimi, grok, venice, muninn, archivero = results

    # Contar servicios online
    online_count = sum(
        1
        for r in [kimi, grok, venice, muninn]
        if isinstance(r, dict) and r.get("status") == "online"
    )
    total_count = 5

    return {
        "status": "healthy" if online_count >= 2 else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "kimi_api": kimi
            if not isinstance(kimi, Exception)
            else {"status": "error", "message": str(kimi)},
            "grok_api": grok
            if not isinstance(grok, Exception)
            else {"status": "error", "message": str(grok)},
            "venice_api": venice
            if not isinstance(venice, Exception)
            else {"status": "error", "message": str(venice)},
            "muninn_db": muninn
            if not isinstance(muninn, Exception)
            else {"status": "error", "message": str(muninn)},
            "archivero_agent": archivero
            if not isinstance(archivero, Exception)
            else {"status": "error", "message": str(archivero)},
        },
        "summary": {
            "online": online_count,
            "total": total_count,
            "percentage": (online_count / total_count) * 100,
        },
    }


@router.get("/apis")
async def health_check_apis():
    """
    Solo estado de APIs externas (rápido).
    """
    results = await asyncio.gather(
        check_kimi_api(), check_grok_api(), check_venice_api(), return_exceptions=True
    )

    kimi, grok, venice = results

    return {
        "timestamp": datetime.now().isoformat(),
        "apis": {
            "kimi": kimi if not isinstance(kimi, Exception) else {"status": "error"},
            "grok": grok if not isinstance(grok, Exception) else {"status": "error"},
            "venice": venice
            if not isinstance(venice, Exception)
            else {"status": "error"},
        },
    }
