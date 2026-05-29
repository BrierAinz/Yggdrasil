# Plan 24: Yggdrasil Intelligence Evolution

> **Estatus**: Propuesta  
> **Fecha**: 2026-05-21  
> **Reino**: Cross-realm / Vanaheim (Agents) + Asgard (Core)  
> **Prioridad**: P0 (fundacional) → P3 (exploratorio)

---

## Resumen Ejecutivo

Hoja de ruta para evolucionar Yggdrasil de un ecosistema de agentes **reactivos** (comando → respuesta) a uno **proactivo e inteligente** — con memoria persistente, orquestación multi-agente con grafo de estados, percepción multimodal, y bucle de auto-mejora. El objetivo: que Lilith y sus agentes no solo respondan, sino que **piensen, remembered, anticipen y colaboren**.

**Estado actual**: Agentes Vanir (Adan/Eva/Odin) son stubs, orchestrator hace fallback a LLM directo, memoria es SQLite básica, sin RAG, sin grafo de estados, sin visión integrada.

---

## Fase 1: Cimientos de Inteligencia (P0 — Semana 1-2)

### 1.1 Memory Evolution — lilith-memory v2.0

**Reino**: Asgard/lilith-memory  
**Impacto**: CRÍTICO — sin memoria, no hay inteligencia

La memoria actual es un SQLite vector store básico. Necesitamos:

- **Capas de memoria**: Corto plazo (sesión), medio plazo (contexto reciente), largo plazo (permanent facts)
- **Auto-consolidación**: Al cerrar sesión, consolidar hechos temporales en permanentes
- **Búsqueda semántica**: Embeddings locales (sentence-transformers) para retrieval
- **Memory decay**: Hechos no accedidos en N días pierden relevancia gradualmente
- **User preferences store**: Preferencias explícitas + inferidas separadas de conocimiento general

```
lilith_memory/
├── backends/
│   ├── sqlite_backend.py      # Existente
│   ├── mem0_backend.py        # Nuevo — mem0ai integration
│   └── chroma_backend.py      # Nuevo — ChromaDB local
├── layers/
│   ├── working_memory.py      # Context window (volátil)
│   ├── episodic_memory.py     # Sesiones recientes (7d decay)
│   └── semantic_memory.py     # Hechos permanentes
├── consolidation.py           # Auto-summarize + fact extraction
└── preferences.py             # User preference learning
```

**Dependencias**: `pip install mem0ai chromadb sentence-transformers`

### 1.2 Persona Engine — Vanaheim/Core/persona v2

**Reino**: Vanaheim/Core  
**Impacto**: Alto — personalidad consistente entre sesiones

El módulo `persona/` existe pero es básico. Evolucionar a:

- **Persona templates**: JSON/YAML con rasgos, estilo de comunicación, dominios de conocimiento
- **Dynamic adaptation**: La persona evoluciona según interacciones (no estática)
- **Persona switching**: Múltiples personas en el mismo agente (Lilith formal vs casual vs técnica)
- **Consistency validation**: Checks antes de responder para mantener coherencia con la persona

```
persona/
├── templates/
│   ├── lilith_dark_fantasy.yaml   # Diosa oscura, runas, forja
│   ├── mimir_scholarly.yaml       # Erudito, citas, analítico
│   └── odin_wise.yaml             # Sabio, estratégico, directo
├── engine.py                       # Runtime persona injection
├── adaptation.py                   # Learn user patterns → adjust tone
└── validator.py                    # Consistency checks before response
```

### 1.3 Smart Tool Router — lilith-tools v2

**Reino**: Asgard/lilith-tools  
**Impacto**: Alto — el agente elige herramientas inteligentemente

Actualmente el tool registry es estático. Evolucionar a:

- **Semantic tool matching**: User query → embedding → closest tool (no keyword matching)
- **Tool chaining**: Composición automática de tools (ej: "genera imagen de Lilith" → ComfyUI + LoRA selector + prompt builder)
- **Failure recovery**: Si un tool falla, intentar alternativo automáticamente
- **Usage analytics**: Track qué tools se usan más, optimizar para esos paths

```python
class SmartToolRouter:
    """Route queries to the best tool using semantic similarity."""

    async def route(self, query: str, context: dict) -> ToolPlan:
        """Returns an execution plan, not just one tool."""

    async def chain(self, steps: list[str]) -> ChainResult:
        """Execute a sequence of tools in order."""

    async def recover(self, failed_tool: str, error: Exception) -> ToolPlan:
        """Find alternative when a tool fails."""
```

---

## Fase 2: Orquestación Inteligente (P1 — Semana 3-4)

### 2.1 LangGraph Agent Framework — Vanaheim/vanaheim-framework

**Reino**: Vanaheim  
**Impacto**: Alto — orquestación con estado, no solo LLM calls

langgraph 1.2.0 ya está en el radar. Integrar:

- **StateGraph**: Flujo del agente como grafo dirigido (no cadena rígida)
- **Conditional edges**: Decisión dinámica basada en contexto (no if/else hardcodeado)
- **Human-in-the-loop**: Checkpoints donde Lilith consulta al usuario antes de actuar
- **Parallel branches**: Múltiples agentes ejecutándose en paralelo

```
vanaheim_framework/
├── graphs/
│   ├── research_graph.py        # Mimir: buscar → analizar → sintetizar
│   ├── creative_graph.py         # ForgeMaster: idea → prototipo → test → release
│   └── conversation_graph.py     # Lilith: perceive → think → respond
├── nodes/
│   ├── classifier.py             # Intent classification
│   ├── retriever.py              # Knowledge retrieval
│   ├── executor.py               # Tool execution
│   ├── validator.py              # Response validation
│   └── memory_update.py          # Post-interaction learning
├── state/
│   ├── conversation_state.py
│   └── task_state.py
└── checkpoints/
    └── sqlite_checkpoint.py      # Persist graph state
```

### 2.2 Agent Council — Multi-Agent Orchestration

**Reino**: Vanaheim/Agents  
**Impacto**: Alto — agentes que colaboran, no solo funcionan independientes

Los agentes Vanir (Adan, Eva, Odin, Mimir, Shalltear) existen como stubs. Convertirlos en un **Council** funcional:

- **Odin**: Strategic planner — descompone tareas complejas en subtareas
- **Mimir**: Research specialist — búsqueda profunda con RAG
- **Eva**: Creative — generación de contenido, diseño, prompts
- **Adan**: Executor — implementa, escribe código, ejecuta tools
- **Lilith** (coordinadora): Recibe input, decide quién actúa, sintetiza respuestas

```python
class CouncilOrchestrator:
    """Orchestrate multiple agents for complex tasks."""

    async def delegate(self, task: str) -> CouncilResult:
        """Decompose task → assign to agents → synthesize."""

    async def collaborate(self, agents: list[str], prompt: str) -> CouncilResult:
        """Multiple agents work together on one problem."""

    async def review(self, result: str, reviewer: str) -> ReviewResult:
        """One agent reviews another's output."""
```

### 2.3 Circuit Breaker v2 — Resilience Patterns

**Reino**: Vanaheim/Core  
**Impacto**: Medio — sin esto, un agente roto rompe todo el sistema

El circuit_breaker.py existe. Ampliar con:

- **Rate limiting**: Por agente y por provider
- **Fallback chains**: Si Gemini falla → OpenAI → local Ollama
- **Circuit states**: Closed → Open → Half-Open (ya existe, verificar)
- **Health aggregation**: Dashboard de salud de todos los agentes

---

## Fase 3: Percepción y Conocimiento (P1 — Semana 5-6)

### 3.1 Mimir 2.0 — RAG con Knowledge Base

**Reino**: Midgard/Mimir  
**Impacto**: CRÍTICO — sin RAG, Lilith no puede razonar sobre su propio ecosistema

El plan-15-mimir existe como diseño. Implementar con mejoras:

- **Indexar todo Yggdrasil**: Docs, código, REGLAS, planes, quick-notes
- **Multi-modal retrieval**: Texto Y diagramas Y código
- **Auto-indexing**: Watcher que re-indexa cuando cambian archivos
- **Citation-linked responses**: Cada claim tiene fuente verificable
- **Integration con lilith-memory**: Hechos extraídos → memoria persistente

**Stack**: FastAPI + ChromaDB + sentence-transformers + LilithEngine

### 3.2 Vision Bridge — Agent ↔ ComfyUI

**Reino**: Asgard/lilith-bridge  
**Impacto**: Alto — Lilith puede ver y crear

Conectar Lilith directamente con ComfyUI para:

- **Image understanding**: Lilith recibe una imagen → la describe, analiza, compara
- **Image generation**: Lilith decide qué generar → construye el prompt → ejecuta pipeline
- **Iterative refinement**: "No me gusta el color" → Lilith ajusta parámetros → regenera
- **LoRA management**: Lilith sabe qué LoRAs tiene, cuándo usar cada uno

```python
class VisionBridge:
    """Bridge between Lilith agents and ComfyUI pipelines."""

    async def perceive(self, image_path: str) -> ImageDescription:
        """Understand an image — describe, analyze, compare."""

    async def create(self, spec: GenerationSpec) -> GenerationResult:
        """Generate an image from a specification."""

    async def refine(self, result: GenerationResult, feedback: str) -> GenerationResult:
        """Iteratively refine based on user feedback."""

    async def list_loras(self) -> list[LoRAInfo]:
        """List available LoRAs with trigger words and descriptions."""
```

### 3.3 Context-Aware Interactions

**Repo**: Asgard/lilith-core  
**Impacto**: Alto — respuestas que consideran contexto completo

- **Session context**: Qué se habló en los últimos N turnos
- **Project context**: En qué proyecto estamos trabajando, qué archivos tienen interés
- **Temporal context**: Hora del día, día de la semana, tiempo desde último mensaje
- **Emotional context**: Sentimiento detectado → ajustar tono de respuesta
- **Cross-session memory**: Lo que aprendió sobre el usuario en sesiones anteriores

---

## Fase 4: Auto-Mejora (P2 — Semana 7-8)

### 4.1 Reflective Agent Loop

**Reino**: Vanaheim  
**Impacto**: Medio-alto — el agente aprende de sus propios errores

Patrón: **Act → Reflect → Learn**

```
1. Agent ejecuta tarea
2. Agent evalúa resultado (self-reflection)
3. Si resultado insatisfactorio → identificar qué salió mal
4. Actualizar estrategia/tool preference/persona weights
5. Guardar learning en memoria semántica
6. Siguiente interacción usa el learning
```

Implementación:

```python
class ReflectiveLoop:
    """Post-interaction learning cycle."""

    async def reflect(self, interaction: Interaction, result: Result) -> Reflection:
        """Evaluate what went well, what didn't."""

    async def learn(self, reflection: Reflection) -> Learning:
        """Extract patterns from reflection → update memory/preferences."""

    async def apply(self, learning: Learning) -> None:
        """Adjust future behavior based on learnings."""
```

### 4.2 AutoForge Intelligence Upgrade

**Reino**: Muspelheim/ForgeMaster  
**Impacto**: Medio — de "ejecutar linters" a "entender el código"

El AutoForge actual (cronjob) ejecuta ruff, pytest, dead code. Evolucionar a:

- **Pattern learning**: Detectar patrones de errores recurrentes → sugerir fixes preventivos
- **Dependency analysis**: Detectar deps que se pueden actualizar sin romper nada
- **Test generation**: Escribir tests para código que no los tiene
- **Documentation drift**: Detectar docs desactualizadas vs código
- **Smart prioritization**: Fix lo que más impacta primero, no FIFO

### 4.3 Proactive Intelligence

**Reino**: Vanaheim  
**Impacto**: Medio-alto — Lilith inicia, no solo responde

- **Watch patterns**: Detectar que el usuario siempre hace X a hora Y → pre-preparar
- **Anomaly detection**: Notificar cambios inusuales (nuevo error, dep abandonado, disk llenándose)
- **Suggestion engine**: "Noté que actualizaste X, quieres que también actualice Y?"
- **Scheduled deep-tasks**: Cuando el usuario está AFK, ejecutar tareas de mantenimiento pesadas

---

## Fase 5: Ecosistema Expandido (P3 — Mes 3+)

### 5.1 MCP Server Yggdrasil — Exposing Intelligence

**Reino**: Midgard  
**Impacto**: Medio — otros agentes pueden usar Yggdrasil como backend

FastMCP v3.3.1 ya está en el stack. Crear un MCP server que exponga:

- `yggdrasil://agents/list` — listar agentes disponibles
- `yggdrasil://memory/search` — buscar en la knowledge base
- `yggdrasil://forge/generate` — generando contenido
- `yggdrasil://comfyui/execute` — ejecutar pipelines de imagen
- `yggdrasil://health/check` — estado del ecosistema

Esto permitiría que Hermes, Claude, u otros agentes se conecten al ecosistema Yggdrasil como herramienta.

### 5.2 pydantic-ai Agent Bridge

**Reino**: Asgard/lilith-orchestrator  
**Impacto**: Medio — modernizar el orquestador

pydantic-ai v1.99.0 ofrece:

- **Structured output**: Respuestas tipadas, no strings libres
- **Model-agnostic**: Cambiar de modelo sin cambiar código
- **Built-in validation**: Pydantic models como contrato de respuesta
- **Dependency injection**: Más limpio que el sistema actual

Migrar LilithEngine de su implementación custom a pydantic-ai Agents.

### 5.3 bytedance/Lance Multimodal Perception

**Reino**: Vanaheim  
**Impacto**: Exploratorio — si Lance cumple, agentes con "ojos"

Lance (⭐400+ y creciendo) es un modelo multimodal 3B que puede:
- Entender imágenes Y texto conjuntamente
- Razonar sobre screenshots, diagramas, UI
- Potencialmente correr local en RTX 3060 (3B参数)

Evaluación: Si corre bien en 12GB VRAM → integrar como perception layer de los agentes.

---

## Arquitectura Post-Inteligencia

```
                        ┌─────────────────────────────────────────┐
                        │            LILITH (Coordinadora)        │
                        │  ┌───────────────────────────────────┐ │
                        │  │   LangGraph StateGraph             │ │
                        │  │   ├── Perceive (Vision + Text)     │ │
                        │  │   ├── Think (RAG + Memory)          │ │
                        │  │   ├── Plan (Task Decomposition)     │ │
                        │  │   ├── Act (Tool Execution)          │ │
                        │  │   └── Reflect (Self-Improvement)    │ │
                        │  └───────────────────────────────────┘ │
                        └───────────┬─────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────────┐
              │                      │                         │
   ┌──────────▼──────────┐ ┌───────▼────────┐ ┌──────────────▼──────────┐
   │    COUNCIL           │ │   MEMORY v2    │ │   TOOLS v2              │
   │  ┌───────┐ ┌──────┐ │ │  ┌───────────┐ │ │  ┌──────────────────┐  │
   │  │ Odin  │ │Mimir │ │ │  │ Semantic  │ │ │  │ Smart Router      │  │
   │  │Plan   │ │RAG   │ │ │  │ Episodic  │ │ │  │ Vision Bridge     │  │
   │  ├───────┤ ├──────┤ │ │  │ Working   │ │ │  │ MCP Server        │  │
   │  │ Eva   │ │ Adán │ │ │  │ Preference│ │ │  │ ComfyUI Bridge    │  │
   │  │Create │ │Exec  │ │ │  └───────────┘ │ │  │ pydantic-ai       │  │
   │  └───────┘ └──────┘ │ └────────────────┘ │ └──────────────────────┘  │
   └─────────────────────┘                     └───────────────────────────┘
              │                                           │
   ┌──────────▼───────────────────────────────────────────▼──────────┐
   │                    SVARTALFHEIM (Knowledge)                      │
   │  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────────────┐ │
   │  │ ChromaDB  │ │ Khoj    │ │ Docs     │ │ Auto-Indexed       │ │
   │  │ Vectors   │ │ Search  │ │ Wiki     │ │ Code + Plans       │ │
   │  └──────────┘ └─────────┘ └──────────┘ └────────────────────┘ │
   └─────────────────────────────────────────────────────────────────┘
```

---

## Tabla de Prioridades

| #  | Feature                              | Prioridad | Esfuerzo | Impacto | Dependencia           | Fase |
|----|--------------------------------------|-----------|----------|---------|-----------------------|------|
| 1  | Memory v2 (capas + mem0)            | P0        | 3-4d     | Crítico | Ninguna              | 1    |
| 2  | Persona Engine v2                    | P0        | 2-3d     | Alto    | Memory v2            | 1    |
| 3  | Smart Tool Router                    | P0        | 2-3d     | Alto    | lilith-tools existente| 1    |
| 4  | LangGraph Agent Framework            | P1        | 5-7d     | Alto    | vanaheim-framework   | 2    |
| 5  | Agent Council (multi-agent)          | P1        | 4-5d     | Alto    | LangGraph             | 2    |
| 6  | Circuit Breaker v2                   | P1        | 1-2d     | Medio   | circuit_breaker.py   | 2    |
| 7  | Mimir 2.0 (RAG)                      | P1        | 5-7d     | Crítico | Memory v2 + ChromaDB  | 3    |
| 8  | Vision Bridge (ComfyUI)              | P1        | 4-5d     | Alto    | lilith-bridge         | 3    |
| 9  | Context-Aware Interactions           | P1        | 2-3d     | Alto    | Memory v2 + Persona   | 3    |
| 10 | Reflective Agent Loop                | P2        | 3-4d     | Medio   | Memory v2             | 4    |
| 11 | AutoForge Intelligence Upgrade      | P2        | 2-3d     | Medio   | ForgeMaster v1.0      | 4    |
| 12 | Proactive Intelligence               | P2        | 3-4d     | Medio   | Reflective Loop       | 4    |
| 13 | MCP Server Yggdrasil                 | P3        | 3-5d     | Medio   | FastMCP 3.3.1         | 5    |
| 14 | pydantic-ai Bridge                   | P3        | 3-4d     | Medio   | pydantic-ai v1.99     | 5    |
| 15 | Lance Multimodal Perception          | P3        | 2-3d     | Explor  | bytedance/Lance       | 5    |

---

## KPIs de Éxito

1. **Memoria persistente** — Lilith recuerda preferencias y hechos entre sesiones sin intrusión manual
2. **Orquestación multi-agente** — Al menos 3 agentes (Odin + Mimir + Eva) colaborando en tareas reales
3. **RAG funcional** — Mimir responde preguntas sobre Yggdrasil con citations verificables
4. **Visión integrada** — Lilith puede ver imágenes y generar con ComfyUI sin intervención manual
5. **Auto-mejora** — El sistema aprende de errores y ajusta comportamiento sin hardcoding
6. **Zero-downtime resilience** — Circuit breaker + fallback chains = ningún agente cae sin recovery
7. **Tiempo de respuesta** — Tool routing semántico < 200ms, end-to-end < 3s para queries simples

---

## Criterios de Decisión — ¿Qué construir primero?

1. **Memory v2** → Todo lo demás depende de esto. Sin memoria, no hay personalidad ni aprendizaje.
2. **Smart Tool Router** → Impacto inmediato en velocidad y calidad de respuesta.
3. **LangGraph + Council** → Una vez que la memoria y tools son inteligentes, los agentes necesitan orquestación real.
4. **Mimir RAG** → Con memoria y orquestación, Mimir se vuelve el knowledge backbone.
5. **Vision Bridge** → Diferenciador visual. Yggdrasil = diosa oscura que tambien puede VER.

---

*"La forja más poderosa no es la que produce más hierro, sino la que recuerda cada golpe."*
*— Crónicas de Svartalfheim*