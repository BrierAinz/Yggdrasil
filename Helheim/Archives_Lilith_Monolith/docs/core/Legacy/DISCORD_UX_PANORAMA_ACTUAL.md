# Panorama actual: UX/UI del bot de Discord

Documento de investigación que responde a las preguntas clave sobre componentes interactivos, hilos, presencia y actualización de embeds. Sirve como base para diseñar mejoras de alto impacto.

---

## 1. Componentes interactivos (UI Kit)

**Pregunta:** ¿Las confirmaciones (✅/❌) se manejan con reactions o con el Discord UI Kit (Botones, Menús, Modales mediante `discord.ui.View`)?

**Estado actual:** **Solo reacciones (reactions)**.

- El flujo de confirmación se implementa en **`Discord/handlers/chat_handler.py`**:
  - **`_request_confirmation_dm`**: envía un embed por DM al owner (o al que deba aprobar), añade las reacciones ✅ y ❌ al mensaje (`dm_msg.add_reaction("✅")`, `add_reaction("❌")`), y espera con **`bot.wait_for("reaction_add", timeout=60, check=check)`**. La `check` exige que sea el usuario correcto, el mensaje correcto y el emoji ✅ o ❌.
  - Tras la reacción se hace `dm_msg.clear_reactions()` y se edita el embed con el resultado ("✅ Confirmada. Ejecutando…" o "❌ Cancelada por el operador.").
- En el canal público (o DM del solicitante) se muestra un embed "⏳ Esperando tu confirmación en DM… (60s)" que luego se edita a "✅ Confirmado." o "⏰ Tiempo agotado. Acción cancelada." según el resultado.
- **No** se usa en este flujo:
  - `discord.ui.View`
  - Botones (`discord.ui.Button`)
  - Menús desplegables (`discord.ui.Select`)
  - Modales (`discord.Modal`)

**Conclusión:** Toda la confirmación depende de **reactions** en un mensaje de DM. No hay UI Kit para confirmaciones ni para otros flujos del chat principal.

---

## 2. Gestión de hilos (threads) y ruido visual

**Pregunta:** Cuando Lilith ejecuta una extracción masiva (minería web, varias URLs), ¿responde en el canal público/DM o se crea un hilo dedicado (`create_thread`) para no ensuciar el chat principal?

**Estado actual:** **Respuesta directa en el mismo canal/DM** para el flujo de chat y minería.

- **Mensajes normales y slash `/charla`:** La respuesta (embed con el texto de Lilith, o el flujo de confirmación) se envía siempre en el **mismo canal** donde se recibió el mensaje (o en el DM del usuario). No se crea ningún hilo.
- **Memoria de hilo:** Existe **`discord_thread_memory`** (y `thread_id` en el payload a la API) para **guardar contexto por hilo** cuando la conversación ya tiene lugar **dentro** de un hilo existente (`_channel_and_thread_ids` detecta si el canal es un hilo y envía `thread_id`). Es decir: si el usuario escribe en un hilo, se usa ese hilo para memoria; pero el bot **no crea** hilos para aislar respuestas largas.
- **Excepción:** El comando **`/auto`** (modo automático multi-agente) **sí** crea un hilo cuando se usa en un servidor:
  - En **`Discord/bot.py`**, `slash_auto` hace `interaction.channel.create_thread(name=f"auto: {objetivo[:30]}", type=discord.ChannelType.public_thread, auto_archive_duration=60)` y envía el mensaje inicial y el reporte **dentro de ese hilo** (mediante un shim que reutiliza el handler con `channel = thread`).
  - Esto **no** se aplica a la minería web ni al lore extractor: si el usuario pide "extrae el lore de estas 3 URLs" por mensaje normal o por `/charla`, la respuesta (y cualquier contexto enorme) va **directamente al canal o DM** donde se escribió.

**Conclusión:** No hay lógica para crear un hilo dedicado cuando se dispara una extracción masiva (minería/lore). Solo `/auto` crea hilo; el resto del chat (incluido DAG con varias URLs) responde en el mismo sitio, lo que puede generar ruido visual en canales muy activos.

---

## 3. Presencia y estados dinámicos (Rich Presence)

**Pregunta:** ¿Lilith usa `discord.Activity` para reflejar lo que está procesando (ej. "Viendo 3 enlaces de Reddit...", "Escuchando a Lucifer")?

**Estado actual:** **No**.

- En el código del bot (**`Discord/bot.py`**) y en los handlers no aparece:
  - `discord.Activity`
  - `bot.change_presence(...)`
  - Ningún uso de "Playing", "Watching", "Listening to", "Competing" o "Custom status".
- El bot arranca y no actualiza su estado según el agente o la herramienta en curso. No hay canal de eventos desde el PlanExecutor (ni desde la API) hacia el cliente Discord para cambiar la presencia.

**Conclusión:** La presencia del bot es la por defecto de Discord (sin actividad personalizada). No hay Rich Presence ni estados dinámicos ligados al orquestador o a las tools.

---

## 4. Actualización de embeds en tiempo real

**Pregunta:** Con el placeholder "🔮 Lilith está pensando...", ¿Lilith edita el mensaje una sola vez al final o hay un flujo donde el PlanExecutor emite eventos parciales para actualizar el embed paso a paso?

**Estado actual:** **Una edición opcional (solo en timeout) y luego borrado del placeholder**; no hay actualizaciones paso a paso.

- En **`Discord/handlers/chat_handler.py`** (flujo de mensajes normales, no slash):
  1. Se envía **un** mensaje de placeholder: `progress_msg = await channel.send("🔮 Lilith está pensando...")`.
  2. Se espera la respuesta de la API con `asyncio.wait_for(..., timeout=120)`.
  3. **Si hay timeout** a los 120 s: se añade reacción de "procesando", se **edita** el placeholder a `"⏳ Procesando tu solicitud (puede tardar un poco)..."` y se espera hasta 60 s más; si al final falla, se borra el placeholder y se envía un mensaje de error.
  4. **Al terminar** (éxito o después del segundo wait): se **borra** el placeholder (`progress_msg.delete()`) y se envía la respuesta real (embed o flujo de confirmación).
- No hay:
  - Múltiples ediciones del mismo mensaje con "Paso 1 completado...", "Paso 2 en curso...", etc.
  - Ningún mecanismo por el que el **PlanExecutor** (o la API) emita eventos parciales (por paso u oleada) hacia el bot.
  - WebSockets ni otro canal en tiempo real desde el backend al Discord client para actualizar el embed.

**Nota:** Los comandos slash (p. ej. `/charla`) usan `interaction.response.defer()` y luego `followup.send(...)` con la respuesta final; no usan el mismo placeholder de texto en canal, pero tampoco hay actualizaciones intermedias del mensaje diferido.

**Conclusión:** El placeholder existe para evitar la sensación de "bot colgado", pero se edita **como mucho una vez** (solo si hay timeout) y al final se elimina y se envía el resultado. No hay flujo de eventos parciales ni actualización paso a paso del embed.

---

## Resumen para priorizar mejoras

| Área | Estado actual | Posible evolución |
|------|----------------|--------------------|
| **Confirmaciones** | Reactions ✅/❌ en DM | UI Kit: botones "Confirmar" / "Cancelar" en embed o modal para acciones sensibles |
| **Hilos / ruido** | Respuesta en el mismo canal; solo `/auto` crea hilo | Crear hilo dedicado para planes "pesados" (minería, N URLs, /auto-style) y responder ahí |
| **Presencia** | Sin Activity | `change_presence(activity=Activity(name="Viendo 3 enlaces…", type=ActivityType.watching))` según paso/agente (requiere canal de eventos backend → bot) |
| **Placeholder** | Un mensaje "pensando...", 0–1 edición, luego borrar y enviar resultado | Eventos por paso/oleada desde PlanExecutor → API → bot para editar el mismo mensaje ("Paso 1/5…", "Paso 2/5…") o embed progresivo |

---

*Documento de investigación para diseño de mejoras UX/UI en Discord. Coherente con ORQUESTACION_Y_ESTRUCTURACION_4_0.md (feedback asíncrono, límites Discord).*
