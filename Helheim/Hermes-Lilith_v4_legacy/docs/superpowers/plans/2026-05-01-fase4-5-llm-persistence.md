# FASE 4: LLM Integration + FASE 5: Swarm Persistence
## Plan de Implementacion

**Fecha:** 2026-05-01
**Dependencias:** FASE 3 (Swarm Coordination)
**Objetivo:** Agentes ejecutan tools reales via LLM + persistencia de estado

---

## FASE 4: LLM Integration

### Problema actual
Los agentes solo simulan trabajo (`time.sleep()`). Necesitan ejecutar tools reales.

### Solucion

#### 1. SwarmAgent LLM-powered (`Lilith/Swarm/agent.py`)
- Agregar `llm_client` al agente
- `_execute_task()` llama al LLM con system prompt especializado
- El LLM decide que tools usar (coding, files, browser, etc.)
- Resultado real se guarda en `TaskResult`

#### 2. System Prompt para Agentes (`Lilith/Swarm/prompts.py`)
- Prompt especializado para agentes swarm
- Instrucciones: "Eres un agente worker. Tienes acceso a tools. Ejecuta la tarea asignada."
- Contexto: files_read, task, capabilities
- Formato de respuesta: JSON con action + params

#### 3. Tool Executor (`Lilith/Swarm/executor.py`)
- Recibe decision del LLM (que tool, que params)
- Ejecuta la tool real (desde `Lilith/tools/`)
- Captura output/error
- Retorna resultado al agente

#### 4. Integracion con ChatManager
- `ChatManager` ya tiene conexion al LLM
- Reutilizar `chat_with_model()` para agentes
- Cada agente tiene su propio contexto/historial corto

---

## FASE 5: Swarm Persistence

### Problema actual
Todo se pierde al cerrar Lilith. Swarm, resultados, conflictos — todo en RAM.

### Solucion

#### 1. SwarmDatabase (`Lilith/Swarm/database.py`)
- SQLite en `data/swarm.db`
- Tablas:
  - `swarm_sessions`: id, task, status, created_at, completed_at
  - `agents`: id, swarm_id, task, status, result_json, started_at, completed_at
  - `messages`: id, swarm_id, from_id, to_id, type, content, timestamp
  - `conflicts`: id, swarm_id, file_path, agent_ids, severity, resolution, created_at
  - `file_locks`: id, swarm_id, file_path, agent_id, acquired_at, released_at

#### 2. SwarmManager persistence
- `save_session()` — guarda estado completo del swarm
- `load_session(session_id)` — recupera swarm del disco
- `list_sessions()` — historial de swarms
- Auto-save en background cada 30s

#### 3. CLI commands nuevos
- `/swarm save <name>` — guardar sesion actual
- `/swarm load <name>` — cargar sesion
- `/swarm history` — listar sesiones pasadas
- `/swarm resume <id>` — reanudar swarm pausado

---

## Tareas

### FASE 4
- [ ] Crear `Lilith/Swarm/prompts.py` — system prompt para agentes
- [ ] Crear `Lilith/Swarm/executor.py` — tool executor
- [ ] Modificar `SwarmAgent._execute_task()` — usar LLM real
- [ ] Integrar con `ChatManager` — reutilizar conexion LLM
- [ ] Tests para ejecucion real

### FASE 5
- [ ] Crear `Lilith/Swarm/database.py` — SQLite schema + operations
- [ ] Modificar `SwarmManager` — save/load sessions
- [ ] Agregar auto-save background thread
- [ ] Comandos CLI `/swarm save`, `/swarm load`, `/swarm history`
- [ ] Tests para persistencia
- [ ] Commit
