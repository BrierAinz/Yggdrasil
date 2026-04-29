# Cambios documentados — Crystal, Discord y Telegram

Documento de referencia para los cambios del eje:

- **Crystal en Discord público**
- **Discord DM como asistente (sin control de PC por defecto)**
- **Telegram como canal operativo para PC (NL -> intent -> PC Agent)**

---

## 1) Resumen ejecutivo

Se implementó una separación de responsabilidades por canal:

- **Discord público**: usa **Crystal** como cara visible.
- **Discord DM**: mantiene a **Lilith** como asistente conversacional.
- **Control de PC**: se deriva a **Telegram** (con token interno y confirmaciones del PC Agent).

Esto reduce superficie de riesgo en Discord y centraliza operaciones de sistema en un canal dedicado.

---

## 2) Cambios implementados

## 2.1 Crystal (canal público Discord)

### Archivos clave

- `Core/Backend/core/agents/crystal_agent.py`
- `Core/Backend/llm/kimi_client.py`
- `Discord/handlers/chat_handler.py`
- `Discord/bot.py` (registro de comandos Crystal)

### Qué se construyó

- Agente **Crystal** con personalidad propia para público.
- Cliente Kimi dedicado para Crystal (API directa, no OpenRouter).
- Cascada de respuesta de Crystal (v4.2):
  1) Kimi API directa (`kimi-for-coding`)
  2) Fallback local (Ollama)
  3) Mensaje amigable de error
- Comandos slash públicos de Crystal (`/crystal ayuda`, `codigo`, `chiste`, `meme`, `info`).

> **Nota v4.2 (2026-03-23):** Crystal migró de OpenRouter a Kimi API directa.
> - Variable anterior: `OPENROUTER_API_KEY`
> - Variable nueva: `CRYSTAL_KIMI_API_KEY`
> - Menor latencia y mayor control sobre el modelo.

### Hardening aplicado

- Crystal evita exponer implementación interna.
- Crystal no debe operar como agente con herramientas peligrosas.
- En recuperación semántica, filtra tags sensibles/operativos (p. ej. `telegram`, `pc_ops`, `owner`).

---

## 2.2 Discord (sin PC por defecto)

### Archivo clave

- `Discord/bot.py`

### Qué cambió

- Se agregó gating por variable:
  - `DISCORD_PC_ENABLED=false` (default recomendado).
- Comandos y flujo auto-PC en Discord quedan bloqueados si no está habilitado.
- Cuando está deshabilitado, se redirige a Telegram para operaciones de PC.

### Objetivo

- Evitar control de sistema desde canales Discord como comportamiento normal.
- Mantener Discord como interfaz de conversación y coordinación.

---

## 2.3 Telegram operativo para PC (lenguaje natural)

### Archivos clave

- `Core/Backend/api/telegram_api.py`
- `Telegram/telegram_bot.py`
- `Core/Backend/core/pc_agent.py`

### Qué se construyó

- Endpoint interno `POST /api/telegram/chat` con verificación de `X-Lilith-Token`.
- Bot Telegram por polling que reenvía mensajes al backend.
- Parser NL (vía LLM) para mapear texto a intent estructurado:
  - `list_dir`, `mkdir`, `move`, `copy`, `delete`, `write_file`, `exec`, `status`, `scaffold`.
- Dispatcher de intent -> operación del PC Agent.
- Soporte de scaffold (creación de estructura de proyecto) por intent.
- Confirmación por token para operaciones sensibles del PC Agent.
- Registro episódico etiquetado para separar memoria operativa de Telegram.

---

## 3) Seguridad y separación de memoria

## 3.1 Seguridad de canal

- Telegram usa token interno para autenticación backend.
- Discord puede bloquear PC completamente por flag.
- PC Agent mantiene controles de rutas/comandos/confirmaciones en backend.

## 3.2 Separación de contexto y memoria

- En la parte pública (Crystal), se evita contaminar con memoria operativa privada.
- En Telegram, la actividad operativa se etiqueta para mantener aislamiento semántico.

---

## 4) Configuración mínima requerida

- `LILITH_INTERNAL_TOKEN` (mismo valor en backend y bots/clients internos)
- `CRYSTAL_KIMI_API_KEY` (para Crystal - API Kimi directa, v4.2+)
- `DISCORD_PC_ENABLED=false` (recomendado)
- Variables Telegram:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_OWNER_CHAT_ID` (recomendado)
  - `LILITH_API_URL`
  - `LILITH_INTERNAL_TOKEN`

---

## 5) Verificación rápida (smoke tests)

1. **Crystal público**
   - En un canal público: probar `/crystal ayuda` y `/crystal codigo`.
   - Confirmar que responde como Crystal y no ejecuta acciones de sistema.

2. **Discord PC bloqueado**
   - Probar `/pc ...` con `DISCORD_PC_ENABLED=false`.
   - Debe responder que PC está deshabilitado en Discord / redirigir a Telegram.

3. **Telegram operativo**
   - Enviar en Telegram una instrucción NL de PC (ej. crear carpeta/proyecto).
   - Confirmar que devuelve plan/resultado y pide confirmación cuando aplica.

4. **Aislamiento**
   - Verificar que contenido operativo Telegram no aparece como memoria pública de Crystal.

---

## 6) Estado actual y próximos ajustes sugeridos

- Estado general: **implementado y funcional a nivel de arquitectura**.
- Recomendado cerrar:
  - revisar mensajes UX de redirección Discord -> Telegram;
  - endurecer prompts Crystal ante jailbreak;
  - mantener checklist de secretos/variables por entorno (`.env.example`).

---

## 7) Referencias relacionadas

- `Core/Docs/CHECKLIST_PLAN_DISCORD_TELEGRAM_PC.md`
- `Core/Docs/DESCRIPCION_COMPLETA_PROYECTO_LILITH.md`
- `Core/Docs/HISTORIA_CONSTRUCCION_LILITH.md`

