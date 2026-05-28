# Checklist ejecutable — Plan Discord/Telegram/PC (Lilith)

Este documento convierte el plan acordado en **checklists accionables** para implementar y validar el sistema.

---

## 0) Objetivo final (definición)

- **Discord**
  - Público: agente **Crystal** (OpenRouter) como "cara visible".
  - DM: **Lilith Discord** (asistente), **sin control de PC**.
- **Telegram**
  - **Lilith Telegram** (polling) con "lenguaje natural → batch".
  - Ejecución por **PC Agent** con **1 confirmación** por lote.
- **Seguridad (Opción B)**
  - Acceso amplio (D:\, E:\, Desktop, Downloads), pero con denylist fuerte (Windows/AppData/secrets).

---

## 1) Configuración mínima (variables y archivos)

### 1.1 Variables requeridas (backend)

- [ ] `LILITH_INTERNAL_TOKEN` definido (mismo valor que usen bots/clients).
  - Fuente actual en este repo: `Discord/.env` (el backend carga ese `.env` al arrancar).

### 1.2 Variables requeridas (Telegram)

- [ ] `TELEGRAM_BOT_TOKEN` (BotFather).
- [ ] `TELEGRAM_OWNER_CHAT_ID` (opcional pero recomendado; para restringir a tu chat).
- [ ] `LILITH_API_URL` (default: `http://127.0.0.1:8000`).
- [ ] `LILITH_INTERNAL_TOKEN` (igual que backend).
- [ ] Crear archivo `Telegram/.env` con esas variables (NO subir al repo).
- [ ] Crear `Telegram/.env.example` como plantilla (SÍ subir al repo).

### 1.3 Variables recomendadas (Discord)

- [ ] `DISCORD_PC_ENABLED=false` (mantener **PC deshabilitado en Discord**).

---

## 2) Seguridad PC Agent (Opción B)

Archivo: `Core/Config/pc_agent.json`

- [x] `allowed_roots` incluye rutas deseadas (D:\, E:\, Desktop, Downloads). ✓ Hecho
- [ ] `denied_patterns` — **fix**: reemplazar `"token"` genérico por patrones específicos:
  - Cambiar `"token"` → `".env"`, `"*token*.env"`, `"webhook_secrets"` para evitar falsos positivos en rutas legítimas.
- [x] `high_risk_requires_phrase=false`. ✓ Hecho
- [x] `confirm_timeout_seconds=60`. ✓ Hecho
- [x] `kill_switch=false`. ✓ Hecho

---

## 3) Discord (sin PC)

Archivo: `Discord/bot.py`

- [ ] `/pc`, `/pc_confirm`, `/pc_lock`, `/pc_unlock` deben responder "PC deshabilitado en Discord…" (por defecto).
- [ ] En DM (owner), no debe ejecutar macros de PC si `DISCORD_PC_ENABLED=false`.
- [ ] En DM (owner), si preguntas por PC, debe redirigir a Telegram (directiva DM en backend).

Prueba rápida:

- [ ] Ejecuta `/pc op:status` en Discord → debe responder que está deshabilitado en Discord.

---

## 4) Telegram (polling) — "lenguaje natural → batch"

### 4.1 Bot Telegram (polling)

Archivo: `Telegram/telegram_bot.py` — **YA EXISTE** ✓

- [x] Se conecta a Telegram por polling (`getUpdates`). ✓
- [x] Envía mensajes al backend y reenvía respuesta. ✓
- [x] Restringe por `TELEGRAM_OWNER_CHAT_ID`. ✓
- [ ] **Pendiente**: añadir manejo de señales (`signal.SIGTERM/SIGINT`) para cierre limpio.
- [ ] **Pendiente**: logging estructurado (actualmente falla silencioso en excepciones).

### 4.2 Backend: endpoint Telegram

Archivo: `Core/Backend/api/telegram_api.py` — **EXISTE pero limitado**

Estado actual: solo reconoce "crear proyecto en Yggdrasil/Asgard" + CONFIRM.

- [x] Endpoint `POST /api/telegram/chat` con auth. ✓
- [x] Scaffold de proyectos en Asgard. ✓
- [x] Confirmación con `CONFIRM <token>`. ✓
- [ ] **Pendiente**: router NL general — delegar al LLM la intención cuando no matchea scaffold.
  - Intents a soportar: `list_dir`, `mkdir`, `move`, `copy`, `delete`, `exec`, `write_file`, `status`.
  - Si el LLM infiere intent → construir batch → devolver preview + token.
  - Si no entiende → pedir clarificación.

---

## 5) Scaffold completo (proyecto "esqueleto completo")

Objetivo: al pedir "crea proyecto X en Asgard", crear estructura completa con batch.

- [x] `README.md`, `backend/app.py`, `backend/requirements.txt`, `frontend/README.md`, `data/README.md`. ✓

Prueba rápida:

- [ ] Crear proyecto nuevo por Telegram.
- [ ] Confirmar.
- [ ] Verificar que existen todas las rutas/archivos.

---

## 6) Arranque recomendado (local)

Archivo: `arranque_lilith.bat`

- [x] Arranca MuninnDB. ✓
- [x] Arranca FastAPI. ✓
- [x] Arranca Discord bot. ✓
- [ ] **Pendiente**: añadir arranque del bot Telegram (`python Telegram\telegram_bot.py`).

---

## 7) Crystal (OpenRouter) en público (Discord)

Pendiente de implementación.

Checklist:

- [ ] Configurar `OPENROUTER_API_KEY` (en `Discord/.env`).
- [ ] Crear `Core/Backend/llm/openrouter_client.py` (cliente HTTP OpenRouter).
- [ ] Crear `Core/Backend/core/agents/crystal_agent.py` con directivas propias (público, sin PC, sin datos sensibles).
- [ ] Routing en `discord_api.py`: canales públicos → Crystal; DM/owner → Lilith completa.
- [ ] Garantizar: Crystal **sin herramientas peligrosas** (solo `charla`, `chiste`, `meme`, `web_search`).

---

## 8) Memoria separada (Discord vs Telegram)

Pendiente de implementación.

Checklist:

- [ ] Separar tags/vaults/colecciones por transporte:
  - [ ] `telegram_*` (preferencias operativas, procedimientos, proyectos)
  - [ ] `discord_*` (social/público)
- [ ] En `telegram_api.py`: pasar `source="telegram"` al guardar en memoria.
- [ ] En `discord_api.py`: pasar `source="discord"` al guardar en memoria.
- [ ] En el prompt de Crystal: excluir hechos con tag `telegram_*`.
- [ ] No mezclar "aprendizaje operativo" de Telegram en el prompt de Discord público.

---

## 9) Hardening telegram_bot.py

Archivo: `Telegram/telegram_bot.py`

- [ ] Añadir `signal.signal(signal.SIGTERM, ...)` para cierre limpio desde `.bat` o proceso externo.
- [ ] Logging estructurado: reemplazar `except Exception: pass` por `logger.exception(...)`.
- [ ] Retry con backoff exponencial en fallos de red (actualmente `time.sleep(2.0)` fijo).
- [ ] Respuesta de "escribiendo..." (`sendChatAction`) mientras espera al backend (UX).

---

## 10) Troubleshooting mínimo

- **403 Token inválido**:
  - [ ] Verifica que **backend** y **bots** usen el mismo `LILITH_INTERNAL_TOKEN`.
  - [ ] Reinicia FastAPI (carga variables al arrancar).
- **PC Agent no carga config**:
  - [ ] Verifica que `Core/Config/pc_agent.json` sea JSON válido.
- **Telegram no responde**:
  - [ ] Confirma `TELEGRAM_BOT_TOKEN`.
  - [ ] Confirma que el bot polling está corriendo.
  - [ ] Si restringes por `TELEGRAM_OWNER_CHAT_ID`, confirma que es tu chat correcto.
- **Ruta legítima bloqueada por PC Agent**:
  - [ ] Revisar `denied_patterns` — evitar strings genéricos como `"token"` o `"key"`.

---

## Orden de implementación

| # | Tarea | Archivo(s) | Estado |
|---|-------|-----------|--------|
| 1 | `.env.example` para Telegram + raíz | `Telegram/.env.example`, `.env.example` | ✅ Hecho |
| 2 | Fix `denied_patterns` en pc_agent.json | `Core/Config/pc_agent.json` | ✅ Hecho |
| 3 | Añadir Telegram al `.bat` + cerrar_lilith.bat | `arranque_lilith.bat`, `cerrar_lilith.bat` | ✅ Hecho |
| 4 | Hardening `telegram_bot.py` (señales, logging, backoff, typing) | `Telegram/telegram_bot.py` | ✅ Hecho |
| 4b | Fix server.py carga .env desde path incorrecto | `Core/Backend/api/server.py` | ✅ Hecho |
| 4c | Fix episodic_store.py silent except graph_relations | `Core/Backend/core/episodic_store.py` | ✅ Hecho |
| 4d | Muninn token fuera de JSON → env var MUNINN_TOKEN | `muninn.json`, `muninn_memory.py` | ✅ Hecho |
| 4e | Fix ruta hardcodeada Asgard en telegram_api.py | `Core/Backend/api/telegram_api.py` | ✅ Hecho |
| 4f | Fix type hints list[dict] → List[dict] en telegram_api.py | `Core/Backend/api/telegram_api.py` | ✅ Hecho |
| 4g | Fix context mutable default en MessageRequest | `Core/Backend/api/server.py` | ✅ Hecho |
| 4h | requirements.txt para Telegram/ | `Telegram/requirements.txt` | ✅ Hecho |
| 4i | pc_agent.json + secrets.env añadidos a .gitignore | `.gitignore` | ✅ Hecho |
| 5 | Router NL general en `telegram_api.py` | `Core/Backend/api/telegram_api.py` | ✅ Hecho |
| 6 | Discord: deshabilitar PC, redirigir a Telegram | `Discord/bot.py` | ✅ Hecho |
| 7 | Crystal agent (OpenRouter) | `llm/openrouter_client.py`, `agents/crystal_agent.py`, `discord_api.py` | ✅ Hecho |
| 8 | Memoria separada discord/telegram | `telegram_api.py`, `discord_api.py`, `episode_builder.py` | ✅ Hecho |
