#!/usr/bin/env python3
"""
Indexador standalone de documentación a MuninnDB.
No depende de imports de Lilith Backend.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import httpx


# Configuración
YGG_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = YGG_ROOT / "Svartalfheim" / "Knowledge_Base"
MUNINN_URL = "http://127.0.0.1:8475/api"
MUNINN_TOKEN = ""  # Se carga de config
VAULT_NAME = "default"  # Fallback: usar 'default' si 'docs' no está configurado

# Chunking config
CHUNK_SIZE_TOKENS = 1500
OVERLAP_TOKENS = 300
CHARS_PER_TOKEN = 4
CHUNK_CHARS = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN


def load_config():
    """Carga config de Muninn desde Lilith."""
    global MUNINN_URL, MUNINN_TOKEN
    config_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
    if config_path.exists():
        with config_path.open() as f:
            cfg = json.load(f)
            MUNINN_URL = cfg.get("url", MUNINN_URL).rstrip("/") + "/api"
            token = cfg.get("muninn_token") or cfg.get("token") or ""
            if token:
                MUNINN_TOKEN = token.strip()


def chunk_markdown(content: str, doc_metadata: dict) -> list[dict]:
    """Divide markdown en chunks estratégicos."""
    chunks = []
    doc_id = doc_metadata.get("filename", "unknown")

    # Dividir por secciones (##)
    sections = re.split(r"\n(?=## )", content)

    for section_idx, section in enumerate(sections):
        section_lines = section.split("\n")
        section_title = "Introducción"

        if section_lines and section_lines[0].startswith("##"):
            section_title = section_lines[0].strip("#").strip()
            section_content = "\n".join(section_lines[1:])
        else:
            section_content = section

        section_content = section_content.strip()
        if not section_content:
            continue

        # Si cabe en un chunk
        if len(section_content) <= CHUNK_CHARS:
            chunk_id = f"{doc_id}_s{section_idx}_c0"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "content": section_content,
                    "section": section_title,
                    "subsection": "",
                    "doc_id": doc_id,
                    "metadata": doc_metadata,
                }
            )
        else:
            # Dividir en sub-chunks
            start = 0
            text_len = len(section_content)
            sub_idx = 0

            while start < text_len:
                end = start + CHUNK_CHARS

                if end >= text_len:
                    sub_content = section_content[start:].strip()
                else:
                    # Buscar corte inteligente
                    search_end = min(end, text_len)
                    search_start = max(start + CHUNK_CHARS - 200, start)
                    paragraph_end = section_content.rfind("\n\n", search_start, search_end)

                    if paragraph_end != -1 and paragraph_end > start + 100:
                        cutoff = paragraph_end
                    else:
                        sentence_end = section_content.rfind(".\n", search_start, search_end)
                        cutoff = (
                            sentence_end + 1
                            if sentence_end != -1 and sentence_end > start + 100
                            else search_end
                        )

                    sub_content = section_content[start:cutoff].strip()

                chunk_id = f"{doc_id}_s{section_idx}_c{sub_idx}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "content": sub_content,
                        "section": section_title,
                        "subsection": f"Parte {sub_idx + 1}",
                        "doc_id": doc_id,
                        "metadata": doc_metadata,
                    }
                )

                start = max(end - OVERLAP_CHARS, start + 100)
                sub_idx += 1

                if end >= text_len:
                    break

    return chunks


async def store_chunk(client: httpx.AsyncClient, chunk: dict) -> bool:
    """Almacena un chunk en MuninnDB."""
    concept = f"{chunk['doc_id']}:{chunk['section']}"
    if chunk["subsection"]:
        concept += f":{chunk['subsection']}"

    tags = [
        f"doc:{chunk['doc_id']}",
        f"section:{chunk['section']}",
        "type:documentation",
    ]

    path_lower = chunk["metadata"].get("path", "").lower()
    if "lilith_docs" in path_lower:
        tags.append("category:current")
    elif "el_inicio_del_todo" in path_lower:
        tags.append("category:historical")
    elif "legacy" in path_lower:
        tags.append("category:legacy")

    payload = {
        "vault": VAULT_NAME,
        "concept": concept[:200],
        "content": chunk["content"][:2000],
        "tags": tags,
        "metadata": {
            "chunk_id": chunk["chunk_id"],
            "doc_title": chunk["metadata"].get("title", chunk["doc_id"]),
            "section": chunk["section"],
        },
    }

    headers = {}
    if MUNINN_TOKEN:
        headers["Authorization"] = f"Bearer {MUNINN_TOKEN}"

    try:
        r = await client.post(f"{MUNINN_URL}/engrams", json=payload, headers=headers)
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


async def index_document(client: httpx.AsyncClient, doc_path: Path, doc_meta: dict) -> int:
    """Indexa un documento completo."""
    try:
        content = doc_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [ERROR] Leyendo {doc_path}: {e}")
        return 0

    chunks = chunk_markdown(content, doc_meta)

    for chunk in chunks:
        await store_chunk(client, chunk)

    return len(chunks)


async def main():
    """Indexa toda la Knowledge Base."""
    load_config()

    index_file = KB_ROOT / "index.json"
    if not index_file.exists():
        print("[ERROR] No se encontró index.json")
        print("[INFO] Ejecuta primero: python Scripts/generate_docs_metadata.py")
        return

    with index_file.open(encoding="utf-8") as f:
        index_data = json.load(f)

    docs = index_data.get("documents", [])

    print(f"[INDEX] Indexando {len(docs)} documentos a MuninnDB")
    print(f"[INDEX] Vault: {VAULT_NAME}")
    print(f"[INDEX] URL: {MUNINN_URL}")
    print(f"[INDEX] Chunk: {CHUNK_SIZE_TOKENS} tokens / {OVERLAP_TOKENS} overlap\n")

    headers = {}
    if MUNINN_TOKEN:
        headers["Authorization"] = f"Bearer {MUNINN_TOKEN}"

    total_chunks = 0

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Verificar conexión
        try:
            r = await client.get(f"{MUNINN_URL}/health")
            if r.status_code != 200:
                print(f"[WARNING] MuninnDB no responde correctamente: {r.status_code}")
        except Exception as e:
            print(f"[ERROR] No se puede conectar a MuninnDB: {e}")
            print("[INFO] Asegúrate de que MuninnDB esté corriendo en 127.0.0.1:8475")
            return

        # Indexar documentos
        for i, doc_meta in enumerate(docs, 1):
            doc_path = KB_ROOT / doc_meta["path"]

            if not doc_path.exists():
                print(f"  [{i}/{len(docs)}] SKIP {doc_meta['filename']}")
                continue

            chunk_count = await index_document(client, doc_path, doc_meta)
            total_chunks += chunk_count
            print(f"  [{i}/{len(docs)}] {doc_meta['filename']} -> {chunk_count} chunks")

    print("\n[SUCCESS] Indexacion completa:")
    print(f"  Documentos: {len(docs)}")
    print(f"  Total chunks: {total_chunks}")

    # Guardar stats
    stats = {
        "indexed_at": datetime.now().isoformat(),
        "documents": len(docs),
        "chunks": total_chunks,
        "vault": VAULT_NAME,
    }
    with (KB_ROOT / "index_stats.json").open("w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
