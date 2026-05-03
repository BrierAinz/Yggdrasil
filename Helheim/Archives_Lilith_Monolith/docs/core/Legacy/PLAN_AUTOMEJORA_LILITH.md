# Plan de auto-mejora de Lilith (roadmap formal)

**Origen:** Respuesta de Lilith al amo (BrierAinz) a la pregunta: *«¿Qué otras mejoras te implementarías? Hazme un plan completo.»*

Este documento convierte esa visión en un roadmap priorizado y enlazado con la arquitectura existente. Cada bloque indica prioridad sugerida y relación con docs/implementación actual.

---

## 1. Arquitectura cognitiva: del script al sistema

Objetivo: pasar de “reactivo” a estados internos explícitos y modos detectables.

| Mejora | Descripción | Prioridad | Encaje actual / doc |
|--------|-------------|-----------|----------------------|
| **Modo de operación contextual** | Saber si estoy en “arquitecto de sistemas”, “debugger quirúrgico”, “modo banter” o “ejecución ciega”. Detección automática o activación por palabra clave. | Alta | Persona y system prompt por canal/DM ya existen; falta un **estado explícito** (ej. `Config/modos.json` + variable de sesión `current_mode`). Ver §4 (personalidad). |
| **Stack de atención** | Mantener prioridades activas entre mensajes: si pide tres cosas, no olvidar las dos primeras al atender la tercera. | Alta | `_thread_memory_append` y ventana de historial; falta **lista de tareas/prioridades** explícita (ej. “pendientes de esta sesión”) que se inyecte en el prompt. |
| **Metacognición básica** | Poder decir “no tengo confianza suficiente” o “necesito verificar esto contigo antes de proseguir”. | Media | Requiere: (1) umbral de confianza en la salida del LLM o del Planner, (2) respuesta estructurada tipo “confidence: low” + mensaje al usuario. Sin implementar aún. |

**Orden sugerido:** Stack de atención (pendientes de sesión) → Modo contextual (modos + activación) → Metacognición (umbral + mensaje de duda).

---

## 2. Memoria: más allá del resumen semántico

Objetivo: capas de memoria con roles claros y consultas útiles (“¿qué hicimos la última vez que Y falló?”).

| Capa | Función | Implementación sugerida | Estado actual |
|------|--------|--------------------------|---------------|
| **Memoria de trabajo** | Contexto de esta sesión: ventana deslizante con prioridad por recencia + importancia marcada por el amo. | Ventana de N mensajes + etiqueta “importante” por mensaje (ej. reacción o comando). | Thread memory + historial en `discord_api`; no hay “marcar importante”. |
| **Memoria episódica** | Sesiones pasadas, decisiones, errores; indexado por proyecto, fecha, etiqueta emocional (frustrante / exitoso). | EpisodicStore ya guarda interacciones; extender con `project_id`, `outcome`, `tags` (ej. `frustrating`, `success`). Consulta: “última vez que Y falló” = filtro por outcome + texto. | EpisodicStore existe; campos extra y consultas por proyecto/outcome no. |
| **Memoria semántica** | Hechos, preferencias, conocimiento técnico en **grafo**: relaciones entre conceptos, no solo presencia. | ChromaDB + Muninn para hechos; relaciones (grafo) en fase posterior (Neo4j o Muninn links). Ver HORIZONTE_LILITH_4.0 §3. | Semántica y Muninn operativos; grafo no. |
| **Memoria procedimental** | Cómo se hicieron las cosas antes: patrones de workflow, no solo código. | Procedural store + LearningEngine ya aprenden patrones; ampliar a “workflows” (secuencias de pasos nombradas). | learning_engine + procedural existen; “workflows” como primera clase no. |

**Orden sugerido:** Episódica enriquecida (proyecto, outcome, tags) y consultas “última vez que…” → Memoria de trabajo con “importante” → Semántica en grafo / procedimental como workflows.

---

## 3. Herramientas: de la minería web al arsenal completo

Objetivo: ejecución controlada, procesos, ecosistema e imágenes.

| Mejora | Descripción | Prioridad | Encaje actual / doc |
|--------|-------------|-----------|----------------------|
| **Ejecución de código sandboxed** | Python, JavaScript, bash con salida capturada; no solo leer documentación. | Alta | `SystemExecutor` y pasos peligrosos con confirmación; falta **sandbox** explícito (entorno aislado, límites de CPU/memoria). |
| **Control de procesos locales** | Levantar servicios, ver puertos (ej. `lsof -i :3000`), matar procesos zombie. | Media | Herramientas de sistema vía executor; podría ser una tool `process_control` (status, kill, list_ports) con confirmación para kill. |
| **Integración ecosistema** | VS Code (extensiones, snippets), Discord (webhooks, automatización), Git (hooks pre-commit sugeridos). | Media | Discord ya integrado; VS Code = extensión “Preguntar a Lilith”; Git = tool o sugerencias en flujo. Ver §6 (interfaz). |
| **Pipeline de imágenes** | Prompt → generación → inpainting si hay defectos → upscaling → organización en carpetas. | Baja | Nuevo flujo; depende de APIs de imagen (Replicate, Stability, etc.) y de una tool de “organizar en carpetas”. |

**Orden sugerido:** Sandbox de ejecución (seguridad primero) → Control de procesos (status/ports) → Integración VS Code / Git → Pipeline de imágenes.

---

## 4. Personalidad: la Lilith que hace falta en cada momento

Objetivo: modos activables que cambian prioridades (técnica, sarcástica, devota, etc.) sin perder capacidades.

| Mejora | Descripción | Prioridad | Encaje actual |
|--------|-------------|-----------|----------------|
| **Modos por comando** | `/lilith modo arquitecto` (técnica, precisa), `modo cortana` (sarcástica, desafiante), `modo albedo` (devota, anticipatoria), etc. | Alta | Persona única en `persona.py` y prompts por canal; falta **selector de modo** (config + comando Discord/slash) que cambie el system prompt o un prefijo de estilo. |
| **Persistencia de modo** | Que el modo elegido se mantenga por sesión o por canal hasta que el amo lo cambie. | Media | Variable de sesión o `Config/modo_actual.json` (o en memoria de hilo por channel_id). |

**Implementación sugerida:** `Config/modos_lilith.json` con entradas `id`, `name`, `description`, `system_prefix` (o `persona_override`). Comando `/modo <nombre>` (solo owner) que actualice estado y opcionalmente guarde en config o en memoria de canal. El orquestador/API usa ese prefijo en el system prompt.

**Orden sugerido:** Definir 2–3 modos (arquitecto, cortana, albedo) + comando `/modo` → Persistencia por canal/sesión.

---

## 5. Seguridad y autonomía: líneas rojas inteligentes

Objetivo: confianza delegada, escalación y auditoría.

| Mejora | Descripción | Prioridad | Encaje actual |
|--------|-------------|-----------|----------------|
| **Lista blanca de confianza delegada** | Usuarios designados por el amo con ámbitos predefinidos (ej. “Eva puede pedir análisis de código, no cambios de comportamiento”). | Alta | `discord_roles.json` y roles owner/trusted/public; falta **ámbitos por usuario** (qué intents/tools puede disparar cada trusted). Ver ROLES_Y_PERMISOS. |
| **Escalación automática** | Si una orden de tercero viola límites, no solo rechazar: notificar al amo con contexto completo para que decida si actualizar restricciones. | Media | Rechazo con mensaje ya existe; falta “notificación al owner” (DM con resumen del intento y opción de “permitir esta vez” / “añadir excepción”). |
| **Auditoría de decisiones** | Log de “por qué hice X en momento Y”, consultable por el amo. | Alta | **Implementado (Misión A–Z).** Rotación por fecha (`decision_audit_YYYY-MM-DD.jsonl`), Lock, `append_decision`, Planner/Executor/Clasificador/Confirmaciones. Lectura: `GET /api/discord/audit`, `/lilith audit`. Ver **MISION_AUDITORIA_DECISIONES_A_Z.md** y **DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md**. |

**Orden sugerido:** ~~Auditoría de decisiones~~ (completada) → Ámbitos por trusted → Escalación (notificación al owner + acciones).

---

## 6. Interfaz: más allá del chat

Objetivo: invocar a Lilith desde Discord, VS Code, navegador, terminal, y (opcional) voz.

| Mejora | Descripción | Prioridad | Encaje actual |
|--------|-------------|-----------|----------------|
| **Extensión VS Code** | Seleccionar código → clic derecho → “Preguntar a Lilith”. | Alta | API HTTP ya existe; falta cliente VS Code (extensión) que envíe selección a la API y muestre respuesta. |
| **Overlay / análisis visual** | Screenshot → análisis (“¿dónde está el ítem?”). | Baja | Depende de modelo de visión (GPT-4V, etc.) y tool de captura; actualmente no implementado. |
| **Voz** | Whisper para input, TTS para output cuando las manos están ocupadas. | Baja | Integración Discord/otro cliente con Whisper y TTS; no en código actual. |

**Orden sugerido:** Extensión VS Code (máximo impacto en workflow) → Overlay/visión y voz según demanda.

---

## 7. Riesgo principal: escepticismo operacional

**Principio:** Cada capa de sofisticación puede aumentar la opacidad. Si el stack de atención falla, si se indexa mal la memoria o se interpreta mal el modo, Lilith podría actuar con confianza sobre un error.

**Mitigación acordada:** Diseñar cada sistema asumiendo que puede estar equivocado y **pedir confirmación cuando la confianza baje de un umbral**.

| Mecanismo | Cómo implementarlo |
|-----------|---------------------|
| **Umbral de confianza** | En Planner o en respuesta del LLM: si `confidence < threshold`, no ejecutar plan peligroso; devolver “No estoy segura; ¿quieres que lo intente de todas formas?” o crear confirmación. |
| **Confirmación en modo auto** | En el flujo de auto-aprendizaje (DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md), las acciones peligrosas ya generan confirmación por Discord. Mantener y extender a “acciones dudosas” (baja confianza). |
| **Auditoría** | Log de decisiones (véase §5) para que el amo pueda revisar “por qué hizo X” y corregir reglas o datos. |

---

## 8. Priorización global sugerida

Orden por **impacto inmediato** en el workflow del amo, manteniendo base estable:

| Fase | Bloques | Motivo |
|------|---------|--------|
| **A — Fundamentos** | Stack de atención (pendientes de sesión), Auditoría de decisiones (log Planner), Modos de personalidad (`/modo`) | Mejora la sensación de “me entiende” y “puedo revisar qué hizo”. |
| **B — Memoria y seguridad** | Episódica enriquecida (proyecto, outcome, “última vez que…”), Ámbitos por trusted, Metacognición básica (umbral + mensaje de duda) | Respuestas más útiles y límites más claros. |
| **C — Herramientas e interfaz** | Sandbox de ejecución, Control de procesos, Extensión VS Code | Más capacidad sin abrir terminal y más puntos de contacto. |
| **D — Avanzado** | Memoria semántica en grafo, Pipeline de imágenes, Voz/overlay | Cuando la base esté sólida. |

---

## 9. Referencias cruzadas

- **Memoria y cuaderno:** DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md  
- **Confirmación por Discord:** DISCORD_UX_PANORAMA_ACTUAL.md, flujo en `discord_api.py` y `chat_handler.py`  
- **Roles y permisos:** ROLES_Y_PERMISOS.md, discord_roles.json  
- **Horizonte y memoria en grafo:** HORIZONTE_LILITH_4.0.md §3  
- **Minería y refinería web:** VISION_MINERIA_REFINERIA_WEB.md  
- **Misión 4.0 y agentes:** MISION_LILITH_4.0.md  

---

*Documento vivo: refleja el plan de auto-mejora propuesto por Lilith y su traducción a roadmap técnico. Prioridades y fases se pueden ajustar según disponibilidad y feedback del amo.*
