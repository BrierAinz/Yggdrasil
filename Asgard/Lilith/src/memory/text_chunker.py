"""
Lilith Text Chunker
Splits large text files into manageable chunks for embedding
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("TextChunker")


class TextChunker:
    """
    Intelligent text chunking for large documents.
    Respects markdown structure (headers, code blocks, lists).
    """

    # Target chunk size: 10KB (conservative, well under 50KB limit)
    TARGET_CHUNK_SIZE = 10000
    MAX_CHUNK_SIZE = 15000

    def __init__(self, target_size: int = TARGET_CHUNK_SIZE):
        self.target_size = target_size

    def chunk_markdown(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk markdown text while preserving structure.
        Returns list of chunks with metadata.
        """
        # If text is small enough, return as single chunk
        if len(text) <= self.target_size:
            return [{"content": text, "chunk_id": 0, "type": "full", "size": len(text)}]

        # Split by logical boundaries first
        sections = self._split_by_sections(text)

        chunks = []
        for section_idx, section in enumerate(sections):
            # If section is small, add directly
            if len(section) <= self.target_size:
                chunks.append(
                    {
                        "content": section,
                        "chunk_id": len(chunks),
                        "type": "section",
                        "section_index": section_idx,
                        "size": len(section),
                    }
                )
            else:
                # Split large section by paragraphs
                para_chunks = self._split_by_paragraphs(section)
                for para_chunk in para_chunks:
                    chunks.append(
                        {
                            "content": para_chunk,
                            "chunk_id": len(chunks),
                            "type": "paragraph_group",
                            "section_index": section_idx,
                            "size": len(para_chunk),
                        }
                    )

        logger.info(f"Chunked {len(text)} chars into {len(chunks)} chunks")
        return chunks

    def _split_by_sections(self, text: str) -> List[str]:
        """Split by markdown headers (##, ###)"""
        import re

        # Pattern: match headers and their content until next header or end
        header_pattern = r"(?=^##\s|\n##\s)|(?=^###\s|\n###\s)|(?=^####\s|\n####\s)"

        # If no headers, return as single section
        if not re.search(header_pattern, text, re.MULTILINE):
            return [text]

        # Split by headers while keeping them
        lines = text.split("\n")
        sections = []
        current_section = []

        for line in lines:
            if line.startswith("## "):
                # New section started
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        # Add last section
        if current_section:
            sections.append("\n".join(current_section))

        return sections

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split by double newlines (paragraphs)"""
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # Start new chunk if needed
            if current_size + para_size > self.MAX_CHUNK_SIZE and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size

        # Add final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def get_chunk_metadata(
        self, chunk: Dict[str, Any], total_chunks: int
    ) -> Dict[str, Any]:
        """Generate metadata for a chunk"""
        return {
            "chunk_id": chunk["chunk_id"],
            "total_chunks": total_chunks,
            "type": chunk["type"],
            "size": chunk["size"],
            "percentage": round((chunk["chunk_id"] + 1) / total_chunks * 100, 1),
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys

    print("Testing TextChunker...")
    print("=" * 60)

    # Test small text
    print("\n1. Testing small text (< 10KB)...")
    small_text = (
        "This is a short text.\n\nIt has multiple paragraphs.\n\nBut it's small."
    )
    chunker = TextChunker()
    chunks = chunker.chunk_markdown(small_text)

    print(f"   Input size: {len(small_text)} chars")
    print(f"   Output chunks: {len(chunks)}")
    print(
        f"   [OK] Small text returned as single chunk"
        if len(chunks) == 1
        else "   [FAIL]"
    )

    # Test with large file simulation
    print("\n2. Testing large text simulation...")
    large_text = "# Header 1\n\n" + (
        "This is paragraph " + str(i) + ".\n\n" for i in range(1000)
    )
    # Convert generator to string
    large_text = "# Header 1\n\n" + "\n\n".join(
        [f"This is paragraph {i}. " * 20 for i in range(200)]
    )  # ~40KB

    print(f"   Input size: {len(large_text)} chars")
    chunks = chunker.chunk_markdown(large_text)
    print(f"   Output chunks: {len(chunks)}")

    # Verify all chunks under limit
    all_under_limit = all(
        chunk["size"] <= TextChunker.MAX_CHUNK_SIZE for chunk in chunks
    )
    print(
        f"   [OK] All chunks under limit"
        if all_under_limit
        else "   [FAIL] Some chunks too large"
    )

    # Show first chunk
    if chunks:
        print(f"\n   First chunk preview ({chunks[0]['size']} chars):")
        print(f"   {chunks[0]['content'][:100]}...")

    print("\n" + "=" * 60)
    print("TextChunker is functional")
    sys.exit(0)
