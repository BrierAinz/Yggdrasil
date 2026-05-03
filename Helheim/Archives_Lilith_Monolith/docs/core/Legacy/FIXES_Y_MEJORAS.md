# Fixes y mejoras documentados — Lilith (post-3.6 / 3.7)

Documentación de los cambios implementados en confianza (trust), perfiles, roles, trato por rol, confirmación cuando un trusted pide acciones peligrosas, UX de espera y comandos de avatar/portada.

---

## 1. Trust por ID de Discord e itinerario de preguntas

### Trust por mención o por ID
- **Comandos:** `/lilith trust`, `/lilith untrust`, `/lilith set_perfil` aceptan **usuario** (mención) **o** **id** (ID de Discord).
- **Motivo:** Poder dar/quitar confianza o definir perfil por ID cuando el usuario no está en el servidor o no se quiere mencionar.
- **Archivos:** `Discord/bot.py` (parámetros opcionales `usuario`/`id` en los tres comandos).

### Itinerario al añadir a trust
- Al usar `/lilith trust` (por mención o por ID), si el usuario se añade correctamente, **Lilith le envía un DM** con un itinerario de preguntas para crear su perfil:
  1. ¿Cómo te llamas?
  2. ¿Qué relación tienes con Ainz? (ej. amigo, compañero)
  3. ¿Algo más que quieras que Lilith sepa?
- Si el usuario tiene DMs cerrados, se muestra un aviso al operador y se intenta mencionar al usuario en el canal con un resumen del mensaje.
- **Archivos:** `Discord/bot.py` (bloque después de `add_trusted_user`).

---

## 2. Perfiles de usuarios de confianza

### Almacenamiento
- **Ruta:** `Core/Memory/discord/trusted_profiles.json`.
- **Formato:** `{ "user_id": { "name": "...", "relation": "...", "notes": "..." } }`.

### Comando `/lilith set_perfil`
- Solo operador. Parámetros: **usuario** o **id**, **nombre**, **relacion**, **notas** (opcional).
- Actualiza o crea el perfil del usuario de confianza.

### Uso en Lilith
- Cuando un **usuario de confianza** escribe en el chat, el backend inyecta en el system prompt el bloque *[Perfil de este usuario de confianza]* con nombre, relación y notas, para que Lilith pueda tratarlo por nombre (ej. “mi amigo Jammess”).
- **Archivos:** `Discord/auth.py` (`load_trusted_profiles`, `get_trusted_profile`, `set_trusted_profile`), `Core/Backend/api/discord_api.py` (`_get_trusted_profile_block`, inyección en flujo trusted).

---

## 3. Dónde se usan los comandos y dónde aplican las bonificaciones de trust

- **Comandos de gestión** (`/lilith trust`, `/lilith trust_id`, `/lilith untrust`, `/lilith set_perfil`, `/lilith users`, etc.): son del **operador** y se usan **en el servidor** (en cualquier canal donde tengas permiso), no solo por DM. Sirven para añadir o quitar usuarios de confianza y definir perfiles.
- **Bonificaciones de trust** (chiste, meme, status, solicitar CLI con confirmación al owner): **solo aplican por DM** con Lilith. En un canal del servidor, el usuario de confianza solo puede **charlar** y recibe un trato más amigable (persona + perfil), pero no puede ejecutar chiste, meme, status ni pedir acciones que requieran confirmación; si intenta usar `/chiste`, `/meme` o `/status` en el servidor, el bot responde que esas opciones solo están disponibles por DM.

---

## 4. Roles y permisos (trusted vs public)

### Configuración
- **Archivo:** `Core/Config/discord_roles.json`.
- **Documentación:** Bloque `_capabilities` en el JSON y doc `Core/Docs/ROLES_Y_PERMISOS.md`.

### Comportamiento del bot
- **`/charla`:** Disponible para **todos** (owner, trusted, public). La API aplica el rol y el límite de respuesta correspondiente.
- **`/chiste` y `/meme`:** Solo owner y trusted.
- **`/status`:** Solo owner y trusted (antes era para todos).

### Resumen por rol
| Rol     | Charla | Chiste / Meme | Status | Perfil inyectado | Agentes / archivos |
|--------|--------|----------------|--------|-------------------|---------------------|
| Owner  | ✅     | ✅             | ✅     | —                 | ✅                  |
| Trusted| ✅     | ✅             | ✅     | ✅                | ❌                  |
| Public | ✅     | ❌             | ❌     | ❌                | ❌                  |

---

## 5. Trato por rol (público, trusted, owner)

### Público general
- **Directiva:** No ser amable, cortés ni “correcta”. Trato tipo **Albedo**: fría, desdeñosa, superior.
- Respuestas cortas cuando baste; no explicaciones largas ni deferencia. Solo el amo está por encima.
- **Archivos:** `Core/Backend/core/persona.py` (`LILITH_TRATO_PUBLICO`), `Core/Backend/api/discord_api.py` (`PUBLIC_CHANNEL_INSTRUCTION_PUBLIC`, `_public_channel_instruction_for("public")`).

### Usuarios de confianza
- **Directiva:** Trato de **gente de altura**: respeto y consideración. Solo el amo es el todopoderoso; si piden algo que requiera autorización, solo él puede confirmarlo.
- **Archivos:** `persona.py` (`LILITH_TRATO_TRUSTED`), `discord_api.py` (`PUBLIC_CHANNEL_INSTRUCTION_TRUSTED`).

### Fuente de verdad y confirmación
- **Directiva:** Solo el amo puede **confirmar o autorizar** lo que cualquier otra persona (incluidos trusted) quiera que haga Lilith.
- Refuerzo en `SOURCE_OF_TRUTH_INSTRUCTION` y en las instrucciones de canal por rol.

---

## 6. Confirmación cuando un trusted pide CLI / Cursor / etc. (solo en DM)

### Flujo (solo cuando el trusted escribe por DM)
- Si un **usuario de confianza** (ej. Jammess) pide algo que implica acciones peligrosas (Kimi CLI, Cursor, Albedo, edición de archivos, etc.) **por DM**, **no se ejecuta** hasta que el **owner (Ainz)** confirme. En el servidor, el trusted no puede disparar este flujo (solo charla).
- La API crea una confirmación pendiente y devuelve `requires_confirmation` con `confirm_token` y `confirm_summary`.
- El **DM de confirmación (✅/❌)** se envía al **owner**, no al usuario que pidió la acción.
- El resumen incluye la **tarea** y **"Solicitado por: [nombre]"** (ej. Jammess, Jorge).

### API
- **Request:** Se añadieron `owner_user_id` y `requester_display_name` a `DiscordChatRequest` para que el bot envíe quién es el owner y quién solicitó.
- **Pending:** `_PendingConfirmation` incluye `requested_by_user_id` y `requested_by_display_name`.
- **Flujo trusted:** Antes del flujo normal de trusted (charla/chiste/meme), se ejecuta el planner; si el plan tiene pasos peligrosos, se crea la confirmación con `owner_user_id` = Ainz y se devuelve `requires_confirmation`.
- **Acciones peligrosas:** Incluyen `delegate_kimi_cli`, `delegate_cursor`, `delegate_albedo`, `edit_file`, `owner_system_action`, etc. (véase `_is_dangerous_step` en `discord_api.py`).

### Discord
- En mensajes y en slash (`/charla`, etc.), el bot envía `owner_user_id` (Ainz) y `requester_display_name` cuando el autor es trusted.
- Si la respuesta es `requires_confirmation` y el autor es trusted, el DM de ✅/❌ se envía al **owner** (resolviendo por `get_ainz_id()`), no al autor del mensaje.
- Al confirmar, se llama a `/api/discord/confirm` con el `user_id` del owner.

---

## 7. Mensaje en canal mientras se espera la aprobación

### Comportamiento
- Tras mostrar el embed de “Confirmación requerida…”, se envía un **segundo mensaje** en el mismo canal:
  - Si lo pidió un **trusted:** *"⏳ Esperando la aprobación de Ainz… (60s)"*.
  - Si lo pidió el **owner:** *"⏳ Esperando tu confirmación en DM… (60s)"*.
- Cuando el owner responde en DM:
  - **Aprobado:** el mensaje se edita a *"✅ Aprobado por Ainz."* (o *"✅ Confirmado."* si fue el owner) en verde.
  - **Cancelado:** se muestra la respuesta normal del bot.
- Si pasan 60 s sin reacción: el mensaje se edita a *"⏰ Tiempo agotado. Acción cancelada."* en rojo y se envía cancel al backend.
- **Archivos:** `Discord/handlers/chat_handler.py` (en `handle_message` y en `send_chat_for_slash`).

---

## 8. Comandos de avatar y portada de Lilith

### `/lilith avatar`
- **Descripción:** Cambiar la **foto de perfil** del bot (solo operador).
- **Parámetros:** **imagen** (adjunto) **o** **url** (uno de los dos obligatorio). Formatos: PNG, JPG, GIF, WebP; máx. 8 MB.
- **Implementación:** Helper `_get_image_bytes(attachment, url)`; luego `bot.user.edit(avatar=bytes)`.

### `/lilith portada`
- **Descripción:** Cambiar la **portada/banner** de perfil del bot (solo operador).
- **Parámetros:** Igual que avatar (imagen o url).
- **Nota:** Discord puede no permitir banner en bots (función típica de cuentas Nitro/verificadas). Si la API lo rechaza, se muestra un mensaje indicando que la portada no está disponible para este bot.
- **Archivos:** `Discord/bot.py` (comandos `lilith_avatar`, `lilith_portada` y helper `_get_image_bytes`).

---

## 9. Fix previo: “La aplicación no respondió” en `/lilith trust`

- **Causa:** El handler superaba el límite de 3 s de Discord o fallaba sin responder.
- **Solución:** `await interaction.response.defer(ephemeral=True)` al inicio; lógica envuelta en `try/except` y siempre `followup.send` con éxito o error; en `auth.py`, `_save_trusted_users` asegura que exista el directorio antes de escribir.

---

## 10. Refinamientos recientes

### Canal de comunicación y mención @Lilith
- **Canal principal:** `1482356649174761523` (configurado en `Discord/data/allowed_channels.json` y en `Core/Config/discord_context_instructions.json`).
- **En canales del servidor:** Lilith **solo responde cuando la mencionan** (@Lilith). Se comprueba por ID del bot (`1459513542666354720`, configurable con `LILITH_BOT_ID` en `.env`).
- **Strip de mención:** Antes de enviar el mensaje a la API, se quita la mención al bot del texto (ej. `<@!1459513542666354720> dile a Zeo...` → `dile a Zeo...`) para que el modelo reciba el mensaje limpio.
- **Archivos:** `Discord/bot.py` (comprobación por ID), `Discord/config.py` (`get_lilith_bot_id`), `Discord/handlers/chat_handler.py` (`_strip_bot_mention`).

### Comportamiento por contexto (editable sin tocar código)
- **Archivo:** `Core/Config/discord_context_instructions.json`.
- Claves: **`dm`** (cuando es DM), **`default_channel`** (cualquier canal del servidor), o el **ID del canal** (ej. `1482356649174761523`) para un canal concreto.
- Las instrucciones se inyectan en el system prompt como *[Comportamiento en este contexto]* en todos los flujos (owner, trusted, charla).

### Transmitir mensaje (relay) y patrón ampliado
- Cuando el amo pide transmitir un mensaje a alguien (dile/pásale/avísale/escríbele a @X que Y), se delega **directo a Lucifer (Venice)** sin pasar por el modelo principal.
- **Verbos que disparan el bypass:** dile, manda, di a, decirle, pásale, avísale, escríbele, transmítele, cuéntale (+ mención @ o " que ").
- **Archivos:** `Core/Backend/api/discord_api.py` (`_is_owner_relay_request`), `Core/Backend/core/plan_executor.py` (inyección para Venice).

### Confirmación cuando un trusted pide algo peligroso (por DM)
- Si un usuario de confianza escribe **por DM** y pide algo que requiere confirmación (CLI, Cursor, etc.), el **owner** recibe un DM con el contexto (pedido, pasos, "Solicitado por: X") y reacciona ✅/❌. Tras confirmar, el **resultado se envía al DM del trusted**, no al del owner.
- El mismo flujo aplica si el trusted escribe en un canal: la confirmación va al owner; el resultado se devuelve al canal donde escribió el trusted.

### Modelo local sin censura para el público general
- **Objetivo:** Que el público hable con un modelo local (ej. Ollama) sin censura; cotorreo, roasts y relays los responde ese modelo. Si necesita información externa o herramientas, devuelve `DELEGATE_TO_LILITH` y **Lilith** responde (orquestador/herramientas).
- **Config:** `Core/Config/local_public_llm.json`: `enabled`, `base_url` (ej. `http://localhost:11434`), `model` (ej. `llama3.2`), `delegate_marker` (`DELEGATE_TO_LILITH`), `timeout_seconds`, `max_tokens`.
- **Flujo:** Solo cuando `role == "public"` y tiene charla: si el modelo local está habilitado, se llama primero; si la respuesta contiene el marker, se ignora y se usa el flujo normal (GenerateReplyTool / Lilith). Si responde texto normal, se devuelve al usuario.
- **Archivos:** `Core/Backend/core/local_public_client.py`, `Core/Backend/api/discord_api.py` (`_local_public_system_prompt`, rama antes del bloque charla).

### Refinamientos adicionales (implementados)

**1. Timeout de confirmación**  
- Si el owner no reacciona en 60 s, se registra como `timeout` en la auditoría y el **trusted recibe un DM** (o mensaje en el mismo canal): *«Ainz no respondió a tiempo. Puedes volver a pedirlo más tarde.»*  
- El bot envía `timeout: true` al endpoint `/confirm` para que el log distinga timeout de cancelación manual.

**2. Recordatorio de perfil (con throttle 24 h)**  
- Cuando un **trusted** escribe por **DM** y **no tiene perfil** (nombre o relación con Ainz), tras la respuesta normal Lilith puede enviar el recordatorio; se limita a **una vez cada 24 h** por usuario (`profile_reminder_sent.json`).  
- Si el mensaje del trusted parece contener nombre/relación (ej. *«Me llamo Jammess, soy su amigo»*), se **auto-guarda el perfil** y se responde *«Listo, te llamaré X y tengo anotado que eres [relación] de Ainz.»*; así no hace falta usar `/lilith set_perfil` para eso.

**3. Canal principal en .env**  
- **`LILITH_MAIN_CHANNEL_ID`** en `.env` (ej. `1482356649174761523`) es la fuente única del canal principal. Se añade automáticamente a la whitelist de canales permitidos (`get_allowed_channel_ids()`).  
- Opcional: `get_lilith_main_channel_id()` en `Discord/config.py` para usar ese ID en otros puntos del bot.

**4. Logs de confirmación (auditoría)**  
- **`Core/Memory/discord/confirmation_audit.jsonl`**: una línea por evento de confirmación (solicitud y resolución). Campos: `ts`, `event`, `requested_by_user_id`, `requested_by_name`, `owner_id`, `decision` (confirmed / cancelled / timeout), `summary_preview`.  
- En cancelación se usa `timeout` o `cancelled` según si el bot envió la cancelación por tiempo agotado.  
- El log existente `discord_audit.jsonl` sigue registrando eventos; el nuevo archivo facilita auditoría legible.

---

## Referencia rápida de archivos tocados

| Área              | Archivos principales |
|-------------------|----------------------|
| Trust / perfiles  | `Discord/bot.py`, `Discord/auth.py` |
| Perfiles en API   | `Core/Backend/api/discord_api.py` (`_get_trusted_profile_block`, request/response) |
| Roles y permisos  | `Core/Config/discord_roles.json`, `Core/Docs/ROLES_Y_PERMISOS.md` |
| Trato por rol     | `Core/Backend/core/persona.py`, `Core/Backend/api/discord_api.py` (SOURCE_OF_TRUTH, PUBLIC_CHANNEL_*) |
| Confirmación trusted | `Core/Backend/api/discord_api.py` (pending, flujo trusted, _is_dangerous_step) |
| Discord confirmación | `Discord/handlers/chat_handler.py`, `Discord/handlers/command_handler.py` |
| Avatar / portada  | `Discord/bot.py` |
| Mención @Lilith / strip | `Discord/bot.py`, `Discord/config.py`, `Discord/handlers/chat_handler.py` |
| Contexto por canal/DM | `Core/Config/discord_context_instructions.json`, `Core/Backend/api/discord_api.py` (`_context_instructions`) |
| Relay (transmitir mensaje) | `Core/Backend/api/discord_api.py`, `Core/Backend/core/plan_executor.py` |
| Timeout + recordatorio DM al trusted | `Discord/handlers/chat_handler.py` |
| Recordatorio de perfil (throttle 24 h + auto-guardar) | `Discord/handlers/chat_handler.py`, `Discord/auth.py` (get_trusted_profile, should_send_profile_reminder, mark_profile_reminder_sent, try_parse_and_save_profile), `Core/Memory/discord/profile_reminder_sent.json` |
| Canal principal .env | `Discord/config.py` (LILITH_MAIN_CHANNEL_ID, get_lilith_main_channel_id) |
| Auditoría confirmaciones | `Core/Backend/api/discord_api.py` (_confirmation_audit_log, confirmation_audit.jsonl) |

---

## Pre-4.0: MuninnDB (memoria cognitiva)

- **Config:** `Core/Config/muninn.json` — `muninn_enabled`, `muninn_url`, `muninn_token`, `muninn_vault`, `muninn_activate_top_k`. Por defecto `muninn_enabled: false`.
- **Adapter:** `Core/Backend/core/memory/muninn_adapter.py` — `is_enabled()`, `write()`, `activate()`. Requiere `pip install muninndb` si se usa.
- **Integración:** `MemoryManager.search_context()` añade un bloque "[Memoria MuninnDB]" cuando MuninnDB está habilitado y hay query; las memorias activadas se inyectan como complemento al contexto del prompt.
- **Referencia:** `Core/Docs/PRE_4.0_MUNINNDB.md`.

---

---

## Misión 4.0 Fase 0: Matching Learning

- **Objetivo:** Aprender de cada decisión del Planner (mensaje → tool) y usar ese historial para sugerir la tool en mensajes similares cuando se caería en fallback (Lucifer).
- **Módulo:** `Core/Backend/core/matching_learner.py` — `record(base_path, message, primary_tool, outcome)`, `suggest(base_path, message)`.
- **Datos:** `Core/Data/matching_learning.jsonl` (message_preview, tool, outcome, ts). Poda por `matching_learning_max_entries`.
- **Config:** `Config/learning.json` — `matching_learning_enabled`, `matching_learning_min_matches`, `matching_learning_confidence_threshold`, `matching_learning_max_entries`.
- **Planner:** Antes del fallback a Lucifer, consulta `suggest()`; si hay sugerencia con confianza ≥ umbral, usa esa tool (delegate_eva, delegate_lucifer, delegate_adan). Tras cada decisión llama `record()`.
- **Referencia:** `Core/Docs/MISION_LILITH_4.0.md`.

---

*Documento generado a partir de los cambios realizados en trust, perfiles, roles, trato, confirmación por trusted, UX de espera, comandos de avatar/portada, refinamientos (canal, mención, contexto, relay), refinamientos adicionales (timeout, perfil, canal .env, auditoría), Misión 3.8 (config), Pre-4.0 MuninnDB y Misión 4.0 Fase 0 (Matching Learning).*
