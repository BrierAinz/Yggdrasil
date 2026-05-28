# Sistema RAG - Archivero de Svartalfheim

> **Versión:** 1.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Yggdrasil/Svartalfheim/`

---

## Visión General

El **Sistema RAG (Retrieval-Augmented Generation)** con el **Agente Archivero** permite consultar semánticamente toda la documentación del ecosistema Lilith (~1.1 MB, 99 documentos).

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────────┐
│                     SISTEMA RAG ARCHIVERO                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📚 KNOWLEDGE BASE (Svartalfheim)                                │
│  ├── Lilith_Docs/              # Docs actuales (00-17)          │
│  ├── Lilith_Legacy/            # Docs históricos (80 archivos)  │
│  └── index.json                # Metadata de documentos         │
│                                                                  │
│  🔧 INDEXACIÓN (Scripts/)                                        │
│  ├── generate_docs_metadata.py # Extrae metadata                │
│  ├── index_docs_to_muninn.py   # Indexa a MuninnDB              │
│  └── ask_archivero.py          # CLI de consulta                │
│                                                                  │
│  🤖 AGENTE ARCHIVERO (Lilith/Core/Backend/)                      │
│  ├── core/agents/archivero_agent.py    # Agente especialista    │
│  ├── core/tools_v3/archivero_tool.py   # Tool delegate_*        │
│  └── api/docs_api.py                   # API REST               │
│                                                                  │
│  💾 MUNINNDB (Vault: "docs")                                     │
│  ├── ~1,200+ chunks indexados (1500 tokens c/u)                 │
│  ├── Embeddings semánticos                                      │
│  └── Búsqueda por activación cognitiva                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura del Sistema

### 1. Chunking Estratégico

**Configuración:**
- **Chunk size:** 1,500 tokens
- **Overlap:** 300 tokens
- **Estrategia:** División por secciones (`##`) con cortes inteligentes

### 2. Indexación en MuninnDB

**Vault:** `docs`

### 3. Agente Archivero

**Modelo:** Kimi (262k context)

---

## Uso

### Discord

```
/docs ¿Cómo funciona el DAG Executor?
```

### CLI

```bash
python Scripts/ask_archivero.py "¿Qué es MuninnDB?"
```

### API REST

```bash
POST /api/docs/query
{
  "question": "¿Cómo funciona el DAG Executor?"
}
```

---

*Documentación completa en desarrollo*
