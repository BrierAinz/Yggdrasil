# 17 - Guía de Uso: DAG Execution Engine

> **Versión:** 4.2  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/17_GUIA_DAG_ENGINE.md`

---

## 17.1 Introducción

El **DAG Execution Engine** permite ejecutar planes de Lilith de forma paralela, aprovechando las dependencias entre pasos para reducir el tiempo total de ejecución.

### ¿Qué es un DAG?

**DAG** = **D**irected **A**cyclic **G**raph (Grafo Dirigido Acíclico)

- **Dirigido**: Las dependencias tienen dirección (A → B)
- **Acíclico**: No hay ciclos (no puede haber A → B → A)
- **Grafo**: Conjunto de nodos (pasos) conectados por aristas (dependencias)

### Cuándo Usar DAG

| Escenario | ¿Usar DAG? | Razón |
|-----------|------------|-------|
| 5 extracciones web independientes | ✅ Sí | Se ejecutan en paralelo |
| Análisis que requiere paso anterior | ✅ Sí | Dependencias explícitas |
| Secuencia lineal simple | ⚠️ Opcional | Puede usar secuencial |
| Solo 1-2 pasos | ❌ No | Overhead innecesario |

---

## 17.2 Uso Básico

### Crear un DAG Simple

```python
from Backend.core.dag import PlanDag, DagExecutor

# Crear el DAG
dag = PlanDag(name="investigacion_web")

# Añadir nodos
dag.add_node(
    node_id="scrape",
    tool_name="delegate_web_scraper",
    params={"url": "https://example.com"}
)

dag.add_node(
    node_id="limpiar",
    tool_name="content_cleaner",
    params={"html": "{{scrape_output}}"},
    dependencies=["scrape"]  # Depende de 'scrape'
)

dag.add_node(
    node_id="analizar",
    tool_name="delegate_odin",
    params={"text": "{{limpiar_output}}"},
    dependencies=["limpiar"]
)

# Validar
errors = dag.validate()
if errors:
    print(f"Errores: {errors}")
else:
    print("✅ DAG válido")
```

### Ejecutar el DAG

```python
import asyncio

# Crear executor
executor = DagExecutor(max_workers=5)

# Ejecutar
result = await executor.execute(dag)

if result.success:
    print(f"✅ Completado en {result.execution_time_ms}ms")
    print(f"Resultado: {result.node_results['analizar']}")
else:
    print(f"❌ Fallos: {result.node_errors}")
```

---

## 17.3 Construcción desde Steps

### Desde el Planner

```python
from Backend.core.planner import Step
from Backend.core.dag import PlanDag

# Steps con dependencias
steps = [
    Step(
        tool_name="read_file",
        params={"path": "data.txt"},
        step_id="leer"
    ),
    Step(
        tool_name="delegate_eva",
        params={"query": "Analiza {{leer_output}}"},
        step_id="analizar",
        depends_on=["leer"]  # Dependencia explícita
    ),
    Step(
        tool_name="store_semantic_fact",
        params={"fact": "{{analizar_output}}"},
        step_id="guardar",
        depends_on=["analizar"]
    ),
]

# Convertir a DAG
dag = PlanDag.from_steps(steps, name="pipeline_analisis")
```

### DAG con Ramas Paralelas

```python
#     [A] ──┬──> [B] ──> [D]
#           │
#           └──> [C] ──> [E]

dag = PlanDag(name="paralelo")

# Nodo inicial
dag.add_node("A", "read_file", {"path": "input.txt"})

# Rama 1: A → B → D
dag.add_node("B", "process_1", {"input": "{{A_output}}"}, ["A"])
dag.add_node("D", "merge", {"in1": "{{B_output}}"}, ["B"])

# Rama 2: A → C → E
dag.add_node("C", "process_2", {"input": "{{A_output}}"}, ["A"])
dag.add_node("E", "merge", {"in2": "{{C_output}}"}, ["C"])

# Merge final (depende de D y E)
dag.add_node("F", "finalize", {
    "data1": "{{D_output}}",
    "data2": "{{E_output}}"
}, ["D", "E"])

# B y C se ejecutan en paralelo después de A
# D y E se ejecutan en paralelo (cada uno depende de su rama)
```

---

## 17.4 Visualización

### Formato para vis.js

```python
# Obtener datos para visualización
viz_data = dag.to_visualization_format()

print(viz_data)
# {
#   "nodes": [
#     {"id": "A", "label": "read_file", "status": "done", "color": "#90EE90"},
#     {"id": "B", "label": "delegate_eva", "status": "running", "color": "#FFD700"}
#   ],
#   "edges": [
#     {"from": "A", "to": "B", "arrows": "to"}
#   ]
# }
```

### Usar con vis.js (Frontend)

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head>
<body>
    <div id="dag-viz" style="width: 800px; height: 600px; border: 1px solid #ccc;"></div>
    
    <script>
        // Datos del backend
        const data = {
            nodes: new vis.DataSet([
                {id: 'A', label: 'read_file', color: '#90EE90'},
                {id: 'B', label: 'delegate_eva', color: '#FFD700'},
                {id: 'C', label: 'store_result', color: '#CCCCCC'}
            ]),
            edges: new vis.DataSet([
                {from: 'A', to: 'B', arrows: 'to'},
                {from: 'B', to: 'C', arrows: 'to'}
            ])
        };
        
        const container = document.getElementById('dag-viz');
        const options = {
            layout: { hierarchical: { direction: 'LR' } },
            physics: false
        };
        
        new vis.Network(container, data, options);
    </script>
</body>
</html>
```

### API de Visualización

```python
import requests

# Enviar steps para visualización
response = requests.post("http://localhost:8000/api/dag/visualize", json={
    "plan_id": "mi_plan",
    "steps": [
        {"step_id": "A", "tool_name": "read_file", "params": {}},
        {"step_id": "B", "tool_name": "edit_file", "params": {}, "depends_on": ["A"]}
    ]
})

data = response.json()
print(f"Nodos: {data['nodes']}")
print(f"Aristas: {data['edges']}")
print(f"Oleadas: {data['waves']}")
```

---

## 17.5 Optimización

### Analizar un DAG

```python
from Backend.core.dag import DagOptimizer

optimizer = DagOptimizer()

# Análisis completo
opt = optimizer.optimize(dag)

print(f"⏱️  Tiempo estimado: {opt.estimated_time_ms / 1000:.1f}s")
print(f"🎯 Camino crítico: {' -> '.join(opt.critical_path)}")
print(f"⚡ Factor paralelización: {opt.parallelization_factor:.1f}x")

if opt.suggestions:
    print("💡 Sugerencias:")
    for suggestion in opt.suggestions:
        print(f"   - {suggestion}")
```

### Identificar Cuellos de Botella

```python
# Top 3 nodos más lentos
bottlenecks = optimizer.find_bottlenecks(dag, top_n=3)

for node_id, time_ms in bottlenecks:
    print(f"🐌 {node_id}: {time_ms/1000:.1f}s")
```

### Estimar Tiempos por Oleada

```python
wave_times = optimizer.estimate_wave_times(dag)

for i, time_ms in enumerate(wave_times):
    print(f"Oleada {i+1}: {time_ms/1000:.1f}s")
```

---

## 17.6 Manejo de Errores

### Políticas de Fallo

```python
# 1. fail_fast (default): Abortar en primer error
executor = DagExecutor(failure_policy="fail_fast")

# 2. continue_on_error: Continuar con nodos independientes
executor = DagExecutor(failure_policy="continue_on_error")

# 3. cancel_dependents: Cancelar nodos que dependen del fallido
executor = DagExecutor(failure_policy="cancel_dependents")
```

### Detectar Ciclos

```python
dag = PlanDag()
dag.add_node("A", "tool")
dag.add_node("B", "tool")
dag.add_edge("A", "B")
dag.add_edge("B", "A")  # Ciclo!

try:
    dag.validate()
except DAGCycleError as e:
    print(f"❌ Ciclo detectado: {e.cycle_nodes}")
    # ['A', 'B', 'A']
```

### Manejo de Timeouts

```python
executor = DagExecutor(
    node_timeout_seconds=30,  # Timeout por nodo
    max_workers=5
)

result = await executor.execute(dag)

if not result.success:
    for node_id, error in result.node_errors.items():
        if "Timeout" in error:
            print(f"⏱️  {node_id} excedió el tiempo")
```

---

## 17.7 Callbacks de Progreso

### WebSocket / Discord

```python
async def on_progress(progress):
    """Callback llamado en cada cambio de estado."""
    print(f"📊 {progress.completed_nodes}/{progress.total_nodes} completados")
    print(f"🔄 Wave {progress.current_wave}/{progress.total_waves}")
    
    # Enviar a Discord/WebSocket
    await discord_ws.send({
        "type": "dag_progress",
        "completed": progress.completed_nodes,
        "total": progress.total_nodes,
        "statuses": progress.node_statuses
    })

executor = DagExecutor()
executor.set_progress_callback(on_progress)

result = await executor.execute(dag)
```

### Progress Bar (CLI)

```python
from tqdm import tqdm

progress_bar = tqdm(total=len(dag.nodes), desc="Ejecutando DAG")

def update_progress(p):
    progress_bar.n = p.completed_nodes
    progress_bar.refresh()

executor = DagExecutor()
executor.set_progress_callback(update_progress)

result = await executor.execute(dag)
progress_bar.close()
```

---

## 17.8 Integración con Orchestrator

### Uso Automático

El `Orchestrator` detecta automáticamente planes con dependencias:

```python
# Si algún step tiene 'depends_on', usa DagExecutor automáticamente
steps = [
    Step(tool_name="A", params={}, step_id="A"),
    Step(tool_name="B", params={}, step_id="B", depends_on=["A"]),
]

# El orchestrator detecta y usa DagExecutor
result = orchestrator.execute_plan(
    message="Analiza esto",
    steps=steps  # Tiene dependencias -> DagExecutor
)
```

### Forzar Modo

```python
# Para usar DAG explícitamente
from Backend.core.dag import PlanDag, DagExecutor

dag = PlanDag.from_steps(steps)
executor = DagExecutor()
result = await executor.execute(dag)
```

---

## 17.9 Ejemplos Completos

### Ejemplo 1: Pipeline de Minería Web

```python
async def pipeline_mineria(urls: List[str]):
    """Extrae y analiza múltiples URLs en paralelo."""
    
    dag = PlanDag(name="mineria_batch")
    
    # Crear nodos de scraping para cada URL
    for i, url in enumerate(urls):
        dag.add_node(
            f"scrape_{i}",
            "delegate_web_scraper",
            {"url": url}
        )
        dag.add_node(
            f"clean_{i}",
            "content_cleaner",
            {"html": f"{{{{scrape_{i}_output}}}"},
            dependencies=[f"scrape_{i}"]
        )
        dag.add_node(
            f"analyze_{i}",
            "delegate_odin",
            {"text": f"{{{{clean_{i}_output}}}"},
            dependencies=[f"clean_{i}"]
        )
    
    # Todos los scrapings se ejecutan en paralelo!
    
    executor = DagExecutor(max_workers=10)
    result = await executor.execute(dag)
    
    return result
```

### Ejemplo 2: Análisis de Código

```python
async def analizar_proyecto(path: str):
    """Lee múltiples archivos y los analiza en paralelo."""
    
    dag = PlanDag(name="analisis_codigo")
    
    # Listar archivos
    archivos = ["main.py", "utils.py", "models.py"]
    
    # Leer todos en paralelo
    for archivo in archivos:
        dag.add_node(
            f"read_{archivo}",
            "read_file",
            {"path": f"{path}/{archivo}"}
        )
    
    # Analizar cada uno (depende de su lectura)
    for archivo in archivos:
        dag.add_node(
            f"analyze_{archivo}",
            "delegate_eva",
            {"code": f"{{{{read_{archivo}_output}}}"},
            dependencies=[f"read_{archivo}"]
        )
    
    # Síntesis final (depende de todos los análisis)
    dag.add_node(
        "synthesis",
        "delegate_adan",
        {
            "analyses": [f"{{{{analyze_{a}_output}}}" for a in archivos]
        },
        dependencies=[f"analyze_{a}" for a in archivos]
    )
    
    executor = DagExecutor(max_workers=5)
    return await executor.execute(dag)
```

---

## 17.10 Mejores Prácticas

### DO ✅

- **Usa IDs descriptivos**: `"read_config"` mejor que `"step_1"`
- **Valida antes de ejecutar**: Siempre llama `dag.validate()`
- **Maneja errores gracefully**: Usa `continue_on_error` cuando sea apropiado
- **Optimiza**: Usa `DagOptimizer` para identificar mejoras
- **Visualiza**: Usa la API de visualización para debuggear

### DON'T ❌

- **No crees ciclos**: A → B → A romperá la validación
- **No dependencias innecesarias**: Solo declara dependencias reales
- **No ignores errores**: Siempre revisa `result.success`
- **No sobrecargues workers**: `max_workers` razonable (3-10)

---

## 17.11 Referencias Rápidas

### Imports

```python
from Backend.core.dag import (
    PlanDag,           # Grafo
    DagNode,           # Nodo individual
    NodeStatus,        # Estados
    DagExecutor,       # Ejecutor
    DagOptimizer,      # Optimizador
    DAGCycleError,     # Excepción de ciclo
    DAGValidationError,  # Excepción de validación
)
```

### Configuración

```python
# Config en Core/Config/planner.json
{
    "dag_max_workers": 5,
    "dag_use_parallel": true,
    "dag_wave_timeout_seconds": 120,
    "dag_partial_failure_tolerant": false
}
```

---

*Documento 17 del índice - Guía de Uso del DAG Execution Engine*
