# Robustez Operacional — Health Checks, Telemetría y Backups (A.1 + A.2 + A.3)

**Versión:** 4.1
**Fecha:** 2026-03-21

---

## A.1 — Health Checks y Auto-recovery

### Endpoint `/health`

```http
GET /health
```

Verifica el estado de todos los subsistemas y devuelve un diagnóstico estructurado:

```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-03-21T10:30:00Z",
  "total_latency_ms": 45,
  "subsystems": {
    "muninn":       {"status": "healthy", "latency_ms": 12},
    "schedulers":   {"status": "healthy", "active_jobs": 8},
    "discord_bot":  {"status": "healthy"},
    "telegram_bot": {"status": "degraded", "note": "bot inactivo"},
    "episodic_db":  {"status": "healthy", "entries": 1234, "size_bytes": 524288}
  }
}
```

**Códigos HTTP:**
- `200` — Todos healthy/disabled/unknown
- `207` — Algún subsistema degraded (no crítico)
- `503` — Subsistema crítico unhealthy (`muninn` o `discord_bot`)

**Check individual:**
```http
GET /health/subsystem/muninn
GET /health/subsystem/schedulers
GET /health/subsystem/episodic_db
```

### Subsistemas críticos vs. degraded

| Subsistema | Crítico | Descripción del check |
|------------|---------|----------------------|
| `muninn` | ✅ Sí | Query simple a vault `lilith`, timeout 3s |
| `schedulers` | ✅ Sí | Verifica que el APScheduler tenga jobs activos |
| `discord_bot` | No | Verifica que el orchestrator esté instanciado |
| `telegram_bot` | No | Verifica estado del bot |
| `episodic_db` | No | Lee `episodic_log.jsonl` y cuenta entradas |

### Auto-recovery

El `AutoRecoveryManager` monitorea subsistemas críticos cada 60 segundos (configurable).

**Flujo de recuperación:**

```
Job "auto_recovery" (cada 60s)
       ↓
AutoRecoveryManager.run_check_cycle()
       ↓
Para cada subsistema crítico:
  ├─ healthy → limpiar failure_count
  │    └─ Si antes era unhealthy → notificar owner: ✅ restaurado
  └─ unhealthy → failure_count++
       ├─ Si count==1 → notificar owner: ⚠️ fallo detectado
       ├─ attempt_recovery(subsistema)
       │    ├─ muninn: cerrar clientes cacheados + reconectar
       │    ├─ discord_bot: verificar orchestrator
       │    └─ schedulers: reanudar jobs pausados
       └─ Si count >= max_retries → notificar owner: ❌ requiere intervención
```

**Notificaciones al owner:**
```
⚠️ Subsistema `muninn` falló. Intentando recuperación automática...
✅ Subsistema `muninn` restaurado tras recuperación automática.
❌ Subsistema `muninn` no se pudo recuperar tras 3 intentos. Requiere intervención manual.
```

**Configuración (`Config/auto_recovery.json`):**
```json
{
  "enabled": true,
  "check_interval_seconds": 60,
  "retry_attempts": 3,
  "critical_subsystems": ["muninn", "discord_bot"],
  "restart_on_failure": true
}
```

---

## A.2 — Telemetría

### Métricas Prometheus

**Endpoint:**
```http
GET /metrics
```
Devuelve métricas en formato texto Prometheus para scraping.

**Métricas disponibles:**

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `lilith_llm_requests_total` | Counter | `model`, `user_role` | Total de requests LLM |
| `lilith_llm_errors_total` | Counter | `model`, `error_type` | Errores LLM |
| `lilith_llm_tokens_total` | Counter | `model`, `direction` | Tokens consumidos (input/output) |
| `lilith_llm_latency_seconds` | Histogram | `model` | Latencia de requests LLM |
| `lilith_tool_calls_total` | Counter | `tool_name`, `status` | Llamadas a tools (success/error/timeout) |
| `lilith_tool_latency_seconds` | Histogram | `tool_name` | Latencia de tools |
| `lilith_active_sessions` | Gauge | `transport` | Sesiones activas (discord/telegram/vscode) |
| `lilith_subsystem_healthy` | Gauge | `subsystem` | 1=healthy, 0=unhealthy |
| `lilith_plans_generated_total` | Counter | `reason` | Planes por razón |
| `lilith_plan_confidence` | Histogram | `reason` | Confianza del planner |

**Instrumentar código LLM:**
```python
from Backend.telemetry.metrics import time_llm_call, record_llm_request

with time_llm_call(model="kimi-k2.5"):
    response = call_llm(...)

record_llm_request(
    model="kimi-k2.5",
    user_role="owner",
    input_tokens=1024,
    output_tokens=512,
)
```

**Instrumentar tools:**
```python
from Backend.telemetry.metrics import time_tool_call

with time_tool_call(tool_name="delegate_eva"):
    result = tool.execute(params)
```

### Trazas OpenTelemetry

Las trazas instrumentan el flujo completo de cada request:

```
span: process_request
  ├─ span: create_plan
  ├─ span: execute_step_delegate_odin
  │    └─ span: llm_call
  └─ span: execute_step_store_semantic_fact
```

**Uso:**
```python
from Backend.telemetry.tracing import span_request, span_plan, span_step

with span_request(message, transport="discord", user_id="123"):
    with span_plan(message):
        plan = planner.plan(message)
    for i, step in enumerate(plan.steps):
        with span_step(step.tool_name, i):
            executor.execute_step(step)
```

**Activar en `Config/telemetry.json`:**
```json
{
  "opentelemetry": {
    "enabled": true,
    "endpoint": "localhost:4317",
    "service_name": "lilith-backend"
  }
}
```

Requiere Jaeger o Grafana Tempo en `localhost:4317` (OTLP gRPC).

### Dashboard Grafana

**Importar:** `Core/Telemetry/grafana_dashboard.json` → Grafana → Import dashboard.

**Datasource requerido:** Prometheus apuntando a `http://localhost:9090` (o el puerto donde esté el `/metrics` de Lilith scrapeado por Prometheus).

**Paneles incluidos:**
1. Estado de subsistemas (semáforo verde/rojo)
2. Tasa de requests LLM por modelo
3. Latencia LLM P95 y P50
4. Tool calls: tasa éxito vs. error
5. Sesiones activas por transporte
6. Planes por razón (últimas 24h)
7. Latencia P95 por tool

---

## A.3 — Backups Automáticos

### Cómo funciona

El `BackupManager` crea snapshots ZIP con:
- `Core/Data/episodic_log.jsonl` — episodios de conversación
- `Core/Data/decision_audit.jsonl` — auditoría de decisiones
- `Core/Config/*.json` — toda la configuración
- `checksums.json` — SHA256 de cada archivo incluido

**Job diario (03:00):** el scheduler ejecuta automáticamente `create_snapshot()`.

**Job semanal (domingos 05:00):** el scheduler ejecuta `verify_all_snapshots()`.

### API REST de backups

```http
GET  /api/backups/list              # Lista snapshots disponibles
POST /api/backups/create            # Crea snapshot manual inmediatamente
POST /api/backups/verify/{name}     # Verifica integridad de un snapshot
POST /api/backups/restore           # Restaura snapshot (con dry_run opcional)
GET  /api/backups/verify-all        # Verifica todos los snapshots
```

**Ejemplo: crear snapshot manual:**
```bash
curl -X POST http://localhost:8000/api/backups/create
# → {"ok": true, "path": "D:/Backups/Lilith/lilith_backup_2026-03-21_10-00-00.zip",
#    "size_bytes": 245760, "files": 42}
```

**Ejemplo: restaurar con dry-run primero:**
```bash
# 1. Verificar qué se restauraría (sin modificar archivos)
curl -X POST http://localhost:8000/api/backups/restore \
  -H "Content-Type: application/json" \
  -d '{"snapshot_name": "lilith_backup_2026-03-20_03-00-00.zip", "dry_run": true}'

# 2. Restaurar (solo si dry_run fue ok)
curl -X POST http://localhost:8000/api/backups/restore \
  -H "Content-Type: application/json" \
  -d '{"snapshot_name": "lilith_backup_2026-03-20_03-00-00.zip", "dry_run": false}'
```

### Política de retención

| Tipo | Cantidad | Descripción |
|------|----------|-------------|
| Diarios | 7 | Los 7 snapshots más recientes |
| Semanales | 4 | Últimas 4 semanas (domingos) |

Los snapshots fuera de política se eliminan automáticamente al crear uno nuevo.

### Verificación de integridad

Cada snapshot incluye `checksums.json` con el SHA256 de cada archivo. Al restaurar:
1. Se verifica el checksum de cada archivo contra el registrado
2. Si hay mismatch → restauración abortada
3. Antes de sobrescribir → se crea un snapshot de rollback automático

**Notificaciones:**
```
# Backup diario exitoso → solo log (sin notificación para no spamear)
[BackupManager] Snapshot created: lilith_backup_2026-03-21_03-00-00.zip (24.5 MB)

# Backup fallido → notificación al owner
❌ Backup diario falló: sin archivos para incluir

# Snapshot corrupto detectado en verificación semanal → notificación al owner
⚠️ Backup verify: 1 snapshot(s) corrupto(s): lilith_backup_2026-03-15_03-00-00.zip
```

### Configuración (`Config/backups.json`)

```json
{
  "enabled": true,
  "backup_dir": "D:/Backups/Lilith",
  "schedule": "daily",
  "time": "03:00",
  "retention": {
    "daily_backups": 7,
    "weekly_backups": 4
  },
  "include": [
    "Core/Data/episodic_log.jsonl",
    "Core/Data/decision_audit.jsonl",
    "Core/Config"
  ]
}
```

---

## Tests

```bash
# Ejecutar todos los tests de robustez
pytest Tests/test_health_checks.py Tests/test_telemetry.py Tests/test_backups.py -v

# → 34 passed
```

| Archivo | Tests | Qué cubre |
|---------|-------|-----------|
| `test_health_checks.py` | 11 | Health endpoint, códigos HTTP, auto-recovery |
| `test_telemetry.py` | 13 | Métricas Prometheus, context managers, endpoint /metrics |
| `test_backups.py` | 10 | Crear snapshot, verificar, restaurar, detectar corrupción |

---

## Jobs del scheduler relacionados

| Job ID | Frecuencia | Descripción |
|--------|-----------|-------------|
| `auto_recovery` | Cada 60s | Health check + auto-recuperación |
| `daily_backup` | Diario 03:00 | Crear snapshot |
| `backup_verify` | Domingos 05:00 | Verificar integridad de todos los snapshots |
| `pattern_analysis` | Diario 08:30 | Detectar patrones repetitivos (D.11) |

---

## Archivos implementados

| Archivo | Descripción |
|---------|-------------|
| `Backend/api/health_api.py` | Endpoint `/health` + checks por subsistema |
| `Backend/core/auto_recovery.py` | AutoRecoveryManager |
| `Backend/telemetry/metrics.py` | Métricas Prometheus |
| `Backend/telemetry/tracing.py` | Trazas OpenTelemetry |
| `Backend/api/metrics_api.py` | Endpoint `/metrics` |
| `Backend/core/backup_manager.py` | BackupManager |
| `Backend/api/backups_api.py` | API REST de backups |
| `Telemetry/grafana_dashboard.json` | Dashboard Grafana importable |
| `Config/auto_recovery.json` | Config de auto-recovery |
| `Config/backups.json` | Config de backups |
| `Config/telemetry.json` | Config de telemetría |
