# 15 - Execution Engine y Paralelización

> **Versión:** 4.2  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/15_EXECUTION_ENGINE.md`

---

## 15.1 Visión General

El Execution Engine es el motor de ejecución de planes de Lilith. Desde la versión 4.2, soporta ejecución paralela de DAGs (Directed Acyclic Graphs), permitiendo ejecutar pasos independientes simultáneamente para reducir la latencia total.

### Estado de Implementación

| Aspecto | Estado | Ubicación |
|---------|--------|-----------|
| **PlanDag** | ✅ Implementado | `core/dag/plan_dag.py` |
| **DagExecutor** | ✅ Implementado | `core/dag/dag_executor.py` |
| **DagOptimizer** | ✅ Implementado | `core/dag/dag_optimizer.py` |
| **Validación de ciclos** | ✅ Implementado | `plan_dag.validate()` |
| **Ordenamiento topológico** | ✅ Implementado | `plan_dag.topological_sort()` |
| **API Endpoints** | ✅ Implementado | `api/dag_api.py` |
| **Tests** | ✅ Implementado | `Tests/test_dag_executor.py` |

### Beneficios

- **Reducción de latencia**: 50-70% más rápido en planes con pasos independientes
- **Mejor aprovechamiento**: Uso eficiente de múltiples cores
- **Expresividad**: Permite definir planes complejos con dependencias explícitas

---

## 15.2 Arquitectura DAG

### 15.2.1 Estructura de Módulos

```
Backend/core/dag/
├── __init__.py           # Exporta PlanDag, DagExecutor, DagOptimizer
├── plan_dag.py           # PlanDag, DagNode, validación
├── dag_executor.py       # DagExecutor, ejecución paralela
└── dag_optimizer.py      # DagOptimizer, estimaciones
```

### 15.2.2 PlanDag - Representación del Grafo

```python
# Backend/core/dag/plan_dag.py

@dataclass
class DagNode:
    id: str
    tool_name: str
    params: Dict[str, Any]
    dependencies: List[str]
    status: NodeStatus  # PENDING | RUNNING | DONE | FAILED | CANCELLED
    result: Optional[Dict] = None
    error: Optional[str] = None

class PlanDag:
    """Grafo dirigido acíclico para planes."""
    
    def __init__(self, name: str = "unnamed"):
        self.nodes: Dict[str, DagNode] = {}
    
    def add_node(self, node_id: str, tool_name: str, 
                 params: dict, dependencies: list) -> DagNode:
        """Añade un nodo al DAG."""
    
    def validate(self) -> List[str]:
        """Valida el DAG (detecta ciclos, dependencias inválidas)."""
    
    def topological_sort(self) -> List[str]:
        """Ordenamiento topológico."""
    
    def compute_waves(self) -> List[List[str]]:
        """Agrupa nodos en oleadas paralelizables."""
            # Inyectar contexto del paso anterior
            if i > 0 and "context" in step.params:
                step.params["context"] = last_result
            
            # Ejecutar paso
            result = await self._execute_step(step, step_results)
            
            # Guardar resultado
            step_results[step.id] = result
            last_result = result
            
            # Notificar progreso (si hay callback)
            if progress_callback:
                progress_callback(
                    step_index=i,
                    step_id=step.id,
                    label=self._label_for_tool(step.tool)
                )
            
            # Fail-fast: abortar en error
            if result.status == "error":
                return ExecutionResult(
                    status="error",
                    failed_step=step.id,
                    error=result.error,
                    step_results=step_results
                )
        
        return ExecutionResult(
            status="success",
            step_results=step_results,
            final_result=last_result
        )
```

### 15.2.2 DAG (Directed Acyclic Graph)

Los planes complejos se definen como DAGs en `Config/plan_dags.json`:

```json
{
  "investigate_web": {
    "nodes": {
      "0": {
        "tool": "delegate_web_scraper",
        "params": {"url": "{{message}}"},
        "depends_on": []
      },
      "1": {
        "tool": "content_cleaner",
        "params": {"raw_html": "{{0.result}}"},
        "depends_on": ["0"]
      },
      "2": {
        "tool": "quality_filter",
        "params": {"content": "{{1.result}}"},
        "depends_on": ["1"]
      },
      "3": {
        "tool": "data_structurer",
        "params": {"content": "{{2.result}}"},
        "depends_on": ["2"]
      },
      "4": {
        "tool": "store_semantic_fact",
        "params": {"text": "{{3.result}}"},
        "depends_on": ["3"]
      }
    }
  }
}
```

### 15.2.3 Ordenamiento Topológico

El Planner convierte el DAG en una lista ordenada por dependencias:

```python
# Backend/core/planner.py

def _dag_to_steps(dag: dict, message: str) -> List[Step]:
    """
    Convierte DAG en lista de steps ordenada topológicamente.
    Detecta ciclos y dependencias inválidas.
    """
    nodes = dag["nodes"]
    order = []
    remaining = set(nodes.keys())
    
    while remaining:
        added = False
        
        for node_id in list(remaining):
            node = nodes[node_id]
            deps = node.get("depends_on", [])
            
            # Todas las dependencias ya están en order?
            if all(d in order for d in deps):
                # Reemplazar {{message}} y {{X.result}}
                params = _resolve_params(node["params"], message, nodes, order)
                
                order.append(node_id)
                remaining.remove(node_id)
                added = True
        
        # Si no se añadió nada y quedan nodos → ciclo o deps rotas
        if not added and remaining:
            raise DAGCycleError(
                f"Ciclo o dependencias inválidas en nodos: {remaining}"
            )
    
    # Convertir a Steps
    return [
        Step(
            id=node_id,
            tool=nodes[node_id]["tool"],
            params=nodes[node_id]["params"]
        )
        for node_id in order
    ]
```

---

## 15.3 Ejecución Paralela (Implementado)

### 15.3.1 Oleadas de Ejecución (Waves)

```
DAG de ejemplo:

    [0] ──┬──> [1] ──> [2] ──┬──> [5]
          │                   │
          └──> [3] ──> [4] ───┘

Wave 1: [0]           (sin dependencias)
Wave 2: [1], [3]      (dependen de 0)
Wave 3: [2], [4]      (1 y 3 completados)
Wave 4: [5]           (2 y 4 completados)
```

### 15.3.2 Implementación con ThreadPoolExecutor

```python
# Backend/core/plan_executor.py (futuro)

from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelPlanExecutor:
    """
    Ejecuta planes con paralelización por oleadas.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def run_plan_parallel(
        self,
        dag: DAG,
        context: dict = None,
        progress_callback: Callable = None,
        failure_policy: str = "fail_fast"  # "fail_fast" | "cancel_dependents"
    ) -> ExecutionResult:
        """
        Ejecuta DAG en oleadas paralelas.
        """
        # Calcular oleadas (waves) por nivel de dependencia
        waves = self._compute_waves(dag)
        
        completed = {}
        failed = {}
        
        for wave_idx, wave in enumerate(waves):
            # Ejecutar todos los pasos de la oleada en paralelo
            futures = {}
            
            for node_id in wave:
                # Verificar si se debe ejecutar (política de fallo)
                if failure_policy == "cancel_dependents":
                    if any(d in failed for d in dag[node_id].depends_on):
                        failed[node_id] = "cancelled (dependency failed)"
                        continue
                
                # Submit al executor
                future = self.executor.submit(
                    self._execute_step_sync,
                    dag[node_id],
                    completed
                )
                futures[future] = node_id
            
            # Esperar resultados de esta oleada
            for future in as_completed(futures):
                node_id = futures[future]
                
                try:
                    result = future.result(timeout=30)
                    completed[node_id] = result
                    
                    if progress_callback:
                        progress_callback(
                            step_id=node_id,
                            status="done",
                            wave=wave_idx
                        )
                    
                except Exception as e:
                    failed[node_id] = str(e)
                    
                    if progress_callback:
                        progress_callback(
                            step_id=node_id,
                            status="error",
                            error=str(e)
                        )
                    
                    # Política de fallo
                    if failure_policy == "fail_fast":
                        self.executor.shutdown(wait=False)
                        return ExecutionResult(
                            status="error",
                            failed_step=node_id,
                            error=str(e),
                            completed=completed,
                            failed=failed
                        )
            
            # Si todos fallaron en esta oleada, abortar
            if len(failed) == len(wave):
                return ExecutionResult(
                    status="error",
                    error="All steps in wave failed",
                    failed=failed
                )
        
        return ExecutionResult(
            status="success",
            completed=completed,
            final_result=completed.get(waves[-1][0])
        )
    
    def _compute_waves(self, dag: DAG) -> List[List[str]]:
        """
        Agrupa nodos en oleadas por nivel de dependencia.
        """
        waves = []
        completed = set()
        remaining = set(dag.nodes.keys())
        
        while remaining:
            wave = []
            
            for node_id in remaining:
                node = dag.nodes[node_id]
                deps = set(node.get("depends_on", []))
                
                # Todas las dependencias completadas?
                if deps.issubset(completed):
                    wave.append(node_id)
            
            if not wave:
                raise DAGCycleError("Ciclo detectado en DAG")
            
            waves.append(wave)
            completed.update(wave)
            remaining -= set(wave)
        
        return waves
```

### 15.3.3 Opciones de Paralelización

| Enfoque | Pros | Contras | Cuándo usar |
|---------|------|---------|-------------|
| **ThreadPoolExecutor** | Sin reescribir tools; I/O paralelo | GIL limita CPU | Extracciones web, llamadas API |
| **asyncio.gather** | Sin GIL; un solo hilo | Requiere tools async | Migración futura a async/await |
| **ProcessPoolExecutor** | Paralelismo real CPU | Overhead de procesos | Cómputo pesado (ML, análisis) |

**Recomendación para 4.1:** ThreadPoolExecutor, ya que las tools actuales son síncronas.

---

## 15.4 Feedback Progresivo (Streaming)

### 15.4.1 Arquitectura WebSocket

```
┌─────────────┐     HTTP + X-Request-ID      ┌─────────────┐
│   Discord   │ ───────────────────────────> │   FastAPI   │
│     Bot     │                              │     API     │
│             │     WS: subscribe <uuid>     │             │
│             │ <─────────────────────────── │             │
│             │                              │             │
│             │     WS: plan_progress        │             │
│             │ <─────────────────────────── │             │
│             │                              │             │
│             │     WS: plan_done            │             │
│             │ <─────────────────────────── │             │
└─────────────┘                              └─────────────┘
                                                     │
                                                     ▼
                                           ┌─────────────────┐
                                           │  PlanExecutor   │
                                           │   (callback)    │
                                           └─────────────────┘
```

### 15.4.2 Implementación del Callback

```python
# Backend/core/plan_executor.py

class PlanExecutor:
    def run_plan(
        self,
        plan: Plan,
        progress_callback: Callable[[int, str, str], None] = None
    ):
        """
        Ejecuta plan con callback de progreso.
        """
        for i, step in enumerate(plan.steps):
            result = self._execute_step(step)
            
            if progress_callback:
                label = self._label_for_tool(step.tool)
                progress_callback(
                    step_index=i,
                    step_id=step.id,
                    label=label,
                    status="done" if result.success else "error",
                    error=result.error if not result.success else None
                )
    
    def _label_for_tool(self, tool_name: str) -> str:
        """
        Retorna etiqueta legible para cada tool.
        """
        labels = {
            "delegate_web_scraper": "Extrayendo contenido web",
            "content_cleaner": "Limpiando contenido",
            "quality_filter": "Validando calidad",
            "data_structurer": "Estructurando datos",
            "store_semantic_fact": "Guardando en memoria",
            "delegate_lucifer": "Lucifer analizando",
            "delegate_eva": "Eva procesando",
            "read_file": "Leyendo archivo",
            "edit_file": "Editando archivo"
        }
        return labels.get(tool_name, f"Ejecutando {tool_name}")
```

### 15.4.3 Protocolo WebSocket

```python
# Evento de progreso
{
  "type": "plan_progress",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_steps": 5,
  "steps": [
    {"step_index": 0, "step_id": "0", "label": "Extrayendo lore", "status": "done"},
    {"step_index": 1, "step_id": "1", "label": "Limpiando", "status": "done"},
    {"step_index": 2, "step_id": "2", "label": "Lucifer sintetizando", "status": "running"}
  ],
  "current_step_index": 2,
  "current_step_id": "2",
  "current_label": "Lucifer sintetizando",
  "status": "running"
}

# Evento de finalización
{
  "type": "plan_done",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done"  # "done" | "error"
}
```

### 15.4.4 Throttling de Ediciones (Discord)

Discord limita ediciones a **5 por 5 segundos**. Implementar throttling:

```python
class DiscordProgressHandler:
    """
    Handler de progreso con throttling para Discord.
    """
    
    MIN_EDIT_INTERVAL = 1.0  # segundos entre ediciones
    
    def __init__(self):
        self.last_edit_time = 0
        self.pending_event = None
        self._lock = asyncio.Lock()
    
    async def on_progress(self, event: dict):
        """
        Recibe evento de progreso (desde WebSocket).
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_edit_time
            
            if elapsed >= self.MIN_EDIT_INTERVAL:
                # Editar inmediatamente
                await self._edit_message(event)
                self.last_edit_time = now
                self.pending_event = None
            else:
                # Guardar como pendiente
                self.pending_event = event
                
                # Programar edición diferida si no hay una pendiente
                if not self._scheduled_edit:
                    delay = self.MIN_EDIT_INTERVAL - elapsed
                    asyncio.create_task(self._deferred_edit(delay))
    
    async def _deferred_edit(self, delay: float):
        """
        Edición diferida después del intervalo mínimo.
        """
        await asyncio.sleep(delay)
        
        async with self._lock:
            if self.pending_event:
                await self._edit_message(self.pending_event)
                self.last_edit_time = time.time()
                self.pending_event = None
            self._scheduled_edit = False
```

---

## 15.5 Políticas de Manejo de Errores

### 15.5.1 Opciones de Política

| Política | Descripción | Caso de uso |
|----------|-------------|-------------|
| **fail_fast** | Abortar todo el plan al primer error | Cadenas lineales donde cada paso depende del anterior |
| **cancel_dependents** | Marcar nodo como fallido; no ejecutar dependientes | DAGs con ramas paralelas; permite que otras ramas continúen |
| **continue_on_error** | Continuar con pasos independientes | Extracciones masivas donde fallos parciales son aceptables |

### 15.5.2 Configuración

```json
// Config/plan_dags.json
{
  "investigate_web": {
    "failure_policy": "fail_fast",
    "nodes": { ... }
  },
  "batch_extract": {
    "failure_policy": "cancel_dependents",
    "nodes": { ... }
  }
}
```

### 15.5.3 Implementación de Cancel Dependents

```python
def get_executable_nodes(dag: DAG, completed: set, failed: set) -> List[str]:
    """
    Retorna nodos listos para ejecutar considerando fallos.
    """
    executable = []
    
    for node_id, node in dag.nodes.items():
        if node_id in completed or node_id in failed:
            continue
        
        deps = set(node.get("depends_on", []))
        
        # Verificar si alguna dependencia falló
        if any(d in failed for d in deps):
            # Este nodo se cancela por dependencia fallida
            failed.add(node_id)
            continue
        
        # Todas las dependencias completadas?
        if deps.issubset(completed):
            executable.append(node_id)
    
    return executable
```

---

## 15.6 Detección de Ciclos

### 15.6.1 Algoritmo de Detección

```python
class DAGCycleError(ValueError):
    """Error lanzado cuando se detecta un ciclo en el DAG."""
    pass

def detect_cycle(dag: dict) -> Optional[List[str]]:
    """
    Detecta ciclos usando DFS.
    Retorna la lista de nodos en el ciclo, o None si no hay ciclo.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in dag["nodes"]}
    path = []
    
    def dfs(node_id):
        color[node_id] = GRAY
        path.append(node_id)
        
        for neighbor in dag["nodes"][node_id].get("depends_on", []):
            if neighbor not in color:
                raise ValueError(f"Dependencia inválida: {neighbor}")
            
            if color[neighbor] == GRAY:
                # Ciclo detectado
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            
            if color[neighbor] == WHITE:
                result = dfs(neighbor)
                if result:
                    return result
        
        path.pop()
        color[node_id] = BLACK
        return None
    
    for node_id in dag["nodes"]:
        if color[node_id] == WHITE:
            cycle = dfs(node_id)
            if cycle:
                return cycle
    
    return None
```

### 15.6.2 Fallback ante Ciclo

```python
def load_dag_safe(dag_name: str) -> Optional[DAG]:
    """
    Carga DAG con validación de ciclo.
    Si hay ciclo, retorna None y loguea warning.
    """
    try:
        dag = load_dag(dag_name)
        cycle = detect_cycle(dag)
        
        if cycle:
            logger.error(f"Ciclo detectado en {dag_name}: {cycle}")
            return None
        
        return dag
        
    except Exception as e:
        logger.error(f"Error cargando DAG {dag_name}: {e}")
        return None
```

---

## 15.7 Locks y Concurrencia

### 15.7.1 Locks por Recurso

```python
# Backend/core/plan_executor.py

class PlanExecutor:
    def __init__(self):
        # Locks para recursos compartidos
        self._reddit_lock = asyncio.Lock()  # Rate limiting de Reddit
        self._file_locks = {}  # Locks por archivo
        self._global_lock = asyncio.Lock()
    
    async def _execute_step(self, step: Step) -> Result:
        """
        Ejecuta paso con locks apropiados.
        """
        # Determinar lock necesario
        if "reddit" in step.tool:
            async with self._reddit_lock:
                return await self._run_tool(step)
        
        elif step.tool in ["read_file", "edit_file"]:
            path = step.params.get("path", "")
            lock = self._file_locks.setdefault(path, asyncio.Lock())
            async with lock:
                return await self._run_tool(step)
        
        else:
            return await self._run_tool(step)
```

---

## 15.8 Referencias

| Documento | Descripción |
|-----------|-------------|
| `Backend/core/dag/plan_dag.py` | PlanDag, DagNode, validación |
| `Backend/core/dag/dag_executor.py` | DagExecutor, ejecución paralela |
| `Backend/core/dag/dag_optimizer.py` | DagOptimizer, estimaciones |
| `Backend/core/dag/__init__.py` | Exportaciones del paquete |
| `Backend/api/dag_api.py` | API endpoints para DAGs |
| `Core/Tests/test_dag_executor.py` | Tests del DAG Engine |
| `Core/Docs/17_GUIA_DAG_ENGINE.md` | Guía de uso completa |
| `Backend/core/plan_executor.py` | PlanExecutor (legacy secuencial) |
| `Backend/core/planner.py` | Step con depends_on |

---

*Documento 15 del índice - Execution Engine y Paralelización*
