"""
Mejora-2 — MemoryRouter: punto de escritura único y lectura dual (ChromaDB + MuninnDB).
- Escribe siempre en JSONL + ChromaDB.
- Escribe en MuninnDB sólo si important=True.
- Búsqueda con dedup por source_id y filtro de transporte (aísla Crystal/discord_public).
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.memory_router")

# Transporte que va a Crystal (Discord público) — recibe sólo episodios propios
_CRYSTAL_TRANSPORT = "discord_public"


class MemoryRouter:
    """
    Uso:
        router = MemoryRouter(base_path)
        router.write(text, source_id="fact_001", topic="gamedev", transport="discord_dm")
        results = router.search("query", transport="discord_dm", k=5)
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    # ── Escritura ────────────────────────────────────────────────────────────

    def write(
        self,
        text: str,
        source_id: Optional[str] = None,
        topic: Optional[str] = None,
        transport: str = "discord",
        important: bool = False,
    ) -> None:
        """
        Escribe un hecho en JSONL + ChromaDB.
        Si important=True, también en MuninnDB.
        transport se añade como tag en la escritura semántica para filtrado posterior.
        """
        if not (text and text.strip()):
            return

        # 1) SemanticMemory (JSONL + ChromaDB)
        try:
            from src.core.memory.semantic_memory import SemanticMemory

            sem = SemanticMemory(self.base_path)
            topic_tag = topic or transport
            sem.add_fact(text, source_id=source_id, topic=topic_tag)
        except Exception as e:
            logger.warning("MemoryRouter write semantic: %s", e)

        # 2) MuninnDB — sólo si importante
        if important:
            try:
                from src.core.memory.muninn_memory import (
                    MuninnMemory,
                    _run_coro_fire_and_forget,
                )

                tags = [transport] if transport else []
                if topic:
                    tags.append(topic)
                _run_coro_fire_and_forget(
                    MuninnMemory(self.base_path).write_episode(
                        concept=(source_id or text[:60]),
                        content=text,
                        tags=tags,
                    )
                )
            except Exception as e:
                logger.debug("MemoryRouter write muninn: %s", e)

    # ── Búsqueda ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        transport: str = "discord",
        k: int = 5,
        include_muninn: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda dual ChromaDB + MuninnDB con dedup por source_id.
        Crystal (discord_public) sólo recibe resultados etiquetados como discord_public.
        """
        results: List[Dict[str, Any]] = []

        # 1) ChromaDB
        try:
            from src.core.memory.semantic.vector_store import is_available, search_facts

            if is_available(self.base_path):
                # Crystal sólo ve su propio topic
                topic_filter = (
                    _CRYSTAL_TRANSPORT if transport == _CRYSTAL_TRANSPORT else None
                )
                hits = search_facts(
                    self.base_path,
                    query,
                    k=k * 2,
                    topic=topic_filter,
                )
                for h in hits:
                    results.append({**h, "_source": "chromadb"})
        except Exception as e:
            logger.debug("MemoryRouter search chromadb: %s", e)

        # 2) MuninnDB — no para Crystal (evitar contaminación)
        if include_muninn and transport != _CRYSTAL_TRANSPORT:
            try:
                import asyncio

                from src.core.memory.muninn_memory import MuninnMemory

                muninn = MuninnMemory(self.base_path)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                        muninn_hits = ex.submit(
                            lambda: asyncio.run(muninn.search(query, limit=k))
                        ).result(timeout=3)
                else:
                    muninn_hits = loop.run_until_complete(muninn.search(query, limit=k))
                for h in muninn_hits or []:
                    content = h.get("content") or h.get("text") or ""
                    results.append(
                        {
                            "text": content,
                            "distance": None,
                            "source_id": h.get("concept") or h.get("id"),
                            "metadata": h,
                            "_source": "muninn",
                        }
                    )
            except Exception as e:
                logger.debug("MemoryRouter search muninn: %s", e)

        # Dedup por source_id — ChromaDB tiene prioridad (ya tiene score)
        seen_sources: set = set()
        deduped: List[Dict[str, Any]] = []
        for r in results:
            sid = (r.get("source_id") or "").strip()
            if sid and sid in seen_sources:
                continue
            if sid:
                seen_sources.add(sid)
            deduped.append(r)

        return deduped[:k]
