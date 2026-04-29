# Deep Dive — Arquitectura técnica de Lilith

Respuestas precisas a preguntas de investigación sobre memoria, orquestación, pipeline 4.0 y seguridad en Discord. Basado en el código actual del Core.

---

## 1. Arquitectura de la memoria

**Pregunta:** ¿Se usa base de datos vectorial (ChromaDB/FAISS) para recuperación semántica o solo archivos planos/JSON?

**Respuesta:** **Híbrido.** La memoria semántica tiene dos capas:

| Capa | Ubicación | Función |
|------|-----------|--------|
| **Persistencia base** | `Backend/memory/semantic_memory.py` → archivo JSONL (`Memory/semantic/recent_facts.jsonl` o ruta configurada) | Todos los hechos se escriben en JSONL (ts + text). |
| **Búsqueda por similitud** | `Backend/core/memory/semantic/vector_store.py` | Si las dependencias están instaladas (**ChromaDB** + **sentence-transformers**, modelo `all-MiniLM-L6-v2`), cada hecho se indexa también en ChromaDB (persist en `Data/chroma_facts`). La búsqueda semántica usa embeddings y devuelve los K hechos más similares a la query. |

Flujo concreto:

- **`SemanticMemory.add_fact(text)`** (en `semantic_memory.py`): escribe en el JSONL y, si el vector store está disponible, llama a `Backend.core.memory.semantic.vector_store.add_fact()`.
- **`SemanticMemory.get_context_for_prompt(query)`**: si hay `query` y el vector store está disponible, usa `vector_store.search_facts(base_path, search_query, k)` (con `k` desde `memory.json` → `vector_facts_k`, por defecto 5). Si no hay vector store o no hay query, devuelve los últimos N hechos por recencia desde el JSONL.
- **`Core/Memory/`**: en el código, los datos de memoria (semántica, episódica, procedimental) viven bajo la raíz del Core; la persistencia de ChromaDB está en `Data/chroma_facts` (relativo a esa raíz).

No se usa FAISS en el Core actual; solo ChromaDB + sentence-transformers para la recuperación semántica rápida. Si ChromaDB o sentence-transformers no están instalados, el vector store no se inicializa y se usa solo el JSONL (recencia, sin similitud).

---

## 2. Orquestación y comunicación entre agentes (Eva, Adán, Lucifer)

**Pregunta:** ¿Cómo se transfiere el contexto entre agentes? ¿Vía IPC en main.py o estado compartido en FastAPI?

**Respuesta:** El flujo principal de Discord **no pasa por el IPC de main.py** para la ejecución del plan. La transferencia de contexto es **en proceso, dentro de la API FastAPI**, y se hace **solo por parámetros** (sin estado compartido entre agentes).

- **Quién orquesta:** En `discord_api.py`, cuando el rol tiene `orchestrator_full`, se usa un **Orchestrator** singleton (`_get_orchestrator()`): mismo Planner, mismo ToolRegistryV3, mismo MemoryManager, mismo PlanExecutor. Todo en el mismo proceso de la API.
- **Cómo se pasa el contexto entre pasos:** En `plan_executor.py`, en cada paso del plan se hace:
  - `if i > 0 and "context" in params: params["context"] = last_result`
  - Es decir, la **salida del paso anterior** se inyecta como `params["context"]` del siguiente. No hay estado global compartido: cada step recibe (task, context) y el AgentCaller/registry ejecuta la tool o el agente registrado con esos params.
- **Cómo se invoca a Eva/Adán/Lucifer:** Las tools `delegate_eva`, `delegate_adan`, `delegate_lucifer` (en `tools_v3/agent_tools.py`) reciben `task` y `context`. Dentro de cada tool se llama a `AgentRouter().execute(task, agent_name=..., context=context)`. El AgentRouter vive en el proceso de la API y usa los sub-agentes (Eva, Adán, Lucifer) vía sus backends (APIs externas); no hay IPC entre ellos, solo la cadena task+context que llega por params.
- **IPC (main.py):** El proceso **Core** (`main.py`) expone un **IPCServer** (pipe con nombre) para comandos/eventos (chat, estado, etc.). La **API FastAPI** puede usar un **IPCClient** para enviar mensajes al Core o recibir eventos. Pero la ruta típica de “mensaje Discord → plan → ejecutar pasos → respuesta” usa el Orchestrator **dentro del proceso de la API**, sin obligar a pasar por el Core. Es decir: el orquestador que ejecuta el plan y pasa contexto entre pasos (y entre agentes vía `context`) está en la API; el IPC es opcional para otros flujos (por ejemplo modo auto o integraciones que sí hablan con el Core).

Resumen: **transferencia de contexto = inyección de `last_result` en `params["context"]` del siguiente paso, en el PlanExecutor, dentro del proceso FastAPI.** Los agentes no comparten estado en memoria; reciben todo por argumentos. El IPC no es el canal de la orquestación principal de Discord.

---

## 3. Pipeline de minería 4.0 — Cómo evalúa el QualityFilter

**Pregunta:** ¿El QualityFilter usa heurísticas de código o llamadas a un LLM para validar relevancia antes del DataStructurer?

**Respuesta:** **Solo heurísticas de código.** No hay llamadas a ningún LLM dentro del QualityFilter.

Implementación (`Backend/core/quality_filter_agent.py`):

- **Longitud:** `_length_score(text, min_length, ideal_min_length)`: score 0–1 según número de caracteres (por debajo de `min_length` → 0; por encima de `ideal_min_length` → 1; interpolación lineal entre ambos). Umbrales en `Config/quality_filter.json` (`min_length`, `ideal_min_length`).
- **Densidad de información:** `_information_density(text)`: ratio (palabras que no son stopword) / (total de palabras). Lista fija de stopwords en español e inglés en el módulo.
- **Score global:** `quality_score = 0.4 * length_score + 0.6 * density`, acotado a [0, 1].
- **Decisión:** Si `quality_score < min_score` (config), el agente devuelve mensaje de “Contenido filtrado por baja calidad” y no pasa el texto al DataStructurer. Si supera el umbral, devuelve el texto con un prefijo tipo `[Calidad validada: X]` para el siguiente paso.

No hay modelo de lenguaje ni API externa; todo es código determinista. La idea es filtrar por longitud y “sustancia” del texto (menos palabras vacías = más contenido). Una evolución futura podría añadir un paso opcional con LLM para coherencia o relevancia temática sin cambiar el contrato del agente.

---

## 4. Seguridad y permisos en Discord (roles)

**Pregunta:** ¿Los roles (owner, trusted, public) actúan como middleware que limita la profundidad de ejecución de herramientas o el acceso a la memoria procedimental?

**Respuesta:** Los roles **no son un middleware dentro del backend** que recorte “profundidad” de una misma ejecución. Actúan como **ramas de flujo en la API**: según el rol se elige **qué camino de código se ejecuta** y, por tanto, **qué herramientas y qué memoria se usan**.

- **Configuración:** `Backend/core/discord_roles_config.py` lee `Config/discord_roles.json` y expone `role_can(role, capability, base_path)`. Las capacidades son cosas como `orchestrator_full`, `limited_chat`, `charla`, `chiste`, `meme`, `status`. Por defecto: owner tiene `["*"]` (todo); trusted tiene `limited_chat`, charla, chiste, meme, status; public solo charla, chiste, meme.

- **Efecto en la ejecución:**
  - **Si el rol tiene `orchestrator_full`** (en la práctica, owner): se usa el **Orchestrator** con el **registro completo** de tools (read_file, edit_file, delegate_eva, delegate_adan, delegate_lucifer, minería web, etc.). Se llama a `orchestrator.execute_plan(message, ...)`. Al terminar, el Orchestrator llama a `memory_manager.post_interaction(...)`, que actualiza memoria episódica y puede reforzar patrones en memoria procedimental. Es decir: **sí** se ejecutan todas las herramientas y **sí** se escribe en memoria (episódica y procedimental).
  - **Si el rol tiene `limited_chat`** (trusted, y en la práctica solo en DM): no se usa el Orchestrator para el mensaje libre. Se usa un **registro limitado** `create_trusted_registry(project_root)` que solo registra `generate_reply`, `chiste`, `meme`. No hay read_file, edit_file, delegate_*, ni pipeline de minería. Si el plan generado para un trusted contiene pasos “peligrosos” (p. ej. herramientas de archivo o delegación), el flujo puede pedir **confirmación al owner** por DM en lugar de ejecutar. Es decir: la “limitación de profundidad” es **no invocar el orquestador completo** y no dar ese registro amplio.
  - **Public:** solo charla, chiste, meme (con registro limitado o modelo local), sin orquestador ni acceso a herramientas pesadas ni a `post_interaction` del orquestador.

- **Memoria procedimental:** Solo se actualiza cuando se ejecuta `memory_manager.post_interaction`, es decir cuando hay una ejecución de plan del **Orchestrator** (y se pasa `planner` para refuerzo de patrones). Esas ejecuciones solo ocurren para quien tiene `orchestrator_full`. Por tanto, **solo el flujo con orquestador completo (owner) escribe en memoria procedimental** en el sentido de refuerzo de patrones; los flujos trusted/public con registro limitado no llaman a `execute_plan` ni a `post_interaction`.

En resumen: los roles **no** son un middleware que recorte pasos dentro del mismo plan; **deciden qué rama de código corre** (orquestador completo vs registro limitado) y así limitan qué herramientas existen en esa rama y si se toca memoria episódica/procedimental.

---

## Prueba de estrés teórica (escalabilidad hacia 4.0)

Evaluación de cuatro escenarios que pueden limitar la escalabilidad o la calidad del sistema.

---

### 5. Estrategia de fragmentación (chunking) vectorial

**Pregunta:** Si el texto inyectado en `add_fact(text)` es un artículo largo (minería web), ¿hay chunking antes de la vectorización o se trunca y se pierde información?

**Respuesta:** **No hay chunking.** Se trunca por caracteres y el modelo puede truncar de nuevo por tokens.

- **SemanticMemory.add_fact(text)** (`semantic_memory.py`): escribe en JSONL con `entry["text"] = str(text).strip()[:2000]`. Solo los primeros 2000 caracteres se guardan en el hecho y se pasan al vector store.
- **vector_store.add_fact()** (`core/memory/semantic/vector_store.py`): hace `fact_text.strip()[:2000]` y pasa ese string a `_EMBEDDER.encode([...])`. No hay división en párrafos ni en ventanas de tokens.
- **Límite del modelo:** `all-MiniLM-L6-v2` tiene `max_seq_length` típico de 256 tokens (≈ 512 caracteres aproximados). SentenceTransformer.encode() trunca internamente a ese máximo. Por tanto:
  - Primero se trunca a 2000 caracteres en código.
  - Luego el encoder trunca a ~256 tokens.
  - Todo lo que pase de eso **no** entra en el espacio latente; un artículo largo de minería queda representado por un único vector de los primeros ~500 caracteres útiles.

**Riesgo:** Artículos o hechos largos (p. ej. salida del DataStructurer de varias páginas) pierden la mayor parte del contenido en el índice vectorial. La búsqueda semántica solo verá el inicio del texto.

**Recomendación para 4.0:** Implementar chunking antes de `add_fact`: por párrafos, por ventana de N caracteres (p. ej. 400–500) con solapamiento opcional, o por número de tokens. Guardar cada chunk como documento separado en ChromaDB con un `fact_id` derivado (ej. `{ts}_chunk_{i}`) y opcionalmente un `source_id` para agrupar chunks del mismo hecho. En búsqueda, devolver los K chunks más similares y, si se desea, deduplicar o reordenar por `source_id`.

---

### 6. Retención de contexto en cadenas no lineales (scratchpad del plan)

**Pregunta:** En un plan donde el Paso 3 necesita la salida del Paso 1 pero el Paso 2 ya sobrescribió `last_result`, ¿existe un scratchpad o memoria temporal del plan?

**Respuesta:** **No.** Solo se retiene la salida del paso inmediatamente anterior.

- En `plan_executor.py` la única variable de “estado” entre pasos es `last_result`. En cada iteración: `params["context"] = last_result` para el siguiente paso y luego `last_result = _result_to_str(result)`. No hay lista de resultados por step_id ni estructura tipo `results[step_id] = ...`.
- Los planes actuales son **lineales** (lista ordenada de Steps). No hay DAG ni referencias del tipo “usa la salida del paso 1”. Si en el futuro se definieran planes no lineales (por ejemplo “Paso 3: Lucifer analiza la salida del Paso 1 y del Paso 2”), el ejecutor actual **no** puede satisfacerlos: el Paso 3 solo recibiría la salida del Paso 2.

**Riesgo:** Cualquier diseño 4.0 que requiera “el agente C recibe la salida de A y de B” choca con la implementación actual.

**Recomendación para 4.0:** Introducir un **scratchpad del plan**: por ejemplo `step_results: Dict[str, str]` (o lista indexada) donde cada paso escribe con una clave (step_id o índice). Al ejecutar un paso, además de `last_result` se actualice `step_results[step_id] = result`. Permitir en la definición del Step (o en un DAG) referencias del tipo `context_from_steps: ["step_1", "step_2"]` y que el PlanExecutor inyecte en `params["context"]` la concatenación de esas salidas. Así se mantiene compatibilidad con cadenas lineales (donde “context” sigue siendo la del paso anterior) y se habilita el uso de salidas arbitrarias en planes no lineales.

---

### 7. Falsos positivos en el QualityFilter (código y logs)

**Pregunta:** ¿Cómo reacciona `_information_density(text)` ante código fuente o logs? ¿Se bloquea información técnica valiosa?

**Respuesta:** La densidad se calcula sobre **palabras** (split por espacios) y una lista de stopwords de **lenguaje natural**. Con código o logs el comportamiento es impredecible y hay **riesgo de falsos positivos y falsos negativos**.

- **Cálculo actual:** `words = text.lower().split()`; `meaningful = sum(1 for w in words if re.sub(r"\W", "", w) and w not in _STOPWORDS)`; `density = meaningful / len(words)`.
  - Solo se consideran “palabras” los tokens separados por espacios. Símbolos pegados (`def foo():`, `x+=1`) generan tokens como `def`, `foo():`, `x+=1`. Tras `re.sub(r"\W", "", w)` quedan `def`, `foo`, `x` (o vacío). `def` no está en la lista de stopwords; `for`, `in`, `is` sí.
  - Código Python: muchos identificadores y keywords; la ratio puede ser **alta** (poca stopword) y el filtro tendería a **dejar pasar** código. Pero si el fragmento es corto, `length_score` puede ser bajo y bajar el score global.
  - Logs (timestamps, rutas, números): muchos “palabras” son números o tokens raros; no son stopwords, así que cuentan como “meaningful”. Densidad puede ser alta; de nuevo el riesgo es más por **longitud** (logs muy largos podrían pasar; fragmentos cortos fallar por `min_length`).
  - Texto técnico mezclado (documentación con bloques de código): depende de la proporción. En la práctica, el filtro **no fue diseñado para código ni logs**; está pensado para prosa (artículos, documentación). No hay detección de “es código” ni umbrales distintos.

**Riesgos concretos:**
- **Falsos negativos:** Código o logs cortos pero valiosos pueden no alcanzar `ideal_min_length` y recibir un `length_score` bajo; si además la densidad cae (p. ej. mucho `for`, `in`, `if`), el score global puede quedar por debajo de `min_score` y **bloquear** contenido técnico útil.
- **Falsos positivos:** Ruido o spam con muchas “palabras” no stopword y longitud suficiente podría pasar.

**Recomendación:** (1) Documentar que el QualityFilter está pensado para **texto en lenguaje natural** (minería web de artículos/docs), no para código ni logs. (2) Si el pipeline va a procesar también código o logs, añadir un modo “técnico” (por ejemplo saltar el filtro, o usar umbrales distintos y/o detección heurística de “bloque de código” para no penalizar por densidad). (3) Opcional: un paso opcional con LLM para “¿es contenido útil?” solo cuando el heurístico sea dudoso.

---

### 8. Continuidad conversacional para usuarios públicos y trusted

**Pregunta:** Como solo el flujo con orquestador llama a `post_interaction`, ¿cómo mantiene Lilith el hilo conversacional a corto plazo (últimos mensajes) para trusted y public?

**Respuesta:** **Dos mecanismos:** historial enviado por el cliente en cada request y memoria de hilo persistida en servidor por canal/hilo.

- **Historial en el request:** El modelo de la API (`DiscordChatRequest`) incluye `history: Optional[List[Dict[str, str]]]` (lista de `{role, content}`). El **cliente** (bot de Discord en `Discord/handlers/chat_handler.py`) obtiene las últimas **20 mensajes** del canal/hilo (`_fetch_channel_history(..., limit=20)`) y los envía en cada llamada. Eso se usa en **todos** los flujos que construyen el system prompt (owner, trusted con limited_chat, public con charla/chiste/meme). Es decir: **todos los roles** reciben contexto de conversación reciente si el cliente envía `history`.
- **Memoria de hilo (server-side):** En `discord_api.py` se usa `_thread_memory_block(base_path, channel_id, thread_id)` para cargar mensajes persistidos por canal/hilo (implementación en `Backend/core/discord_thread_memory`). Ese bloque se inyecta en el system prompt en las ramas de **owner** (orchestrator), **trusted** (limited_chat con generate_reply/chiste/meme) y **public** (charla, chiste, meme). Después de responder, se llama a `_thread_memory_append(project_root, channel_id, thread_id, user_msg, response_text)` en esas mismas ramas. Por tanto, **trusted y public sí tienen** memoria de hilo en servidor: se **lee** por canal/hilo y se **escribe** tras cada respuesta (sin pasar por `post_interaction` del orquestador).

No hay una caché en memoria volátil en `discord_api.py` keyed por user_id; la persistencia a corto plazo es:
1. **request.history** (últimos 20 mensajes, enviados por el cliente en cada request).
2. **Thread memory** (archivos/datos por `channel_id`/`thread_id`, cargados y actualizados en cada request).

Con eso, trusted y public mantienen continuidad en la conversación dentro del mismo canal/hilo, aunque no escriban en memoria episódica ni procedimental.

---

---

## Referencias

- **Casos límite y decisiones 4.0:** `Docs/PROYECCION_4_0_CASOS_LIMITE.md` (scratchpad, MMR/diversidad, bypass QualityFilter, saturación memoria de hilo).
- **Agentes y orquestación:** `Docs/AGENTES_Y_ORQUESTACION_LILITH.md` (AgentRegistry, Planner, PlanExecutor, AgentCaller, flujos por tarea).
- **Orquestación y estructuración 4.0:** `Docs/ORQUESTACION_Y_ESTRUCTURACION_4_0.md` (structurer vs LLM, ejecución paralela DAG, topic routing).

*Documento generado a partir del código en Core/Backend. Si cambias la arquitectura, conviene actualizar este deep dive.*
