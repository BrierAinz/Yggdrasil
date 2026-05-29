"""
DocIndexer: Indexación de documentación en MuninnDB.
Vault: "docs" - Knowledge Base de Svartalfheim
"""
import asyncio
import json

# Setup path para imports
import sys
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent
CORE_DIR = BACKEND_DIR / "core"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(CORE_DIR))

from doc_chunker import DocChunk, DocChunker
from muninn_memory import MuninnMemory

KB_ROOT = Path("D:/Proyectos/Yggdrasil/Svartalfheim/Knowledge_Base")
BASE_PATH = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith")


class DocIndexer:
    """
    Indexa documentación de Svartalfheim en MuninnDB.

    Cada chunk se almacena como un engrama con:
    - concept: identificador del chunk
    - content: contenido del chunk
    - tags: metadatos para filtrado
    - metadata: información adicional
    """

    def __init__(self, vault_name: str = "docs"):
        self.chunker = DocChunker(chunk_size=1500, overlap=300)
        self.muninn = MuninnMemory(base_path=BASE_PATH, vault_name=vault_name)
        self.vault_name = vault_name
        self.indexed_count = 0
        self.chunk_count = 0

    async def index_document(self, doc_path: Path, doc_metadata: dict) -> int:
        """
        Indexa un único documento.

        Args:
            doc_path: Path al archivo markdown
            doc_metadata: Metadata del documento

        Returns:
            Número de chunks indexados
        """
        try:
            content = doc_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] Leyendo {doc_path}: {e}")
            return 0

        # Generar chunks
        chunks = self.chunker.chunk_markdown(content, doc_metadata)

        # Indexar cada chunk
        for chunk in chunks:
            await self._store_chunk(chunk)

        self.chunk_count += len(chunks)
        self.indexed_count += 1

        return len(chunks)

    async def _store_chunk(self, chunk: DocChunk) -> None:
        """Almacena un chunk en MuninnDB."""
        # Construir concepto descriptivo
        concept = f"{chunk.doc_id}:{chunk.section}"
        if chunk.subsection:
            concept += f":{chunk.subsection}"

        # Tags para categorización
        tags = [
            f"doc:{chunk.doc_id}",
            f"section:{chunk.section}",
            "type:documentation",
        ]

        # Añadir tag de categoría según path
        path_lower = chunk.metadata.get("path", "").lower()
        if "lilith_docs" in path_lower:
            tags.append("category:current")
        elif "el_inicio_del_todo" in path_lower:
            tags.append("category:historical")
        elif "legacy" in path_lower:
            tags.append("category:legacy")

        # Metadata adicional
        metadata = {
            "chunk_id": chunk.chunk_id,
            "doc_title": chunk.metadata.get("title", chunk.doc_id),
            "doc_version": chunk.metadata.get("version", ""),
            "doc_date": chunk.metadata.get("date", ""),
            "section": chunk.section,
            "subsection": chunk.subsection,
        }

        # Almacenar en Muninn
        await self.muninn.write(
            vault=self.vault_name,
            concept=concept[:200],
            content=chunk.content[:2000],  # Límite de Muninn
            tags=tags,
            metadata=metadata,
        )

    async def index_knowledge_base(self, kb_root: Optional[Path] = None) -> Dict:
        """
        Indexa toda la Knowledge Base.

        Args:
            kb_root: Path raíz de la Knowledge Base

        Returns:
            Estadísticas de indexación
        """
        kb_root = kb_root or KB_ROOT
        index_file = kb_root / "index.json"

        if not index_file.exists():
            print(f"[ERROR] No se encontró {index_file}")
            print("[INFO] Ejecuta primero: python Scripts/generate_docs_metadata.py")
            return {"error": "index.json not found"}

        # Cargar metadata
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        docs_metadata = index_data.get("documents", [])

        print(f"[INDEX] Indexando {len(docs_metadata)} documentos...")
        print(f"[INDEX] Vault: {self.vault_name}")
        print(f"[INDEX] Chunk size: 1500 tokens, Overlap: 300 tokens\n")

        # Indexar cada documento
        for i, doc_meta in enumerate(docs_metadata, 1):
            doc_path = kb_root / doc_meta["path"]

            if not doc_path.exists():
                print(
                    f"  [{i}/{len(docs_metadata)}] SKIP {doc_meta['filename']} (no existe)"
                )
                continue

            chunk_count = await self.index_document(doc_path, doc_meta)
            print(
                f"  [{i}/{len(docs_metadata)}] {doc_meta['filename']} → {chunk_count} chunks"
            )

        # Estadísticas
        stats = {
            "documents_indexed": self.indexed_count,
            "chunks_indexed": self.chunk_count,
            "vault": self.vault_name,
            "kb_root": str(kb_root),
        }

        print(f"\n[SUCCESS] Indexación completa:")
        print(f"  Documentos: {self.indexed_count}")
        print(f"  Chunks: {self.chunk_count}")

        return stats

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca en la documentación indexada.

        Args:
            query: Consulta de búsqueda
            limit: Máximo de resultados

        Returns:
            Lista de resultados relevantes
        """
        results = await self.muninn.activate(
            context=query, vault=self.vault_name, max_results=limit
        )
        return results


async def main():
    """CLI para indexar documentación."""
    import sys

    indexer = DocIndexer(vault_name="docs")

    # Comandos
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # Modo búsqueda
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "DAG Executor"
        print(f"[SEARCH] Buscando: '{query}'\n")
        results = await indexer.search(query, limit=5)

        print(f"Resultados: {len(results)}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.get('concept', 'N/A')}")
            print(f"   Score: {r.get('score', 0):.3f}")
            print(f"   Content: {r.get('content', '')[:150]}...")
            print()
    else:
        # Modo indexación
        stats = await indexer.index_knowledge_base()

        # Guardar stats
        stats_path = KB_ROOT / "index_stats.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"\n[STATS] Guardado en: {stats_path}")


if __name__ == "__main__":
    asyncio.run(main())
