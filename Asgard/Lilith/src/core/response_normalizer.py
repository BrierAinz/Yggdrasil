"""
3.7 — Normalizador de respuesta para Discord (pipeline tres velos, velo II).
Quita metadatos crudos (TurnBegin, ThinkPart, ToolCall, etc.) de cualquier salida de agente
antes de enviarla a Discord.
"""
import re

# Patrones de metadatos que no deben llegar al usuario
_CRUD_LINE_PREFIXES = (
    "TurnBegin(",
    "StepBegin(",
    "ThinkPart(",
    "ToolCall(",
    "ToolResult(",
    "StatusUpdate(",
)


def normalize_response_for_discord(raw: str) -> str:
    """
    Limpia la salida de un agente para Discord: quita líneas de log/metadatos
    y extrae texto de bloques tipo text='...' si existe.
    """
    if not raw or not isinstance(raw, str):
        return (raw or "").strip()
    text = raw.strip()
    if not text:
        return text
    # Intentar extraer contenido de TextPart(text='...')
    parts = re.findall(r"text=['\"]([^'\"]*(?:\\.[^'\"]*)*)['\"]", text)
    if parts:
        return "\n\n".join(p.replace("\\n", "\n") for p in parts).strip()
    # Quitar líneas que son metadatos
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if any(s.startswith(x) for x in _CRUD_LINE_PREFIXES):
            continue
        if s:
            lines.append(line)
    return "\n".join(lines).strip() if lines else text.strip()
