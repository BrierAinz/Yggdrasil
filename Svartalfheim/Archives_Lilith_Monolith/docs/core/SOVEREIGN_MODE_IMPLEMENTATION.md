# La Corona de Lilith - Modo Soberano

## Implementación Completa v4.3

---

## Resumen

El modo Soberano transforma a Lilith de un orquestador que procesa todas las tareas con el mismo flujo, a una arquitectura híbrida donde:

- **70% del tráfico** (tareas simples) se delega directamente a agentes de Vanaheim
- **30% del tráfico** (tareas complejas) se orquesta mediante DAGs con Lilith

---

## Arquitectura

### Componentes Principales

```
Usuario → Orchestrator.execute_plan()
    ↓
┌─────────────────────────────────────┐
│  MODO SOBERANO (SovereignMode)      │
│  - Analiza complejidad              │
│  - Decide: DELEGATE vs ORCHESTRATE  │
└─────────────────────────────────────┘
    ↓
    ┌──────────────┐    ┌──────────────────┐
    │  DELEGATE    │    │   ORCHESTRATE    │
    │   (70%)      │    │     (30%)        │
    └──────┬───────┘    └────────┬─────────┘
           ↓                     ↓
    ┌──────────────┐    ┌──────────────────┐
    │  Bifrost     │    │  Planner         │
    │  → Vanaheim  │    │  → DAG Builder   │
    │     Agent    │    │  → DagExecutor   │
    └──────┬───────┘    └────────┬─────────┘
           ↓                     ↓
    ┌──────────────┐    ┌──────────────────┐
    │ Freya/Heim.  │    │ VanaheimNodeExec │
    │ Eir/Balder   │    │ (nodos en Vana)  │
    └──────┬───────┘    └────────┬─────────┘
           │                     │
           └──────────┬──────────┘
                      ↓
              ┌──────────────┐
              │   Respuesta  │
              └──────────────┘
```

---

## Archivos Implementados

### Core del Modo Soberano

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `core/sovereign_complexity.py` | ~200 | Analizador de complejidad con umbrales configurables |
| `core/sovereign_state.py` | ~250 | Tracking de busy state de Lilith, proyectos activos |
| `core/sovereign_mode.py` | ~300 | Punto de integración, decisión DELEGATE/ORCHESTRATE |
| `core/sovereign_metrics.py` | ~350 | Métricas, ratio tracking, health reports |
| `core/vanaheim_router.py` | ~200 | Routing de tareas a agentes de Vanaheim |

### DAG Engine Mejorado

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `core/dag/vanaheim_node_executor.py` | ~250 | Ejecutor de nodos DAG vía agentes Vanaheim |

### Agentes de Vanaheim

| Agente | Especialidad | Modelo |
|--------|-------------|--------|
| `Vanaheim/Agents/freya_agent.py` | Conversación, saludos, FAQs | GPT-4o-mini |
| `Vanaheim/Agents/heimdall_agent.py` | Búsquedas, información | GPT-4o-mini |
| `Vanaheim/Agents/eir_agent.py` | Código simple, explicaciones | Qwen (Ollama) |
| `Vanaheim/Agents/balder_agent.py` | Documentos, resúmenes | GPT-4o-mini |

### Orquestador de Vanaheim

| Archivo | Propósito |
|---------|-----------|
| `Vanaheim/Core/vanaheim_orchestrator.py` | Recibe tareas de Asgard, ejecuta agentes locales |

### Configuración

| Archivo | Propósito |
|---------|-----------|
| `Config/sovereign_config.json` | Configuración del modo soberano |
| `Config/vanaheim.json` | Configuración de agentes de Vanaheim |

### Tests

| Archivo | Propósito |
|---------|-----------|
| `tests/test_sovereign_mode.py` | Tests unitarios del modo soberano |
| `tests/verify_sovereign_mode.py` | Script de verificación completo |

---

## Modificaciones a Archivos Existentes

### `core/orchestrator.py`

1. **Imports**: Agregados imports de modo soberano
2. **`__init__`**: Agregada inicialización de `SovereignMode` y `VanaheimNodeExecutor`
3. **`_get_sovereign_mode()`**: Método lazy-init para obtener instancia
4. **`_get_vanaheim_node_executor()`**: Método lazy-init para Vanaheim executor
5. **`execute_plan()`**: Decisión soberana al inicio del método
6. **`_execute_with_dag()`**: Integración con `VanaheimNodeExecutor` para nodos `delegate_*`

---

## Umbrales de Decisión

```
Score 0-40:   DELEGATE (Vanaheim)
Score 40-60:  Zona gris (usar confianza)
Score 60-100: ORCHESTRATE (Lilith DAG)
```

### Puntuación por Nivel
- TRIVIAL: 10 puntos
- SIMPLE: 30 puntos
- MODERATE: 50 puntos
- COMPLEX: 75 puntos
- EXPERT: 90 puntos

### Factores Adicionales
- `has_dependencies`: +20 puntos
- `requires_multiple_agents`: +15 puntos
- `estimated_steps > 1`: +5 puntos por paso adicional

---

## Flujo de Ejecución

### Modo DELEGATE (70%)

1. Usuario envía mensaje
2. `SovereignMode.decide_mode()` analiza complejidad
3. Score < 40 → Modo DELEGATE
4. `VanaheimRouter.select_agent()` elige agente (Freya/Heimdall/Eir/Balder)
5. `BifrostClient.execute()` delega a Vanaheim
6. Si Bifrost falla → fallback a agente local (in-process)
7. Respuesta al usuario

### Modo ORCHESTRATE (30%)

1. Usuario envía mensaje complejo
2. `SovereignMode.decide_mode()` → Score >= 60
3. `Planner.plan()` genera plan con steps
4. Si hay dependencias → `DagExecutor`
5. Para nodos `delegate_*` → `VanaheimNodeExecutor`
6. Ejecución en waves paralelas
7. Consolidación y respuesta

---

## Métricas y Monitoreo

### Ratio Target
- **DELEGATE**: 70% ± 10%
- **ORCHESTRATE**: 30% ± 10%

### Alertas Automáticas
- Ratio fuera de tolerancia
- Latencia alta en DELEGATE (>2s)
- Latencia alta en ORCHESTRATE (>10s)
- Tasa de fallos > 5%

### Health Report
```python
{
    "status": "healthy|warning|critical",
    "ratio": { "delegate_ratio": 0.68, ... },
    "latency": { "delegate": { "avg_ms": 150 }, ... },
    "recommendations": [...]
}
```

---

## Configuración Clave

### `sovereign_config.json`

```json
{
    "enabled": true,
    "thresholds": {
        "delegate_max_score": 40,
        "orchestrate_min_score": 60,
        "lilith_busy_threshold": 70
    },
    "vanaheim_agents": {
        "freya": { "enabled": true, "model": "gpt-4o-mini" },
        "heimdall": { "enabled": true, "model": "gpt-4o-mini" },
        "eir": { "enabled": true, "model": "qwen2.5-coder:7b" },
        "balder": { "enabled": true, "model": "gpt-4o-mini" }
    },
    "busy_detection": {
        "max_concurrent_projects": 2,
        "max_dag_nodes_busy": 10,
        "auto_delegate_when_busy": true
    }
}
```

---

## Verificación

Ejecutar script de verificación:

```bash
cd Core/Backend/tests
python verify_sovereign_mode.py
```

### Tests Incluidos
- ✓ Syntax Check
- ✓ Complexity Analyzer
- ✓ Sovereign State
- ✓ Vanaheim Router
- ✓ DELEGATE Mode
- ✓ ORCHESTRATE Mode
- ✓ Metrics
- ✓ Workload Simulation

---

## Integración con Sistema Existente

### Uso de BifrostClient
El modo soberano integra con el `BifrostClient` existente en `core/bifrost_client.py`:
- HTTP a servicio Vanaheim (puerto 9000)
- Circuit breaker por agente
- Fallback a ejecución local

### Uso de Albedo:Sombra
El modo soberano complementa (no reemplaza) a Albedo:Sombra:
- Albedo:Sombra clasifica primero
- Si ya hay decisión de Vanaheim desde Albedo, se respeta
- Si no, el modo soberano decide

---

## Próximos Pasos (Opcional)

1. **Integrar LLMs reales** en agentes de Vanaheim (actualmente placeholders)
2. **Servicio HTTP Vanaheim** en puerto 9000 para Bifrost completo
3. **Dashboard de métricas** en tiempo real
4. **Ajuste dinámico** de umbrales basado en feedback

---

## Autor

Implementado por Claude Code (Anthropic) para Ainz.

**Versión**: 4.3.0
**Fecha**: 2026-04-03
