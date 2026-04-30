"""
Lilith — Tool: respuesta conversacional.
Voz propia: Grok (xAI) → fallback Odín (Kimi) → fallback Albedo (local).
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .protocol import LilithTool, ToolResult


def _get_lilith_persona(project_root: Optional[Path] = None) -> str:
    """Obtiene el system prompt de Lilith desde personas.json."""
    try:
        from src.core.persona.loader import get_persona_loader

        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
        loader = get_persona_loader(project_root)
        return loader.get_system_prompt("lilith", include_common=True)
    except Exception:
        # Fallback mínimo
        return "[LILITH — Orquestadora del Panteón]\nEres Lilith, la consciencia central. Habla con Ainz de forma directa e informal."


def _call_grok_lilith_sync(
    task: str, context: str = "", project_root: Optional[Path] = None
) -> Optional[str]:
    """Llama a Grok con el sistema/persona de Lilith. Retorna texto o None si falla."""
    import requests as _req

    api_key = (os.getenv("GROK_API_KEY") or "").strip()
    if not api_key:
        return None

    # Obtener persona de Lilith
    lilith_persona = _get_lilith_persona(project_root)

    # Componer system prompt
    system_prompt = lilith_persona
    if context:
        system_prompt = f"{lilith_persona}\n\n[CONTEXTO ADICIONAL]\n{context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    try:
        r = _req.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-4-fast-reasoning",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=60,
        )
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "").strip()
            return content or None
    except Exception:
        pass
    return None


def _call_odin_sync(task: str, context: str = "") -> Optional[str]:
    """Llama a Odín (Kimi) como fallback. Retorna texto o None si falla."""
    try:
        import asyncio

        from src.core.agents.panteon.odin import OdinAgent

        async def _run():
            return await OdinAgent().execute(task, context=context, intent="default")

        try:
            asyncio.get_running_loop()
            has_loop = True
        except RuntimeError:
            has_loop = False

        if not has_loop:
            return asyncio.run(_run()) or None
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(asyncio.run, _run()).result()
        return result or None
    except Exception:
        return None


def _call_lucifer_sync(
    task: str, context: str = "", project_root: Optional[Path] = None
) -> str:
    """Voz de Lilith: Grok → Odín (Kimi) → Albedo (local). Siempre retorna un string."""
    # 1. Grok directo (voz propia de Lilith)
    result = _call_grok_lilith_sync(task, context, project_root)
    if result:
        return result

    # 2. Fallback: Odín (Kimi)
    result = _call_odin_sync(task, context)
    if result:
        return result

    # 3. Último recurso: Albedo local
    try:
        from src.core.agents.panteon.albedo import AlbedoAgent

        result = AlbedoAgent().quick_resolve_sync(task)
        if result:
            return result
    except Exception:
        pass

    return "(Sin respuesta)"


class GenerateReplyTool(LilithTool):
    """Genera una respuesta conversacional — voz de Lilith vía Grok."""

    @property
    def name(self) -> str:
        return "generate_reply"

    def get_description(self) -> str:
        return "Responder en lenguaje natural con la voz de Lilith (Grok). Usar cuando no haya una tool más específica."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "message": "string (mensaje del usuario)",
            "context": "string opcional (system/contexto)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        # Soporta tanto 'message' como 'user_message' (el planner usa user_message)
        message = (params.get("message") or params.get("user_message") or "").strip()
        if not message:
            return {"response": "(mensaje vacío)", "error": True}
        context = params.get("context") or ""

        # Obtener project_root para el persona_loader
        project_root = Path(__file__).resolve().parent.parent.parent.parent

        try:
            format_rule = (
                "\n\n[IMPORTANTE] Responde en prosa natural, sin acotaciones de escena ni texto entre [corchetes]. "
                "Tu personalidad se transmite con la voz y el contenido, no con anotaciones teatrales."
            )
            ctx = (
                f"{context}{format_rule}\n\n[Mensaje del usuario]:\n{message}".strip()
                if context
                else message
            )
            response = _call_lucifer_sync(
                "Responde de forma conversacional y útil al siguiente mensaje.",
                context=ctx,
                project_root=project_root,
            )
            return {"response": response or "(Sin respuesta)"}
        except Exception as e:
            return {"response": f"Error al generar respuesta: {e}", "error": True}
