# HORIZONTE LILITH 4.0

**Propósito:** Mapa de visión para la siguiente gran evolución, una vez cerrada y validada la Misión 3.0. Ideas y direcciones discutidas (agentes de dominio, DAGs, memoria en grafos, dashboard); no son compromisos de implementación, sino base para futuras decisiones.

**Secuencia:** 3.8 → 3.9 → [opcional] MuninnDB → **4.0 Fase 0 (Matching Learning)** → Fases 1–3 (AgentRegistry, delegador, inter-agente). Ver **[MISION_LILITH_4.0.md](MISION_LILITH_4.0.md)**.

---

## 0. Visión: de Cerebro Único a Ecosistema de Agentes Autónomos

### Estado actual: modelo centralizado con herramientas remotas

```
┌─────────────────────────────────────────────┐
│ LILITH (Orquestador + Cerebro Local)         │
│ - Decide el intent                           │
│ - Elige la tool (local o agente)             │
│ - Usa su propia memoria y contexto           │
└───────┬───────────────┬─────────────────────┘
        │               │
        ▼               ▼
┌─────────────┐ ┌──────────────────────┐
│ HERRAMIENTAS │ │    AGENTES (APIs)    │
│ (locales)   │ │ (Eva, Adán, Lucifer) │
│ read_file   │ │ Son "tools" que      │
│ edit_file   │ │ Lilith invoca para   │
│ ...         │ │ generar lenguaje.    │
└─────────────┘ └──────────────────────┘
```

- **Lilith** es el cerebro: piensa, elige y recuerda.
- **Agentes** son "músculos": modelos de lenguaje a los que Lilith llama para tareas que no hace localmente.
- **Herramientas** son extensiones de Lilith (read_file, edit_file, etc.).
- **Limitación:** Los agentes no tienen autonomía: no tienen memoria propia, no colaboran entre sí sin que Lilith medie, no tienen herramientas especializadas propias.

### Futuro: ecosistema de agentes autónomos

Lilith pasa de ser el cerebro que lo hace todo a **la mente directora de un consejo de especialistas**.

```
┌───────────────────────────────────────────────────────────────────┐
│ LILITH (Orquestadora / Mente Directora)                            │
│ - Recibe la intención del usuario.                                 │
│ - Descompone el objetivo en subtareas.                             │
│ - Decide qué agentes o equipos son los adecuados.                 │
│ - Coordina la comunicación entre ellos.                            │
└──────────────────┬──────────────────────────────┬─────────────────┘
                   │                              │
                   ▼                              ▼
┌─────────────────────────┐        ┌──────────────────────────────┐
│ AGENTE DE CÓDIGO (ADÁN)  │        │   AGENTE DE ANÁLISIS (EVA)   │
│ - Refactor, tests,       │        │ - Auditoría, documentación,  │
│   optimización.          │        │   insights.                   │
│ - Memoria: proyectos,    │        │ - Memoria: decisiones de      │
│   patrones.              │        │   arquitectura, estándares.  │
│ - Herramientas:          │        │ - Herramientas:              │
│   analyze_code,          │        │   security_audit,             │
│   run_tests, git_diff    │        │   generate_docs, search_*    │
└─────────────────────────┘        └──────────────────────────────┘
                   │                              │
                   └──────────┬───────────────────┘
                              ▼
         Colaboración: Eva audita → Lilith pasa resultado a Adán → Adán refactoriza.
```

- **Lilith** = directora de orquesta: interpreta la partitura (tu petición) y señala a cada agente cuándo y qué hacer.
- **Agentes** = entidades autónomas: identidad propia, memoria especializada, conjunto de herramientas propias.
- **Herramientas** = especializadas por agente (analyze_code es de Adán; security_audit es de Eva).

**Ventajas:** escalabilidad (nuevo agente = registro en directorio), especialización real, colaboración poderosa, claridad arquitectónica.

### Plan de implementación (4.0 / 4.1)

| Fase | Descripción |
|------|-------------|
| **Fase 1 — Registro de agentes** | `AgentRegistry` (análogo a ToolRegistry). Cada agente es una clase `Agent` con memoria y tools propias. Ej.: `class AdanAgent(Agent): self.memory = ...; self.tools = [AnalyzeCodeTool(), RunTestsTool()]`. |
| **Fase 2 — Delegador universal** | El Planner no elige `delegate_eva` / `delegate_adan`; elige un agente: `agent = agent_registry.get("adan")` y llama `agent.execute(task="...", context=...)`. |
| **Fase 3 — Comunicación inter-agente** | Lilith actúa como bus de mensajes: recibe el informe de Eva y lo pasa como contexto a Adán. A futuro, agentes podrían comunicarse entre sí vía Lilith. |

---

## 1. Agentes de dominio específico

**Idea:** En lugar de (o además de) agentes genéricos (Eva, Adán, Lucifer), definir agentes locales especializados y ligeros. En el **ecosistema 4.0** (sección 0), cada agente tendrá su propia memoria y herramientas; aquí se describen bloques que pueden evolucionar hacia ese modelo.

| Ejemplo | Descripción | Ventaja |
|--------|-------------|---------|
| **PythonRefactorAgent** | Basado en AST; refactors seguros (renombrar, extraer función) sin LLM | Rápido, barato, determinista |
| **DocumentationAgent** | Genera docs desde código (docstrings, README) usando plantillas + LLM local opcional | Menor dependencia de APIs |
| **TestGeneratorAgent** | Análisis de código + generación de tests con reglas fijas y/o modelo pequeño | Mejor control y repetibilidad |

**Encaje con 3.0:** El ToolRegistryV3 ya permite registrar cualquier tool. Un “agente de dominio” es una tool que encapsula lógica especializada (local o con API dedicada).

---

## 2. Ejecución paralela y planificación compleja (DAGs)

**Idea:** El Orchestrator actual es **secuencial**. Evolucionar a planes que sean **grafos de ejecución (DAGs)**: algunos pasos pueden ejecutarse en paralelo y otros dependen de resultados previos.

- **Planner:** En lugar de `List[Step]`, devolver un **grafo** (nodos = steps, aristas = dependencias).
- **Orchestrator:** Ejecutor que resuelve el DAG (orden topológico, paralelismo donde no hay dependencias).
- **Beneficio:** Tareas como “analizar estos 3 archivos y luego resumir” se pueden acelerar ejecutando los 3 análisis en paralelo.

**Encaje con 3.0:** Step y execute_plan siguen siendo la interfaz; la extensión es interna (representación del plan + ejecutor DAG).

---

## 3. Memoria híbrida avanzada (grafo)

**Idea:** Para la memoria semántica, explorar una **base de datos de grafos** (p. ej. Neo4j) o un modelo de datos en grafo en disco, para soportar consultas relacionales más ricas.

- Ejemplos de consultas: “¿Qué decisiones tomamos sobre el módulo X que afectaron al rendimiento de Y?”, “¿En qué tareas hemos usado delegate_adan en el último mes?”.
- **Encaje con 3.0:** MemoryManager ya es una fachada; una implementación “semantic_store_v2” que use un backend en grafo mantendría el contrato `search_semantic` y opcionalmente nuevos métodos (consultas por relación, tiempo, etc.).

---

## 4. Interfaz de usuario para la memoria (dashboard)

**Idea:** Dashboard (web o CLI) para:

- Explorar la **memoria semántica** (perfil, proyectos, decisiones).
- Ver **patrones aprendidos** (procedural) y logs recientes (episódica).
- Revisar y **aprobar/rechazar** sugerencias de `self_improve` antes de que se apliquen a reglas o configuración.

**Encaje con 3.0:** Las APIs de memoria y los stores ya exponen datos; el dashboard sería una capa de presentación y flujos de aprobación sobre esos datos.

---

## 5. Plan de auto-mejora (Lilith)

Roadmap formal derivado de la visión de Lilith sobre sus propias mejoras: arquitectura cognitiva (modos, stack de atención, metacognición), memoria en capas, herramientas (sandbox, procesos, pipeline imágenes), personalidad (modos por comando), seguridad (lista blanca, escalación, auditoría), interfaz (VS Code, voz). Priorización y referencias cruzadas: **[PLAN_AUTOMEJORA_LILITH.md](PLAN_AUTOMEJORA_LILITH.md)**.

---

## 6. Resumen de direcciones

| Dirección | Objetivo | Relación con visión (sección 0) |
|-----------|----------|----------------------------------|
| Ecosistema de agentes | AgentRegistry, agentes con memoria y tools propias, colaboración vía Lilith | Núcleo 4.0: Fases 1–3 |
| Agentes de dominio | Especialización local (refactor, docs, tests) | Bloques que pasan a ser agentes autónomos |
| DAGs / paralelo | Planes complejos y ejecución más rápida | Coordinación de subtareas entre agentes |
| Memoria en grafo | Consultas relacionales sobre decisiones y uso | Memoria por agente + visión global |
| Dashboard memoria | Visualización y control de memoria y aprendizaje | APIs y stores existentes |
| **Minería y refinería web** | Extracción, limpieza, filtrado y estructuración de datos desde la web → memoria | Agentes de dominio (WebScraper, ContentCleaner, QualityFilter, DataStructurer). Ver **[VISION_MINERIA_REFINERIA_WEB.md](VISION_MINERIA_REFINERIA_WEB.md)**. |

---

## 7. Minería y refinería web (visión extendida)

Lilith como **refinería de datos**: extraer texto crudo de la web → limpiar → validar → estructurar → indexar y guardar en memoria. Agentes de dominio: WebScraperAgent, ContentCleanerAgent, QualityFilterAgent, DataStructurerAgent; fuentes por nivel de calidad (alta/media/baja); flujo encadenado (scraper → cleaner → filter → structurer → store). Implementación recomendada por fases: empezar por un WebScraperAgent básico sobre una fuente de alta calidad, luego añadir cleaner, filter y structurer, y escalar con cola de tareas y (opcional) base de grafos. Detalle completo: **[VISION_MINERIA_REFINERIA_WEB.md](VISION_MINERIA_REFINERIA_WEB.md)**.

---

*Documento de horizonte post–3.0. Priorización y diseño detallado según necesidad del proyecto. El legado 3.0 queda documentado en `MISION_LILITH_3.0_COMPLETO.md`.*
