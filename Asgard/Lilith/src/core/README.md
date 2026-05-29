# Backend/core

Motor de planificacion y ejecucion para Lilith v2.0. Implementa ReAct pattern con Chain-of-Thought.

## Componentes Principales

### PlanningEngine (`planning_engine.py`)
Descompone solicitudes complejas en planes ejecutables multi-paso.

**Caracteristicas:**
- Streaming en tiempo real de razonamiento
- Evaluacion de riesgo y confianza
- Contexto enriquecido con estadisticas de proyecto
- Historial de sesion persistente

**Ejemplo de uso:**
```python
from Backend.core.planning.planning_engine import PlanningEngine

engine = PlanningEngine(llm_client)
plan = await engine.generate_plan(
    user_intent="@plan optimizar el codigo del proyecto",
    context={"project_files": [...], "available_tools": [...]}
)
```

### ExecutionEngine
Ejecution robusta con manejo de errores, timeouts y reintentos.

**Pipeline B-A-C Ejecutado:**
- 15,021 archivos Python escaneados en Resources
- 1,475 duplicados por nombre identificados
- 790 marcadores de tecnica debt (405 TODOs, 385 FIXMEs)
- Confianza de planificacion: 92%

### Archivos Clave

- `planning_engine.py` (657 LOC): Core de planificacion
- `memory_manager.py`: Contexto persistente de sesion
- `context_builder.py`: Enriquecimiento de contexto
- `risk_analyzer.py`: Evaluacion de riesgo
- `confidence_scorer.py`: Puntuacion de confianza

## Estadisticas

- **LOC totales:** 1,748
- **Funciones:** 67
- **Clases:** 26
- **Entry points:** 2 (planning_engine, execution_engine)
- **Promedio funciones/archivo:** 6.7

## Configuracion

Ver `Config/settings.json`:
```json
{
  "memory_window": 40,
  "max_tool_runtime_sec": 120,
  "approval_timeout_sec": 10
}
```

## Uso en Main

```python
# En Backend/main.py
if user_text.startswith("@plan"):
    planning_engine = PlanningEngine(llm_client)
    plan = await planning_engine.generate_plan(user_intent, context)
    # Streaming en tiempo real a Frontend/WebUI/index_v2.html
```

## Pruebas

```bash
cd D:\Proyectos\Yggdrasil\Asgard\Lilith
python -m pytest Tests/test_planning_engine.py -v
```

## Notas

- Complejidad: Manejable
- Prioridad de refactor: Media
- Dependencia critica: ToolRegistry, LLM providers
