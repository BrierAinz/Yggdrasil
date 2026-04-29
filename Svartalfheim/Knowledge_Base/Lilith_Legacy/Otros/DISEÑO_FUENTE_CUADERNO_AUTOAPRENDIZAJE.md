# Diseño: Fuente constante, cuaderno propio y modo auto-aprendizaje con confirmación por Discord

**Propósito:** Definir cómo añadir (1) una fuente de información constante para Lilith, (2) un “cuaderno” donde marque *esto es importante* / *esto no*, y (3) un modo en el que, al activarse, auto-aprenda, delegue tareas y pida confirmación al amo por Discord cuando haga falta.

**Contexto:** Ya existe flujo de confirmación por DM (pasos peligrosos → token → botones Autorizar/Denegar). Muninn (vault `lilith`) y ChromaDB están operativos. El objetivo es integrar estas piezas en un flujo coherente.

---

## 1. Fuente de información constante

**Idea:** Una o varias fuentes que Lilith consulte de forma periódica (o bajo demanda) para mantener su contexto actualizado sin que tengas que pedírselo cada vez.

| Tipo de fuente | Ejemplo | Cómo integrarlo |
|----------------|---------|------------------|
| **RSS/Atom** | Blogs, noticias, documentación con feed | Job periódico (cron/scheduler) o endpoint `POST /api/feed/ingest` que lea URLs de un `Config/fuentes_constantes.json` y use el pipeline existente (scrape → limpieza → filtro) para extraer texto y pasarlo al cuaderno/memoria. |
| **Carpetas vigiladas** | `D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Docs`, `Workspace/Notas` | Lista en config; cada X minutos (o al arranque) `gather_directory` sobre esas rutas, diff con último hash/lista de archivos; solo procesar archivos nuevos o modificados y enviar contenido al clasificador (importante / no → cuaderno). |
| **URLs fijas** | Documentación, wikis | Igual que minería actual: `lore_extractor` o `delegate_web_scraper` sobre una lista en config; resultado → clasificador → cuaderno + memoria. |

**Config sugerida:** `Config/fuentes_constantes.json`

```json
{
  "enabled": true,
  "rss_feeds": ["https://ejemplo.com/feed.xml"],
  "watch_folders": ["Core/Docs", "Workspace/Notas"],
  "watch_interval_minutes": 60,
  "urls_static": ["https://docs.ejemplo.com/"],
  "max_items_per_run": 20,
  "on_new_content": "classify_and_store",
  "rss_retention_days": 30
}
```

- `rss_retention_days`: días que se conservan entradas RSS en `Data/ingest_state.json`; tras ese tiempo se purgan (ver §6.2.1).

- `on_new_content`: `"classify_and_store"` = tras extraer contenido, pasarlo al clasificador (importante / no) y guardar en cuaderno + opcionalmente memoria semántica/Muninn.

---

## 2. Cuaderno propio de Lilith (“esto es importante” / “esto no”)

**Idea:** Un almacén dedicado donde Lilith (o el flujo automático) anote ítems con una marca de importancia, para consultarlo después al armar contexto o al decidir qué delegar.

| Campo | Uso |
|-------|-----|
| `id` | Identificador único (ULID o UUID). |
| `content` | Texto o resumen del ítem. |
| `important` | `true` / `false` — “esto es importante” vs “esto no”. |
| `source` | Origen: `"rss"`, `"folder"`, `"url"`, `"user"`, `"session"`. |
| `source_detail` | URL, ruta de archivo o descripción. |
| `created_at` | Fecha/hora. |
| `tags` | Opcionales (ej. `["lenguajes", "config"]`) para filtrar. |

**Implementación posible:**

- **Opción A — JSONL en disco:** `Data/lilith_notebook.jsonl`. Una línea por ítem (JSON). Fácil de inspeccionar y hacer backup. Búsqueda por `important`, `source`, `tags` en Python.
- **Opción B — Muninn:** Usar el vault `lilith` con tags `important` / `not_important` (o un tag `cuaderno`) y el contenido en `concept`/`content`. Ventaja: ya tienes activate por contexto; el “cuaderno” sería una vista (filtrar por tag).
- **Opción C — Híbrido:** Cuaderno JSONL para orden y rapidez; opcionalmente sincronizar ítems “importantes” a Muninn para que entren en `search_context` y en el flujo de memoria actual.

**Tools/API sugeridas:**

- `notebook_add(content, important, source, source_detail, tags)` — Añade entrada al cuaderno (desde el flujo de fuente constante o desde una tool/comando).
- `notebook_search(query, important_only=False)` — Devuelve entradas que coincidan con la query (y opcionalmente solo `important == true`). Puede implementarse sobre JSONL o sobre Muninn si se usa Opción B/C.

Así Lilith puede “escribir” en su cuaderno cuando procesa la fuente constante y luego usar “lo importante” al responder o al delegar.

---

## 3. Modo auto-aprendizaje (activar/desactivar) y confirmación por Discord

**Idea:** Un modo que, cuando está **activado**:

1. **Auto-aprende:** Usa la fuente constante (y opcionalmente episodios recientes) para producir ítems del cuaderno y/o hechos en memoria (ChromaDB, Muninn).
2. **Delega cuando convenga:** Si el contenido encaja con una tarea de un agente (Eva, Lucifer, etc.), puede generar un “plan interno” (ej. “resumir este doc”, “extraer entidades”) y ejecutarlo en background o en cola, sin que el usuario tenga que escribir un comando cada vez.
3. **Pide confirmación por Discord:** Si la acción que quiere hacer es “peligrosa” o ambigua (editar archivos, ejecutar comandos, enviar algo externo), en lugar de ejecutarla directo, crea una **confirmación pendiente** y te la envía por DM con botones Autorizar/Denegar, reutilizando el flujo actual.

**Activación del modo:**

- **Config:** `Config/auto_learn.json` (o una sección en `planner.json` / `memory.json`):

```json
{
  "auto_learn_enabled": false,
  "sources_use": "fuentes_constantes",
  "delegate_when": "match_intent",
  "confirm_dangerous": true,
  "max_delegations_per_run": 5
}
```

- **Comando Discord:** Por ejemplo `/auto-learn on` y `/auto-learn off` (solo owner) que actualicen `auto_learn_enabled` y opcionalmente persistan en ese JSON o en una tabla simple.

**Flujo cuando `auto_learn_enabled` es true:**

1. **Trigger:** Periódico (cada N minutos) o tras “hay contenido nuevo” de la fuente constante.
2. **Ingest:** Obtener ítems nuevos (RSS, carpetas, URLs) como hasta ahora.
3. **Clasificar:** Para cada ítem, decidir:
   - ¿Es importante? → `notebook_add(..., important=true/false)`.
   - ¿Requiere una acción (resumir, extraer, guardar en memoria)? → Generar un mini-plan (1–2 pasos).
4. **Ejecutar acciones “seguras”:** Por ejemplo: `store_semantic_fact`, `notebook_add`, `delegate_lucifer` con tarea de solo “resumir”. Sin tocar archivos ni shell.
5. **Acciones “peligrosas”:** Si el plan incluye `edit_file`, `system_execute`, `owner_system_action`, etc.:
   - No ejecutar.
   - Crear `_PendingConfirmation` con el plan y un token.
   - Llamar a un **servicio de notificación Discord** (o el mismo endpoint que usa el bot) para que al owner le llegue un DM con el resumen y los botones ✅/❌.
6. Cuando el owner confirma en Discord, el flujo existente de confirmación ejecuta el plan y devuelve el resultado (al canal o por DM, según cómo lo tengas hoy).

Así, “si necesita confirmación me la envía por Discord” queda cubierto reutilizando `_pending_confirmations` y el handler de confirmación por DM.

**Detalle técnico:** El “job” de auto-aprendizaje puede vivir:

- En la **API** (FastAPI): un background task que cada N minutos lea `auto_learn_enabled`, lee fuentes, clasifica y o bien ejecuta pasos seguros o bien crea pending confirmation y notifica por Discord (vía cliente HTTP que simule “hay una confirmación pendiente para el user X” y el bot envía el DM).  
- O en un **script/worker** separado que llame a la API para “ingest” y para “request_confirmation”, y el bot solo envía DMs cuando la API le dice que hay un token pendiente para el owner.

La opción más limpia con lo que ya tienes es: el job (en la API o en un worker) que al detectar “acción peligrosa” escriba en `_pending_confirmations` y guarde en disco, y luego **notifique al bot** (webhook interno o cola) con `owner_user_id` y `confirm_token` para que el bot envíe el DM con los botones. Si ya tienes un endpoint tipo “listar confirmaciones pendientes para user X”, el bot podría polling o recibir un evento; si no, un endpoint `POST /api/discord/notify-pending-confirmation` que reciba `user_id` y `token` y que el bot consuma para enviar el DM.

---

## 4. Orden sugerido de implementación

| Fase | Qué hacer |
|------|-----------|
| **4.1** | Definir `Config/fuentes_constantes.json` y módulo que lea RSS/carpetas/URLs; **estado en `Data/ingest_state.json`** (ver §6.2) para no reprocesar ítems ya vistos. Devolver solo “ítems nuevos”; sin cuaderno aún, opcionalmente `add_fact`/Muninn. |
| **4.2** | Cuaderno **híbrido** (ver §6.3): JSONL `Data/lilith_notebook.jsonl` + sync de `important=true` a Muninn. Primitivas `notebook_add` y `notebook_search`. Clasificación en dos fases (§6.1): heurística primero, LLM solo para lo que pase criba (con tope por run). |
| **4.3** | Añadir `Config/auto_learn.json` y flag `auto_learn_enabled`; job periódico que use fuentes + cuaderno y genere planes “seguros” (solo memoria/cuaderno) o “peligrosos” (editar, ejecutar). Para peligrosos: crear confirmación y notificar al owner por Discord (integrar con `_pending_confirmations` y el flujo DM existente). |
| **4.4** | Comando Discord `/auto-learn on|off` (solo owner) y opcionalmente `/cuaderno` para listar últimas entradas importantes. |

---

## 5. Resumen

- **Fuente constante:** Config (RSS, carpetas, URLs) + job que ingesta contenido y lo pasa al siguiente paso.
- **Cuaderno:** Store (JSONL o Muninn) con `important` / `source` / `tags`; herramientas para añadir y buscar; uso en contexto y en decisiones de delegación.
- **Modo auto-aprendizaje:** Activado por config y/o por comando; cuando está on, usa la fuente, clasifica, guarda en cuaderno/memoria, delega tareas seguras y, si hace falta una acción peligrosa, pide confirmación al amo por Discord con el flujo actual de DM y botones.

Con esto tienes una hoja de ruta clara para “fuente constante”, “cuaderno propio” y “modo que auto-aprende y me pide confirmación por Discord”.

---

## 6. Decisiones de diseño (Deep Dive: evitar bucles y explosión de coste)

Tres decisiones críticas para que el auto-aprendizaje no devore recursos ni sature la memoria.

### 6.1 Coste de la clasificación (señal vs. ruido)

**Problema:** Con 5 feeds RSS y 3 carpetas vigiladas, pueden llegar cientos de ítems al día. Clasificar cada uno con Lucifer (Kimi) o Eva (Grok) quemaría el presupuesto de tokens.

**Decisión:** Clasificador en dos fases.

| Fase | Quién | Qué hace |
|------|--------|----------|
| **Criba** | Clasificador local barato | Heurísticas: longitud mínima, palabras clave de “importante” (ej. en `Config/notebook.json`: `important_keywords: ["documentación", "API", "breaking", "seguridad", "config"]`), opcionalmente `LocalIntentClassifier` si está entrenado, o score por densidad de términos. Solo los ítems que superen un umbral (o un **sample** si hay muchos) pasan a la fase 2. |
| **Refino (opcional)** | Lucifer/Kimi o Eva | Solo para lo que pasó la criba, o para un **máximo por ejecución** (ej. 5–10 ítems por run). Pregunta tipo: “¿Este contenido es importante para el proyecto o el amo? Responde solo important: true/false.” Así se controla el coste y se reservan los agentes para lo dudoso. |

**Config sugerida** en `Config/auto_learn.json` o `Config/notebook.json`:

- `classification_mode`: `"heuristic_only"` | `"heuristic_then_llm"` | `"llm_only"` (por defecto `heuristic_then_llm`).
- `max_llm_classifications_per_run`: 10.
- `important_keywords`: lista de términos que suman puntos para `important=true` en la heurística.

---

### 6.2 Rastreo de estado (evitar la amnesia y el bucle infinito)

**Problema:** Si el job corre cada 60 minutos, hay que saber qué ítems ya se procesaron para no reingerir y reclasificar lo mismo una y otra vez.

**Decisión:** Estado persistente en **`Data/ingest_state.json`** (o SQLite si se prefiere más adelante).

| Fuente | Qué guardar por ítem |
|--------|----------------------|
| **RSS** | `feed_url` + `guid` o `link` + `published` (o hash del contenido). Clave única: `(feed_url, guid)` o `(feed_url, link)`. |
| **Carpetas** | `folder_path` + `file_path` relativo + `mtime` (o hash del contenido). Clave: `(folder, relative_path)`. |
| **URLs estáticas** | `url` + `etag` o `last_modified` o hash del body. Clave: `url`. |

Antes de procesar un ítem, se consulta el estado: si ya existe y no ha cambiado (mtime igual, etag igual), se **salta**. Tras procesar con éxito, se actualiza el estado (mtime, etag, hash) y la fecha de último ingest. Opcional: límite de entradas por fuente (ej. guardar solo los últimos 500 ítems por feed) para no hinchar el JSON; se puede rotar por antigüedad.

**Estructura mínima sugerida** `Data/ingest_state.json`:

```json
{
  "rss": { "https://ejemplo.com/feed.xml": { "last_seen": {"guid1": "2026-03-15T12:00:00", "guid2": "..."}, "last_run": "2026-03-15T21:00:00" } },
  "folders": { "Core/Docs": { "files": { "README.md": "2026-03-15T20:30:00", "API.md": "..." }, "last_run": "..." } },
  "urls": { "https://docs.ejemplo.com/": { "etag": "...", "last_run": "..." } }
}
```

Así se evita el bucle infinito y la reingesta duplicada.

#### 6.2.1 Gestión de crecimiento de `ingest_state.json`

**Problema:** Con varios feeds RSS diarios, el archivo de estado crece con nuevos GUIDs/URLs. ¿Purga por antigüedad o crecimiento indefinido?

**Decisión:** **Política de limpieza configurable.**

- En **`Config/fuentes_constantes.json`** (o en un bloque `ingest_state` dentro) se define:
  - `rss_retention_days`: número de días que se conservan entradas RSS en el estado (ej. `30`). Las entradas con `last_seen` (o equivalente) más antiguas se purgan en cada run o en un job de mantenimiento.
  - Opcional: `folders_retention_days` y `urls_retention_days` si se quiere acotar también carpetas/URLs (por defecto las carpetas pueden conservarse por `mtime` sin límite de tiempo, y las URLs estáticas suelen ser pocas).
- **Implementación:** Antes o después de cada ingest (o en un paso explícito de “limpieza”), el módulo que lee/escribe `ingest_state.json` elimina del diccionario `rss[feed_url]` las claves (GUID/link) cuya fecha asociada sea anterior a `now - rss_retention_days`. El archivo así tiene un tamaño acotado y predecible.
- **Alternativa descartada para RSS:** Crecimiento indefinido. Aunque el texto plano pese poco, con muchos feeds a largo plazo el JSON puede volverse lento de parsear y difícil de auditar; la purga por antigüedad no afecta a la corrección (los ítems ya no se reingerirían porque siguen en el estado hasta que se purgan, y tras purgar simplemente se tratarían como “nuevos” si el feed republish — aceptable).

---

### 6.3 Motor del cuaderno (JSONL vs. Muninn vs. híbrido)

**Problema:** Elegir almacenamiento para `notebook_add` y `notebook_search`: JSONL (rápido, simple), Muninn (temporal, Hebbiano) o híbrido.

**Decisión:** **Opción C — Híbrido.**

| Capa | Rol |
|------|-----|
| **JSONL** (`Data/lilith_notebook.jsonl`) | Fuente de verdad para el cuaderno. Todas las escrituras van aquí: `notebook_add` escribe una línea por ítem (`id`, `content`, `important`, `source`, `source_detail`, `created_at`, `tags`). `notebook_search` lee y filtra (por texto, `important`, `source`, `tags`); para búsqueda por similitud se puede usar búsqueda de substring o, si se quiere, un índice local ligero. Ventaja: implementación inmediata, auditoría clara, backup trivial. |
| **Muninn** (vault `lilith`) | Solo ítems con **`important=true`**. Tras `notebook_add(..., important=true)`, se hace un `write` a Muninn (concept/content + tags `cuaderno`, `important`) para que entren en `activate` y en el bloque “[Memoria MuninnDB]” del contexto. Así lo “importante” del cuaderno participa de la prioridad temporal y el aprendizaje Hebbiano sin duplicar toda la lógica de escritura. |

Flujo concreto:

- `notebook_add` → escribe en JSONL; si `important=true`, además llama a Muninn `write` (o a `MemoryManager.add_fact` con topic `cuaderno` si prefieres unificar por ChromaDB).
- `notebook_search` → lee de JSONL (filtros, paginación); si se necesita “lo relevante para esta consulta” en el contexto general, ya está cubierto por Muninn/ChromaDB porque lo importante se sincronizó.

Con esto se apuesta **definitivamente por el híbrido** para las primitivas del cuaderno: JSONL como cuaderno explícito y rápido, Muninn (o memoria semántica) para lo importante y su uso en el flujo de contexto.

#### 6.3.1 Sincronización de identificadores (JSONL ↔ Muninn)

**Problema:** Un ítem con `important=true` existe en JSONL y en Muninn. Si en el futuro Lilith (o el amo) cambia un apunte de importante a no importante, hay que poder **encontrar y borrar o desactivar el concepto correspondiente en la bóveda** para no dejar huérfanos ni duplicar lógica.

**Decisión:** **Mismo identificador en ambos lados.**

- El **`id`** de cada entrada del cuaderno (ULID o UUID) se genera **una sola vez** al hacer `notebook_add` y se escribe en la línea JSONL.
- Al sincronizar a Muninn (solo cuando `important=true`), se usa **ese mismo `id`** como identificador del concepto en la bóveda:
  - Si la API de Muninn admite un campo tipo `external_id` o `source_id`, se guarda ahí el `id` del cuaderno.
  - Si no, el `id` se incluye de forma fiable en el contenido o en metadatos/tags que permitan recuperar el concepto (ej. tag `cuaderno:id=<ulid>`), de modo que en una operación “actualizar/borrar por id” se pueda localizar el nodo en Muninn.
- **Flujo de actualización:** Si un ítem pasa de `important=true` a `false` (p. ej. por una tool `notebook_set_important(id, false)` o por re-clasificación):
  1. Se actualiza la línea en el JSONL (o se reescribe la línea con `important: false`).
  2. Se llama a una función tipo `muninn_remove_notebook_concept(id)` que, usando el `id`, busca y elimina (o marca como inactivo) el concepto correspondiente en el vault `lilith`.
- Así, **una sola fuente de verdad para el identificador** (el `id` del JSONL) y Muninn queda siempre alineado con “solo los ítems actualmente importantes”.

---

### 6.4 Parseador de feeds (RSS/Atom) — stack técnico

**Contexto:** Para la fase 4.1, carpetas y URLs estáticas están cubiertas por herramientas existentes (`gather_directory`, `delegate_web_scraper`). Falta definir cómo **leer feeds RSS/Atom** desde las URLs listadas en `fuentes_constantes.json`.

**Opciones:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **`feedparser`** | Estándar de facto, maneja RSS 0.9x/1.0/2.0 y Atom, nombres de campos normalizados, fechas y codificación bien resueltos. | Una dependencia más en el proyecto. |
| **BeautifulSoup + requests** | Ya presentes en `requirements.txt`; cero dependencias nuevas. | Parsing manual de XML, manejo de variantes RSS/Atom y de fechas más frágil; más código y mantenimiento. |

**Decisión:** **Añadir `feedparser` como dependencia.**

- Razón principal: robustez y mantenibilidad. Los feeds reales tienen variantes (namespaces, fechas en formatos distintos, entradas sin GUID), y `feedparser` ya encapsula esos casos; un extractor ligero con BeautifulSoup sería más propenso a fallos con feeds poco estándar.
- El coste es un único paquete ligero y sin dependencias pesadas. Se añade a `Core/requirements.txt` (ej. `feedparser>=6.0.0`) y el módulo de ingesta 4.1 usa `feedparser.parse(url)` (o el contenido descargado vía `requests`) para obtener la lista de entradas y extraer `id`/`link`, `title`, `published`, `summary`/`content` según la especificación del diseño (§6.2).

**Alternativa documentada:** Si en algún momento se prioriza “cero dependencias nuevas”, se puede sustituir por un módulo interno que use solo `requests` + `BeautifulSoup` para XML, con la advertencia de que habrá que probar contra cada feed concreto y posiblemente ampliar el parser para edge cases.

---

## 7. Auditoría del flujo Human-in-the-Loop

Para validar que el puente asíncrono (pending-for-dm + polling + _ConfirmViewWithToken) y el registro de autorización/denegación funcionan de punta a punta:

1. **Configurar** `Config/auto_learn.json`: asigna tu ID de Discord a `owner_discord_id` (ej. `"owner_discord_id": "123456789012345678"`).
2. **Asegurar** que la API Lilith y el bot de Discord están en marcha.
3. **Disparar** la confirmación de prueba:
   ```bash
   curl -X POST http://localhost:8000/api/discord/auto-learn/audit-confirm
   ```
4. **Esperar** hasta ~45 s: el bot hace polling a `GET /api/discord/pending-for-dm?owner_id=<tu_id>` y te envía un DM con el mensaje de auditoría y los botones **Autorizar** / **Denegar**.
5. **Pulsar** uno de los botones: la vista llama a `POST /api/discord/confirm`; la API ejecuta (autorizar) o cancela (denegar) y queda registrado en `Data/discord_audit.jsonl` y `Data/confirmation_audit.jsonl`.

Si recibes el DM y la decisión queda registrada, el flujo de escalación humana está operativo.

---

## 8. Calibración: frecuencia, criba y URLs estáticas

### 8.1 Frecuencia de polling vs. rate limits (Reddit)

- **User-Agent:** Todas las peticiones RSS usan por defecto `LilithBot/1.0 (Auto-learn; RSS/Atom ingest)`. Configurable en `Config/fuentes_constantes.json` con `rss_user_agent` (vacío = usar el por defecto). Así Reddit y otros hosts reciben un cliente identificable y se reduce el riesgo de 429.
- **Intervalo:** Si incluyes feeds de Reddit (p. ej. `reddit.com/r/LocalLLaMA/top/.rss?t=day`), conviene un **intervalo de ingesta conservador**. En `Config/auto_learn.json` usa `interval_minutes` ≥ 240 (4 h) cuando haya varios feeds Reddit para no saturar el límite.

### 8.2 Alineación de la criba heurística

En `Config/notebook.json`, el campo **`important_keywords`** debe alinearse con las fuentes que uses:

- **IA y LLMs (Hugging Face, OpenAI, LocalLLaMA):** términos como `llm`, `rag`, `agent`, `model`, `quantization`, `transformer`, `embedding`, `hugging face`, `openai`.
- **Game dev y worldbuilding (Game Developer, r/gamedesign, Godot):** `game loop`, `shader`, `gamedev`, `game design`, `godot`, `unreal`, `engine`, `worldbuilding`, `narrativa`.
- **Genéricos:** `documentación`, `API`, `tutorial`, `python`, `fix`, `bug`, `release`.

La Fase 1 del clasificador deja pasar ítems que contengan al menos uno de estos términos; la Fase 2 (LLM) refina con tope `max_llm_classifications_per_run`.

### 8.3 Boilerplate en URLs estáticas

Las **URLs estáticas** no se comparan solo por ETag: el módulo de ingesta **limpia el HTML** con BeautifulSoup antes de hashear:

- Se eliminan `script`, `style`, `noscript`.
- Se toma el contenido de `main`, `article`, `[role=main]` o, en su defecto, `body` tras quitar `nav`, `header`, `footer`, `aside`, `form`.
- El **hash** se calcula sobre ese texto principal, de modo que cambios en widgets, fecha del footer o rotadores de anuncios no marcan la página como “nueva” y se evita reprocesado infinito.

Para URLs que devuelven Atom/RSS (p. ej. GitHub Releases), se trata el feed como una sola unidad: se hashea título del feed + títulos/links/resúmenes de las primeras entradas.

---
