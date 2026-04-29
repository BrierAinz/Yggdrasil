# 14 - Operaciones y Telemetría

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/14_OPERACIONES_TELEMETRIA.md`

---

## 14.1 Visión General

El sistema de operaciones garantiza la disponibilidad continua de Lilith mediante health checks, recuperación automática, tareas programadas y telemetría en tiempo real.

```
┌─────────────────────────────────────────────────────────────┐
│                    STACK OPERACIONAL                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Health    │    │  Scheduled  │    │   Auto      │     │
│  │   Checks    │◄──►│   Tasks     │◄──►│  Recovery   │     │
│  └──────┬──────┘    └─────────────┘    └─────────────┘     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Telemetry Layer                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │   │
│  │  │Prometheus│  │OpenTel. │  │  Logs   │  │ Alerts │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 14.2 Health Checks

### 14.2.1 Endpoint /health

```http
GET /health
```

**Respuesta exitosa (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-21T10:30:00Z",
  "total_latency_ms": 45,
  "version": "4.0.2",
  "subsystems": {
    "muninn": {
      "status": "healthy",
      "latency_ms": 12,
      "vaults_active": ["lilith", "odin", "eva"]
    },
    "schedulers": {
      "status": "healthy",
      "active_jobs": 8,
      "pending_jobs": 2
    },
    "discord_bot": {
      "status": "healthy",
      "shard_id": 0,
      "latency_ms": 45
    },
    "telegram_bot": {
      "status": "degraded",
      "note": "bot inactivo - configuración pendiente"
    },
    "episodic_db": {
      "status": "healthy",
      "entries": 1234,
      "size_bytes": 524288,
      "last_write": "2026-03-21T10:25:00Z"
    },
    "chroma_db": {
      "status": "healthy",
      "documents": 567,
      "collections": 3
    }
  }
}
```

**Códigos HTTP:**
| Código | Significado | Acción |
|--------|-------------|--------|
| `200` | Todo healthy/disabled | Ninguna |
| `207` | Algo degraded (no crítico) | Monitorear |
| `503` | Subsistema crítico unhealthy | Alerta + Auto-recovery |

### 14.2.2 Health Individual

```http
GET /health/subsystem/{name}
```

Subsistemas disponibles:
- `muninn` - Base de conocimiento cognitivo
- `schedulers` - APScheduler jobs
- `discord_bot` - Conexión Discord
- `telegram_bot` - Conexión Telegram
- `episodic_db` - Memoria episódica
- `chroma_db` - Vector store

**Ejemplo:**
```http
GET /health/subsystem/muninn

{
  "subsystem": "muninn",
  "status": "healthy",
  "latency_ms": 12,
  "vaults": {
    "lilith": {"entries": 150, "edges": 45},
    "odin": {"entries": 89, "edges": 23}
  }
}
```

### 14.2.3 Implementación

```python
# Backend/api/routes/health.py

from fastapi import APIRouter, HTTPException
import time
from typing import Dict

router = APIRouter(prefix="/health")

# Subsistemas críticos que disparan 503
CRITICAL_SUBSYSTEMS = ["muninn", "schedulers"]

@router.get("")
async def health_check() -> Dict:
    """
    Health check completo de todos los subsistemas.
    """
    start = time.time()
    
    subsystems = {
        "muninn": await _check_muninn(),
        "schedulers": await _check_schedulers(),
        "discord_bot": await _check_discord(),
        "telegram_bot": await _check_telegram(),
        "episodic_db": await _check_episodic(),
        "chroma_db": await _check_chroma()
    }
    
    # Calcular status global
    any_unhealthy = any(
        s["status"] == "unhealthy" 
        for name, s in subsystems.items() 
        if name in CRITICAL_SUBSYSTEMS
    )
    any_degraded = any(
        s["status"] == "degraded" 
        for s in subsystems.values()
    )
    
    if any_unhealthy:
        status = "unhealthy"
        code = 503
    elif any_degraded:
        status = "degraded"
        code = 207
    else:
        status = "healthy"
        code = 200
    
    result = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "total_latency_ms": int((time.time() - start) * 1000),
        "version": LILITH_VERSION,
        "subsystems": subsystems
    }
    
    return JSONResponse(content=result, status_code=code)


async def _check_muninn() -> Dict:
    """Check de MuninnDB."""
    try:
        start = time.time()
        # Query simple para verificar conectividad
        result = await muninn.query(
            vault="lilith",
            query="test",
            top_k=1
        )
        latency = int((time.time() - start) * 1000)
        
        return {
            "status": "healthy",
            "latency_ms": latency,
            "vaults_active": list(muninn.vaults.keys())[:5]
        }
    except Exception as e:
        logger.error(f"Muninn health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }


async def _check_schedulers() -> Dict:
    """Check de APScheduler."""
    try:
        jobs = scheduler.get_jobs()
        
        return {
            "status": "healthy",
            "active_jobs": len([j for j in jobs if j.next_run_time]),
            "pending_jobs": len([j for j in jobs if not j.next_run_time]),
            "scheduler_running": scheduler.running
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
```

---

## 14.3 Auto-Recovery

### 14.3.1 Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    AUTO-RECOVERY                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Job "auto_recovery" (cada 60s)                        │
│          │                                              │
│          ▼                                              │
│   ┌─────────────┐                                       │
│   │  Run Check  │                                       │
│   │   Cycle     │                                       │
│   └──────┬──────┘                                       │
│          │                                              │
│    For each subsystem crítico:                          │
│          │                                              │
│    ├─ healthy → limpiar failure_count                   │
│    │   └─ Si era unhealthy → notificar restauración     │
│    │                                                     │
│    └─ unhealthy → failure_count++                       │
│         ├─ count==1 → notificar fallo                   │
│         ├─ attempt_recovery()                           │
│         └─ count>=max → notificar intervención          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 14.3.2 Configuración

```json
// Core/Config/auto_recovery.json
{
  "enabled": true,
  "check_interval_seconds": 60,
  "retry_attempts": 3,
  "critical_subsystems": ["muninn", "discord_bot"],
  "restart_on_failure": true,
  "notifications": {
    "discord_dm": true,
    "telegram_dm": false,
    "webhook": null
  }
}
```

### 14.3.3 Implementación

```python
# Backend/core/operations/auto_recovery.py

class AutoRecoveryManager:
    """
    Gestiona recuperación automática de subsistemas críticos.
    """
    
    def __init__(self):
        self.failure_counts = {}
        self.max_retries = config.get("retry_attempts", 3)
        self.critical_subsystems = config.get("critical_subsystems", [])
        self._lock = asyncio.Lock()
    
    async def run_check_cycle(self):
        """
        Ejecuta ciclo de verificación y recuperación.
        """
        async with self._lock:
            for subsystem in self.critical_subsystems:
                health = await self._check_subsystem(subsystem)
                
                if health["status"] == "healthy":
                    await self._handle_healthy(subsystem)
                else:
                    await self._handle_unhealthy(subsystem, health)
    
    async def _handle_healthy(self, subsystem: str):
        """Maneja subsistema que volvió a estar healthy."""
        if subsystem in self.failure_counts:
            # Estaba fallando antes, ahora recuperado
            await self._notify_owner(
                f"✅ Subsistema `{subsystem}` restaurado "
                f"tras recuperación automática."
            )
            del self.failure_counts[subsystem]
    
    async def _handle_unhealthy(self, subsystem: str, health: dict):
        """Maneja subsistema unhealthy."""
        count = self.failure_counts.get(subsystem, 0) + 1
        self.failure_counts[subsystem] = count
        
        if count == 1:
            # Primer fallo - notificar
            await self._notify_owner(
                f"⚠️ Subsistema `{subsystem}` falló. "
                f"Intentando recuperación automática..."
            )
        
        # Intentar recuperación
        recovered = await self._attempt_recovery(subsystem)
        
        if not recovered and count >= self.max_retries:
            # Máximo de reintentos alcanzado
            await self._notify_owner(
                f"❌ Subsistema `{subsystem}` no se pudo recuperar "
                f"tras {self.max_retries} intentos. "
                f"Requiere intervención manual."
            )
    
    async def _attempt_recovery(self, subsystem: str) -> bool:
        """
        Intenta recuperar un subsistema específico.
        """
        try:
            if subsystem == "muninn":
                return await self._recover_muninn()
            elif subsystem == "discord_bot":
                return await self._recover_discord()
            elif subsystem == "schedulers":
                return await self._recover_schedulers()
            # ...
        except Exception as e:
            logger.error(f"Recovery failed for {subsystem}: {e}")
            return False
    
    async def _recover_muninn(self) -> bool:
        """
        Recupera conexión a MuninnDB.
        """
        logger.info("Attempting Muninn recovery...")
        
        # 1. Cerrar clientes cacheados
        await muninn.close_cached_clients()
        
        # 2. Reconectar
        await asyncio.sleep(1)
        await muninn.reconnect()
        
        # 3. Verificar
        health = await self._check_subsystem("muninn")
        return health["status"] == "healthy"
    
    async def _recover_discord(self) -> bool:
        """
        Verifica/reconecta bot de Discord.
        """
        logger.info("Attempting Discord recovery...")
        
        # Verificar orchestrator
        if not orchestrator or not orchestrator.is_ready():
            await self._reinitialize_orchestrator()
        
        health = await self._check_subsystem("discord_bot")
        return health["status"] == "healthy"


# Scheduler APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Job de auto-recovery cada 60 segundos
scheduler.add_job(
    auto_recovery_manager.run_check_cycle,
    'interval',
    seconds=60,
    id='auto_recovery',
    replace_existing=True
)
```

---

## 14.4 Tareas Programadas (Scheduled Tasks)

### 14.4.1 Configuración

```json
// Core/Config/scheduled_tasks.json
[
  {
    "id": "daily_hn",
    "enabled": true,
    "cron": "0 9 * * *",
    "action": "investiga",
    "params": { "url": "https://news.ycombinator.com/" },
    "notify_channel": "1453446914350776401",
    "description": "Resumen diario de HN a las 9am"
  },
  {
    "id": "daily_briefing",
    "enabled": true,
    "cron": "0 8 * * *",
    "action": "daily_briefing",
    "params": {},
    "notify_channel": "",
    "description": "Briefing diario (últimas 24h) a las 8am por DM"
  },
  {
    "id": "weekly_report",
    "enabled": false,
    "cron": "0 10 * * 1",
    "action": "run_plan",
    "params": {
      "query": "Resume los episodios de esta semana y dame un informe breve"
    },
    "notify_channel": "1453446914350776401",
    "description": "Informe semanal los lunes"
  },
  {
    "id": "memory_consolidation",
    "enabled": true,
    "cron": "0 */6 * * *",
    "action": "consolidate_learning",
    "params": {},
    "notify_channel": null,
    "description": "Consolidación de aprendizajes cada 6h"
  }
]
```

### 14.4.2 Implementación

```python
# Backend/core/operations/scheduler.py

from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

class TaskScheduler:
    """
    Gestiona tareas programadas con APScheduler.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.tasks_config = self._load_tasks_config()
        
        # Listeners de eventos
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )
    
    def setup_jobs(self):
        """
        Configura jobs desde archivo JSON.
        """
        for task in self.tasks_config:
            if not task.get("enabled", True):
                continue
            
            # Crear trigger desde cron expression
            trigger = CronTrigger.from_crontab(task["cron"])
            
            # Mapear acción a función
            func = self._resolve_action(task["action"])
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=task["id"],
                args=[task["params"]],
                kwargs={"notify_channel": task.get("notify_channel")},
                replace_existing=True,
                misfire_grace_time=3600  # 1 hora de tolerancia
            )
            
            logger.info(f"Scheduled job: {task['id']} ({task['cron']})")
    
    async def run_investigation(self, params: dict, notify_channel: str = None):
        """
        Ejecuta investigación programada.
        """
        url = params.get("url")
        
        try:
            # Usar orchestrator para investigar
            result = await orchestrator.execute_plan(
                message=f"Investiga y resume: {url}",
                channel_id=notify_channel
            )
            
            if notify_channel:
                await self._send_notification(
                    channel=notify_channel,
                    content=f"📋 **Reporte Programado**\n{result['summary']}"
                )
                
        except Exception as e:
            logger.error(f"Scheduled investigation failed: {e}")
            if notify_channel:
                await self._send_notification(
                    channel=notify_channel,
                    content=f"❌ Error en tarea programada: {str(e)[:200]}"
                )
    
    async def run_daily_briefing(self, params: dict, notify_channel: str = None):
        """
        Genera briefing diario de actividad.
        """
        # Recolectar métricas de últimas 24h
        stats = await self._collect_daily_stats()
        
        briefing = f"""
📊 **Daily Briefing - {datetime.now().strftime('%Y-%m-%d')}**

**Actividad:**
• Mensajes procesados: {stats['messages']}
• Planes ejecutados: {stats['plans']}
• Tools invocadas: {stats['tools']}

**Memoria:**
• Nuevos episodios: {stats['episodes']}
• Hechos almacenados: {stats['facts']}

**Sistema:**
• Uptime: {stats['uptime']}
• Health: {stats['health_status']}
        """
        
        # Enviar por DM al owner
        await self._send_dm_to_owner(briefing)
    
    async def consolidate_learning(self, params: dict, notify_channel: str = None):
        """
        Ejecuta consolidación de aprendizajes.
        """
        from Backend.core.learning.consolidator import LearningConsolidator
        
        consolidator = LearningConsolidator()
        results = await consolidator.run_consolidation()
        
        logger.info(f"Learning consolidation complete: {results}")
    
    def _on_job_executed(self, event):
        """Callback cuando un job se ejecuta exitosamente."""
        logger.debug(f"Job {event.job_id} executed successfully")
    
    def _on_job_error(self, event):
        """Callback cuando un job falla."""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        
        # Notificar al owner de fallos críticos
        if event.job_id in ["daily_hn", "memory_consolidation"]:
            asyncio.create_task(
                self._notify_owner_of_failure(event.job_id, str(event.exception))
            )
```

### 14.4.3 Gestión Runtime

```python
# API para gestionar tareas en runtime

@router.get("/api/admin/scheduler/jobs")
async def list_scheduled_jobs():
    """Lista todas las tareas programadas."""
    jobs = scheduler.get_jobs()
    
    return [
        {
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
        for job in jobs
    ]

@router.post("/api/admin/scheduler/jobs/{job_id}/run")
async def trigger_job_now(job_id: str):
    """Ejecuta una tarea inmediatamente."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Modificar trigger para ejecutar ahora
    scheduler.modify_job(job_id, next_run_time=datetime.now())
    
    return {"status": "triggered", "job_id": job_id}

@router.post("/api/admin/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pausa una tarea."""
    scheduler.pause_job(job_id)
    return {"status": "paused", "job_id": job_id}

@router.post("/api/admin/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Reanuda una tarea pausada."""
    scheduler.resume_job(job_id)
    return {"status": "resumed", "job_id": job_id}
```

---

## 14.5 Telemetría

### 14.5.1 Prometheus Metrics

```python
# Backend/core/telemetry/prometheus_exporter.py

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Métricas de negocio
MESSAGES_PROCESSED = Counter(
    'lilith_messages_total',
    'Total de mensajes procesados',
    ['channel', 'role']
)

PLANS_EXECUTED = Counter(
    'lilith_plans_executed_total',
    'Total de planes ejecutados',
    ['status', 'complexity']
)

TOOLS_INVOKED = Counter(
    'lilith_tools_invoked_total',
    'Total de tools invocadas',
    ['tool_name', 'status']
)

# Métricas de latencia
PLAN_EXECUTION_TIME = Histogram(
    'lilith_plan_execution_seconds',
    'Tiempo de ejecución de planes',
    ['complexity'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

LLM_RESPONSE_TIME = Histogram(
    'lilith_llm_response_seconds',
    'Tiempo de respuesta de LLMs',
    ['agent', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Métricas de sistema
ACTIVE_SESSIONS = Gauge(
    'lilith_active_sessions',
    'Sesiones activas actualmente'
)

MEMORY_ENTRIES = Gauge(
    'lilith_memory_entries',
    'Entradas en memoria',
    ['type']  # episodic, semantic, procedural
)

SUBSYSTEM_HEALTH = Gauge(
    'lilith_subsystem_health',
    'Estado de salud de subsistemas',
    ['subsystem']
)


class PrometheusExporter:
    """
    Exporta métricas para Prometheus.
    """
    
    def __init__(self, port: int = 9090):
        self.port = port
        
    def start(self):
        """Inicia servidor HTTP de métricas."""
        start_http_server(self.port)
        logger.info(f"Prometheus metrics server started on port {self.port}")
    
    def record_message(self, channel: str, role: str):
        """Registra mensaje procesado."""
        MESSAGES_PROCESSED.labels(channel=channel, role=role).inc()
    
    def record_plan_execution(self, status: str, complexity: str, duration: float):
        """Registra ejecución de plan."""
        PLANS_EXECUTED.labels(status=status, complexity=complexity).inc()
        PLAN_EXECUTION_TIME.labels(complexity=complexity).observe(duration)
    
    def update_health_gauge(self, subsystem: str, healthy: bool):
        """Actualiza gauge de salud."""
        SUBSYSTEM_HEALTH.labels(subsystem=subsystem).set(1 if healthy else 0)
```

### 14.5.2 OpenTelemetry (Opcional)

```json
// Core/Config/telemetry.json
{
  "prometheus": {
    "enabled": true,
    "port": 9090
  },
  "opentelemetry": {
    "enabled": false,
    "endpoint": "localhost:4317",
    "service_name": "lilith-backend",
    "traces_enabled": true,
    "metrics_enabled": false
  }
}
```

```python
# Backend/core/telemetry/opentelemetry.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

class OpenTelemetryTracer:
    """
    Tracing distribuido con OpenTelemetry.
    """
    
    def __init__(self, endpoint: str, service_name: str):
        self.provider = TracerProvider()
        
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        self.provider.add_span_processor(processor)
        
        trace.set_tracer_provider(self.provider)
        self.tracer = trace.get_tracer(service_name)
    
    def trace_plan_execution(self, plan_id: str, steps: list):
        """Crea span para trazabilidad de plan."""
        with self.tracer.start_as_current_span("plan_execution") as span:
            span.set_attribute("plan.id", plan_id)
            span.set_attribute("plan.step_count", len(steps))
            
            for i, step in enumerate(steps):
                with self.tracer.start_as_current_span(f"step_{i}") as step_span:
                    step_span.set_attribute("step.tool", step.tool)
                    step_span.set_attribute("step.status", step.status)
```

### 14.5.3 Alertas

```python
# Backend/core/telemetry/alerts.py

class AlertManager:
    """
    Gestiona alertas basadas en métricas.
    """
    
    ALERT_RULES = [
        {
            "name": "high_error_rate",
            "condition": "rate(lilith_plans_executed_total{status='error'}[5m]) > 0.1",
            "severity": "warning",
            "message": "Tasa de error elevada en planes (>10%)"
        },
        {
            "name": "slow_llm_responses",
            "condition": "histogram_quantile(0.95, lilith_llm_response_seconds) > 30",
            "severity": "warning", 
            "message": "LLM responses >30s en p95"
        },
        {
            "name": "subsystem_down",
            "condition": "lilith_subsystem_health == 0",
            "severity": "critical",
            "message": "Subsistema caído: {{ $labels.subsystem }}"
        },
        {
            "name": "memory_growth",
            "condition": "rate(lilith_memory_entries[1h]) > 1000",
            "severity": "info",
            "message": "Crecimiento rápido de memoria"
        }
    ]
    
    async def check_alerts(self):
        """Evalúa reglas de alerta."""
        for rule in self.ALERT_RULES:
            if self._evaluate_condition(rule["condition"]):
                await self._send_alert(rule)
    
    async def _send_alert(self, rule: dict):
        """Envía alerta a canales configurados."""
        message = f"[{rule['severity'].upper()}] {rule['message']}"
        
        # Discord DM al owner
        if rule["severity"] in ["critical", "warning"]:
            await self._send_discord_dm_to_owner(message)
        
        # Log
        logger.warning(f"Alert triggered: {rule['name']}")
```

---

## 14.6 Dashboard de Monitoreo

### Endpoints de Administración

```python
# Backend/api/routes/admin.py

@router.get("/api/admin/metrics")
async def get_metrics():
    """Métricas actuales en formato JSON."""
    return {
        "messages_today": await get_message_count(since="today"),
        "plans_executed_today": await get_plan_count(since="today"),
        "average_latency": await get_avg_latency(since="today"),
        "error_rate": await get_error_rate(since="today"),
        "top_tools": await get_top_tools(limit=5),
        "memory_stats": await get_memory_stats(),
        "health": await get_health_summary()
    }

@router.get("/api/admin/logs")
async def get_logs(
    level: str = "INFO",
    since: str = "1h",
    search: str = None,
    limit: int = 100
):
    """Consulta logs del sistema."""
    # Implementar con tail de archivos o query a BD
    ...

@router.post("/api/admin/maintenance")
async def trigger_maintenance(action: str):
    """
    Acciones de mantenimiento:
    - "compact_memory": Compactar bases de datos
    - "clear_cache": Limpiar cachés
    - "reload_config": Recargar configuración
    """
    ...
```

---

## 14.7 Referencias

| Módulo | Ubicación |
|--------|-----------|
| Health Checks | `Backend/api/routes/health.py` |
| Auto-Recovery | `Backend/core/operations/auto_recovery.py` |
| Task Scheduler | `Backend/core/operations/scheduler.py` |
| Prometheus | `Backend/core/telemetry/prometheus_exporter.py` |
| Config Telemetry | `Core/Config/telemetry.json` |
| Config Scheduled Tasks | `Core/Config/scheduled_tasks.json` |
| Config Auto-Recovery | `Core/Config/auto_recovery.json` |

---

*Documento 14 del índice - Operaciones y Telemetría*
