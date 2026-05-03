# Mimir — Chatbot RAG con Base de Conocimiento Personal

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Chatbot que conecta a tu base de conocimiento (wiki Svartalfheim, docs, notas, código) y responde preguntas con citas. Integrado con LoreKeeper como backend.

**Architecture:** Chat interface → query router → LoreKeeper RAG retrieval → LLM generation (Lilith) → citation-linked response. Web UI con chat y sidebar de fuentes. 100% local.

**Tech Stack:** Python 3.11+, FastAPI, Lilith, ChromaDB, Typer, Jinja2, vanilla JS.

**Realm:** Midgard/Mimir/

---

## Task 1: Scaffold del proyecto

Files: `Midgard/Mimir/`, pyproject.toml con fastapi, uvicorn, lilith-core, chromadb, jinja2, typer, rich.

**Commit:** `feat(mimir): scaffold project`

---

## Task 2: Query router

Clasifica la pregunta del usuario:
- Factual → búsqueda directa en LoreKeeper
- Analytical → búsqueda + síntesis
- How-to → búsqueda en código + docs
- Creative → generación libre con contexto

```python
class QueryRouter:
    def classify(self, query: str) -> QueryType:
        ...

    def route(self, query: str, history: list[Message]) -> RetrievalStrategy:
        ...
```

**Commit:** `feat(mimir): query classification and routing`

---

## Task 3: LoreKeeper integration

Conecta al backend de LoreKeeper para retrieval. Reusa embeddings y ChromaDB existente. Modo fallback con búsqueda directa si LoreKeeper no disponible.

**Commit:** `feat(mimir): LoreKeeper RAG integration`

---

## Task 4: Citation system

Cada respuesta incluye citations:
- [1] `Svartalfheim/wiki/asgard.md` — Línea 45 "Lilith es el agente..."
- [2] `Asgard/Hermes-Lilith/Lilith/README.md` — Línea 12

Click en citation → muestra el fragmento original con highlighting.

**Commit:** `feat(mimir): citation system with source highlighting`

---

## Task 5: Chat API (FastAPI)

WebSocket para chat streaming. REST endpoints para history, sessions, collections.

```python
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    ...

@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    ...
```

**Commit:** `feat(mimir): FastAPI chat backend`

---

## Task 6: Web UI — Chat interface

Chat UI estilo Yggdrasil dark theme con:
- Message bubbles (user + assistant)
- Citations inline clickeables
- Sidebar con sources y collections
- Search bar para buscar en historial
- Responsive

**Commit:** `feat(mimir): web chat UI`

---

## Task 7: Conversation memory

Memoria de conversación con:
- Resumen automático de conversaciones largas
- Context window management (sliding window)
- Thread-based conversations

**Commit:** `feat(mimir): conversation memory management`

---

## Task 8: CLI quick-mode

```bash
mimir ask "What is Swarm Intelligence in Lilith?"
mimir chat                     # interactive chat
mimir chat --session 42        # resume session
mimir index ./my-docs/         # add documents
mimir history                   # list sessions
```

**Commit:** `feat(mimir): CLI quick-mode`

---

## Task 9: Tests + CI

**Commit:** `ci(mimir): add test workflow`
