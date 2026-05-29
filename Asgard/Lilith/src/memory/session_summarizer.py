"""
Lilith v2.2 — Fase B: Session Summarizer
Genera resumen estructurado de la sesión con Eva (Grok) y persiste en JSON + ChromaDB.
"""
import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SessionSummarizer")

# Esquema esperado del resumen
SUMMARY_KEYS = [
    "resumen",
    "temas",
    "decisiones_arquitectura",
    "errores_encontrados",
    "archivos_modificados",
    "logros",
]


def _messages_to_context(messages: List[Dict[str, Any]], max_chars: int = 25000) -> str:
    """Convierte lista de mensajes en texto para Eva."""
    parts = []
    total = 0
    for m in messages:
        role = m.get("role", "unknown")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        line = f"[{role.upper()}]: {content}"
        if total + len(line) > max_chars:
            parts.append(line[: max_chars - total] + "\n... (truncado)")
            break
        parts.append(line)
        total += len(line)
    return "\n\n".join(parts)


def _parse_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extrae un objeto JSON de la respuesta de Eva (puede venir envuelta en markdown o texto)."""
    if not response:
        return None
    response = response.strip()
    # Buscar bloque ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if m:
        raw = m.group(1).strip()
    else:
        raw = response
    # Buscar primer { hasta último }
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return None


class SessionSummarizer:
    """
    Resumidor de sesión: llama a Eva con el historial y genera JSON estructurado.
    Guarda en memory/sessions/{session_id}_summary.json y en ChromaDB (session_summaries).
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        # Mismo directorio que SessionManager (Memory/sessions)
        self.sessions_dir = self.base_path / "Memory" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def summarize(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Llama a Eva (Grok) con el historial y genera JSON estructurado.
        Guarda en memory/sessions/{session_id}_summary.json y en ChromaDB.
        Retorna el diccionario de resumen (o vacío si Eva falla).
        """
        if not messages:
            return {}

        context = _messages_to_context(messages)
        task = """Analiza el historial de conversación y genera UN ÚNICO objeto JSON con exactamente estas claves (usa listas vacías si no aplica):
- "resumen": string de 2-3 oraciones sobre qué pasó en la sesión.
- "temas": lista de strings (tags), ej. ["refactor", "API", "bugs"].
- "decisiones_arquitectura": lista de strings con decisiones técnicas tomadas.
- "errores_encontrados": lista de strings con errores o bugs mencionados.
- "archivos_modificados": lista de strings con rutas o nombres de archivos tocados.
- "logros": lista de strings con logros o tareas completadas.

Responde ÚNICAMENTE con el objeto JSON, sin texto antes ni después. Si no hay información para alguna clave, usa []."""

        try:
            from src.core.agents.panteon.eva import EvaAgent

            eva = EvaAgent()
            if not eva.is_available():
                logger.warning("Eva no disponible; no se generó resumen de sesión.")
                return self._empty_summary(session_id)

            # Eva.execute es síncrono; ejecutar en thread para no bloquear
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: eva.execute(task=task, context=context),
            )

            summary = _parse_json_from_response(response or "")
            if not summary or not isinstance(summary, dict):
                logger.warning("Eva no devolvió JSON válido para el resumen.")
                summary = self._empty_summary(session_id)
            else:
                # Normalizar listas
                for key in SUMMARY_KEYS:
                    if key not in summary:
                        summary[key] = [] if key != "resumen" else ""
                    elif key == "resumen" and not isinstance(summary[key], str):
                        summary[key] = str(summary[key]) if summary[key] else ""
                    elif key != "resumen" and not isinstance(summary[key], list):
                        summary[key] = [summary[key]] if summary[key] else []

            summary["session_id"] = session_id
            summary["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Guardar en memory/sessions/{session_id}_summary.json
            safe_id = re.sub(r'[<>:"/\\|?*]', "_", session_id)
            summary_path = self.sessions_dir / f"{safe_id}_summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.info("Session summary saved: %s", summary_path.name)

            # Guardar en ChromaDB colección session_summaries
            self._add_to_chromadb(summary)

            # Consolidación periódica de memoria: cada 10 sesiones resumidas
            try:
                count = len(list(self.sessions_dir.glob("*_summary.json")))
                if count % 10 == 0:
                    await self.consolidate_memory()
            except Exception as e:
                logger.warning("consolidate_memory skipped: %s", e)

            return summary

        except Exception as e:
            logger.exception("Session summarizer failed: %s", e)
            return self._empty_summary(session_id)

    def _empty_summary(self, session_id: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "resumen": "",
            "temas": [],
            "decisiones_arquitectura": [],
            "errores_encontrados": [],
            "archivos_modificados": [],
            "logros": [],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _add_to_chromadb(self, summary: Dict[str, Any]) -> None:
        """Añade el resumen a la colección ChromaDB session_summaries."""
        try:
            from src.core.memory.vector_store import VectorStore

            store = VectorStore()
            store.add_session_summary(
                summary_text=summary.get("resumen", ""),
                session_id=summary.get("session_id", ""),
                metadata={
                    "session_id": summary.get("session_id", ""),
                    "generated_at": summary.get("generated_at", ""),
                    "temas": json.dumps(summary.get("temas", [])),
                    "has_decisiones": bool(summary.get("decisiones_arquitectura")),
                    "has_archivos": bool(summary.get("archivos_modificados")),
                },
            )
        except Exception as e:
            logger.warning("Could not add session summary to ChromaDB: %s", e)

    async def consolidate_memory(self) -> None:
        """
        Revisa la memoria semántica/procedimental y consolida patrones.
        Implementación inicial: placeholder con logging; la lógica detallada
        se puede extender en futuras fases.
        """
        logger.info("Starting periodic memory consolidation...")
        try:
            from src.core.memory.procedural_memory import ProceduralMemory
            from src.core.memory.semantic_memory import SemanticMemory

            base = self.base_path
            sem = SemanticMemory(base)
            proc = ProceduralMemory(base)

            # Cargar estructuras actuales (no modificamos todavía mucho para evitar ruido).
            _ = sem.load_user_profile()
            _ = sem.load_code_style()
            _ = proc.load_error_history()
            logger.info("Memory consolidation snapshot loaded (semantic + procedural).")
        except Exception as e:
            logger.warning("consolidate_memory internal error: %s", e)
