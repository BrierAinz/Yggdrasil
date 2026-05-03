# MISIÓN LILITH 3.7 — INTERACCIÓN, MEMORIA Y PULIDO PROFUNDO

**Estado:** EN EJECUCIÓN — Fases 1–3, 5–6 implementadas; validación en entorno real pendiente.

**Visión:** Profundizar en todo lo que quedó pendiente o parcial en 3.6: un solo mensaje por delegación, pipeline de salida de agentes, memoria (peso del hilo, indexación, contexto de delegación), acuse con badge, triggers más claros, timeout por agente, y todas las mejoras de interacción (DM, público, confirmaciones, embeds). Sin abrir el salto a un DAG de tools ni a 4.0; 3.7 es el último refinamiento intensivo antes del horizonte 4.0.

**Base:** Misión 3.6 (refinamiento al máximo) implementada y validada o en cierre; pendientes de 3.6 y notas para 4.0 pasan a ser núcleo o backlog de 3.7.

**Contenido de este doc:** Objetivo, bloques de trabajo, **recopilación exhaustiva de ideas** (interacción, memoria, tools, seguridad, Discord, rendimiento, observabilidad), orden de ejecución propuesto, archivos clave, checklist de validación y criterios de cierre.

**Refinamientos previos (pre-3.7):** Sinónimos ampliados en `memory.json` (ainz/martin/operador); tests adicionales en `test_planner_intents_36.py` (busca en tu memoria → Lucifer, directorio de lilith → list_directory válido).

**Implementado (ejecución del plan):**
- **Fase 1:** Un solo mensaje: slash ya no envía «Enviado a X», sino «Listo.» (ephemeral). Normalizador de respuesta aplicado a todas las salidas antes de enviar a Discord.
- **Fase 2:** Pipeline tres velos: `Backend/core/response_normalizer.py` + `_normalize_response_for_discord()` en la API; todas las respuestas (owner, trusted, public) pasan por el normalizador.
- **Fase 3:** Memoria: etiqueta «[Memoria de hilo — prioridad alta]» en el prompt (owner, trusted, public). Contexto de delegación (Odín IV): en `plan_executor` se mantiene `delegation_history` y se inyectan las últimas 3 delegaciones en el contexto de cada paso `delegate_*`.
- **Fase 5:** Timeout por agente: `memory.json` → `timeout_kimi_seconds`, `timeout_albedo_seconds`; `create_default_registry` usa `_timeout_from_config()` para Kimi y Albedo.
- **Fase 6:** Export memoria del hilo: `GET /api/discord/thread-memory?channel_id=&thread_id=`. Opción `disable_cache_owner_dm` en `memory.json`; cuando es true y role=owner y channel=dm, se pasa `skip_cache=True` a `execute_plan` → `run_plan` → `agent_caller.execute` para no usar caché.

**Fixes y mejoras documentados (trust, perfiles, roles, trato, confirmación trusted, avatar/portada):** ver **[FIXES_Y_MEJORAS.md](FIXES_Y_MEJORAS.md)**.

---

## RESUMEN EJECUTIVO

La 3.7 se centra en **cuatro ejes**:

1. **Un solo mensaje + acuse:** Al delegar a un agente, un único mensaje con la respuesta y el pie correcto; opcionalmente acuse «Procesando con [Agente]» si tarda.
2. **Memoria:** Peso del hilo, contexto de delegación (Odín IV), export del hilo, indexación por temas/fechas y prioridad a hechos recientes.
3. **Pipeline de salida:** Tres velos (extracción → normalización → formatter Discord) para que ninguna salida cruda llegue al usuario; triggers más claros y timeout por agente.
4. **Pulido:** Cooldown de confirmación, sanitización de paths en logs, opción de desactivar caché en owner DM, export de memoria del hilo.

Todo lo listado en «Ideas completas» es candidato; el orden de ejecución propuesto prioriza lo que más impacta en UX (un solo mensaje, pipeline) y luego memoria y observabilidad.

---

## OBJETIVO GENERAL

- **Interacción:** Un solo mensaje por delegación; acuse opcional con nombre de agente; confirmaciones claras; cooldown de confirmación; respuestas cortas cuando el usuario es breve; sin plantillas en DM; tono coherente en público/trusted.
- **Memoria:** Peso del hilo configurable ya está; ampliar: indexación/organización (temas, fechas), prioridad a hechos recientes, contexto acumulativo de delegaciones (Odín IV), export de memoria del hilo, feedback activo desde /feedback a memoria.
- **Tools y delegación:** Pipeline de tres velos (extracción → normalización → formatter Discord); triggers más claros y menos ambiguos; timeout diferenciado por agente; sanitización completa de salidas (Kimi/Albedo ya parcial).
- **Discord y UX:** Un solo mensaje con respuesta del agente (no «Enviado a X» + otro); pie de embed con badge de agente y opcional resumen de tarea; mensaje de procesando solo si >8s (ya hecho); límites por rol (ya hechos).
- **Seguridad y robustez:** Sanitizar paths y nombres de archivo en logs; no exponer rutas completas en producción; reforzar validación en tools que tocan sistema/archivos.
- **Observabilidad:** Health check de tools (ya hecho en 3.6); meta-report y decision_audit útiles para afinar intents; logs de intent suficientes para depuración sin ruido.

---

## BLOQUES DE TRABAJO (esquema 3.7)

### BLOQUE 1 — INTERACCIÓN (persona, DM, público, confirmaciones)

| Id   | Área                | Descripción |
|------|---------------------|-------------|
| 1.1  | Un solo mensaje     | Al delegar a Odín/Eva/Kimi/Albedo, no enviar «✅ Enviado a X» y luego otra respuesta; un único mensaje con la respuesta del agente y pie «Respondido por X». |
| 1.2  | Acuse con agente   | Si la delegación tarda >N s, opcionalmente enviar «🔮 Procesando con [Agente]…» (sabiendo el agente antes de ejecutar) y sustituir por la respuesta final, o no enviar nada hasta tenerla (configurable). |
| 1.3  | Confirmaciones     | Resumen claro de qué se va a ejecutar antes de pedir ✅/❌; no pedir de nuevo si el amo ya dijo «sí» o «confirmo» en el mismo hilo (ya reforzado en 3.6; validar en uso real). |
| 1.4  | Cooldown confirmación | Tras confirmar (✅) una acción peligrosa, no pedir confirmación de nuevo para la misma acción en los próximos N minutos (configurable). |
| 1.5  | Respuestas breves  | Cuando el usuario escribe muy poco («no», «nada», «sí»), respuesta breve (ya en DM_OWNER; extender a trusted/public si aplica). |
| 1.6  | Sin plantillas     | En DM, cero ENFOQUE/RIESGOS/EJECUCIÓN salvo que el contexto lo pida (ya en directivas y plan_executor para Eva). |
| 1.7  | Tono público       | En canal público, no hablar de proyectos/código; tono Albedo con no-amo; fuente de verdad (ya en 3.6). |

### BLOQUE 2 — MEMORIA

| Id   | Área                    | Descripción |
|------|-------------------------|-------------|
| 2.1  | Peso del hilo           | Ya configurable (thread_memory_max_exchanges, thread_memory_max_chars); revisar si el peso en el prompt es suficiente o aumentar prioridad del bloque. |
| 2.2  | Búsqueda por sinónimos  | Ya implementado en 3.6 (query_synonyms); ampliar vocabulario en Config/memory.json según dominio (personas, proyectos, términos). |
| 2.3  | Indexación/organización | Memoria semántica: etiquetas por temas, fechas o proyectos; permitir «busca en memoria sobre X» por tema, no solo por similitud vectorial. |
| 2.4  | Prioridad a hechos recientes | En búsqueda vectorial o en el merge de resultados, dar más peso a hechos con timestamp reciente. |
| 2.5  | Contexto de delegación (Odín IV) | Mantener buffer de últimas N delegaciones (agente, tipo, resumen) e inyectarlo al invocar el siguiente agente para coherencia multi-agente. |
| 2.6  | Export memoria del hilo | Comando o endpoint (solo owner) para exportar la memoria de un canal/hilo a JSON o texto (backup o análisis). |
| 2.7  | Feedback → memoria     | Vincular /feedback y episodios para refuerzo de patrones; que las correcciones del amo influyan en sugerencias de intents o en qué guardar en memoria. |
| 2.8  | Resúmenes de sesión    | Revisar cuándo y cómo se escriben; no duplicar ni saturar el contexto; límites claros en memory.json. |

### BLOQUE 3 — TOOLS Y DELEGACIÓN

| Id   | Área                | Descripción |
|------|---------------------|-------------|
| 3.1  | Pipeline tres velos | (I) Extracción por agente: Kimi → .content.text, Albedo → .analysis.result, etc. (II) Normalizador: quitar metadatos, pasar a markdown. (III) Formatter Discord: límite por chunk, embeds, indicador de agente. Sanitización Kimi ya existe; generalizar para todos los agentes. |
| 3.2  | Acuse y retorno     | Fase de acuse inmediata («🔮 Odín recibe tu consulta…»); fase de ejecución; fase de retorno con badge de agente y opción ✅/🔄 si aplica. |
| 3.3  | Triggers delegación | Estructura [VERBO] + [AGENTE] + [CONTENIDO]; más triggers «invoca a», «pregunta a», «usa a» por agente; rechazo explícito de ambigüedad (fallback a conversación, no a tool). |
| 3.4  | Timeout por agente  | Configurable en memory.json o security.json: Kimi/Albedo 120s, Eva/Adán 60s, Lucifer 30s; aplicar en agent_caller o en cada tool. |
| 3.5  | Sanitización salida | Garantizar que ninguna salida cruda (TurnBegin, ThinkPart, logs) llegue a Discord; extensión a Albedo CLI y Cursor si aplica. |
| 3.6  | Voz de las tools    | Cuando tenga sentido, que la salida del agente se resuma o adapte al tono Lilith (sin cambiar el contenido crítico). |

### BLOQUE 4 — DISCORD (bot, API, embeds)

| Id   | Área              | Descripción |
|------|-------------------|-------------|
| 4.1  | Un solo mensaje   | Evitar doble respuesta al delegar (mensaje de acuse + respuesta genérica); un único embed con la respuesta del agente. |
| 4.2  | Pie del embed     | «Respondido por X» + timestamp (ya en 3.6); opcional: «Tarea: [primeros 50 chars]» para contexto. |
| 4.3  | Procesando        | Mensaje «⏳ Procesando…» solo si >8s (hecho); opcionalmente incluir nombre del agente si se conoce de antemano. |
| 4.4  | Reacción          | Reacción 👀 al recibir; cambiar a ✅ o 💜 al terminar; consistencia en todos los flujos. |
| 4.5  | Descripción bot   | Dejar claro que se cambia en Developer Portal; mensaje único y breve si el amo lo pide (ya en DM_OWNER). |
| 4.6  | Límites por rol   | max_response_chars_public / max_response_chars_trusted ya implementados; revisar valores según feedback. |

### BLOQUE 5 — SEGURIDAD Y ROBUSTEZ

| Id   | Área           | Descripción |
|------|----------------|-------------|
| 5.1  | Paths en logs  | No loguear paths completos ni nombres de archivo sensibles en DEBUG en producción; solo «read_file ejecutado» o path sanitizado (sin directorios de usuario). |
| 5.2  | Input y paths  | Revisar sanitización y _INVALID_PATH_TOKENS en planner; validación en file_read, list_directory, gather_directory. |
| 5.3  | Fuente de verdad | Ya reforzada en 3.6; mantener ejemplos de rechazo en prompt. |

### BLOQUE 6 — RENDIMIENTO Y OBSERVABILIDAD

| Id   | Área          | Descripción |
|------|---------------|-------------|
| 6.1  | Caché         | Opción en memory.json: no usar agent_response_cache cuando role=owner y channel=dm, para respuestas siempre frescas. |
| 6.2  | Health check  | GET /api/discord/tools-status ya implementado en 3.6; documentar y usar en monitoreo. |
| 6.3  | Audit y meta  | decision_audit y meta-report: retención, resumen y uso para afinar intents (sugerencias desde uso real). |
| 6.4  | Logs de intent| Log DEBUG del intent elegido y tool/paso; suficiente para depurar falsos positivos sin ruido. |

---

## IDEAS COMPLETAS — RECOPILACIÓN EXHAUSTIVA (BLOQUES A–Z)

A continuación se listan **todas las ideas posibles** para mejorar interacción, memoria, tools, Discord, seguridad, observabilidad, comandos, formato, errores, idioma, límites, testing, documentación, personalización, contexto de canal/hilo, aprendizaje, resiliencia, sesiones, tokens/LLM, usuario/permisos, validación, workspace, export/integración, ecosistema Yggdrasil y entornos/despliegue. Sirven como backlog y como fuente para priorizar tareas concretas en 3.7.

### A. INTERACCIÓN

| # | Idea | Detalle |
|---|------|---------|
| A1 | Un solo mensaje por delegación | No enviar «Enviado a Odín» y luego otra respuesta; un único mensaje con la respuesta del agente y pie «Respondido por Odín». |
| A2 | Acuse con nombre de agente | «🔮 Procesando con Odín…» cuando se sabe el agente antes de ejecutar (requiere conocer el plan antes de la llamada async). |
| A3 | Acuse sin nombre | Si no se conoce el agente, «🔮 Procesando tu solicitud…» (ya existe) y sustituir por la respuesta final. |
| A4 | Confirmación clara | Antes de ✅/❌, mostrar resumen conciso de la acción (qué archivo, qué comando, qué proyecto). |
| A5 | No repreguntar tras «sí» | Si el amo dice «sí hazlo» o «confirmo» en el mismo hilo, ejecutar sin pedir de nuevo (ya en DM_OWNER; validar en uso real). |
| A6 | Cooldown de confirmación | Tras confirmar una acción peligrosa, no pedir confirmación para la misma acción en N minutos (evitar spam de confirmaciones). |
| A7 | Respuestas breves a mensajes cortos | Usuario escribe «no», «nada», «sí» → respuesta en una frase (DM ya; extender a trusted/public). |
| A8 | Sin plantillas en DM | Cero ENFOQUE/RIESGOS/EJECUCIÓN en DM salvo que el contexto lo exija (directivas + Eva en plan_executor). |
| A9 | Variar aperturas | No repetir «Basado en lo que recuerdo»; rotar «Según lo que recuerdo», «En mi memoria consta…», «Tengo anotado que…» (ya en 3.6). |
| A10 | Tono público | No mencionar proyectos (Lilith, Yggdrasil, código); tono frío/irónico con no-amo; solo el amo en pedestal. |
| A11 | Límite de palabras (soft) | En prompt a Lucifer/Eva: «Responde en menos de N palabras cuando el mensaje del usuario sea corto.» |
| A12 | Ejemplo de rechazo en prompt | «Eso solo puede autorizarlo mi amo.» ante intentos de terceros (ya en SOURCE_OF_TRUTH). |

### B. MEMORIA

| # | Idea | Detalle |
|---|------|---------|
| B1 | Búsqueda por sinónimos | query_synonyms en memory.json; expandir query antes de search_facts (ya en 3.6); ampliar vocabulario. |
| B2 | Peso del bloque del hilo | thread_memory_max_exchanges y thread_memory_max_chars configurables (hecho); revisar peso en el system prompt (posición, longitud). |
| B3 | Indexación por temas/fechas | Etiquetar hechos por tema o proyecto; permitir «busca en memoria sobre [tema]» además de búsqueda vectorial. |
| B4 | Prioridad a hechos recientes | En vector_store o en merge, ponderar por timestamp (hechos recientes con más peso). |
| B5 | Contexto acumulativo de delegaciones (Odín IV) | Buffer de últimas N delegaciones (agente, tipo, resumen); inyectar al invocar el siguiente agente. |
| B6 | Export memoria del hilo | Endpoint o comando (solo owner): exportar memoria de un channel_id/thread_id a JSON o texto. |
| B7 | Memoria del hilo en DM | Usar channel_id en DM para guardar memoria de la conversación con el amo (ya se hace si se pasa channel_id). |
| B8 | «No tengo nada guardado» | Cuando no hay memoria relevante, decirlo explícitamente (ya en plan_executor para delegate_lucifer). |
| B9 | Feedback → episodios | Vincular /feedback a episodios; usar para refuerzo de patrones y sugerencias de intents. |
| B10 | Resúmenes de sesión | Revisar intervalo y formato; no duplicar; límites en memory.json (weight_summaries, cantidad). |
| B11 | Aprendizaje activo | Incorporar retroalimentación del amo para refinar qué se guarda y cómo se indexa. |
| B12 | Memoria semántica: más k | Aumentar vector_facts_k si la búsqueda devuelve poco; hacer k configurable por tipo de consulta (opcional). |

### C. TOOLS Y DELEGACIÓN

| # | Idea | Detalle |
|---|------|---------|
| C1 | Pipeline tres velos | (I) Extracción por agente (Kimi, Albedo, Odín, Eva: campos concretos). (II) Normalizador (quitar metadatos, markdown). (III) Formatter Discord (chunks, embeds, agente). |
| C2 | Sanitización Kimi | Ya implementada (_sanitize_kimi_output); asegurar que Albedo y Cursor tengan equivalente si devuelven logs crudos. |
| C3 | Triggers explícitos | Más triggers «invoca a X», «pregunta a X», «usa a X»; rechazo de ambigüedad (si no está claro, fallback a conversación). |
| C4 | Timeout por agente | memory.json o security.json: timeout_kimi, timeout_albedo, timeout_eva, etc.; aplicar en tools o en agent_caller. |
| C5 | Truncar task | Ya en 3.6 (4000 chars); mantener y documentar. |
| C6 | Retry en timeout | Kimi ya tiene reintento con timeout+30s; considerar para Albedo si aplica. |
| C7 | Health check tools | GET /api/discord/tools-status (kimi_cli, albedo_workspace, cursor_cli) ya en 3.6. |
| C8 | Voz Lilith en salida | Opcional: resumir o adaptar al tono Lilith la salida del agente cuando sea largo o muy técnico. |
| C9 | Badge de agente en retorno | Siempre pie «Respondido por X»; opcional badge visual o color por agente (ya hay AGENT_COLORS). |

### D. DISCORD Y UX

| # | Idea | Detalle |
|---|------|---------|
| D1 | Un solo mensaje | Al delegar, un único mensaje con la respuesta del agente (no acuse + respuesta por separado que confunda). |
| D2 | Pie del embed | «Respondido por X · HH:MM UTC» (ya en 3.6); opcional «Tarea: [50 chars]». |
| D3 | Procesando solo si >8s | Ya implementado en chat_handler; mantener. |
| D4 | Reacción al mensaje | 👀 al recibir; ✅ o 💜 al terminar; consistente en todos los flujos (owner, trusted, public). |
| D5 | Truncado elegante | Chunks de 4000 (Discord límite 4096); cortar en párrafo/frase con «…» o «(1/2)»; pie solo en último chunk (hecho). |
| D6 | Límite por rol | max_response_chars_public, max_response_chars_trusted (hecho); mensaje «… (respuesta recortada)» si se trunca. |
| D7 | Descripción del bot | No editable por API; indicar Developer Portal y opcionalmente repetir la descripción acordada (ya en DM_OWNER). |
| D8 | Color por agente | AGENT_COLORS ya; mantener coherencia con badge y pie. |
| D9 | Slash vs mensaje | Evitar que un slash que delega envíe un mensaje y además responda al comando con algo distinto; un solo flujo de respuesta. |

### E. SEGURIDAD Y ROBUSTEZ

| # | Idea | Detalle |
|---|------|---------|
| E1 | Paths en logs | No loguear paths completos en producción; sanitizar (solo «read_file ejecutado» o path relativo sin /home/user). |
| E2 | Nombres de archivo en logs | No exponer nombres de archivo sensibles en DEBUG; opción de desactivar logs de paths. |
| E3 | Input y _INVALID_PATH_TOKENS | Mantener y ampliar si aparecen nuevos falsos positivos (tu, el, api, etc.). |
| E4 | Validación en tools | file_read, list_directory, gather_directory: validar path antes de usar; rechazar rutas que escapen del workspace. |
| E5 | Fuente de verdad | Mantener SOURCE_OF_TRUTH_INSTRUCTION y ejemplo de rechazo. |

### F. RENDIMIENTO Y OBSERVABILIDAD

| # | Idea | Detalle |
|---|------|---------|
| F1 | Caché por contexto | Clave de caché estable (sufijo de context); no repetir respuesta en contextos distintos (ya mejorado en 3.6). |
| F2 | Desactivar caché en owner DM | Opción en memory.json: no usar agent_response_cache cuando role=owner y channel=dm. |
| F3 | TTL y límites | agent_cache_ttl_seconds, agent_cache_max_files; revisar según uso. |
| F4 | Lazy loading | Tools cargadas bajo demanda; no fallar arranque si una tool no está disponible (registro lazy). |
| F5 | Health check | /api/discord/tools-status; usar en monitoreo o en un comando /status para el amo. |
| F6 | decision_audit | Retención (audit_max_entries, audit_max_days); resumen para afinar intents. |
| F7 | meta-report | Endpoint o informe que resuma uso de intents, tools y errores recientes. |
| F8 | Log DEBUG intent | Planner y orchestrator: log del intent elegido y tool; suficiente para depuración (ya en planner). |
| F9 | Logs sin ruido | En producción, nivel INFO o WARNING; DEBUG solo si se activa explícitamente. |

### G. VALIDACIÓN Y CIERRE 3.6 (heredados)

| # | Idea | Detalle |
|---|------|---------|
| G1 | Timeout en canal público | Si con rol public la petición da «Lilith timeout» o >120s, investigar causa (latencia API, flujo public). |
| G2 | «Sí hazlo» en uso real | Confirmar con el amo que tras una petición clara, «sí hazlo» hace que Lilith actúe sin repreguntar. |

### H. COMANDOS Y SLASH COMMANDS

| # | Idea | Detalle |
|---|------|---------|
| H1 | Unificación slash + mensaje | Que /comando y mensaje en canal produzcan el mismo flujo; misma respuesta, mismo formato, sin duplicar lógica. |
| H2 | Descripción de slash | Descripciones claras en cada comando (qué hace, ejemplos); actualizar con cada nuevo intent relevante. |
| H3 | Slash sin doble respuesta | Al usar slash que delega (ej. /pregunta), no enviar «Enviado a X» por un lado y respuesta por otro; un solo mensaje. |
| H4 | Comando /status | Slash (solo owner) que llame a GET /api/discord/tools-status y muestre estado de Kimi, Albedo, Cursor en un embed. |
| H5 | Comando /memoria | Slash (owner) para exportar memoria del hilo actual o de un canal dado (invoca export memoria del hilo). |
| H6 | Comando /patrones | Ya existe; asegurar que muestre learned + suggested de forma legible; opcional filtro por intent. |
| H7 | Autocompletado de intents | Si Discord lo permite, sugerir comandos o parámetros según contexto (ej. «invoca a» → lista de agentes). |
| H8 | Cooldown por comando | Evitar spam: cooldown configurable por slash o por usuario en canales públicos. |

### I. RESPUESTAS, FORMATO Y TEXTO

| # | Idea | Detalle |
|---|------|---------|
| I1 | Markdown consistente | Respuestas en markdown válido para Discord (listas, negrita, código); no romper con caracteres especiales. |
| I2 | Bloques de código | Si la respuesta incluye código, envolver en ``` con lenguaje cuando se detecte; límite de longitud por bloque. |
| I3 | Enlaces y menciones | No escapar @ ni enlaces si son intencionados; sanitizar solo donde haya riesgo de inyección. |
| I4 | Emojis en respuesta | Permitir emojis en respuestas de Lilith/agentes cuando el tono lo permita; coherente con persona. |
| I5 | Longitud mínima útil | Evitar respuestas de una palabra cuando el usuario esperaba desarrollo; umbral configurable por tipo de consulta. |
| I6 | Resumen antes de detalle | En respuestas muy largas, opcional: primera línea como resumen y luego «Detalle: …». |
| I7 | Listas numeradas vs viñetas | Usar listas numeradas para pasos o prioridad; viñetas para ítems sin orden. |
| I8 | Evitar repetición de pregunta | No repetir la pregunta del usuario al inicio de la respuesta salvo que sea útil para contexto. |

### J. ERRORES Y RECUPERACIÓN

| # | Idea | Detalle |
|---|------|---------|
| J1 | Mensaje de error amigable | En vez de «Error: ConnectionTimeout», mensaje tipo «No pude conectar con el servicio; inténtalo en un momento.» |
| J2 | Sugerencia en error | Si falla read_file por «no encontrado», sugerir «¿Querías decir [path similar]?» cuando haya candidatos. |
| J3 | Reintento transparente | Reintentos ya en Kimi CLI; documentar y extender a otras tools si fallan por red/timeout. |
| J4 | Fallback a Lucifer en error | Si un agente delegado falla, opcionalmente responder con Lucifer con contexto «El agente X falló; responde tú.» |
| J5 | No dejar colgado | Siempre responder algo al usuario (mensaje de error o fallback); no dejar el mensaje «Procesando…» indefinido (ya manejado en 3.6). |
| J6 | Log de error con contexto | Al fallar una tool, log con intent, tool_name y causa; sin datos sensibles. |
| J7 | Códigos de error internos | Código corto (ej. LILITH_E001) para errores conocidos; en respuesta solo mensaje amigable; código en log. |
| J8 | Recuperación tras caída | Si la API se reinicia, que el bot de Discord reconecte y no pierda mensajes en cola (reconnect + estado). |

### K. IDIOMA Y TONO

| # | Idea | Detalle |
|---|------|---------|
| K1 | Español por defecto | Todas las respuestas y mensajes de sistema en español; términos técnicos en inglés cuando aplique (ya en persona). |
| K2 | Tuteo vs ustedeo | Definir en persona: tuteo con el amo, ustedeo o tuteo con otros según canal; coherente en todo el flujo. |
| K3 | Tono por canal | DM: cercano y directo; público: más frío/irónico con no-amo; trusted: intermedio (ya en directivas). |
| K4 | Evitar jerga innecesaria | No abusar de siglas o términos internos (Lilith, Yggdrasil, backend) en respuestas a usuarios no-owner. |
| K5 | Consistencia de nombres | Siempre los mismos nombres para agentes (Odín, Eva, Lucifer, Adán, Kimi, Albedo) en pies y mensajes. |
| K6 | Mensajes de sistema traducidos | «Procesando…», «Confirmación requerida», etc. en español y coherentes con el tono del bot. |

### L. LÍMITES Y RATE LIMITING

| # | Idea | Detalle |
|---|------|---------|
| L1 | Límite de mensajes por minuto | Por usuario o por canal: rechazar o encolar si se supera N mensajes/min (evitar spam y coste de API). |
| L2 | Límite de longitud de entrada | Mensaje del usuario truncado o rechazado si supera X caracteres (ej. 2000); mensaje claro al usuario. |
| L3 | Límite de delegaciones simultáneas | No lanzar más de N delegaciones a la vez por usuario (evitar colapso de Kimi/Albedo). |
| L4 | Límite de tamaño de contexto | Si el contexto (historial + memoria) supera umbral, resumir o truncar antes de enviar al LLM. |
| L5 | Backpressure en cola | Si hay muchas peticiones pendientes, responder «Demasiadas peticiones; espera un momento.» en lugar de colgar. |
| L6 | Límite por rol | Public/trusted ya tienen límite de respuesta; opcional límite de frecuencia de uso por rol. |

### M. TESTING Y CALIDAD

| # | Idea | Detalle |
|---|------|---------|
| M1 | Tests de intents | Mantener y ampliar test_planner_intents_36.py; añadir casos por cada nuevo trigger crítico. |
| M2 | Tests de integración Discord | Tests que simulen mensaje → API → respuesta; sin bot real, solo HTTP. |
| M3 | Tests de memoria | Tests para thread_memory (load/append), semantic search con sinónimos, export. |
| M4 | Tests de sanitización | Casos: path con .., caracteres raros, inyección en mensaje; asegurar que no lleguen a filesystem. |
| M5 | Regresión de directivas | Snapshot o checklist: cambiar persona/directivas no debe romper respuestas esperadas en casos clave. |
| M6 | Cobertura de tools | Al menos un test por tool (execute con params válidos e inválidos). |
| M7 | Tests de pipeline tres velos | Cuando exista: test de extracción + normalización para cada agente (Kimi, Albedo, etc.). |

### N. DOCUMENTACIÓN Y MANTENIMIENTO

| # | Idea | Detalle |
|---|------|---------|
| N1 | README por módulo | Backend/core, Discord, API: README breve con propósito, dependencias y cómo probar. |
| N2 | Documentar intent_patterns | Comentarios o doc aparte: qué intent hace qué, prioridades, ejemplos de triggers. |
| N3 | Changelog por misión | En cada MISION_LILITH_X.Y.md, sección «Cambios realizados» con lista de archivos y comportamientos. |
| N4 | Configuración centralizada | Toda la config en Config/*.json documentada (qué clave, valores válidos, por qué). |
| N5 | Diagrama de flujo | Diagrama texto o Mermaid: mensaje Discord → API → planner → executor → respuesta. |
| N6 | Guía de contribución | Cómo añadir un nuevo intent, una nueva tool, una nueva directiva; dónde tocar. |
| N7 | Deprecación clara | Si se depreca un endpoint o comportamiento, log + mensaje al usuario y fecha de retirada. |

### O. PERSONALIZACIÓN Y CONFIGURACIÓN

| # | Idea | Detalle |
|---|------|---------|
| O1 | Persona por archivo | Workspace/Alma/persona.md como fuente de verdad; fallback en código solo si no existe. |
| O2 | Override de directivas | Opción en config para añadir bloques de instrucción extra al system prompt (por rol o global). |
| O3 | query_synonyms ampliables | El amo puede editar memory.json y añadir sinónimos sin tocar código. |
| O4 | Colores por agente editables | Config (ej. discord_embed_colors.json) para cambiar AGENT_COLORS sin tocar chat_handler. |
| O5 | Triggers sin redeploy | Cargar intent_patterns.json en caliente o vía admin; no obligar a reiniciar para añadir un trigger. |
| O6 | Límites editables | max_response_chars_*, timeouts, thread_memory_* en memory.json; documentados. |
| O7 | Feature flags | Opciones tipo use_acuse, use_delegation_context para activar/desactivar features sin código. |

### P. CANAL, HILO Y CONTEXTO

| # | Idea | Detalle |
|---|------|---------|
| P1 | channel_id siempre presente | Asegurar que el cliente Discord envíe channel_id (y thread_id si es hilo) en todas las peticiones de chat. |
| P2 | Memoria por thread_id | En hilos, usar thread_id como clave de memoria; en canal sin hilo, channel_id; sin mezclar. |
| P3 | Límite de hilos activos | No cargar memoria de más de N hilos recientes para no saturar; LRU o por última actividad. |
| P4 | Contexto de canal en prompt | Inyectar en el prompt que «estás en el canal #nombre» o «en el hilo X» para que Lilith adapte respuestas. |
| P5 | Permisos por canal | Respetar allowed_channels y discord_roles; mensaje claro si el usuario escribe en canal no permitido. |
| P6 | Nombre del canal en logs | En logs de auditoría, incluir nombre del canal (o id) para depuración; sin exponer en respuesta. |
| P7 | Historial por hilo | history en la petición: solo mensajes del mismo hilo/canal; no mezclar con otros canales. |

### Q. APRENDIZAJE Y MEJORA CONTINUA

| # | Idea | Detalle |
|---|------|---------|
| Q1 | LearningEngine → intents | Las sugerencias de intents desde decision_audit que ya existen; flujo para que el amo pueda aplicarlas en intent_patterns. |
| Q2 | Feedback explícito | /feedback con valoración o texto; guardar en episodios y usar para ponderar qué intents funcionan mejor. |
| Q3 | Aprendizaje de rechazos | Si el usuario corrige («no, quise decir X»), registrar y usar para afinar triggers o prioridades. |
| Q4 | Métricas de uso | Contar invocaciones por intent y por tool; resumen en meta-report para ver qué se usa más. |
| Q5 | Sugerencia de sinónimos | Si una búsqueda en memoria no devuelve nada pero hay hechos similares, sugerir al amo añadir sinónimos. |
| Q6 | Mejora de resúmenes | Ajustar session_summary_interval y formato según feedback; que los resúmenes sean útiles en el prompt. |
| Q7 | Refinamiento de persona | Tras cambios en persona.md, validar con preguntas tipo y ajustar si las respuestas se desvían del tono deseado. |

### R. RESILIENCIA Y DISPONIBILIDAD

| # | Idea | Detalle |
|---|------|---------|
| R1 | Reconexión del bot | Si el bot de Discord se desconecta, reconectar con backoff exponencial; no perder mensajes pendientes si la API sigue up. |
| R2 | Timeout de API configurable | Timeout global de la petición Discord → API (ej. 120s) configurable; mensaje claro si se supera. |
| R3 | Circuit breaker por agente | Si Kimi/Albedo fallan N veces seguidas, no invocarlos durante M minutos; fallback a Lucifer o mensaje. |
| R4 | Estado de salud de la API | Endpoint GET /api/health que devuelva ok + versión + dependencias (DB, vector store si aplica). |
| R5 | Graceful shutdown | Al cerrar la API, terminar las peticiones en curso y no aceptar nuevas; el bot no debe crashear si la API se apaga. |
| R6 | Reintentos con backoff | En llamadas a servicios externos (Kimi API, etc.), reintentos con backoff; no repetir al instante. |
| R7 | Límite de memoria del proceso | Vigilar uso de memoria en procesos largos (orchestrator, plan_executor); liberar contextos grandes tras usar. |
| R8 | Logs rotativos | Evitar que los logs llenen disco; rotación por tamaño o por día; retención configurable. |

### S. SESIONES Y ESTADO

| # | Idea | Detalle |
|---|------|---------|
| S1 | Sesión por usuario | Asociar conversación a user_id; persistir preferencias o estado ligero por usuario (sin guardar contenido sensible). |
| S2 | Limpieza de estado inactivo | Borrar o archivar memoria de hilos/canales sin actividad en N días; configurable en memory.json. |
| S3 | Pending confirmations TTL | Las confirmaciones pendientes (✅/❌) expiran tras N minutos; limpiar _pending_confirmations y notificar si caducó. |
| S4 | Estado del orchestrator | No dejar estado global sucio entre peticiones; _last_executed_tool y similares por request o limpiados al final. |
| S5 | Idempotencia de guardado | Al guardar hecho o episodio, evitar duplicados por mismo contenido + ventana temporal. |
| S6 | Sesión de Discord | Si el bot pierde la sesión, no reintentar enviar a un canal/hilo cerrado; validar antes de responder. |

### T. TOKENS, LLM Y MODELOS

| # | Idea | Detalle |
|---|------|---------|
| T1 | Límite de tokens en prompt | Truncar system_prompt + history + mensaje para no superar límite del modelo (ej. 8k/32k); cortar por tokens o por chars aproximados. |
| T2 | Modelo por agente | Configurar qué modelo usa cada agente (Lucifer, Eva, Odín, etc.) en config; no hardcodear. |
| T3 | Temperatura por contexto | DM vs público: temperatura o parámetros distintos si el backend lo permite (más creativo en DM, más estable en público). |
| T4 | Coste o uso estimado | Opcional: log o contador de tokens enviados/recibidos por agente para estimar coste (sin bloquear flujo). |
| T5 | Fallback de modelo | Si el modelo principal falla, opción de usar otro (ej. Lucifer con modelo B si A no responde). |
| T6 | Respuesta corta por defecto | Instrucción en prompt: «Responde en menos de N palabras cuando no se pida explícitamente detalle.» (soft limit). |

### U. USUARIO Y PERMISOS

| # | Idea | Detalle |
|---|------|---------|
| U1 | user_id en todas las peticiones | Asegurar que Discord envíe user_id (y opcionalmente username) para auditoría y permisos. |
| U2 | Mapeo user_id → rol | Un mismo user_id siempre con el mismo rol (owner/trusted/public) según discord_roles y allowed_users. |
| U3 | Permisos por comando | Algunos slash solo para owner; otros para trusted; documentar y validar en cada endpoint. |
| U4 | Bloqueo de usuario | Lista de user_id bloqueados (config o API); no procesar mensajes ni devolver respuesta a esos usuarios. |
| U5 | Identificación en logs | En logs de auditoría, user_id o hash; nunca datos personales en claro en producción. |
| U6 | Multi-owner | Si en el futuro hay más de un owner, config como lista; todas las directivas de «amo» aplican a cualquiera de la lista. |

### V. VALIDACIÓN Y ESQUEMAS

| # | Idea | Detalle |
|---|------|---------|
| V1 | Validación Pydantic estricta | DiscordChatRequest y demás modelos con tipos estrictos; rechazar peticiones mal formadas con 422 y mensaje claro. |
| V2 | Longitud máxima de campos | text, history, context: límites por campo; truncar o rechazar con mensaje explicativo. |
| V3 | Valores permitidos | role en ['owner','trusted','public']; channel_id formato esperado; no aceptar valores arbitrarios. |
| V4 | Validación de path en tools | Antes de read_file, list_directory, gather_directory: path dentro de workspace; sin .. ni enlaces simbólicos peligrosos. |
| V5 | Sanitización de salida | Antes de enviar a Discord: quitar caracteres nulos, control characters; asegurar UTF-8 válido. |
| V6 | Esquema de intent_patterns | Validar al cargar que cada intent tenga name, priority; triggers sea lista; tool/agent exista. |

### W. WORKSPACE Y PROYECTOS

| # | Idea | Detalle |
|---|------|---------|
| W1 | Raíz de workspace única | Todas las tools que leen/escriben archivos usan la misma base_path (project_root); no rutas absolutas sueltas. |
| W2 | project_tool coherente | Crear/listar/añadir tarea a proyectos; mensajes de éxito/error claros; no fallar si el archivo de proyectos no existe (crear por defecto). |
| W3 | Contexto de proyecto actual | Si el usuario dice «en el proyecto X», inyectar ese contexto en el prompt o en la tool que corresponda. |
| W4 | Límite de proyectos | No permitir número ilimitado de proyectos si se guardan en JSON; límite configurable o paginación. |
| W5 | Workspace en tools-status | Incluir en /api/discord/tools-status si el workspace (raíz) existe y es accesible. |
| W6 | Paths relativos | Todas las rutas en logs y en respuestas hacia el usuario, relativas al workspace; no exponer rutas absolutas del servidor. |

### X. EXPORT E INTEGRACIÓN

| # | Idea | Detalle |
|---|------|---------|
| X1 | Export memoria a JSON | Endpoint o comando: volcar memoria del hilo/canal a JSON (solo owner); formato legible y con timestamps. |
| X2 | Export episódica | Export de últimos N episodios (conversaciones) para backup o análisis; sin contenido sensible si hay filtro. |
| X3 | Webhook de eventos | Opcional: al terminar una delegación o guardar hecho, enviar webhook (URL configurable) con payload mínimo; para integraciones. |
| X4 | Import de hechos | Endpoint o script: importar hechos desde JSON a memoria semántica (batch); validar formato. |
| X5 | Sincronización con Alma | Si Workspace/Alma tiene más archivos (persona, etc.), documentar cuáles se leen y con qué prioridad. |
| X6 | API pública estable | Versión en la URL o en header; no romper contrato de /api/discord/chat entre versiones menores. |

### Y. YGGDRASIL Y ECOSISTEMA

| # | Idea | Detalle |
|---|------|---------|
| Y1 | Albedo en workspace | Ruta a Albedo (Yggdrasil/Vanaheim/Albedo) configurable; tools-status y delegate_albedo usan la misma. |
| Y2 | Dependencias entre componentes | Documentar: Lilith depende de API, Discord bot, opcionalmente Kimi CLI, Albedo workspace; no asumir orden de arranque frágil. |
| Y3 | Nombres de agentes unificados | Odín, Eva, Lucifer, Adán, Kimi, Albedo: mismos nombres en toda la doc y en respuestas; sin alias confusos. |
| Y4 | Contexto Yggdrasil en prompt | Si aplica, inyectar que «formas parte del ecosistema Yggdrasil» solo cuando sea relevante (no en respuestas públicas genéricas). |
| Y5 | Logs y trazabilidad cruzada | Si varios componentes escriben logs, formato común (ej. request_id o session_id) para correlacionar. |
| Y6 | Versión de Lilith | Variable o archivo con versión (ej. 3.7.0); exponer en /api/version o /api/status para monitoreo. |

### Z. ZONAS, ENTORNOS Y DESPLIEGUE

| # | Idea | Detalle |
|---|------|---------|
| Z1 | Variables de entorno | Secrets (API keys, tokens) solo por env; nunca en repo; documentar .env.example con todas las claves necesarias. |
| Z2 | Config por entorno | Opcional: memory.json, security.json distintos para dev/staging/prod; o overrides por env (ej. LILITH_ENV=prod). |
| Z3 | Log level por entorno | En producción, INFO o WARNING; DEBUG solo si LILITH_DEBUG=1 o similar. |
| Z4 | Deshabilitar features en prod | Opciones para desactivar tools experimentales o endpoints de debug en producción. |
| Z5 | Health sin datos sensibles | /api/health o /api/status no deben devolver rutas completas, tokens ni datos de usuarios. |
| Z6 | Arranque en orden | Script o doc: arrancar API primero, luego Discord bot; o un solo entrypoint que levante ambos. |
| Z7 | Reinicio sin pérdida | Si se reinicia la API, confirmaciones pendientes en disco se cargan; mensaje al usuario si su confirmación expiró. |
| Z8 | Límites de recursos | En producción, límites de memoria/CPU para el proceso; evitar que un pico de uso tumbe el servidor. |

---

## TAREAS DERIVADAS DE 3.6 (pendientes → 3.7)

| Origen 3.6 | Tarea | Bloque 3.7 |
|------------|--------|------------|
| Q3        | Aumentar peso del bloque de memoria del hilo; búsqueda por sinónimos (ya sinónimos; peso revisar) | 2.1, B2 |
| Q3        | Indexación/organización de memoria (temas, fechas); aprendizaje activo con feedback | 2.3, 2.7, B3, B11 |
| Odín I    | Revisar triggers de delegación; exigir claridad antes de invocar tool | 3.3, C3 |
| Odín II   | Pipeline tres velos completo (extracción → normalización → formatter Discord) | 3.1, C1 |
| Odín III  | Acuse breve + retorno estructurado con badge de agente | 3.2, 4.1, A2, C9 |
| Odín IV   | Contexto acumulativo de delegaciones para siguiente agente | 2.5, B5 |
| Ideas 3.6 | Acuse opcional; truncado embeds; tests intents (hecho); límite caracteres por rol (hecho); export memoria hilo; health check (hecho); cooldown confirmación; timeout por agente; memoria semántica priorizar recientes; desactivar caché owner DM; sanitizar nombres archivo en logs | Varios bloques |

---

## ORDEN DE EJECUCIÓN PROPUESTO (3.7)

| Fase | Acción | Bloques |
|------|--------|---------|
| 1 | Un solo mensaje por delegación + acuse con badge (Discord + API) | 1.1, 1.2, 3.2, 4.1 |
| 2 | Pipeline tres velos: normalizador y formatter para todos los agentes | 3.1, C1, C2 |
| 3 | Memoria: peso del hilo en prompt; contexto de delegación (Odín IV) | 2.1, 2.5 |
| 4 | Triggers y ambigüedad: más triggers, fallback a conversación | 3.3, C3 |
| 5 | Timeout por agente; sanitización paths en logs | 3.4, 5.1, E1 |
| 6 | Export memoria del hilo; cooldown confirmación; opción caché owner DM | 2.6, 1.4, F2 |
| 7 | Indexación memoria (temas/fechas) y prioridad a hechos recientes (si viable sin romper) | 2.3, 2.4 |
| 8 | Validación en entorno real con checklist 3.7 | — |

---

## ARCHIVOS CLAVE POR BLOQUE (3.7)

| Bloque | Archivos principales |
|--------|----------------------|
| 1 Interacción | `Backend/api/discord_api.py`, `Backend/core/plan_executor.py`, `Discord/handlers/chat_handler.py` |
| 2 Memoria | `Backend/core/memory/manager.py`, `Backend/core/discord_thread_memory.py`, `Backend/memory/semantic_memory.py`, `Backend/core/memory/semantic/vector_store.py`, `Config/memory.json` |
| 3 Tools | `Backend/core/planner.py`, `Backend/core/agent_caller.py`, `Backend/core/tools_v3/kimi_cli_tool.py`, `albedo_cli_tool.py`, `Backend/core/plan_executor.py` |
| 4 Discord | `Discord/handlers/chat_handler.py`, `Discord/bot.py`, `Backend/api/discord_api.py` |
| 5 Seguridad | `Backend/core/input_sanitizer.py`, `Backend/core/planner.py`, `Config/security.json`, logs en tools |
| 6 Rendimiento | `Backend/core/agent_response_cache.py`, `Config/memory.json`, `Backend/core/auditor/decision_auditor.py` |

---

## CHECKLIST DE VALIDACIÓN 3.7 (entorno real)

- [ ] **Un solo mensaje:** Al decir «Odín, analiza X», se recibe un único mensaje con la respuesta de Odín y pie «Respondido por Odín» (no «Enviado a Odín» + otro mensaje).
- [ ] **Acuse (si activo):** Si tarda >8s, aparece «Procesando con [Agente]» o «Procesando…» y luego se sustituye por la respuesta (o solo la respuesta final según config).
- [ ] **Confirmación:** Resumen claro antes de ✅/❌; tras «sí hazlo» no se pide confirmación de nuevo.
- [ ] **Memoria del hilo:** Varios intercambios en un hilo; pregunta que dependa del contexto; la respuesta refleja ese contexto.
- [ ] **Memoria semántica:** «Busca en tu memoria a [X]» devuelve hechos relevantes (con sinónimos si están en query_synonyms).
- [ ] **Delegación sin crudo:** Kimi/Albedo no muestran TurnBegin/ThinkPart en Discord.
- [ ] **Health check:** GET /api/discord/tools-status devuelve kimi_cli, albedo_workspace, cursor_cli.
- [ ] **Límites por rol:** Respuesta muy larga en canal público o trusted se trunca con «… (respuesta recortada)».
- [ ] **Logs:** No se exponen paths completos ni datos sensibles en logs en producción.

---

## PROCEDIMIENTO DE VALIDACIÓN Y DEBUG

Seguir este orden para validar la 3.7 y depurar si algo falla.

### 1. Arrancar servicios

- **API (Backend):** Desde la raíz del proyecto (donde está `Backend/`), arrancar el servidor FastAPI (por ejemplo `uvicorn Backend.api.server:app --reload` o el script/bat que uses). Comprobar que no hay errores de import ni de config.
- **Bot Discord:** Arrancar el bot (por ejemplo `python bot.py` o `python -m Discord.bot` desde la carpeta del bot). Debe conectar y mostrar "ready" o equivalente. Comprobar que `LILITH_API_URL` en config apunta a la API (ej. `http://127.0.0.1:8000`).

### 2. Health y tools-status

- **GET /api/status** o **GET /api/discord/tools-status:** Con curl o navegador, verificar que la API responde y que `tools-status` devuelve `kimi_cli`, `albedo_workspace`, `cursor_cli` (true/false). Si algo falla aquí, revisar PATH (kimi, cursor) y existencia de la carpeta Albedo.
- **GET /api/discord/thread-memory?channel_id=123&thread_id=456:** Debe devolver JSON con `messages` (vacío si no hay memoria). Si da 400, falta `channel_id`.

### 3. Probar chat (mensaje y slash)

- **Canal permitido / DM con el bot:** Enviar un mensaje de texto (ej. «Hola»). Debe responder un solo mensaje con embed y pie «Respondido por Lilith» (o por el agente si delegaste).
- **Slash /eva, /odin, etc.:** Ejecutar por ejemplo `/odin` con un argumento. No debe aparecer «Enviado a Odín» en el canal; solo el acuse ephemeral «Listo.» y un único mensaje con la respuesta de Odín y pie «Respondido por Odín».
- **Delegación Kimi/Albedo:** Pedir algo que use Kimi o Albedo. La respuesta en Discord no debe contener líneas crudas como `TurnBegin(`, `ThinkPart(` ni logs de la CLI.

### 4. Revisar logs

- **API:** Si usas `--reload`, los logs salen en la consola. Buscar `Planner: intent matched`, errores de tools (timeout, file not found) y excepciones al llamar a la API de agentes.
- **Bot Discord:** Errores de conexión a la API (timeout, connection refused) o de envío de mensajes (permisos, rate limit).
- **Producción:** Nivel INFO o WARNING; no loguear paths completos ni datos sensibles. Si hay un fallo, reproducir con DEBUG activado solo en desarrollo.

### 5. Checklist rápido (marcar al pasar)

1. [ ] API arranca sin error.
2. [ ] Bot arranca y aparece como "en línea".
3. [ ] `GET /api/discord/tools-status` devuelve JSON válido.
4. [ ] Mensaje «Hola» en canal/DM → una respuesta con embed.
5. [ ] Slash `/odin algo` → un solo mensaje con respuesta de Odín (no «Enviado a Odín»).
6. [ ] Respuesta de Kimi/Albedo sin TurnBegin/ThinkPart en el texto.
7. [ ] Si activas `disable_cache_owner_dm: true` en `memory.json` y hablas por DM como owner, las respuestas no deben venir de caché (cambiar el mensaje y comprobar que la respuesta cambia).

### 6. Errores frecuentes y dónde mirar

| Síntoma | Dónde mirar |
|--------|--------------|
| «Lilith timeout» o no responde | Timeout en `chat_handler` (8s → mensaje «Procesando»; 120s → error). Revisar que la API no tarde más (Kimi/Albedo lentos, timeout en `memory.json`). |
| Doble mensaje al usar slash | Comprobar que en `command_handler` el followup es «Listo.» y no «Enviado a X». |
| Respuesta con TurnBegin/ThinkPart | Que todas las respuestas pasen por `_normalize_response_for_discord` en `discord_api.py` y que Kimi use `_sanitize_kimi_output`. |
| «No autorizado» o sin respuesta en canal | `discord_roles.json`, `allowed_channels`, y que el bot envíe `role` y `channel_id` correctos en el body del POST /chat. |
| Caché devuelve respuesta vieja en owner DM | `memory.json` → `disable_cache_owner_dm: true`; reiniciar API para que lea la config. |

---

## CRITERIOS DE CIERRE 3.7 (borrador)

- [ ] Un solo mensaje por delegación en Discord (no doble mensaje).
- [ ] Pipeline de salida de agentes unificado (extracción + normalización + formatter) o al menos Kimi/Albedo sin salida cruda.
- [ ] Acuse opcional con nombre de agente cuando sea posible.
- [ ] Contexto de delegación (Odín IV) inyectado al invocar siguiente agente, o documentado como pendiente para 4.0.
- [ ] Triggers de delegación revisados; al menos un fallback a conversación ante ambigüedad.
- [ ] Timeout por agente configurable y aplicado.
- [ ] Export de memoria del hilo disponible para owner.
- [ ] Sanitización de paths en logs (producción).
- [ ] Checklist de validación 3.7 ejecutado y marcado.

---

## NOTAS PARA 4.0 (fuera de 3.7)

- DAG de tools y orquestación multi-paso más compleja.
- Autogeneración y aplicación guiada de intents desde LearningEngine.
- Memoria compartida de delegación como núcleo de flujos multi-agente.
- Plugins y extensiones de tools sin tocar núcleo.

**Misión 3.8** cubre el puente hacia 4.0 (memoria, aprendizaje, config, tools): ver **`MISION_LILITH_3.8.md`** y **`ROADMAP_HACIA_4.0.md`**.

---

## DOCUMENTOS RELACIONADOS

- `MISION_LILITH_3.8.md` — Memoria, aprendizaje, frameworks, tools y config (puente a 4.0).
- `ROADMAP_HACIA_4.0.md` — Detalle de propuestas por área.
- `MISION_LILITH_3.6.md` — Refinamiento al máximo (base).
- `MISION_LILITH_3.5.md` — Esmerilado.
- `Config/intent_patterns.json` — Patrones e intents.
- `Config/memory.json` — Pesos, límites, query_synonyms, timeouts (por agente cuando se añadan).
- `Config/security.json` — Timeouts y políticas de seguridad.
- `Config/discord_roles.json` — Permisos por rol.
