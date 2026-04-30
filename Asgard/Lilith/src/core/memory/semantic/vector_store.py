"""
Misión 3.4 D.3a — Store vectorial de hechos (ChromaDB + sentence-transformers).
Búsqueda por similitud semántica. Degradación elegante si dependencias no están.
4.0: source_id en metadatos, chunking con overlap, diversidad one_per_source.
"""
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("VectorStore")

# Límite por documento para el encoder (~256 tokens); chunking por debajo
_DEFAULT_CHUNK_SIZE = 450
_DEFAULT_OVERLAP = 50

_EMBEDDER = None
_CHROMA_CLIENT = None
_COLLECTION = None
_AVAILABLE = False
_PATH: Optional[Path] = None


def _init(
    base_path: Path,
    persist_path: str = "Data/chroma_facts",
    model_name: str = "all-MiniLM-L6-v2",
) -> bool:
    global _EMBEDDER, _CHROMA_CLIENT, _COLLECTION, _AVAILABLE, _PATH
    if _PATH is not None and _PATH == base_path:
        return _AVAILABLE
    _PATH = Path(base_path)
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.debug(
            "VectorStore: dependencias no instaladas (%s). Búsqueda vectorial desactivada.",
            e,
        )
        _AVAILABLE = False
        return False
    try:
        _EMBEDDER = SentenceTransformer(model_name)
        persist_dir = _PATH / persist_path
        persist_dir.mkdir(parents=True, exist_ok=True)
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=str(persist_dir), settings=Settings(anonymized_telemetry=False)
        )
        _COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
            "facts", metadata={"description": "Hechos recientes Lilith"}
        )
        _AVAILABLE = True
        logger.info("VectorStore: ChromaDB + %s listo en %s", model_name, persist_dir)
    except Exception as e:
        logger.warning("VectorStore: no se pudo inicializar: %s", e)
        _AVAILABLE = False
    return _AVAILABLE


def is_available(base_path: Optional[Path] = None) -> bool:
    if base_path is not None and _PATH != base_path:
        _init(base_path)
    return _AVAILABLE


def chunk_text(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_OVERLAP,
    prefer_sentence_boundary: bool = True,
) -> List[str]:
    """
    Fragmenta el texto en chunks con solapamiento para no cortar oraciones.
    4.0: intenta cortar en . \\n ! ? ; si no hay (Base64, JSON minificado), fallback a último espacio/tab.
    """
    text = (text or "").strip()
    if not text or chunk_size <= 0 or overlap >= chunk_size:
        return [text] if text else []
    chunks: List[str] = []
    start = 0
    margin = 80
    while start < len(text):
        candidate_end = min(start + chunk_size, len(text))
        end = candidate_end
        if candidate_end < len(text):
            window = text[start:candidate_end]
            found = False
            for sep in (". ", ".\n", "! ", "? ", "\n\n"):
                idx = window.rfind(sep)
                if idx != -1 and idx >= (len(window) - margin):
                    end = start + idx + len(sep)
                    found = True
                    break
            if not found and prefer_sentence_boundary:
                # Respaldo: último espacio o tab en la ventana para no partir tokens (Base64, JSON, datos)
                for fallback in (" ", "\t"):
                    idx = window.rfind(fallback)
                    if idx != -1 and idx >= (len(window) - margin):
                        end = start + idx + len(fallback)
                        break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)
        if start >= len(text):
            break
    return chunks


def add_fact(
    base_path: Path,
    fact_id: str,
    fact_text: str,
    source_id: Optional[str] = None,
    topic: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> None:
    """
    Añade un hecho al store vectorial. 4.0: source_id y topic en metadatos, chunking con overlap.
    Mejora-1/4: si fact_text supera chunk_size, divide en chunks y los upserta como fact_id_chunk_N.
    Mejora-4: timestamp ISO UTC en metadatos para decay temporal.
    """
    if not fact_text or not fact_text.strip():
        return
    if not _init(base_path):
        return
    from datetime import datetime, timezone

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    raw = fact_text.strip()
    sid = str(source_id)[:64] if source_id is not None else None
    topic_str = (
        str(topic).strip()[:64] if topic is not None and str(topic).strip() else None
    )

    def _build_meta() -> Dict[str, Any]:
        m: Dict[str, Any] = {"timestamp": ts}
        if sid:
            m["source_id"] = sid
        if topic_str:
            m["topic"] = topic_str
        return m

    try:
        if len(raw) <= _DEFAULT_CHUNK_SIZE:
            emb = _EMBEDDER.encode([raw])
            _COLLECTION.upsert(
                ids=[fact_id],
                embeddings=emb.tolist(),
                documents=[raw],
                metadatas=[_build_meta()],
            )
        else:
            chunks = chunk_text(
                raw, chunk_size=_DEFAULT_CHUNK_SIZE, overlap=_DEFAULT_OVERLAP
            )
            for i, ch in enumerate(chunks):
                cid = f"{fact_id}_chunk_{i}"
                emb = _EMBEDDER.encode([ch])
                _COLLECTION.upsert(
                    ids=[cid],
                    embeddings=emb.tolist(),
                    documents=[ch],
                    metadatas=[_build_meta()],
                )
    except Exception as e:
        logger.warning("VectorStore add_fact: %s", e)


def _chunk_index_from_fact_id(fact_id: Any) -> int:
    """Extrae el índice de chunk de fact_id (ej. 'abc123_chunk_0' -> 0). Sin _chunk_ devuelve 0."""
    if not fact_id:
        return 0
    s = str(fact_id).strip()
    if "_chunk_" not in s:
        return 0
    try:
        return int(s.split("_chunk_")[-1])
    except (ValueError, IndexError):
        return 0


def _sort_key_distance_then_chunk(r: Dict[str, Any]) -> tuple:
    """Orden: menor distance primero; empate resuelto por chunk index (preferir chunk_0 como contexto principal)."""
    dist = 999.0 if r.get("distance") is None else (r.get("distance") or 999.0)
    idx = _chunk_index_from_fact_id(r.get("fact_id"))
    return (r.get("distance") is None, dist, idx)


def _diversify_by_source(
    results: List[Dict[str, Any]],
    k: int,
) -> List[Dict[str, Any]]:
    """
    one_per_source: un resultado por source_id hasta llenar k; luego rellenar por score.
    Empates de similitud: se prefiere el chunk con índice menor (chunk_0 = introducción/contexto).
    """
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        sid = (
            r.get("source_id") or r.get("metadata", {}).get("source_id") or ""
        ).strip() or "_none"
        by_source.setdefault(sid, []).append(r)
    for sid in by_source:
        by_source[sid].sort(key=_sort_key_distance_then_chunk)
    out: List[Dict[str, Any]] = []
    used_sources: set = set()

    def best_first(p):
        grp = p[1]
        return _sort_key_distance_then_chunk(grp[0]) if grp else (True, 999.0, 0)

    for sid, group in sorted(by_source.items(), key=best_first):
        if len(out) >= k:
            break
        if sid not in used_sources and group:
            out.append(group[0])
            used_sources.add(sid)
    remaining = [r for g in by_source.values() for r in g[1:]]
    remaining.sort(key=_sort_key_distance_then_chunk)
    for r in remaining:
        if len(out) >= k:
            break
        out.append(r)
    return out[:k]


def search_facts(
    base_path: Path,
    query: str,
    k: int = 5,
    k_candidates_multiplier: int = 3,
    diversity_strategy: str = "one_per_source",
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve los K hechos más similares. 4.0: diversidad por source_id; topic opcional acota por dominio (rol_lore, gamedev, etc.).
    """
    if not (query or query.strip()):
        return []
    if not _init(base_path):
        return []
    k_ask = min(max(k * k_candidates_multiplier, k), 50)
    try:
        emb = _EMBEDDER.encode([query.strip()[:2000]])
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": emb.tolist(),
            "n_results": k_ask,
            "include": ["documents", "distances", "metadatas"],
        }
        if topic and str(topic).strip():
            query_kwargs["where"] = {"topic": str(topic).strip()[:64]}
        res = _COLLECTION.query(**query_kwargs)
        out: List[Dict[str, Any]] = []
        if res and res.get("documents") and res["documents"][0]:
            metadatas = (
                (res.get("metadatas") or [[]])[0] if res.get("metadatas") else []
            )
            ids_list = (res.get("ids") or [[]])[0] if res.get("ids") else []
            for i, doc in enumerate(res["documents"][0]):
                dist = (
                    res["distances"][0][i]
                    if res.get("distances") and res["distances"][0]
                    else None
                )
                meta = metadatas[i] if i < len(metadatas) else {}
                fact_id = ids_list[i] if i < len(ids_list) else None
                out.append(
                    {
                        "text": doc,
                        "distance": dist,
                        "source_id": meta.get("source_id")
                        if isinstance(meta, dict)
                        else None,
                        "metadata": meta if isinstance(meta, dict) else {},
                        "fact_id": fact_id,
                    }
                )
        if diversity_strategy == "one_per_source" and len(out) > k:
            out = _diversify_by_source(out, k)
        else:
            out = out[:k]
        # Mejora-4: decay temporal post-processing
        out = _apply_temporal_decay(out)
        return out
    except Exception as e:
        logger.warning("VectorStore search_facts: %s", e)
        return []


def _apply_temporal_decay(
    results: List[Dict[str, Any]],
    half_life_days: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Mejora-4: ajusta `distance` con decay exponencial basado en timestamp del metadata.
    adjusted_score = (1 - distance) * decay_factor; decay = 2^(-age_days / half_life_days).
    Resultados sin timestamp no se penalizan. Re-ordena de mayor a menor adjusted_score.
    """
    now = datetime.now(timezone.utc)
    for r in results:
        meta = r.get("metadata") or {}
        ts_str = meta.get("timestamp") or ""
        decay = 1.0
        if ts_str:
            try:
                dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
                decay = math.pow(2.0, -age_days / half_life_days)
            except Exception:
                pass
        dist = r.get("distance") or 0.0
        r["decay_factor"] = round(decay, 4)
        r["adjusted_score"] = round((1.0 - dist) * decay, 4)
    results.sort(key=lambda x: x.get("adjusted_score", 0.0), reverse=True)
    return results


def purge_decayed_facts(
    base_path: Path, decay_threshold: float = 0.1, half_life_days: float = 30.0
) -> int:
    """
    Mejora-4: elimina de ChromaDB los hechos cuyo decay sea inferior a decay_threshold.
    Devuelve el número de entradas eliminadas. Seguro de ejecutar periódicamente (job semanal).
    """
    if not _init(base_path):
        return 0
    try:
        res = _COLLECTION.get(include=["metadatas"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        now = datetime.now(timezone.utc)
        to_delete: List[str] = []
        for doc_id, meta in zip(ids, metas):
            ts_str = (meta or {}).get("timestamp") or ""
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
                decay = math.pow(2.0, -age_days / half_life_days)
                if decay < decay_threshold:
                    to_delete.append(doc_id)
            except Exception:
                continue
        if to_delete:
            _COLLECTION.delete(ids=to_delete)
            logger.info(
                "VectorStore purge: eliminados %d hechos decaídos", len(to_delete)
            )
        return len(to_delete)
    except Exception as e:
        logger.warning("VectorStore purge_decayed_facts: %s", e)
        return 0
