---
title: Glosario del Ecosistema Yggdrasil
last_updated: 2026-05-02
---

# 📖 Glosario del Ecosistema Yggdrasil

> *Las runas hablan — pero primero hay que aprender su lengua.*

## 🌳 Términos del Ecosistema

| Término | Definición |
|---------|-----------|
| **Yggdrasil** | El árbol cósmico que sostiene los 9 reinos. En nuestro caso, el monorepo que contiene todo el ecosistema. |
| **Reino** | Cada uno de los 9 dominios del ecosistema (Asgard, Vanaheim, etc.). Funciona como namespace organizacional. |
| **Bifröst** | Puente arcoíris entre reinos. Análogamente, las APIs y conexiones entre módulos. |
| **Völundr** | El forjador legendario. Nombre del arquitecto/desarrollador principal del ecosistema. |
| **Hermes** | Mensajero de los dioses. El agente externo que communicate con Lilith. |
| **Lilith** | Agente CLI con memoria persistente. El producto principal de Asgard. |

## 🏗️ Términos Técnicos

| Término | Definición |
|---------|-----------|
| **Orchestrator** | Loop principal de conversación de Lilith. Despacha tools, maneja memoria y coordina providers. |
| **LLM Provider** | Backend de language model (LM Studio local, Kimi remoto, etc.). Interfaz OpenAI-compatible. |
| **Circuit Breaker** | Patrón de resilience que bloquea llamadas a un provider tras N fallos consecutivos. Estados: CLOSED, OPEN, HALF_OPEN. |
| **Retry con Backoff** | Reintento automático con espera exponencial. Solo para errores transitorios (429, 5xx, timeouts). |
| **Session Store** | Persistencia de sesiones con embeddings, FTS5 y crash recovery en SQLite. |
| **Skill** | Template YAML+MD con triggers que activa comportamiento especializado en Lilith. |
| **Skill Parser** | Parser que lee archivos de skills con YAML frontmatter y Markdown body. |
| **Swarm** | Sistema de multi-agente donde múltiples workers cooperan en subtareas. |
| **SwarmAgent** | Worker individual del swarm con estados (IDLE, WORKING, REVIEWING, COMPLETE, ERROR). |
| **MessageBus** | Sistema de mensajería pub/sub para comunicación entre agentes del swarm. |
| **MCP** | Model Context Protocol — especificación JSON-RPC 2.0 para descubrir y ejecutar tools externas. |
| **MCPManager** | Gestor de múltiples MCP clients en Lilith. |
| **DynamicToolRegistry** | Registry de tools descubiertas via MCP que se integran automáticamente. |
| **BackgroundConsolidator** | Thread daemon que mergea memoria similar (>0.85 cosine), promueve hechos frecuentes y hace decay de relaciones débiles. |
| **EmbeddingModel** | Modelo de sentence-transformers local para generar vectores de embeddings. |
| **MemoryGraph** | Grafo de conocimiento con nodos, edges y pesos. Soporta decay temporal. |
| **Memory RAG** | Memory Retrieval-Augmented Generation — recuperación de contexto relevante antes de generar respuesta. |

## 🔧 Términos de Config

| Término | Definición |
|---------|-----------|
| **config.toml** | Archivo de configuración unificada en `~/.lilith/config.toml`. Prioridad: TOML > env vars > defaults. |
| **TOML** | Tom's Obvious Minimal Language. Formato de config usado por PEP 680. |
| **Frontmatter** | Bloque YAML al inicio de archivos Markdown que define metadata (nombre, triggers, etc.). |
| **trigger_regex** | Patrón regex en skills que activa el skill cuando matchea el input del usuario. |
| **trigger_intent** | Categoría semántica del skill (coding, writing, analysis, etc.). |
| **failure_threshold** | Número de fallos consecutivos antes de abrir el circuit breaker (default: 3). |
| **recovery_timeout** | Segundos antes de transicionar de OPEN a HALF_OPEN (default: 60). |

## 🏛️ Términos Mitológicos → Técnicos

| Mitología | Técnico |
|-----------|---------|
| Asgard | Core tech (Hermes-Lilith, orquestador, providers) |
| Vanaheim | Agentes de IA (bots Discord/Telegram) |
| Alfheim | Prototipos de UI (dashboards, Electron) |
| Svartalfheim | Documentación y conocimiento (wiki, ADRs, runbooks) |
| Muspelheim | Desarrollo activo / WIP (sprints ≤2 semanas) |
| Niflheim | Recursos (modelos LLM, datasets, assets) |
| Helheim | Archivo legacy (código obsoleto, cuarentena) |
| Jotunheim | Proyectos masivos (>1 mes de estimación) |
| Midgard | Aplicaciones personales (productividad, calendario) |
| Norns | Thread daemon de consolidación de memoria |
| Runas | Docstrings y comentarios con sabor dark fantasy |
| Bifröst | API endpoints que conectan reinos |
| Fenris | Circuit breaker abierto (fallos acumulados) |
| Well of Souls | SessionStore con persistencia de conversaciones |
| Mimir | Sistema de memoria híbrida (vector + graph + FTS5) |

## 📐 Abreviaturas

| Abreviatura | Significado |
|-------------|-------------|
| ADR | Architecture Decision Record |
| FTS5 | SQLite Full-Text Search 5 |
| MCP | Model Context Protocol |
| LLM | Large Language Model |
| RAG | Retrieval-Augmented Generation |
| WAL | Write-Ahead Logging (SQLite) |
| WIP | Work In Progress |
| CLI | Command Line Interface |
