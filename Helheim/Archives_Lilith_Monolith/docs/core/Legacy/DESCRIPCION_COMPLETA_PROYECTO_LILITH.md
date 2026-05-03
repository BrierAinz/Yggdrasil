# Lilith — Descripción completa del proyecto

Lilith es un **asistente personal autónomo** orientado a operación real desde **Discord** y, en el plan actual, desde **Telegram** para control de PC. Combina orquestación (planificación + ejecución), memoria (episódica/semántica/cognitiva) y módulos de seguridad para realizar tareas con confirmación y auditoría.

---

## 1) Componentes principales

### 1.1 Backend (FastAPI)

- **Servidor**: `Core/Backend/api/server.py`
- **Propósito**: expone endpoints internos para bot(s), UI y automatizaciones:
  - Discord chat y comandos internos
  - Scheduler (jobs/monitores)
  - Proactive mode
  - PC Agent (filesystem/exec con confirmación)
  - VS Code API
  - Webhooks entrantes
  - Seguridad (scopes temporales)

### 1.2 Discord Bot (puente)

- **Bot**: `Discord/bot.py`
- **Propósito**: recibe mensajes, aplica reglas de rol y llama al backend.
- **Roles**:
  - `owner`: acceso completo (según capacidades del backend)
  - `trusted`: capacidades limitadas (con confirmación al owner en acciones peligrosas)
  - `public`: restricciones más fuertes

### 1.3 Panteón (agentes especializados)

Agentes especializados que Lilith puede delegar:
- **Eva**: análisis/documentación
- **Adán**: código/refactor/tests
- **Lucifer**: creativo/alternativas (con restricciones seguras)
- **Odin**: análisis exhaustivo

La “firma” de estas personalidades se inyecta principalmente en:
- `Core/Backend/core/tools_v3/agent_tools.py` (`PERSONA_*`)
- y coherencia adicional en `Core/Backend/core/agents/*_agent.py` (`get_system_prompt()`).

---

## 2) Orquestación (cómo ejecuta tareas)

### 2.1 Flujo general

1) Entrada (Discord/Telegram/UI)
2) Construcción de contexto (persona + reglas + memoria)
3) Planificación (Planner → pasos)
4) Metacognición (umbral de confianza para bloquear planes peligrosos)
5) Ejecución (PlanExecutor / AgentCaller / ToolRegistryV3)
6) Log episódico + persistencias (memoria, auditoría)

### 2.2 Metacognición

- El Planner produce un resultado con **confidence**.
- Si el plan tiene herramientas peligrosas y la confianza cae bajo umbral, se pide confirmación.

Config: `Core/Config/metacognition.json`  
Código: `Core/Backend/core/planner.py`, `Core/Backend/core/orchestrator.py`, `Core/Backend/api/discord_api.py`

---

## 3) Memoria (capas)

### 3.1 Episódica (log de actividad)

- Registro enriquecido de acciones y resultados.
- Consultable por comandos y por resúmenes automáticos.

Código: `Core/Backend/core/episodic_store.py`

### 3.2 Semántica (facts)

- Hechos guardados para recuperación posterior.
- Integración con vector store local (Chroma) según configuración.

Código: `Core/Backend/core/tools_v3/memory_tools.py`

### 3.3 Cognitiva (MuninnDB)

- Motor externo para activación/retrieval con scoring cognitivo.
- Usado para: RAG preemptivo, proactive mode, almacenamiento de relaciones/edges.

Config: `Core/Config/muninn.json`  
Código: `Core/Backend/core/muninn_memory.py`

---

## 4) Scheduler, Monitores y Proactividad

### 4.1 Scheduler (Cron V2)

- APScheduler ejecuta jobs cron/interval.
- API interna de gestión:
  - listar jobs
  - pausar / reanudar
  - ejecutar ahora

Config: `Core/Config/scheduled_tasks.json`  
Código: `Core/Backend/core/task_scheduler.py`, `Core/Backend/api/scheduler_api.py`

### 4.2 Source Monitor

- Vigila URLs periódicamente.
- Detecta cambios y puede:
  - notificar al owner
  - registrar episodio
  - guardar hechos semánticos

Config: `Core/Config/source_monitors.json`  
Código: `Core/Backend/core/source_monitor.py`

### 4.3 Modo proactivo

- Consulta activaciones de Muninn y notifica sin que el owner pregunte.
- Incluye:
  - rate limiting
  - deduplicación
  - persistencia de estado

Config: `Core/Config/proactive_mode.json`  
Código: `Core/Backend/core/proactive_engine.py`, `Core/Backend/api/proactive_api.py`

---

## 5) Seguridad y permisos

### 5.1 Roles y capacidades

- Roles `owner/trusted/public` con capacidades por config.
- Overrides finos para trusted.

Config: `Core/Config/discord_roles.json`, `Core/Config/trusted_scopes.json`  
Código: `Core/Backend/core/discord_roles_config.py`

### 5.2 Confirmaciones (acciones peligrosas)

- Sistema de confirmación con token y persistencia.
- Usado por:
  - metacognición (planes de baja confianza + peligrosos)
  - PC Agent

Código: `Core/Backend/api/discord_api.py`

---

## 6) PC Agent (control remoto seguro)

### 6.1 Qué hace

Permite operaciones controladas:
- filesystem: `list`, `mkdir`, `move`, `copy`, `delete`, `write_file`
- comandos: `exec` (allowlist)
- `batch` (lote con 1 confirmación)

### 6.2 Guardrails

- allowlists/denylists por ruta
- bloqueo de junctions/symlinks (reparse points)
- revalidación en confirmación (anti-TOCTOU)
- rate limits + kill switch
- redacción de secretos en outputs
- auditoría JSONL

Config: `Core/Config/pc_agent.json`  
Código: `Core/Backend/core/pc_agent.py`, `Core/Backend/api/pc_agent_api.py`

---

## 7) VS Code extension

- Extensión para pedir sugerencias y aplicar parches con diff/confirmación.
- Carpeta: `VSCode/`

---

## 8) Webhooks entrantes

- Endpoint para recibir eventos (ej. GitHub/CI) y:
  - notificar
  - disparar planes
  - guardar facts

Config: `Core/Config/webhook_rules.json`, `Core/Config/webhook_secrets.json`  
Código: `Core/Backend/api/webhook_api.py`, `Core/Backend/core/discord_notifier.py`

---

## 9) Telegram (plan actual para control de PC)

En el plan acordado:
- **Discord** no controla PC.
- **Telegram** es el canal de control de PC con “lenguaje natural → batch + 1 confirmación”.

Backend: `Core/Backend/api/telegram_api.py`  
Bot polling: `Telegram/telegram_bot.py`

---

## 10) Arranque local recomendado (Windows)

Script recomendado:
- `run_lilith_dev.bat` (Muninn + FastAPI + Discord bot)

Notas:
- Asegurar que `LILITH_INTERNAL_TOKEN` esté configurado (bots y backend deben coincidir).
- En Windows, se fija política de event loop compatible con Playwright.

---

## 11) Estado actual y próximos pasos (roadmap)

- Consolidar Telegram (confirmación, macros adicionales, sesiones, etc.)
- ~~Implementar Crystal (OpenRouter)~~ → **Implementado (v4.2): Crystal usa Kimi API directa**
- Separar memoria por transporte (Discord vs Telegram) para evitar contaminación

