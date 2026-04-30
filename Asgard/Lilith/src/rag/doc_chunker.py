"""
DocChunker: Chunking estratégico para documentación técnica.
Chunk size: 1500 tokens, overlap: 300 tokens
"""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DocChunk:
    """Representa un chunk de documento."""

    doc_id: str
    chunk_id: str
    content: str
    section: str
    subsection: str
    metadata: dict


class DocChunker:
    """
    Chunker especializado para documentación markdown.

    Estrategia:
    - Dividir por secciones (##)
    - Si sección > chunk_size, dividir con overlap
    - Preservar contexto entre chunks
    """

    def __init__(self, chunk_size: int = 1500, overlap: int = 300):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # Estimación: ~4 caracteres por token (conservador)
        self.char_per_token = 4
        self.chunk_chars = chunk_size * self.char_per_token
        self.overlap_chars = overlap * self.char_per_token

    def chunk_markdown(self, content: str, doc_metadata: dict) -> List[DocChunk]:
        """
        Divide contenido markdown en chunks estratégicos.

        Args:
            content: Contenido markdown completo
            doc_metadata: Metadata del documento

        Returns:
            Lista de DocChunk
        """
        chunks = []
        doc_id = doc_metadata.get("filename", "unknown")

        # Dividir por secciones principales (##)
        # Patrón: ## Título de sección
        sections = re.split(r"\n(?=## )", content)

        for section_idx, section in enumerate(sections):
            section_lines = section.split("\n")
            section_title = "Introducción"

            # Extraer título de sección si existe
            if section_lines and section_lines[0].startswith("##"):
                section_title = section_lines[0].strip("#").strip()
                section_content = "\n".join(section_lines[1:])
            else:
                section_content = section

            # Limpiar contenido vacío
            section_content = section_content.strip()
            if not section_content:
                continue

            # Si la sección cabe en un chunk, crear chunk único
            if len(section_content) <= self.chunk_chars:
                chunk_id = f"{doc_id}_s{section_idx}_c0"
                chunks.append(
                    DocChunk(
                        doc_id=doc_id,
                        chunk_id=chunk_id,
                        content=section_content,
                        section=section_title,
                        subsection="",
                        metadata=doc_metadata,
                    )
                )
            else:
                # Dividir sección grande en sub-chunks
                sub_chunks = self._split_with_overlap(section_content)
                for sub_idx, sub_content in enumerate(sub_chunks):
                    chunk_id = f"{doc_id}_s{section_idx}_c{sub_idx}"
                    chunks.append(
                        DocChunk(
                            doc_id=doc_id,
                            chunk_id=chunk_id,
                            content=sub_content,
                            section=section_title,
                            subsection=f"Parte {sub_idx + 1}/{len(sub_chunks)}",
                            metadata=doc_metadata,
                        )
                    )

        return chunks

    def _split_with_overlap(self, text: str) -> List[str]:
        """
        Divide texto largo en chunks con overlap.

        Args:
            text: Texto a dividir

        Returns:
            Lista de chunks
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            # Calcular fin del chunk
            end = start + self.chunk_chars

            if end >= text_len:
                # Último chunk
                chunks.append(text[start:].strip())
                break

            # Buscar punto de corte inteligente (fin de párrafo)
            # Retroceder hasta encontrar \n\n o .\n
            search_end = min(end, text_len)
            cutoff = search_end

            # Buscar hasta 200 caracteres atrás para fin de párrafo
            search_start = max(start + self.chunk_chars - 200, start)
            paragraph_end = text.rfind("\n\n", search_start, search_end)

            if paragraph_end != -1 and paragraph_end > start + 100:
                cutoff = paragraph_end
            else:
                # Si no hay fin de párrafo, buscar fin de oración
                sentence_end = text.rfind(".\n", search_start, search_end)
                if sentence_end != -1 and sentence_end > start + 100:
                    cutoff = sentence_end + 1

            chunks.append(text[start:cutoff].strip())

            # Avanzar con overlap
            start = max(cutoff - self.overlap_chars, start + 100)

        return chunks

    def estimate_tokens(self, text: str) -> int:
        """Estima número de tokens en texto."""
        return len(text) // self.char_per_token


def test_chunker():
    """Test básico del chunker."""
    chunker = DocChunker(chunk_size=1500, overlap=300)

    sample_doc = (
        """# 01 - Test Document
> **Versión:** 1.0

## Introducción
Este es el contenido de introducción.

## Sección Principal
"""
        + "Este es un párrafo muy largo. " * 500
        + """

## Conclusión
Fin del documento.
"""
    )

    metadata = {"filename": "test.md", "title": "Test"}
    chunks = chunker.chunk_markdown(sample_doc, metadata)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        tokens = chunker.estimate_tokens(chunk.content)
        print(
            f"  Chunk {i}: {chunk.section} | {tokens} tokens | {len(chunk.content)} chars"
        )

    return chunks


if __name__ == "__main__":
    test_chunker()
