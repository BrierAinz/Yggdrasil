from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .memory_store import SemanticMemory

logger = logging.getLogger("Consolidator")


def _extract_json(text: str) -> Optional[str]:
    """
    Extrae el primer bloque JSON (objeto o array) de un string.
    V1: heurística simple (primer '{' o '[' hasta el último '}' o ']').
    """
    s = (text or "").strip()
    if not s:
        return None
    i_obj = s.find("{")
    i_arr = s.find("[")
    if i_obj == -1 and i_arr == -1:
        return None
    i = i_obj if (i_obj != -1 and (i_arr == -1 or i_obj < i_arr)) else i_arr
    end_obj = s.rfind("}")
    end_arr = s.rfind("]")
    end = end_obj if end_obj > end_arr else end_arr
    if end <= i:
        return None
    return s[i : end + 1].strip()


def _consolidation_prompt(skeleton: Dict[str, Any]) -> str:
    return (
        "Eres el Consolidador de Memoria de Nazarick. Tu tarea es extraer 1 a 3 recuerdos semánticos "
        "de alto nivel, accionables y duraderos a partir del esqueleto de un plan exitoso.\n\n"
        "REGLAS:\n"
        "- Devuelve ÚNICAMENTE JSON válido (sin texto extra).\n"
        "- Devuelve una lista JSON con 1-3 objetos.\n"
        "- Cada objeto debe tener: domain, entity, fact, resolution_path (opcional), tags (lista opcional).\n"
        "- domain y entity en snake_case.\n"
        "- fact: una regla/decisión/bugfix en una frase.\n"
        "- No guardes detalles efímeros ni logs largos.\n\n"
        f"Esqueleto:\n{json.dumps(skeleton, ensure_ascii=False)[:15000]}"
    )


async def _call_lucifer(prompt: str, context: str = "") -> str:
    from .agent_router import AgentRouter

    router = AgentRouter()
    result = await router.execute(prompt, agent_name="lucifer", context=context)
    out = result.get("result")
    return str(out).strip() if out is not None else ""


def consolidate_memories_topdown(
    *,
    plan_serialized: List[Dict[str, Any]],
    final_response: str,
    interruptions: Optional[List[str]] = None,
    source_run_id: Optional[str] = None,
    max_memories: int = 3,
    retries: int = 2,
) -> List[SemanticMemory]:
    """
    Extrae 1-3 recuerdos (SemanticMemory) usando Lucifer, validación Pydantic y retry.
    Sync wrapper: usa asyncio.run / thread-safe según contexto.
    """
    run_id = (source_run_id or "").strip() or uuid.uuid4().hex
    skeleton = {
        "source_run_id": run_id,
        "steps": plan_serialized[:30],
        "final_response": (final_response or "").strip()[:5000],
        "interruptions": (interruptions or [])[-3:],
    }
    prompt = _consolidation_prompt(skeleton)

    last_err = ""
    for attempt in range(retries + 1):
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is None:
                raw = asyncio.run(_call_lucifer(prompt))
            else:
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor(max_workers=1) as pool:
                    raw = pool.submit(asyncio.run, _call_lucifer(prompt)).result()
            js = _extract_json(raw) or raw
            data = json.loads(js)
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                raise ValueError("JSON no es lista")
            out: List[SemanticMemory] = []
            for item in data[: max(1, min(max_memories, 3))]:
                if not isinstance(item, dict):
                    continue
                mem = SemanticMemory(
                    domain=str(item.get("domain") or "general"),
                    entity=str(item.get("entity") or "misc"),
                    fact=str(item.get("fact") or "").strip(),
                    resolution_path=str(item.get("resolution_path") or "").strip(),
                    tags=item.get("tags") if isinstance(item.get("tags"), list) else [],
                    source_run_id=run_id,
                )
                if mem.fact:
                    out.append(mem)
            if out:
                return out
            raise ValueError("Sin recuerdos válidos")
        except Exception as e:
            last_err = str(e)
            logger.debug(
                "Consolidator retry %s/%s: %s", attempt + 1, retries + 1, last_err
            )
            time.sleep(0.2)
            continue
    logger.warning("Consolidator failed: %s", last_err)
    return []
