# MISIÓN: Lilith v3.0 — Local, Tools integradas y Agentes

**Visión:** Lilith deja de depender de “skills con comandos” y se convierte en un **núcleo local** que aprende, tiene **herramientas integradas** (tools) y **ordena a agentes** vía APIs. Ella manda; los demás ejecutan.

---

## 1. Principios 3.0

| Principio | Descripción |
|-----------|-------------|
| **Local first** | El cerebro de Lilith corre en tu máquina: routing, decisión de tools, memoria, aprendizaje. APIs solo cuando hace falta (modelos pesados, agentes externos). |
| **Tools, no comandos** | Una capa única de **tools** (nombre, descripción, parámetros). Lilith elige qué tool usar y con qué argumentos; el Core ejecuta. Sin “skills” sueltos ni comandos mágicos. |
| **Agentes como tools** | Eva, Adán, Lucifer son **una tool más**: `delegate_to_agent(agent, task, context)`. Lilith decide cuándo delegar; las APIs de cada agente ejecutan. |
| **Aprendizaje local** | Memoria tri-capa (semántica, episódica, procedural) en disco; preferencias y patrones que mejoran con el uso. Opcional: modelo pequeño local para intent/routing (ML). |

---

## 2. Arquitectura concreta: el Cerebro de Lilith 3.0

Componentes y responsabilidades para implementar el núcleo local.

```
┌──────────────────────────────────────────────────────────────┐
│                    LILITH 3.0 CORE (Local)                    │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐   ┌──────────────────────┐         │
│  │   1. INTENT ENGINE    │   │   2. MEMORY MANAGER   │         │
│  │ - Clasifica mensaje   │   │ - Almacena/Recupera   │         │
│  │ - Sugiere N tools     │   │   contexto semántico  │         │
│  └───────┬──────────────┘   └───────────┬───────────┘         │
│          │                          │                         │
│          ▼                          ▼                         │
│  ┌──────────────────────┐   ┌──────────────────────┐         │
│  │  3. TOOL REGISTRY     │   │ 4. LEARNING ENGINE    │         │
│  │ - Catálogo dinámico   │   │ - Aprende de logs     │         │
│  │ - Ejecuta handlers    │   │ - Refina intent       │         │
│  └───────┬──────────────┘   └───────────┬───────────┘         │
│          │                          │                         │
│          └────────────┬─────────────────┘                     │
│                       ▼                                       │
│  ┌──────────────────────────────────────────────┐             │
│  │ 5. ORCHESTRATOR (El "Director")               │             │
│  │ - Recibe: mensaje + contexto + tools sugeridas │             │
│  │ - Decide: tool única, cadena de tools o delegar │             │
│  │ - Ejecuta y formatea la respuesta final        │             │
│  └──────────────────────┬───────────────────────┘             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                 GATEWAY DE AGENTES (APIs)                      │
├──────────────────────────────────────────────────────────────┤
│  - Tool: delegate_eva()   → Llama a API de Grok (Eva)         │
│  - Tool: delegate_adan()  → Llama a API de Qwen (Adán)        │
│  - Tool: delegate_lucifer() → Llama a API de Venice (Lucifer) │
│  - Tool: generate_reply() → Llama a API de Kimi/Grok         │
└──────────────────────────────────────────────────────────────┘
```

**Claves de esta arquitectura:**

| Principio | Descripción |
|-----------|-------------|
| **Desacoplamiento** | El Intent Engine no necesita saber cómo se ejecuta una tool, solo cuál es la mejor. |
| **Extensibilidad** | Añadir una nueva tool = registrarla en el Tool Registry. El Orchestrator la usará automáticamente. |
| **Cerebro local** | La decisión, la memoria a corto plazo y el aprendizaje ocurren 100% en tu máquina. Las APIs son meros músculos. |

---

## 3. Catálogo de tools (herramientas integradas)

Todo lo que Lilith “sabe hacer” se expone como **una tool** con nombre, descripción y parámetros. El router/orquestador solo elige entre estas.

### 3.1 Tools de sistema (locales)

| Tool | Descripción | Parámetros | Quién ejecuta |
|------|-------------|------------|----------------|
| `read_file` | Leer y resumir archivo del proyecto | `path`, `max_chars?` | Core (FileManager) |
| `edit_file` | Proponer o aplicar cambio en archivo | `path`, `instruction` o `patch`, `confirm?` | Core (CodeEditor) |
| `create_file` | Crear archivo con contenido | `path`, `content` o `instruction` | Core (FileManager) |
| `list_directory` | Listar archivos en ruta | `path`, `pattern?` | Core (ProjectScanner) |
| `grep` | Buscar en archivos | `pattern`, `path?`, `type?` | Core (GrepTool) |
| `run_tests` | Ejecutar tests en ruta | `path?`, `markers?` | Core (TestRunner) |
| `analyze_code` | Análisis estático (sin LLM) | `path` | Core (CodeAnalyzer) |

### 3.2 Tools de agentes (delegación vía API)

| Tool | Descripción | Parámetros | Quién ejecuta |
|------|-------------|------------|----------------|
| `delegate_eva` | Análisis, documentación, insights | `task`, `context?` | API Eva (Grok) |
| `delegate_adan` | Código, refactor, tests | `task`, `context?` | API Adán (Qwen) |
| `delegate_lucifer` | Tarea especializada | `task`, `context?` | API Lucifer |
| `auto_mode` | Plan + ejecución multi‑agente | `objetivo` | Core (TaskPlanner + TaskExecutor) |

### 3.3 Tools de memoria y contexto (locales)

| Tool | Descripción | Parámetros | Quién ejecuta |
|------|-------------|------------|----------------|
| `get_semantic_context` | Perfil usuario + decisiones + proyectos | `user_id?` | Core (SemanticMemory) |
| `store_insight` | Guardar hallazgo o preferencia | `type`, `content`, `source` | Core (memoria) |
| `search_memory` | Buscar en episódica/procedural | `query`, `limit?` | Core (memoria) |

### 3.4 Tools de orquestación (locales)

| Tool | Descripción | Parámetros | Quién ejecuta |
|------|-------------|------------|----------------|
| `generate_reply` | Respuesta en lenguaje natural (usa LLM) | `message`, `context`, `model?` | API Kimi (o local si hay modelo) |
| `classify_intent` | Intent + sugerencia de tool | `message` | Core (reglas/ML local) |

---

## 4. Flujo unificado (ejemplo)

1. Usuario: *“Explícame Backend/memory/semantic_memory.py y sugiere una mejora.”*
2. **Lilith local (router):**
   - `classify_intent` → “explicación + sugerencia” → tools sugeridos: `read_file`, `analyze_code`, `delegate_eva`.
   - Decide: `read_file(path="Backend/memory/semantic_memory.py")` → luego `delegate_eva(task="explica este código y sugiere una mejora", context=<contenido>)`.
3. **Ejecución:**
   - Core ejecuta `read_file` → obtiene contenido.
   - Core llama API Eva con task + contenido → obtiene explicación y sugerencia.
4. **Respuesta:** Lilith formatea la salida de Eva (y opcionalmente `store_insight` si Ainz confirma que la sugerencia es buena).
5. **Aprendizaje:** se guarda en memoria episódica (qué se preguntó, qué tool se usó, qué agente respondió).

---

## 5. Aprendizaje local (qué “va aprendiendo”)

| Capa | Qué aprende | Dónde |
|------|-------------|--------|
| **Semántica** | Perfil de Ainz, proyectos, decisiones de arquitectura, estilo de código | `Memory/semantic/` |
| **Episódica** | Resúmenes de sesión, temas recurrentes, qué preguntas lleva a qué tools | `Memory/sessions/`, `Memory/discord/users/` |
| **Procedural** | Errores resueltos, patrones de “cómo hacer X”, preferencias de flujo | `Memory/procedural/` |
| **Routing (opcional)** | Con el tiempo: “mensajes como X → tool Y” (fine‑tune pequeño o reglas aprendidas) | Modelo local o reglas en disco |

Sin APIs: Lilith puede mejorar **solo con uso** (memoria, estadísticas de qué tool funciona mejor para qué intent). Con un pequeño modelo local o un clasificador, puede refinar “intent → tool” con el tiempo.

---

## 6. Plan de ataque: fases pragmáticas 2.3 → 3.0

Cada fase entrega valor y la siguiente se construye sobre base sólida.

### Fase 1: El cimiento (Core local y abstracción de tools) → **Lilith 2.4**

**Objetivo:** Reemplazar todos los "comandos" y "skills" por una capa unificada de tools, sin cambiar el comportamiento para el usuario.

| # | Tarea | Estado |
|---|--------|--------|
| 1 | Crear la **interfaz Tool**: clase abstracta o protocolo con `get_description()` y `execute(params)`. | ✅ `core/tools_v3/protocol.py` |
| 2 | **Migrar skills a tools:** `read_file` → FileReadTool, `edit_file` → FileEditTool, `list_directory` → ListDirectoryTool, `generate_reply` (Kimi). | ✅ `core/tools_v3/*.py` |
| 3 | Implementar el **ToolRegistry**: diccionario que mapee nombre a instancia de la tool. | ✅ `core/tools_v3/registry.py` (ToolRegistryV3) |
| 4 | Crear un **SimpleRouter**: por reglas y palabras clave; ante un mensaje devuelve (tool_name, params). | ✅ `core/simple_router.py` |
| 5 | **Refactorizar el handler de mensajes:** flujo = mensaje → SimpleRouter → ToolRegistry → execute() → respuesta. | ✅ `core/message_flow_v3.py` + owner en `discord_api.py` usa este flujo |

**Resultado:** Lilith 2.4. Internamente es un sistema de tools; externamente funciona igual. Deuda técnica de comandos eliminada.

---

### Fase 2: El orquestador (Delegación y encadenamiento) → **Lilith 2.8**

**Objetivo:** Lilith usa agentes y combina varias tools para resolver una tarea.

| # | Tarea |
|---|--------|
| 1 | Crear **tools de delegación:** DelegateEvaTool, DelegateAdanTool, DelegateLuciferTool. Wrappers que solo llaman a la API externa correspondiente. |
| 2 | **Evolucionar SimpleRouter → Planner:** `Planner.plan(message)` → `List[Step]`. Un `Step` = `{"tool": "read_file", "params": {...}}`. Inicialmente el plan puede ser de un solo paso; si el mensaje contiene "mejora" y "archivo", el plan es `[read_file, delegate_eva]`. |
| 3 | **Evolucionar message_flow_v3 → Orchestrator:** `Orchestrator.execute_plan(plan, context)` → resultado final. Ejecuta pasos en secuencia; la salida de un paso puede ser entrada del siguiente (chaining). |
| 4 | **Ejemplo de encadenamiento:** "mejora este archivo X" → plan `[read_file(path=X), delegate_eva(task="analiza y mejora", context=<contenido>)]` → Orchestrator ejecuta, formatea resultado. |
| 5 | Integrar **generate_reply** como tool más. Si el plan está vacío o no hay match, Orchestrator usa esta para respuesta conversacional. |

**Resultado:** Lilith 2.8. Deja de ser solo "reacción a comandos" y pasa a **orquestar soluciones** (varias tools en cadena).

---

### Fase 3: La memoria y el aprendizaje (Local first real) → **Lilith 3.0 Beta**

**Objetivo:** Lilith aprende de cada interacción y se vuelve más inteligente y personal. El enfoque tri-capa (semántica, episódica, procedural) es el estándar de referencia; semántica puede usar BD vectorial local (ChromaDB, SQLite+vectors), episódica/procedural en JSON o SQL.

| # | Tarea |
|---|--------|
| 1 | **MemoryManager:** Semántica (proyectos, preferencias, decisiones) + Episódica: logs (timestamp, user_id, message, tools_used, outcome) en JSON o SQL. |
| 2 | **Tools de memoria:** (a) `search_semantic_memory(query)` — el Planner puede usarla antes de decidir (ej. "¿en qué estábamos con el proyecto X?"). (b) `store_interaction(interaction)` — el Orchestrator la llama al final de cada proceso para guardar qué se hizo; alimenta el aprendizaje futuro. |
| 3 | **Conectar memoria al Planner/Intent:** Antes de decidir, consultar memoria semántica. Ej.: si Ainz suele usar delegate_adan para refactor Python, preseleccionar esa tool. |
| 4 | **LearningEngine:** (a) Feedback loop: "útil" / "malo" → guardar en episódica. (b) Análisis de patrones sobre logs para sugerir nuevas reglas (ej. "si se menciona 'test' → run_tests"). |

**Resultado:** Lilith 3.0 Beta. Sistema local que recuerda, aprende patrones y personaliza.

---

### Fase 4: La autosustentabilidad (Cierre del círculo) → **Lilith 3.0 Final**

**Objetivo:** Reducir dependencia de APIs y permitir que Lilith se mejore a sí misma.

| # | Tarea |
|---|--------|
| 1 | **Modelo local de intent:** Reemplazar SimpleRouter por un clasificador pequeño (scikit-learn o HuggingFace) entrenado con logs de Fase 3. Decisión "qué tool usar" = 100% local y aprendida. |
| 2 | **Tool self_improve(task):** "Revisa mis últimos 10 logs y sugiere cómo podría haber respondido mejor". Usa search_memory → delegate_lucifer/eva para analizar → edit_file para proponer cambios en reglas o en su propio código. |
| 3 | **Modo offline:** Definir qué tools funcionan sin internet (todas las locales + generate_reply si hay LLM local tipo Llama 3 8B o Phi-3). Lilith autónoma cuando no hay conexión. |

**Resultado:** Lilith 3.0 Final. Núcleo local autosustentable que aprende, se auto-mejora y solo usa APIs para cómputo pesado que tú ordenas.

---

## 7. Estrategia de autosustentabilidad

Un sistema que se mantiene y mejora con mínimo esfuerzo.

| Estrategia | Descripción |
|------------|-------------|
| **Código como datos** | Reglas del Intent Engine, descripciones de tools y preferencias del Orchestrator en **YAML o JSON**, no hardcodeadas. Lilith puede leerlos e incluso editarlos con `edit_file` para mejorarse. |
| **Bucle de retroalimentación activo** | Cada interacción es un dato; cada éxito o fracaso es una lección. LearningEngine procesa logs (inicialmente estadística simple: "delegate_adan tiene 95% éxito cuando el mensaje contiene 'refactorizar'"). |
| **Delegación jerárquica** | Lilith no hace todo: su trabajo es **saber qué hacer y con quién**. Tareas complejas → descomponer y delegar al agente especializado. Su inteligencia está en la meta-cognición. |
| **Modelo local como cortafuegos de costes** | LLM local para alto volumen y bajo coste: clasificación de intent, resumen de logs, formateo. APIs costosas (Grok, Kimi) solo para alto valor: código complejo, análisis profundo, creatividad. Sistema económicamente autosustentable. |

---

## 8. Criterios de éxito 3.0

| Criterio | Cómo se mide |
|----------|------------------|
| **Tools únicas** | No hay “comandos mágicos” ni skills sueltos; todo pasa por el catálogo de tools. |
| **Lilith manda** | Eva/Adán/Lucifer solo se invocan vía tools `delegate_*`; no deciden por su cuenta. |
| **Local first** | Routing, memoria, decisión de tools y, si se implementa, clasificación intent → local. |
| **Aprendizaje** | Memoria tri-capa se actualiza con cada interacción; opcional ML para mejorar routing. |
| **Retrocompatibilidad** | Discord y web siguen funcionando; solo cambia la implementación interna (tools en lugar de comandos). |

---

## 9. Resumen de skills → tools (referencia rápida)

| Antes (skills/comandos) | En 3.0 (tool) |
|-------------------------|----------------|
| Comando `/file read`    | `read_file(path)` |
| Comando `/file edit`    | `edit_file(path, instruction)` + confirmación |
| “Pregunta a Eva”        | `delegate_eva(task, context)` |
| “Pregunta a Adán”       | `delegate_adan(task, context)` |
| `/auto [objetivo]`      | `auto_mode(objetivo)` |
| “Explícame la arquitectura” | `classify_intent` → `generate_reply` o `read_file` + `delegate_eva` |
| Ver memoria             | `get_semantic_context` + formatear |

---

## 10. Análisis y alineación (post Fase 1)

- **Interfaz Tool:** El contrato `get_description()` + `get_parameters_schema()` + `execute(params)` permite validación y que futuros modelos "entiendan" qué necesita una tool sin analizar código.
- **ToolRegistryV3:** Catálogo extensible; añadir capacidad = registrar una tool, no tocar el flujo principal.
- **SimpleRouter:** Primer motor de intención; desacopla "decisión" de "ejecución". Enrutamiento determinista es rápido, barato y predecible; la evolución natural es un modelo híbrido (Fase 4).
- **message_flow_v3 + fallback generate_reply:** Garantiza que el sistema siempre pueda responder. El siguiente paso es evolucionar a **Planner** (plan = lista de pasos) y **Orchestrator** (ejecutar plan con chaining).
- **Memoria tri-capa:** Semántica (vectorial/local), episódica y procedural (logs, JSON/SQL) es el estándar de referencia para agentes con memoria persistente.

---

## 11. Versiones y hitos (resumen)

| Versión | Hito |
|---------|------|
| **2.4** | Cimiento: Tool interface + ToolRegistry + SimpleRouter. Todo por tools; comportamiento igual. |
| **2.8** | Orquestador: tools de delegación (Eva, Adán, Lucifer), encadenamiento, generate_reply como tool. |
| **3.0 Beta** | Memoria + aprendizaje: MemoryManager (semántica + episódica), LearningEngine (feedback + patrones). |
| **3.0 Final** | Autosustentable: modelo local de intent, self_improve, modo offline. |

**Próximo paso lógico:** Fase 2 — tools de delegación (DelegateEva, DelegateAdan, DelegateLucifer), SimpleRouter → Planner (plan = List[Step]), message_flow_v3 → Orchestrator (execute_plan con chaining).

---

*Documento vivo: actualizar según avance de fases. Lilith 3.0 = local, con tools integradas y agentes a su mando.*
