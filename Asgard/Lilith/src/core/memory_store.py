from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("MemoryStore")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").strip().split())


def _sha256_hex(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


class SemanticMemory(BaseModel):
    memory_id: str = ""
    domain: str
    entity: str
    fact: str
    resolution_path: str = ""
    tags: List[str] = Field(default_factory=list)
    canonical_text: str = ""
    created_at: float = 0.0
    source_run_id: str = ""

    # NUEVO 4.2: Topics para indexación
    topics: List[str] = Field(default_factory=list)
    topics_str: str = ""

    # Campos operativos (metadatos)
    tags_str: str = ""
    seen_count: int = 1
    last_seen_at: float = 0.0
    obsolete: bool = False

    @model_validator(mode="after")
    def _after(self) -> "SemanticMemory":
        self.domain = _normalize_ws(self.domain).lower()
        self.entity = _normalize_ws(self.entity).lower()
        self.fact = (self.fact or "").strip()
        self.resolution_path = (self.resolution_path or "").strip()

        tags_norm = []
        for t in self.tags or []:
            tt = _normalize_ws(str(t)).lower()
            if tt:
                tags_norm.append(tt)
        tags_norm = sorted(set(tags_norm))
        self.tags = tags_norm
        self.tags_str = ",".join(tags_norm)

        # Normalizar topics
        topics_norm = []
        for t in self.topics or []:
            tt = _normalize_ws(str(t)).lower()
            if tt:
                topics_norm.append(tt)
        topics_norm = sorted(set(topics_norm))
        self.topics = topics_norm
        self.topics_str = ",".join(topics_norm)

        base = f"[{self.domain}/{self.entity}] {self.fact}".strip()
        if self.resolution_path:
            base = f"{base} Ref: {self.resolution_path}".strip()
        self.canonical_text = _normalize_ws(base)

        if not self.created_at:
            self.created_at = time.time()
        if not self.last_seen_at:
            self.last_seen_at = self.created_at

        if not self.memory_id:
            self.memory_id = _sha256_hex(self.canonical_text)
        return self

    def to_chroma_metadata(self) -> Dict[str, Any]:
        # Chroma metadata: str/int/float/bool only
        return {
            "memory_id": self.memory_id,
            "domain": self.domain,
            "entity": self.entity,
            "fact": self.fact,
            "resolution_path": self.resolution_path,
            "tags_str": self.tags_str,
            "topics_str": self.topics_str,  # Nuevo 4.2
            "created_at": float(self.created_at),
            "last_seen_at": float(self.last_seen_at),
            "seen_count": int(self.seen_count),
            "obsolete": bool(self.obsolete),
            "source_run_id": (self.source_run_id or "")[:128],
        }

    def raw_json(self) -> str:
        d = self.model_dump()
        # tags list se guarda en raw_json; metadatos usan tags_str
        return json.dumps(d, ensure_ascii=False)


@dataclass
class MemorySearchHit:
    memory: SemanticMemory
    distance: Optional[float] = None


class MemoryStore:
    def __init__(
        self,
        base_path: Optional[Path] = None,
        *,
        persist_dir: str = "Data/vector_store/chroma",
        collection_name: str = "nazarick_global_memory",
    ) -> None:
        self.base_path = Path(base_path) if base_path else _project_root()
        self.persist_path = self.base_path / persist_dir
        self.collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions
        except Exception as e:
            raise RuntimeError(f"ChromaDB no disponible: {e}")
        self.persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=Settings(anonymized_telemetry=False),
        )
        emb_fn = embedding_functions.ONNXMiniLM_L6_V2()
        self._collection = client.get_or_create_collection(
            self.collection_name,
            embedding_function=emb_fn,
            metadata={
                "description": "Memoria semántica Nazarick (offline ONNXMiniLM_L6_V2)"
            },
        )
        return self._collection

    def upsert_memory(self, mem: SemanticMemory) -> SemanticMemory:
        col = self._get_collection()
        mid = mem.memory_id
        # Read-modify-write: mantener seen_count y last_seen_at
        prev_seen = 0
        prev_created = mem.created_at
        try:
            got = col.get(ids=[mid], include=["metadatas"])
            metas = (got.get("metadatas") or []) if isinstance(got, dict) else []
            if metas and isinstance(metas[0], dict):
                prev_seen = int(metas[0].get("seen_count") or 0)
                prev_created = float(metas[0].get("created_at") or prev_created)
        except Exception:
            pass

        mem.seen_count = max(1, prev_seen + 1) if prev_seen else max(1, mem.seen_count)
        mem.created_at = prev_created
        mem.last_seen_at = time.time()
        mem.obsolete = False

        meta = mem.to_chroma_metadata()
        # Guardar raw_json en el documento para recuperación completa
        doc = mem.raw_json()
        col.upsert(
            ids=[mid],
            documents=[doc],
            metadatas=[meta],
        )
        return mem

    def mark_obsolete(self, memory_id: str, *, reason: str = "") -> bool:
        col = self._get_collection()
        mid = (memory_id or "").strip()
        if not mid:
            return False
        try:
            got = col.get(ids=[mid], include=["metadatas", "documents"])
            metas = (got.get("metadatas") or []) if isinstance(got, dict) else []
            docs = (got.get("documents") or []) if isinstance(got, dict) else []
            if not metas:
                return False
            meta = dict(metas[0]) if isinstance(metas[0], dict) else {}
            meta["obsolete"] = True
            if reason:
                meta["obsolete_reason"] = _normalize_ws(reason)[:200]
            doc = docs[0] if docs else "{}"
            col.upsert(ids=[mid], documents=[doc], metadatas=[meta])
            return True
        except Exception:
            return False

    def search_active_memories(
        self,
        query: str,
        *,
        k: int = 3,
        distance_threshold: Optional[float] = 1.1,
    ) -> List[MemorySearchHit]:
        if not (query or "").strip():
            return []
        col = self._get_collection()
        q = (query or "").strip()[:2000]
        where = {"obsolete": False}
        res = col.query(
            query_texts=[q],
            n_results=max(1, min(10, int(k))),
            where=where,
            include=["documents", "distances", "metadatas"],
        )
        hits: List[MemorySearchHit] = []
        docs = (res.get("documents") or [[]])[0] if isinstance(res, dict) else []
        dists = (res.get("distances") or [[]])[0] if isinstance(res, dict) else []
        metas = (res.get("metadatas") or [[]])[0] if isinstance(res, dict) else []
        for i, doc in enumerate(docs or []):
            dist = dists[i] if i < len(dists) else None
            if (
                distance_threshold is not None
                and dist is not None
                and dist > distance_threshold
            ):
                continue
            meta = metas[i] if i < len(metas) else {}
            try:
                raw = json.loads(doc) if isinstance(doc, str) else {}
                mem = SemanticMemory(**raw) if isinstance(raw, dict) else None
            except Exception:
                mem = None
            if mem is None and isinstance(meta, dict):
                try:
                    mem = SemanticMemory(
                        memory_id=str(meta.get("memory_id") or ""),
                        domain=str(meta.get("domain") or ""),
                        entity=str(meta.get("entity") or ""),
                        fact=str(meta.get("fact") or ""),
                        resolution_path=str(meta.get("resolution_path") or ""),
                        tags=[
                            t for t in str(meta.get("tags_str") or "").split(",") if t
                        ],
                        created_at=float(meta.get("created_at") or 0.0),
                        source_run_id=str(meta.get("source_run_id") or ""),
                    )
                    mem.seen_count = int(meta.get("seen_count") or 1)
                    mem.last_seen_at = float(meta.get("last_seen_at") or mem.created_at)
                    mem.obsolete = bool(meta.get("obsolete") or False)
                except Exception:
                    mem = None
            if mem is None:
                continue
            hits.append(
                MemorySearchHit(
                    memory=mem, distance=float(dist) if dist is not None else None
                )
            )
        return hits[:k]

    def search_by_topic(
        self,
        query: str,
        topics: List[str],
        k: int = 5,
        distance_threshold: Optional[float] = 1.1,
    ) -> List[MemorySearchHit]:
        """
        Búsqueda semántica filtrada por topics.

        Args:
            query: Query de búsqueda
            topics: Lista de topics a filtrar
            k: Número máximo de resultados
            distance_threshold: Umbral de distancia máxima

        Returns:
            Lista de hits filtrados por topic
        """
        if not topics:
            # Sin topics, comportamiento normal
            return self.search_active_memories(
                query, k=k, distance_threshold=distance_threshold
            )

        # Buscar más resultados para poder filtrar
        all_results = self.search_active_memories(
            query, k=k * 4, distance_threshold=distance_threshold
        )

        # Filtrar por topics
        filtered = []
        topics_set = set(t.lower() for t in topics)

        for hit in all_results:
            mem_topics = set(t.lower() for t in (hit.memory.topics or []))
            # Si hay intersección de topics
            if mem_topics & topics_set:
                filtered.append(hit)

        return filtered[:k]

    @staticmethod
    def format_memories_block(hits: List[MemorySearchHit]) -> str:
        if not hits:
            return ""
        lines = [
            "[Recuerdos recuperados (úsalos solo si son estrictamente relevantes)]:",
            "",
        ]
        for h in hits:
            m = h.memory
            ref = f" Ref: {m.resolution_path}" if m.resolution_path else ""
            dist = f" (dist={h.distance:.3f})" if h.distance is not None else ""
            topics = f" [{','.join(m.topics)}]" if m.topics else ""
            lines.append(f"- [{m.domain}/{m.entity}]{topics}{dist} {m.fact}{ref}")
        return "\n".join(lines).strip()
