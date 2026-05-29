import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ENTITY_KEYWORDS = {
    "empresa": ["openai", "anthropic", "google", "microsoft", "meta", "nvidia"],
    "modelo": ["gpt", "claude", "gemini", "llama", "qwen", "mistral", "dolphin"],
    "juego": ["minecraft", "steam", "valorant", "fortnite", "dota", "lol"],
    "seguridad": ["defcon", "cve", "exploit", "malware", "ransomware"],
}


@dataclass
class GraphEdge:
    src: str
    rel: str  # mentions | about | causes | related_to
    dst: str
    weight: float
    evidence: str
    ts: float
    source_url: str = ""
    kind_src: str = "concept"  # entity | event | source | concept
    kind_dst: str = "concept"


def _infer_kind(text: str) -> str:
    t = (text or "").lower()
    if t.startswith("http"):
        return "source"
    if any(k in t for k in ["push", "deploy", "build", "fail", "monitor", "alert"]):
        return "event"
    for _cat, kws in ENTITY_KEYWORDS.items():
        if any(k in t for k in kws):
            return "entity"
    return "concept"


def extract_edges(
    concept: str,
    content: str,
    tags: List[str] | None = None,
    url: str = "",
    topic: str = "",
) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    ts = time.time()
    tags = tags or []

    # concept -mentions-> cada tag
    for tag in tags:
        tag = (tag or "").strip()
        if tag and tag != concept:
            edges.append(
                GraphEdge(
                    src=(concept or "")[:120],
                    rel="mentions",
                    dst=tag,
                    weight=0.7,
                    evidence=(content or "")[:100],
                    ts=ts,
                    source_url=url or "",
                    kind_src=_infer_kind(concept),
                    kind_dst="concept",
                )
            )

    # concept -about-> topic
    if topic and topic != concept:
        edges.append(
            GraphEdge(
                src=(concept or "")[:120],
                rel="about",
                dst=(topic or "")[:120],
                weight=0.9,
                evidence=(content or "")[:100],
                ts=ts,
                source_url=url or "",
                kind_src=_infer_kind(concept),
                kind_dst="concept",
            )
        )

    # concept -related_to-> source URL
    if url:
        edges.append(
            GraphEdge(
                src=(concept or "")[:120],
                rel="related_to",
                dst=(url or "")[:200],
                weight=0.6,
                evidence="",
                ts=ts,
                source_url=url or "",
                kind_src=_infer_kind(concept),
                kind_dst="source",
            )
        )

    return edges


async def save_edges_to_muninn(edges: List[GraphEdge], base_path: Path) -> None:
    if not edges:
        return
    try:
        from src.core.memory.muninn_memory import MuninnMemory

        muninn = MuninnMemory(base_path)
        for edge in edges:
            edge_id = hashlib.md5(
                f"{edge.src}|{edge.rel}|{edge.dst}".encode("utf-8", errors="ignore")
            ).hexdigest()[:12]
            concept = f"edge:{edge.src}|{edge.rel}|{edge.dst}"
            content = json.dumps(
                {
                    "id": edge_id,
                    "src": edge.src,
                    "rel": edge.rel,
                    "dst": edge.dst,
                    "weight": edge.weight,
                    "evidence": edge.evidence,
                    "ts": edge.ts,
                    "source_url": edge.source_url,
                    "kind_src": edge.kind_src,
                    "kind_dst": edge.kind_dst,
                },
                ensure_ascii=False,
            )
            await muninn.write_fact(
                concept=concept[:200],
                content=content[:500],
                tags=[
                    "edge",
                    "graph",
                    f"src:{edge.src[:30]}",
                    f"dst:{edge.dst[:30]}",
                    f"type:{edge.kind_src}",
                ],
            )
    except Exception:
        pass


# Compatibilidad: API anterior usada en algunos hooks
@dataclass(frozen=True)
class Relation:
    src: str
    rel: str
    dst: str
    evidence: str = ""


def extract_relations_from_fact(
    *,
    text: str,
    topic: Optional[str] = None,
    source_id: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
) -> List[Relation]:
    # Mapear a edges básicos para no romper llamadas previas
    edges = extract_edges(
        concept=(topic or "")[:120] or "concept",
        content=text or "",
        tags=list(tags or []),
        url=(source_id or ""),
        topic=(topic or ""),
    )
    rels = [
        Relation(src=e.src, rel=e.rel, dst=e.dst, evidence=e.evidence) for e in edges
    ]
    return rels


def relation_to_fact(r: Relation) -> Tuple[str, str, List[str]]:
    concept = f"edge:{(r.src or '')[:120]}|{(r.rel or '')[:30]}|{(r.dst or '')[:200]}"[
        :200
    ]
    content = json.dumps(
        {
            "src": r.src,
            "rel": r.rel,
            "dst": r.dst,
            "evidence": (r.evidence or "")[:200],
        },
        ensure_ascii=False,
    )[:500]
    return concept, content, ["edge", "graph"]
