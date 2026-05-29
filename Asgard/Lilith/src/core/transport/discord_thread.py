"""
Memoria por hilo/canal de Discord para que Lilith recuerde conversaciones por canal o hilo.
Guarda en Data/discord_threads/{channel_id}.json o {channel_id}_{thread_id}.json.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("discord_thread_memory")

# Máximo de intercambios (user + assistant) a guardar por hilo
MAX_EXCHANGES = 30


def _thread_path(base_path: Path, channel_id: str, thread_id: Optional[str]) -> Path:
    """Ruta del archivo JSON para este canal/hilo."""
    data_dir = Path(base_path) / "Data" / "discord_threads"
    data_dir.mkdir(parents=True, exist_ok=True)
    key = f"{channel_id}_{thread_id}" if thread_id else str(channel_id)
    # Nombres de archivo solo alfanuméricos
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
    return data_dir / f"{safe}.json"


def load_with_summary(
    base_path: Path,
    channel_id: Optional[str],
    thread_id: Optional[str] = None,
    max_exchanges: int = 15,
) -> Dict[str, Any]:
    """
    Carga resumen + últimos intercambios de este canal/hilo.
    Devuelve dict {"summary": str, "messages": [ {role, content}, ... ]}.
    """
    if not channel_id or not str(channel_id).strip():
        return {"summary": "", "messages": []}
    path = _thread_path(
        base_path,
        str(channel_id).strip(),
        str(thread_id).strip() if thread_id else None,
    )
    if not path.exists():
        return {"summary": "", "messages": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"summary": "", "messages": []}
        summary = (data.get("summary") or "").strip()
        raw_messages = data.get("messages") or data.get("history") or []
        if not isinstance(raw_messages, list):
            raw_messages = []
        messages: List[Dict[str, str]] = []
        for m in raw_messages[-max_exchanges:]:
            if isinstance(m, dict) and (m.get("role") or m.get("content")):
                messages.append(
                    {
                        "role": (m.get("role") or "user").strip().lower()[:20],
                        "content": (m.get("content") or "")[:4000],
                    }
                )
        return {"summary": summary, "messages": messages}
    except Exception as e:
        logger.debug("discord_thread_memory load_with_summary: %s", e)
        return {"summary": "", "messages": []}


def load(
    base_path: Path,
    channel_id: Optional[str],
    thread_id: Optional[str] = None,
    max_exchanges: int = 15,
) -> List[Dict[str, str]]:
    """
    Mantiene compatibilidad: devuelve solo la lista de mensajes recientes.
    """
    data = load_with_summary(
        base_path, channel_id, thread_id, max_exchanges=max_exchanges
    )
    return data.get("messages") or []


def append(
    base_path: Path,
    channel_id: Optional[str],
    thread_id: Optional[str],
    user_content: str,
    assistant_content: str,
    max_exchanges: int = MAX_EXCHANGES,
) -> None:
    """Añade un intercambio (user + assistant) al hilo y mantiene solo los últimos max_exchanges (sin resumen)."""
    if not channel_id or not str(channel_id).strip():
        return
    path = _thread_path(
        base_path,
        str(channel_id).strip(),
        str(thread_id).strip() if thread_id else None,
    )
    try:
        data = {"messages": []}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {"messages": []}
        messages = data.get("messages") or []
        if not isinstance(messages, list):
            messages = []
        messages.append({"role": "user", "content": (user_content or "")[:4000]})
        messages.append(
            {"role": "assistant", "content": (assistant_content or "")[:4000]}
        )
        data["messages"] = messages[-max_exchanges:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("discord_thread_memory append: %s", e)


def format_thread_memory_for_prompt(
    summary: str, messages: List[Dict[str, str]], max_chars: int = 2500
) -> str:
    """
    Formatea la memoria del hilo para inyectar en el prompt.
    Incluye, si existe, un resumen histórico + la conversación reciente.
    """
    blocks: List[str] = []
    summary = (summary or "").strip()
    if summary:
        blocks.append("[Historial previo resumido]\n" + summary.strip())

    if messages:
        lines = []
        for m in messages:
            role = (m.get("role") or "user").strip().lower()
            label = "Lilith" if role == "assistant" else "Usuario"
            content = (m.get("content") or "").strip()
            if content:
                lines.append(f"{label}: {content}")
        if lines:
            recent = "\n".join(lines)
            blocks.append("[Conversación reciente]\n" + recent)

    if not blocks:
        return ""

    text = "\n\n".join(blocks)
    if len(text) > max_chars:
        text = "… (resumen)\n" + text[-max_chars:]
    return f"[Memoria de este hilo/canal — prioridad alta]:\n{text}"


def maybe_compress(
    base_path: Path,
    channel_id: Optional[str],
    thread_id: Optional[str],
    max_exchanges: int,
    trigger_count: int,
    keep_count: int,
) -> None:
    """
    Si hay muchos mensajes, comprime los más antiguos en un resumen breve.
    - trigger_count: mínimo de mensajes para disparar la compresión.
    - keep_count: cuántos mensajes recientes dejar sin resumir.
    """
    if not channel_id or not str(channel_id).strip():
        return
    try:
        path = _thread_path(
            base_path,
            str(channel_id).strip(),
            str(thread_id).strip() if thread_id else None,
        )
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        messages = data.get("messages") or []
        if not isinstance(messages, list):
            return
        if len(messages) < trigger_count:
            return

        # Separar antiguos y recientes
        keep_count = max(keep_count, 0)
        if keep_count >= len(messages):
            return
        old = messages[:-keep_count]
        recent = messages[-keep_count:]

        # Texto de los antiguos en formato de conversación
        old_for_prompt: List[Dict[str, str]] = []
        for m in old:
            if isinstance(m, dict) and (m.get("role") or m.get("content")):
                old_for_prompt.append(
                    {
                        "role": (m.get("role") or "user").strip().lower()[:20],
                        "content": (m.get("content") or "")[:4000],
                    }
                )

        if not old_for_prompt:
            return

        # Combinar con resumen previo (si existe)
        previous_summary = (data.get("summary") or "").strip()
        from datetime import datetime, timezone

        text_block = format_thread_memory_for_prompt(
            previous_summary, old_for_prompt, max_chars=4000
        )

        # Usar GenerateReplyTool para sintetizar en 2-3 párrafos
        try:
            from src.core.tools.builtin.generate_reply import GenerateReplyTool

            tool = GenerateReplyTool()
            system = (
                "Eres Lilith resumiendo la conversación de un canal de Discord para ti misma.\n"
                "Escribe un resumen en 2-3 párrafos, en español, manteniendo decisiones técnicas, contexto clave y acuerdos.\n"
                "No repitas todo literalmente; condensa. No añadas información nueva."
            )
            result = tool.execute({"message": text_block, "context": system})
            summary_text = (
                result.get("response") if isinstance(result, dict) else str(result)
            ) or ""
        except Exception as e:
            logger.debug(
                "discord_thread_memory maybe_compress summarization error: %s", e
            )
            return

        summary_text = summary_text.strip()
        if not summary_text:
            return

        data["summary"] = summary_text
        data["summary_updated_at"] = datetime.now(timezone.utc).isoformat()
        data["messages"] = recent[-max_exchanges:]
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("discord_thread_memory maybe_compress: %s", e)
