from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .agent_state_manager import AgentStateManager
from .tools_v3.registry import ToolRegistryV3

_FASTLANE_SYSTEM = (
    "Eres el Carril Rápido de Lilith. Responde en español, directo y útil, en menos de 8 líneas si es posible. "
    "No uses herramientas web ni de disco. Si el usuario pide algo que requiera navegador/archivos, dilo explícitamente "
    "y sugiere reintentar cuando termine /investiga o usar el UAC.\n"
)


def _should_use_memory(query: str) -> bool:
    q = (query or "").lower()
    return any(
        k in q for k in ("memoria", "recuerdas", "recuerda", "anota", "guardaste")
    )


def _summarize_for_injection(query: str, answer: str) -> str:
    q = (query or "").strip().replace("\n", " ")
    a = (answer or "").strip().replace("\n", " ")
    q = q[:120]
    # Si parece respuesta larga o con código, no inyectar el contenido, solo el hecho.
    if "```" in (answer or "") or len(a) > 240:
        return f"Interrupción Fast-Lane: preguntaste «{q}…» y respondí de forma concisa. (Detalles omitidos para no inflar contexto)."
    return f"Interrupción Fast-Lane: preguntaste «{q}» y respondí: {a[:240]}"


@dataclass
class FastLaneResult:
    response: str
    injected_note: str = ""
    used_memory: bool = False


class FastLaneAgent:
    """
    Agente ligero, zero-shot, allowlist rígida.
    - No usa web/disk.
    - Opcional: consulta memoria semántica (search_semantic_memory) si la pregunta lo sugiere.
    - Empuja una nota resumida al buzón del hilo principal.
    """

    def __init__(self, registry: ToolRegistryV3):
        self.registry = registry

    def run(
        self, *, user_id: str, query: str, mode_overlay: str = ""
    ) -> FastLaneResult:
        q = (query or "").strip()
        if not q:
            return FastLaneResult(response="(pregunta vacía)")

        used_memory = False
        mem_block = ""
        if _should_use_memory(q) and self.registry.has("search_semantic_memory"):
            try:
                res = self.registry.execute(
                    "search_semantic_memory", {"query": q, "top_k": 5}
                )
                if isinstance(res, dict) and (res.get("response") or "").strip():
                    mem_block = (res.get("response") or "").strip()
                    used_memory = True
            except Exception:
                pass

        context = _FASTLANE_SYSTEM
        if (mode_overlay or "").strip():
            context = context + "\n" + (mode_overlay or "").strip() + "\n"
        if mem_block:
            context = (
                context
                + "\n[Memoria semántica (solo si relevante)]:\n"
                + mem_block
                + "\n"
            )

        out = self.registry.execute(
            "generate_reply", {"message": q, "context": context}
        )
        if isinstance(out, dict):
            answer = (out.get("response") or "").strip()
        else:
            answer = str(out or "").strip()
        answer = answer or "(Sin respuesta)"

        note = _summarize_for_injection(q, answer)
        try:
            AgentStateManager.push_interruption(user_id, note)
        except Exception:
            pass
        return FastLaneResult(
            response=answer, injected_note=note, used_memory=used_memory
        )
