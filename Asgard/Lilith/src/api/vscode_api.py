"""
Lilith VS Code API — V1 mínima

POST /api/vscode/ask
- Auth: header X-Lilith-VSCode-Token == env LILITH_VSCODE_TOKEN
- Payload: selection + file_path + language_id + workspace_name + prompt
- Backend: generate_reply con contexto "modo desarrollador"
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/vscode", tags=["vscode"])


def _vscode_token() -> str:
    return (os.getenv("LILITH_VSCODE_TOKEN", "") or "").strip()


def _require_token(request: Request) -> None:
    token = _vscode_token()
    if not token:
        raise HTTPException(
            status_code=503, detail="LILITH_VSCODE_TOKEN no está configurado."
        )
    got = (request.headers.get("X-Lilith-VSCode-Token") or "").strip()
    if got != token:
        raise HTTPException(status_code=403, detail="Token inválido.")


class VSCodeAskRequest(BaseModel):
    prompt: str
    selection: str = ""
    file_path: str = ""
    language_id: str = ""
    workspace_name: str = ""

    @field_validator("prompt")
    @classmethod
    def _prompt(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("prompt requerido")
        if len(v) > 4000:
            raise ValueError("prompt demasiado largo (max 4000 chars)")
        return v

    @field_validator("selection")
    @classmethod
    def _selection(cls, v: str) -> str:
        v = v or ""
        if len(v) > 120_000:
            raise ValueError("selection demasiado grande (max 120k chars)")
        return v

    @field_validator("file_path", "language_id", "workspace_name")
    @classmethod
    def _small_strings(cls, v: str) -> str:
        v = (v or "").strip()
        return v[:400]


class VSCodeAskResponse(BaseModel):
    response: str


@router.post("/ask", response_model=VSCodeAskResponse)
async def vscode_ask(payload: VSCodeAskRequest, request: Request) -> VSCodeAskResponse:
    _require_token(request)

    from pathlib import Path

    from src.core.tools.registry import create_trusted_registry

    project_root = Path(__file__).resolve().parent.parent.parent
    reg = create_trusted_registry(project_root)

    selection = (payload.selection or "").strip()
    ctx_parts = [
        "Eres Lilith en modo desarrollador para VS Code.",
        "Responde en español, directo y accionable.",
        "Si falta contexto, pide el mínimo imprescindible.",
        "Si incluyes código, mantenlo corto y enfocado.",
    ]
    if payload.workspace_name:
        ctx_parts.append(f"Workspace: {payload.workspace_name}")
    if payload.file_path:
        ctx_parts.append(f"Archivo: {payload.file_path}")
    if payload.language_id:
        ctx_parts.append(f"Lenguaje: {payload.language_id}")
    if selection:
        # Limitar para evitar inflar contexto innecesariamente
        sel = (
            selection
            if len(selection) <= 20_000
            else (selection[:20_000] + "\n... [truncado]")
        )
        ctx_parts.append("Selección:\n```")
        ctx_parts.append(sel)
        ctx_parts.append("```")
    context = "\n".join(ctx_parts).strip()

    # Log ligero para verificar que language_id y selección llegan bien a generate_reply
    try:
        import logging

        logger = logging.getLogger("VSCodeApi")
        logger.info(
            "[VSCode.ask] lang=%s file=%s workspace=%s ctx_preview=%s",
            payload.language_id,
            payload.file_path,
            payload.workspace_name,
            context[:300].replace("\n", " "),
        )
    except Exception:
        pass

    out = reg.execute("generate_reply", {"message": payload.prompt, "context": context})
    if isinstance(out, dict):
        text = (out.get("response") or "").strip()
    else:
        text = str(out or "").strip()
    return VSCodeAskResponse(response=text or "(Sin respuesta)")
