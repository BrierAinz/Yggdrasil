# Misión v4.2.4 — Dashboard WebSocket Live

> **Versión:** 4.2.4
> **Fecha:** 2026-03-23
> **Ubicación:** `Lilith/Core/Docs/MISION_DASHBOARD_WEBSOCKET_v4.2.4.md`
> **Estado:** Completado

---

## 1. Resumen Ejecutivo

Implementación de dashboard con métricas del sistema en tiempo real vía WebSocket. El dashboard muestra CPU, memoria, disco, health checks y actividad de agentes actualizándose cada 2 segundos.

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Dashboard** | Estático (fetch manual) | Live (WebSocket) |
| **Métricas** | Solo históricas | Tiempo real + histórico |
| **Recursos** | No monitoreados | CPU, RAM, disco en vivo |
| **Health** | Solo por API | Visualización continua |

---

## 2. Componentes Implementados

### 2.1 Backend

| Archivo | Descripción |
|---------|-------------|
| `core/dashboard_websocket.py` | Manager de métricas live, recolecta y transmite |
| `api/dashboard_ws_api.py` | Endpoint WebSocket `/ws/dashboard` |

### 2.2 Frontend

| Archivo | Descripción |
|---------|-------------|
| `components/Dashboard/DashboardPanel.jsx` | Dashboard con modo live/stático toggle |
| `hooks/useWebSocket.js` | Agregados handlers para `dashboard_metrics` y `dashboard_history` |

---

## 3. Arquitectura

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  DashboardPanel │ ◄────────────────► │ DashboardWebSocket│
│    (React)      │   /ws/dashboard    │     Manager       │
└─────────────────┘                    └────────┬─────────┘
       ▲                                        │
       │ dashboard_metrics                     │ psutil
       │ dashboard_history                     │ HealthMonitor
       │                                       │
       └───────────────────────────────────────┘
                    Cada 2 segundos
```

---

## 4. Métricas Transmitidas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `cpu_percent` | float | Porcentaje de uso de CPU |
| `memory_percent` | float | Porcentaje de uso de RAM |
| `memory_used_gb` | float | RAM usada en GB |
| `memory_total_gb` | float | RAM total en GB |
| `disk_percent` | float | Porcentaje de disco usado |
| `disk_free_gb` | float | Espacio libre en GB |
| `health_status` | string | Estado general: healthy/degraded/unhealthy |
| `health_checks` | dict | Estado individual de cada subsistema |
| `active_sessions` | int | Sesiones WebSocket activas |
| `messages_per_minute` | float | Mensajes procesados por minuto |
| `agent_activity` | dict | Contador de acciones por agente |
| `avg_response_time_ms` | float | Latencia promedio de respuestas |

---

## 5. Tipos de Mensajes WebSocket

### 5.1 Server → Client

```typescript
// Métricas en tiempo real
{
  type: "dashboard_metrics",
  data: {
    timestamp: "2026-03-23T14:30:00Z",
    cpu_percent: 12.5,
    memory_percent: 45.2,
    memory_used_gb: 7.2,
    memory_total_gb: 16.0,
    disk_percent: 72.0,
    disk_free_gb: 145.2,
    health_status: "healthy",
    health_checks: {
      muninndb: { status: "healthy", latency_ms: 12 },
      kimi_api: { status: "healthy", latency_ms: 150 }
    },
    active_sessions: 3,
    messages_per_minute: 15.5,
    agent_activity: { lilith: 10, eva: 5 },
    avg_response_time_ms: 245
  }
}

// Historial inicial al conectar
{
  type: "dashboard_history",
  data: {
    metrics: [...],  // Últimos 60 puntos
    total_messages: 1000,
    agent_activity: {...}
  }
}
```

### 5.2 Client → Server

```typescript
// Ping/Pong
{ type: "ping", timestamp: 1234567890 }

// Solicitar stats del manager
{ type: "get_stats" }

// Toggle modo live (futuro)
{ type: "toggle_live", enabled: true }
```

---

## 6. API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/ws/dashboard` | WebSocket | Conexión para métricas live |
| `/api/dashboard/stats` | GET | Datos estáticos (históricos) |

---

## 7. Uso

### 7.1 Conectar desde Frontend

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/dashboard')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)

  if (data.type === 'dashboard_metrics') {
    console.log('CPU:', data.data.cpu_percent + '%')
    console.log('Memory:', data.data.memory_percent + '%')
  }
}
```

### 7.2 Usar DashboardPanel

El componente tiene un toggle para cambiar entre modos:

- **Live**: Métricas en tiempo real vía WebSocket
- **Static**: Datos históricos vía API REST

### 7.3 Registrar Actividad desde Agentes

```python
from Backend.core.dashboard_websocket import get_dashboard_manager

manager = get_dashboard_manager()
manager.record_message(agent="eva", response_time_ms=150)
```

---

## 8. Características

### 8.1 Modo Live
- ✅ Actualización cada 2 segundos
- ✅ Gráficos de CPU/Memoria en tiempo real
- ✅ Indicadores visuales de health
- ✅ Barras de progreso para recursos
- ✅ Contador de sesiones activas

### 8.2 Modo Static
- ✅ Tokens consumidos históricos
- ✅ Sesiones por día (últimos 7 días)
- ✅ Agente usage (pie chart)
- ✅ Métricas de memoria

### 8.3 UI/UX
- ✅ Badge "LIVE" con pulso cuando está conectado
- ✅ Toggle Live/Static
- ✅ Timestamp de última actualización
- ✅ Contador de puntos en memoria
- ✅ Colores según severidad (verde/amarillo/rojo)

---

## 9. Archivos Modificados/Creados

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `core/dashboard_websocket.py` | Creado | 350+ |
| `api/dashboard_ws_api.py` | Creado | 100+ |
| `components/Dashboard/DashboardPanel.jsx` | Reescrito | 550+ |
| `hooks/useWebSocket.js` | Modificado | +10 líneas |

---

## 10. Dependencias

### 10.1 Nuevas Dependencias

```bash
# Backend (ya instalado en misión health checks)
psutil>=5.9.0
```

### 10.2 Integraciones

- `HealthMonitor` → Para estado de subsistemas
- `psutil` → Para recursos del sistema
- WebSocket existente → Para transmisión

---

## 11. Changelog

### v4.2.4 (2026-03-23)

- [x] Creado `core/dashboard_websocket.py` con DashboardWebSocketManager
- [x] Creado `api/dashboard_ws_api.py` con endpoint `/ws/dashboard`
- [x] Reescrito `DashboardPanel.jsx` con modo live
- [x] Agregados tipos de mensaje `dashboard_metrics` y `dashboard_history`
- [x] Integración con HealthMonitor para estado de subsistemas
- [x] Gráficos de CPU/Memoria en tiempo real (AreaChart)
- [x] Toggle entre modo live y static
- [x] Indicadores visuales de conexión y estado
- [x] Documentación de la misión

---

## 12. Referencias

- `core/dashboard_websocket.py` — Manager de métricas live
- `api/dashboard_ws_api.py` — Endpoint WebSocket
- `Core/Frontend/spa/src/components/Dashboard/DashboardPanel.jsx` — Componente React
- `Core/Frontend/spa/src/hooks/useWebSocket.js` — Hook WebSocket
- `MISION_HEALTH_CHECKS_v4.2.4.md` — Integración con HealthMonitor

---

*Misión completada el 2026-03-23*
