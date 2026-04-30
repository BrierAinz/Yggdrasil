"""
Lilith IDE API — Fase 1
Endpoint dedicado para integración con VS Code / Cursor.
POST /api/ide/assistant
"""
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, field_validator


def _load_secrets():
    """Carga Config/secrets.env en el proceso actual si no se hizo todavía."""
    secrets_path = Path(__file__).parent.parent.parent / "Config" / "secrets.env"
    if not secrets_path.exists():
        return
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key not in os.environ:  # No sobreescribir vars ya seteadas
                    os.environ[key] = val


_load_secrets()

logger = logging.getLogger("IDEApi")

router = APIRouter(tags=["IDE Integration"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class IDERequest(BaseModel):
    file_path: str
    content: str
    selection: Optional[str] = None
    intent: Optional[str] = None  # explain|review|refactor|fix|test|doc
    context: Optional[str] = None

    @field_validator("file_path")
    @classmethod
    def _path_seguro(cls, v: str) -> str:
        from src.utils.sanitizer import sanitize_file_path

        cleaned = sanitize_file_path(v)
        if cleaned is None:
            raise ValueError("file_path inseguro")
        return cleaned

    @field_validator("content")
    @classmethod
    def _content_limite(cls, v: str) -> str:
        if len(v or "") > 500_000:
            raise ValueError("Contenido demasiado grande (max 500k chars)")
        return v


class EditSuggestion(BaseModel):
    start_line: int
    end_line: int
    new_content: str


class Diagnostic(BaseModel):
    line: int
    severity: str  # error | warning | info
    message: str


class IDEResponse(BaseModel):
    message: str
    agent: str
    edits: List[EditSuggestion] = []
    diagnostics: List[Diagnostic] = []


# ── Routing por intent ────────────────────────────────────────────────────────

INTENT_ROUTING = {
    "explain": "eva",
    "review": "eva",
    "doc": "eva",
    "refactor": "adan",
    "fix": "adan",
    "test": "adan",
}

AGENT_NAMES = {
    "lilith": "Lilith",
    "eva": "Eva",
    "adan": "Adán",
}


def _build_task(req: IDERequest) -> tuple[str, str]:
    """Construye task y context a partir del request."""
    intent = (req.intent or "").lower().strip()

    intent_descriptions = {
        "explain": "Explica qué hace este código, línea por línea si es necesario.",
        "review": "Revisa el código buscando bugs, code smells y problemas de calidad.",
        "refactor": "Refactoriza el código manteniendo su comportamiento externo.",
        "fix": "Identifica y corrige todos los bugs presentes.",
        "test": "Genera tests unitarios completos para este código.",
        "doc": "Genera docstrings / comentarios completos para todas las funciones públicas.",
    }

    task_description = intent_descriptions.get(
        intent, "Analiza y responde sobre este código."
    )

    # Si hay selección, es la porción sobre la que actuar; si no, el archivo completo
    target_code = req.selection or req.content

    task = f"""Archivo: {req.file_path}

{task_description}

```
{target_code}
```"""

    # Contexto adicional (resto del archivo cuando hay selección, o contexto libre)
    context_parts = []
    if req.selection and req.content != req.selection:
        context_parts.append(
            f"Archivo completo para referencia:\n```\n{req.content}\n```"
        )
    if req.context:
        context_parts.append(req.context)

    context = "\n\n".join(context_parts)
    return task, context


# ── Parsers de respuesta ──────────────────────────────────────────────────────


def _extract_edits(response_text: str, original_content: str) -> List[EditSuggestion]:
    """
    Extrae bloques de código de la respuesta y los convierte en EditSuggestion.
    Busca el primer bloque de código y lo propone como edición completa del archivo.
    """
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL)
    if not code_blocks:
        return []

    # Tomar el bloque más largo como la edición principal
    best_block = max(code_blocks, key=len).strip()
    if not best_block or best_block == original_content.strip():
        return []

    original_lines = original_content.splitlines()
    return [
        EditSuggestion(
            start_line=1, end_line=len(original_lines), new_content=best_block
        )
    ]


def _extract_diagnostics(response_text: str) -> List[Diagnostic]:
    """
    Extrae diagnósticos estructurados de la respuesta.
    Busca patrones como "línea 15: error ..." o "line 15: warning ...".
    """
    diagnostics: List[Diagnostic] = []
    patterns = [
        r"l[íi]nea\s+(\d+)[:\s]+(?:(error|warning|info)[:\s]+)?(.+)",
        r"line\s+(\d+)[:\s]+(?:(error|warning|info)[:\s]+)?(.+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, response_text, re.IGNORECASE):
            line_no = int(match.group(1))
            severity = (match.group(2) or "info").lower()
            if severity not in ("error", "warning", "info"):
                severity = "info"
            msg = match.group(3).strip()[:200]
            diagnostics.append(Diagnostic(line=line_no, severity=severity, message=msg))
    return diagnostics


# ── Endpoint principal ────────────────────────────────────────────────────────


@router.post("/assistant", response_model=IDEResponse)
async def ide_assistant(req: IDERequest) -> IDEResponse:
    """
    Endpoint para VS Code / Cursor.
    Routing automático:
      explain | review | doc  → Eva  (Grok)
      refactor | fix | test   → Adán (Qwen/Ollama)
      sin intent o desconocido → Lilith (Kimi)
    """
    intent = (req.intent or "").lower().strip()
    agent_key = INTENT_ROUTING.get(intent, "lilith")
    task, context = _build_task(req)

    logger.info(
        f"[IDE] intent={intent or 'none'} → agent={agent_key} | file={req.file_path}"
    )

    response_text = ""

    # ── Eva (Grok) ────────────────────────────────────────────────────────────
    if agent_key == "eva":
        try:
            from src.core.agents.panteon.eva import EvaAgent

            agent = EvaAgent()
            if agent.is_available():
                response_text = agent.execute(task=task, context=context)
                if "[Eva error]" in response_text or "[Eva offline]" in response_text:
                    logger.warning("[IDE] Eva falló, fallback a Lilith")
                    agent_key = "lilith"
            else:
                logger.warning(
                    "[IDE] Eva no disponible (sin GROK_API_KEY), fallback a Lilith"
                )
                agent_key = "lilith"
        except Exception as e:
            logger.error(f"[IDE] Eva exception: {e}")
            agent_key = "lilith"

    # ── Adán (Qwen/Ollama) ────────────────────────────────────────────────────
    if agent_key == "adan":
        try:
            from src.core.agents.panteon.adan import AdanAgent

            agent = AdanAgent()
            if agent.is_available():
                response_text = await agent.execute(task=task, context=context)
                if "[Adán offline]" in response_text or "[Adán]" in response_text:
                    logger.warning("[IDE] Adán falló, fallback a Lilith")
                    agent_key = "lilith"
            else:
                logger.warning(
                    "[IDE] Adán no disponible (Ollama offline), fallback a Lilith"
                )
                agent_key = "lilith"
        except Exception as e:
            logger.error(f"[IDE] Adán exception: {e}")
            agent_key = "lilith"

    # ── Lilith (Kimi) — principal y fallback ─────────────────────────────────
    if agent_key == "lilith":
        try:
            from src.llm.kimi_client import KimiClient

            kimi = KimiClient()
            full_task = f"{task}\n\n{context}".strip() if context else task
            response_text = kimi.generate_text(
                prompt=full_task,
                system_prompt="Eres Lilith, orquestadora de IA. Responde siempre en español.",
            )
        except Exception as e:
            logger.error(f"[IDE] Lilith exception: {e}")
            response_text = f"Error al procesar la solicitud: {e}"

    # ── Post-procesado ────────────────────────────────────────────────────────
    edits = []
    diagnostics = []

    # Solo proponer edits para intents de código (no explain/doc/review)
    if intent in ("refactor", "fix", "test"):
        edits = _extract_edits(response_text, req.selection or req.content)

    # Diagnostics para review y fix
    if intent in ("review", "fix"):
        diagnostics = _extract_diagnostics(response_text)

    return IDEResponse(
        message=response_text,
        agent=AGENT_NAMES.get(agent_key, agent_key),
        edits=edits,
        diagnostics=diagnostics,
    )
