"""
RAG Engine - Motor de busqueda semantica
======================================
Permite indexar documentos y responder preguntas sobre ellos.
Ahora con busqueda semantica hibrida (embeddings + keywords).
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Importar busqueda semantica
try:
    from .semantic_search import SemanticSearcher, get_semantic_searcher
except ImportError:
    SemanticSearcher = None

    def get_semantic_searcher():
        return None


# Directorio de datos
RAG_DIR = Path(__file__).parent.parent / "Data" / "rag"
RAG_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = RAG_DIR / "index.json"
CHUNKS_DIR = RAG_DIR / "chunks"


@dataclass
class Chunk:
    """Fragmento de texto indexado."""

    id: str
    content: str
    document_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "document_id": self.document_id,
            "metadata": self.metadata,
        }


@dataclass
class Document:
    """Documento indexado."""

    id: str
    source: str
    title: str
    doc_type: str
    content: str
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    chunk_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "doc_type": self.doc_type,
            "content": self.content,
            "indexed_at": self.indexed_at,
            "chunk_count": self.chunk_count,
        }


class HybridVectorStore:
    """
    Store hibrido: embeddings semanticos + keywords.
    Reemplazable por ChromaDB/Qdrant para produccion.
    """

    def __init__(self, chunks_dir: Path):
        self.chunks_dir = chunks_dir
        self.chunks_dir.mkdir(exist_ok=True)
        self.index: Dict[str, Chunk] = {}
        self._keyword_index: Dict[str, List[str]] = {}
        self._semantic = get_semantic_searcher()

    def add_chunk(self, chunk: Chunk):
        """Agrega un chunk al store (ambos indices)."""
        self.index[chunk.id] = chunk

        # Guardar en archivo
        chunk_file = self.chunks_dir / f"{chunk.id}.json"
        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk.to_dict(), f)

        # Indexar keywords
        words = self._extract_keywords(chunk.content)
        for word in words:
            if word not in self._keyword_index:
                self._keyword_index[word] = []
            if chunk.id not in self._keyword_index[word]:
                self._keyword_index[word].append(chunk.id)

        # Indexar semanticamente
        if self._semantic and self._semantic.is_available():
            self._semantic.add_chunk(
                chunk.id,
                chunk.content,
                metadata={"document_id": chunk.document_id, **chunk.metadata},
            )

    def _extract_keywords(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()
        stopwords = {
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "en",
            "con",
            "para",
            "que",
            "es",
            "son",
            "y",
            "o",
            "a",
            "un",
            "una",
            "por",
            "se",
            "the",
            "a",
            "an",
            "is",
            "are",
            "and",
            "or",
            "to",
            "in",
            "of",
            "this",
            "that",
            "it",
            "for",
            "with",
            "as",
            "on",
            "at",
            "from",
        }
        return [w for w in words if len(w) > 2 and w not in stopwords]

    def search(self, query: str, limit: int = 5) -> List[Tuple[Chunk, float]]:
        """Busqueda hibrida: semantic + keyword fusion."""
        scores: Dict[str, float] = {}

        # 1. Busqueda semantica (peso 0.7)
        if self._semantic and self._semantic.is_available():
            semantic_results = self._semantic.search(query, limit=limit * 3)
            for chunk_id, sim in semantic_results:
                scores[chunk_id] = scores.get(chunk_id, 0) + (sim * 0.7)

        # 2. Busqueda por keywords (peso 0.3)
        query_words = self._extract_keywords(query)
        keyword_hits: Dict[str, int] = {}
        for word in query_words:
            for chunk_id in self._keyword_index.get(word, []):
                keyword_hits[chunk_id] = keyword_hits.get(chunk_id, 0) + 1
        max_kw = max(keyword_hits.values()) if keyword_hits else 1
        for chunk_id, hits in keyword_hits.items():
            scores[chunk_id] = scores.get(chunk_id, 0) + ((hits / max_kw) * 0.3)

        # Ordenar y retornar
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for chunk_id, score in ranked[:limit]:
            if chunk_id in self.index:
                results.append((self.index[chunk_id], score))
        return results

    def load(self):
        """Carga el indice desde disco."""
        self.index = {}
        self._keyword_index = {}

        if not self.chunks_dir.exists():
            return

        for chunk_file in self.chunks_dir.glob("*.json"):
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chunk = Chunk(
                        id=data["id"],
                        content=data["content"],
                        document_id=data["document_id"],
                        metadata=data.get("metadata", {}),
                    )
                    self.index[chunk.id] = chunk
                    words = self._extract_keywords(chunk.content)
                    for word in words:
                        if word not in self._keyword_index:
                            self._keyword_index[word] = []
                        if chunk.id not in self._keyword_index[word]:
                            self._keyword_index[word].append(chunk.id)
            except Exception:
                continue

    def count(self) -> int:
        return len(self.index)


class RAGEngine:
    """Motor RAG para Lilith con busqueda hibrida."""

    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
        ".ps1": "powershell",
        ".bat": "batch",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "header",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
    }

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents: Dict[str, Document] = {}
        self.vector_store = HybridVectorStore(CHUNKS_DIR)
        self._load_index()

    def _load_index(self):
        self.vector_store.load()
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for doc_data in data.get("documents", []):
                        doc = Document(
                            id=doc_data["id"],
                            source=doc_data["source"],
                            title=doc_data["title"],
                            doc_type=doc_data["doc_type"],
                            content=doc_data["content"],
                            indexed_at=doc_data.get("indexed_at", ""),
                            chunk_count=doc_data.get("chunk_count", 0),
                        )
                        self.documents[doc.id] = doc
            except Exception as e:
                print(f"Error loading RAG index: {e}")

    def _save_index(self):
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"documents": [d.to_dict() for d in self.documents.values()]},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def _generate_id(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _chunk_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if end < len(text) and " " in chunk[-50:]:
                last_space = chunk[-50:].find(" ")
                if last_space != -1:
                    end = start + self.chunk_size - 50 + last_space
                    chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        return chunks

    def index_file(self, file_path: str, title: Optional[str] = None) -> bool:
        path = Path(file_path)
        if not path.exists():
            return False
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        doc_id = self._generate_id(content)
        if doc_id in self.documents:
            return True
        doc = Document(
            id=doc_id,
            source=str(path),
            title=title or path.name,
            doc_type=self.SUPPORTED_EXTENSIONS[ext],
            content=content,
        )
        chunks = self._chunk_text(content)
        doc.chunk_count = len(chunks)
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            chunk = Chunk(
                id=chunk_id,
                content=chunk_text,
                document_id=doc_id,
                metadata={"title": doc.title, "source": doc.source, "chunk_index": i},
            )
            self.vector_store.add_chunk(chunk)
        self.documents[doc.id] = doc
        self._save_index()
        return True

    def index_directory(
        self,
        dir_path: str,
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        exclude_dirs = exclude_dirs or [
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            ".hermes",
        ]
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            return stats
        patterns = ["*"] if not extensions else [f"*{ext}" for ext in extensions]
        for pattern in patterns:
            files = path.rglob(pattern) if recursive else path.glob(pattern)
            for file_path in files:
                if not file_path.is_file():
                    continue
                if any(excl in file_path.parts for excl in exclude_dirs):
                    stats["skipped"] += 1
                    continue
                try:
                    if self.index_file(str(file_path)):
                        stats["indexed"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    stats["errors"] += 1
        return stats

    def search(
        self, query: str, limit: int = 5, doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self.vector_store.search(query, limit * 2)
        output = []
        seen_docs = set()
        for chunk, score in results:
            if doc_type and chunk.metadata.get("doc_type") != doc_type:
                continue
            if chunk.document_id in seen_docs:
                continue
            seen_docs.add(chunk.document_id)
            doc = self.documents.get(chunk.document_id)
            if not doc:
                continue
            output.append(
                {
                    "title": doc.title,
                    "source": doc.source,
                    "doc_type": doc.doc_type,
                    "content": chunk.content,
                    "score": round(score, 3),
                    "relevance": "high"
                    if score > 0.6
                    else "medium"
                    if score > 0.3
                    else "low",
                }
            )
            if len(output) >= limit:
                break
        return output

    def get_context_for_query(self, query: str, max_chars: int = 2000) -> str:
        results = self.search(query, limit=3)
        context_parts = ["CONTEXTO DE DOCUMENTOS RELACIONADOS:"]
        total_chars = 0
        for result in results:
            part = (
                f"\n--- {result['title']} ({result['source']}) ---\n{result['content']}"
            )
            if total_chars + len(part) > max_chars:
                break
            context_parts.append(part)
            total_chars += len(part)
        return "\n".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents": len(self.documents),
            "chunks": self.vector_store.count(),
            "by_type": self._count_by_type(),
            "semantic_available": self.vector_store._semantic is not None
            and self.vector_store._semantic.is_available(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for doc in self.documents.values():
            counts[doc.doc_type] = counts.get(doc.doc_type, 0) + 1
        return counts

    def remove_document(self, doc_id: str) -> bool:
        if doc_id not in self.documents:
            return False
        doc = self.documents[doc_id]
        for i in range(doc.chunk_count):
            chunk_file = CHUNKS_DIR / f"{doc_id}_{i}.json"
            if chunk_file.exists():
                chunk_file.unlink()
            emb_file = RAG_DIR / "embeddings" / f"{doc_id}_{i}.npy"
            meta_file = emb_file.with_suffix(".json")
            if emb_file.exists():
                emb_file.unlink()
            if meta_file.exists():
                meta_file.unlink()
        del self.documents[doc_id]
        self._save_index()
        return True


_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
