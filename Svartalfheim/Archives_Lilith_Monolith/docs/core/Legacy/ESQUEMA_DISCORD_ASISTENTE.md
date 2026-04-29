# Esquema: Lilith como bot asistente en Discord (inmersivo, sin webhooks)

**Objetivo:** Definir cómo consolidar a Lilith en Discord como un asistente inmersivo (respuestas siempre como la **cuenta del bot**), con tres roles claros y espacio para ampliar (memes, imágenes, etc.) sin tocar cosas peligrosas.

---

## 1. Principios

| Principio | Descripción |
|-----------|-------------|
| **Sin webhooks** | Las respuestas de Lilith se envían siempre con la cuenta del bot (`channel.send`, `reply`, `followup`). Nunca usar webhooks para suplantar identidad; la bot es “Lilith” como aplicación. |
| **Inmersivo** | La sensación de hablar con una asistente: el bot puede hacer `reply` al mensaje del usuario, mostrar “escribiendo…”, y opcionalmente usar hilos para conversaciones largas. Todo desde la misma cuenta del bot. |
| **Roles fijos** | Tres niveles: **Owner** (tú), **Trusted** (amigos de confianza), **Public** (resto). Cada uno con capacidades y tono definidos. |
| **Extensible** | Nuevas capacidades (ej. “generar meme” para trusted) se añaden como comandos o intents permitidos por rol, sin cambiar el esquema. |

---

## 2. Matriz de roles y capacidades

### 2.1 Resumen por rol

| Rol | Quién | Dónde puede hablar | Comandos slash | Qué puede pedir | Límites |
|-----|--------|---------------------|----------------|------------------|---------|
| **Owner** | Tú (Ainz) | DM + canal #lilith | Todos: /eva, /adan, /lucifer, /auto, /status, /notif, /memory, /file read|edit, /lilith trust\|untrust\|list | Todo: análisis, código, archivos, Cursor CLI, auto_mode, gestión de trusted. | Ninguno. |
| **Trusted** | Amigos en whitelist | Solo canal #lilith (no DM) | Solo los “seguros”: /charla, /meme, /chiste (a futuro /imagen, etc.) | Charla, memes, chistes, preguntas inofensivas. A futuro: generar imagen bajo límites. | No archivos, no /auto, no /file, no /lilith. No tools que escriban en disco o ejecuten código. |
| **Public** | Cualquiera en el servidor | Solo canal #lilith | Ninguno o solo /ayuda | Preguntas generales, asistente básico (explicaciones, conversación light). | Solo respuestas conversacionales; sin acceso a agentes pesados ni datos sensibles. |

### 2.2 Detalle por rol

**Owner (tú)**  
- **Backend:** `role=owner` → Persona completa (persona.md), Orchestrator con todas las tools (read_file, edit_file, delegate_*, delegate_cursor, etc.), shortcuts (hola, quién soy), /auto → TaskPlanner + TaskExecutor.  
- **Discord:** Responde en DM y en #lilith; todos los slash; puede recibir respuestas largas (split en embeds).  
- **Seguridad:** Es el único que puede disparar edición/eliminación/ejecución en el Core.

**Trusted (amigos de confianza)**  
- **Backend:** `role=trusted` → Persona “amigable” (misma voz Lilith pero sin datos sensibles de Ainz; sin memoria semántica de proyecto). Solo intents/tools permitidos: conversación, chiste, meme (a futuro imagen). **No** code_edit, file_write, system_execute, delegate_cursor con --force, /auto, ni acceso a archivos del proyecto.  
- **Discord:** Solo en #lilith (si te escriben por DM, opción: no responder o responder “Hola, habla conmigo en #lilith”). Slash limitados a /charla, /chiste, /meme (y más adelante /imagen).  
- **Extensibilidad:** A futuro: “generar imagen” como tool o comando permitido solo para trusted; límites (tamaño, uso) definidos por ti.

**Public**  
- **Backend:** `role=public` → Persona “asistente general” (corta, útil, sin referencias a Ainz ni a tu entorno). Solo respuestas conversacionales; sin tools de archivo, sin agentes costosos opcionales; opcionalmente un intent “ayuda” que devuelve texto fijo (reglas del servidor, cómo usar a Lilith).  
- **Discord:** Solo #lilith; sin slash o solo /ayuda. Respuestas siempre como embed/texto desde el bot.

---

## 3. Experiencia “inmersiva” (sin webhooks)

Todo se hace con la **cuenta del bot** (Application/Bot en Discord):

| Aspecto | Cómo implementarlo |
|---------|---------------------|
| **Quién envía** | Siempre `channel.send(...)` o `message.reply(...)` o `interaction.followup.send(...)` con el cliente del bot. **No** crear webhooks del canal para enviar “como Lilith”. |
| **Reply al usuario** | Opción: en lugar de `channel.send(embed=...)`, usar `await message.reply(embed=embed)` para que Discord muestre “Lilith respondió a [usuario]”. Más natural en hilos. |
| **Escribiendo…** | Ya tienes `async with message.channel.typing():` antes de la llamada a la API; mantenerlo. |
| **Progreso** | Mantener “⏳ Procesando…” cuando tarde >5s; luego borrarlo y enviar la respuesta final. |
| **Hilos (opcional)** | Para conversaciones largas en #lilith, se puede abrir un hilo con el primer mensaje del usuario y que Lilith responda siempre en ese hilo (misma conversación). Implementación opcional en una fase posterior. |

Con esto, “inmersivo” = el usuario ve a la **bot** escribiendo, respondiendo y citando su mensaje, sin webhooks.

---

## 4. Backend (API): qué cambia por rol

En `Backend/api/discord_api.py` (o donde se procese `POST /api/discord/chat`):

- **owner:** Ya está: Orchestrator + PersonaLoader (owner) + memoria semántica; /auto, shortcuts, todas las tools.  
- **trusted:**  
  - Mismo endpoint, `role=trusted`.  
  - Persona: `PersonaLoader.get_system_prompt(role="trusted")` (sin inyectar memoria semántica de proyecto).  
  - **Restricción de intents/tools:** no llamar al Orchestrator con tools peligrosas. Opciones:  
    - **A)** Un “Orchestrator light”: mismo Planner pero un registry que solo tiene `generate_reply` (Lucifer) + en el futuro tools como `chiste`, `meme`, `imagen`.  
    - **B)** Mantener un intent detector para trusted que solo permita intents: `chitchat`, `chiste`, `meme`, `pregunta_general`; el resto → mensaje fijo “Eso solo puede hacerlo mi operador.”  
- **public:**  
  - Persona: `PersonaLoader.get_system_prompt(role="public")`.  
  - Sin Orchestrator; solo `generate_reply` (Lucifer) con prompt corto de “asistente general”, o respuestas prefijadas para /ayuda.

Resumen: **Owner** = flujo actual completo. **Trusted** = flujo limitado (solo herramientas seguras y conversación). **Public** = solo conversación/asistente básico.

---

## 5. Discord (bot): resumen de cambios

| Archivo / Lugar | Cambio |
|------------------|--------|
| **auth.py** | Ya tienes Owner + Trusted (whitelist) + Public. Mantener. |
| **bot.py** | DM: solo Owner. Servidor: solo canal #lilith. Para Trusted/Public en #lilith: permitir mensajes y (para trusted) slash limitados. |
| **chat_handler.py** | Asegurar que **nunca** se use webhook; usar `message.reply(embed=...)` si quieres respuesta “como reply”. Mantener `typing` y “⏳ Procesando…”. |
| **command_handler.py** | Owner: todos los slash. Trusted: solo /charla, /chiste, /meme (y a futuro /imagen). Public: solo /ayuda o ninguno. Resto de comandos → mensaje efímero “Solo mi operador puede usar esto.” (Owner) o “No disponible para ti.” (Trusted/Public). |
| **Nuevos slash** | Añadir grupo o comandos: `/charla [mensaje]`, `/chiste`, `/meme` (y más adelante `/imagen [descripción]`). Todos invocan `POST /api/discord/chat` con el texto adecuado y `role` ya viene del backend según quien llame. |

No hace falta tocar webhooks si no los usas; solo asegurar que toda salida sea vía el cliente del bot.

---

## 6. Extensibilidad (a futuro)

| Capacidad | Rol | Dónde implementar | Notas |
|-----------|-----|---------------------|--------|
| Generar imagen | Trusted (y opcionalmente Public con límites) | Nueva tool en Core + slash /imagen en Discord; en API, solo permitir esa tool para `role=trusted` (o public con rate limit). | Límites: tamaño, frecuencia; clave de API de imagen en secrets.env. |
| Más “diversión” (trivia, mini-juegos) | Trusted | Nuevos intents o comandos que devuelvan texto/juego desde el backend; mismo flujo que /chiste, /meme. | Sin acceso a archivos ni ejecución. |
| Public con /ayuda | Public | Comando /ayuda que devuelve texto fijo (o un embed) con reglas y “Habla en este canal para preguntarme cosas generales.” | Sin llamada a LLM si quieres; solo respuesta estática. |

Puedes ir añadiendo filas a esta tabla y decidir en qué rol encaja cada cosa.

---

## 7. Orden sugerido de implementación

1. **Fijar comportamiento por rol en la API**  
   - Trusted: en `discord_api.py`, rama `role == "trusted"`: usar PersonaLoader(trusted) y un flujo “solo conversación + chiste/meme” (sin tools de archivo, sin /auto, sin delegate_cursor con --force).  
   - Public: rama `role == "public"`: solo generate_reply con persona public o respuestas cortas.

2. **Discord: comandos por rol**  
   - Owner: todos los slash actuales.  
   - Trusted: registrar /charla, /chiste, /meme (y dejar el resto sin registrar para ellos o devolver “No disponible”).  
   - Public: solo /ayuda (o ninguno).

3. **Opcional: reply en vez de send**  
   - En `chat_handler.py`, cambiar a `await message.reply(embed=embed)` para la primera respuesta (y los chunks siguientes en el mismo canal), para que sea más inmersivo.

4. **DM para no-Owner**  
   - Si un Trusted te escribe por DM: no responder (como ahora) o responder un mensaje fijo: “Hola, habla conmigo en el canal #lilith del servidor.”

5. **A futuro**  
   - Añadir tools/comandos de meme, imagen, etc., y permitirlos solo para trusted (y opcionalmente public con límites) en la API y en Discord.

---

## 8. Resumen de una frase por rol

- **Owner:** Asistente completo para ti: todo lo que hace hoy (archivos, agentes, Cursor, auto_mode, gestión de trusted), sin webhooks, respuestas como bot.  
- **Trusted:** Amigos pueden charlar, pedir chistes/memes (y a futuro imágenes) en #lilith; sin acceso a tu entorno ni a herramientas peligrosas.  
- **Public:** Asistente general en #lilith: conversación y ayuda básica; sin datos sensibles ni comandos avanzados.

Puedes usar este esquema para implementar paso a paso o para marcar qué partes quieres que te codifiquemos primero (por ejemplo: “solo refinar trusted/public en la API” o “solo añadir /chiste y /meme”).
