# LoreKeeper — Base de Conocimiento Conversacional

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ingresa PDFs, docs, código, URLs. Indexa con embeddings, y responde preguntas en lenguaje natural. RAG personal, todo local con sentence-transformers.

**Architecture:** Document ingest → chunking → embedding (sentence-transformers) → vector store (ChromaDB) → retrieval → LLM synthesis (Lilith local) → conversational interface. 100% local, sin APIs externas.

**Tech Stack:** Python 3.11+, ChromaDB, sentence-transformers, PyPDF2, python-docx, httpx+BS4, Lilith, Typer, Rich, Textual.

**Realm:** Svartalfheim/LoreKeeper/

---

## Task 1: Scaffold del proyecto

Files: `Svartalfheim/LoreKeeper/`, pyproject.toml con chromadb, sentence-transformers, PyPDF2, python-docx, lilith-core, typer, rich, textual.

**Commit:** `feat(lorekeeper): scaffold project`

---

## Task 2: Document ingestion pipeline

- PDF parser (PyPDF2)
- DOCX parser (python-docx)
- Markdown parser
- Plain text
- URL scraper (httpx + BS4)
- Code file parser (con permiso de sintaxis)

Chunking: sliding window con overlap (configurable, default 512 tokens, 50 tokens overlap).

**Commit:** `feat(lorekeeper): document ingestion pipeline`

---

## Task 3: Embedding y vector store

Usa sentence-transformers (`all-MiniLM-L6-v2`) para embeddings. ChromaDB como vector store local. Metadata: source, chunk_id, page, section.

**Commit:** `feat(lorekeeper): embedding and vector store with ChromaDB`

---

## Task 4: Retrieval engine

Búsqueda semántica con cosine similarity. Re-ranking opcional con cross-encoder. Soporta: pregunta → top-k chunks → contexto enriquecido.

**Commit:** `feat(lorekeeper): semantic retrieval engine`

---

## Task 5: LLM synthesis (Lilith integration)

Conecta con Lilith para generar respuestas. Prompt template: contexto + pregunta → respuesta con citations. Streaming de respuesta.

**Commit:** `feat(lorekeeper): Lilith LLM synthesis`

---

## Task 6: Conversational memory

Memoria de conversación: historial de Q&A, contexto de sesión, follow-up questions. SQLite para persistencia.

**Commit:** `feat(lorekeeper): conversational memory`

---

## Task 7: CLI completa

```bash
lorekeeper ingest ./docs/                    # ingesta directorio
lorekeeper ingest paper.pdf                  # ingesta PDF
lorekeeper ingest https://example.com/page   # ingesta URL
lorekeeper ask "What is transformer attention?"  # pregunta
lorekeeper ask "Explain more"                # follow-up
lorekeeper sessions                          # listar sesiones
lorekeeper stats                             # estadísticas de la DB
```

**Commit:** `feat(lorekeeper): complete CLI`

---

## Task 8: TUI conversacional

Interface Textual estilo chat: input de pregunta, respuesta con sources, historial, sidebar con collections.

**Commit:** `feat(lorekeeper): Textual conversational UI`

---

## Task 9: Tests + CI

**Commit:** `ci(lorekeeper): add test workflow`
