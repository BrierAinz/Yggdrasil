# 11 - Stack de Atención + Modos de Personalidad

> **Versión:** 4.1  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/11_STACK_ATENCION.md`
> **Estado:** final

Sistema para mantener prioridades activas entre mensajes y adaptar la personalidad de Lilith según el contexto.

---

## 11.1 Stack de Atención

1. [Stack de Atención](#stack-de-atención)
2. [Extracción de Subtareas](#extracción-de-subtareas)
3. [Modos de Personalidad](#modos-de-personalidad)
4. [Comandos](#comandos)
5. [Integración con Planner](#integración-con-planner)
6. [API Reference](#api-reference)

---

## 11.2 Extracción de Subtareas

El **Attention Stack** mantiene una lista persistente de tareas/prioridades por sesión.

### Concepto

Cuando un usuario dice:
> "Necesito que hagas X, luego Y, y finalmente Z"

El sistema:
1. Extrae las 3 subtareas
2. Las añade al stack de la sesión
3. Inyecta el stack en el contexto del planner
4. Marca tareas como completadas según se avanza

### Uso Programático

```python
from Backend.core.attention_stack import get_attention_stack

# Obtener stack para una sesión
stack = get_attention_stack("session_123")

# Añadir tarea
item = stack.push(
    description="Refactorizar módulo X",
    priority=5,  # 1-5, donde 5 es máxima
    dependencies=[]  # IDs de tareas previas
)

# Obtener tareas activas (pendientes + en progreso)
active = stack.get_active()
for item in active:
    print(f"{item.id}: {item.description} (P{item.priority})")

# Completar tarea
stack.pop(item.id)  # Marca como 'done'

# Generar bloque de contexto para el LLM
context = stack.to_context_block()
```

### Estados de Items

| Estado | Emoji | Descripción |
|--------|-------|-------------|
| `pending` | ⏳ | Esperando ser trabajada |
| `in_progress` | 🔨 | Actualmente en progreso |
| `done` | ✅ | Completada |
| `blocked` | 🚫 | Bloqueada por dependencias |
| `cancelled` | 🗑️ | Cancelada/Descartada |

### Persistencia

El stack se guarda en SQLite (`Data/attention_stack.db`):

```sql
CREATE TABLE attention_stack (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    description TEXT,
    priority INTEGER,
    status TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    dependencies TEXT,  -- JSON array
    metadata TEXT       -- JSON object
);
```

---



El **TaskExtractor** detecta automáticamente subtareas en mensajes.

### Métodos de Extracción

1. **Listas explícitas** (mayor confianza):
   ```
   1. Crear base de datos
   2. Implementar API
   3. Escribir tests
   ```

2. **Bullets**:
   ```
   - Configurar servidor
   - Instalar dependencias
   ```

3. **Keywords secuenciales**:
   ```
   "Primero haz X, luego Y, finalmente Z"
   ```

4. **Conjunciones**:
   ```
   "Configura el servidor y también las dependencias"
   ```

### Uso

```python
from Backend.core.task_extractor import extract_tasks

tasks = extract_tasks("""
    Necesito que:
    1. Revises el código
    2. Identifiques bugs
    3. Propongas fixes
""")

for task in tasks:
    print(f"- {task.description} (conf: {task.confidence:.2f})")
# - Revises el código (conf: 0.95)
# - Identifiques bugs (conf: 0.95)
# - Propongas fixes (conf: 0.95)
```

---

## 11.3 Modos de Personalidad

Los **modos de personalidad** adaptan el estilo de respuesta de Lilith según el contexto.

### Modos Disponibles

| Modo | Emoji | Descripción | Tono |
|------|-------|-------------|------|
| **Arquitecto** | 🏗️ | Diseño de sistemas y trade-offs | Técnico, analítico |
| **Debugger** | 🔬 | Análisis de bugs y problemas | Preciso, metódico |
| **Creativo** | 💡 | Brainstorming e ideas | Libre, exploratorio |
| **Ejecutor** | ⚡ | Acciones rápidas | Directo, eficiente |
| **Tutor** | 📚 | Explicaciones didácticas | Pedagógico, paciente |
| **Seguridad** | 🛡️ | Focus en vulnerabilidades | Cauteloso, riguroso |
| **Optimizador** | 🚀 | Performance y eficiencia | Analítico, métrico |

### Activación Manual

```
/modo arquitecto
```

### Activación Automática

El sistema detecta triggers en los mensajes:

```python
# Mensaje: "tengo un bug extraño"
# Detectado: modo "debugger"

# Mensaje: "diseña una arquitectura"
# Detectado: modo "arquitecto"
```

### Modo Sticky

Una vez detectado/activado, el modo persiste por un tiempo:

| Modo | Duración |
|------|----------|
| Arquitecto | 30 min |
| Debugger | 45 min |
| Creativo | 20 min |
| Ejecutor | 15 min |
| Tutor | 60 min |
| Seguridad | 40 min |
| Optimizador | 30 min |

### Overlay en Prompt

Cada modo inyecta un overlay en el system prompt:

```
[Modo Activo: Arquitecto de Sistemas 🏗️]

Eres un arquitecto de sistemas experimentado. Priorizas escalabilidad, 
mantenibilidad y diseño limpio. Presentas opciones con pros/contras analizados.

Tono: técnico, analítico, estructurado
```

### Uso Programático

```python
from Backend.core.personality_mode_manager import (
    get_personality_mode_manager,
    detect_and_set_mode
)

manager = get_personality_mode_manager()

# Cambiar modo manualmente
manager.set_mode("session_123", "debugger")

# Detectar automáticamente
detected = detect_and_set_mode("tengo un bug", "session_123")

# Obtener overlay para prompt
overlay = manager.get_mode_overlay("session_123")

# Obtener modo actual
mode_info = manager.get_current_mode_info("session_123")
print(f"Modo: {mode_info['name']} {mode_info['emoji']}")
```

---

## 11.4 Comandos

### Discord

#### `/modo <modo>`
Cambia el modo de personalidad.

```
/modo arquitecto
/modo debugger
/modo creativo
/modo ejecutor
/modo tutor
/modo seguridad
/modo optimizador
```

#### `/modo_info`
Muestra información sobre todos los modos.

#### `/stack [action] [item_id]`
Gestiona el stack de tareas.

```
/stack action:view              # Ver tareas pendientes
/stack action:complete item_id:abc123  # Marcar como hecho
/stack action:remove item_id:abc123    # Eliminar tarea
/stack action:clear             # Limpiar completados
```

#### `/stack_add <descripcion> [prioridad]`
Añade una tarea al stack manualmente.

```
/stack_add descripcion:"Revisar PR" prioridad:4
```

---

## 11.5 Integración con Planner

El orchestrator enriquece automáticamente el contexto:

```python
from Backend.core.orchestrator_with_stack import enrich_context_for_planner

context = enrich_context_for_planner(
    session_id="session_123",
    base_context={"user_id": "user_456"}
)

# Contexto enriquecido incluye:
# - attention_stack: Bloque con tareas pendientes
# - personality_mode: Overlay del modo activo
# - has_pending_tasks: Boolean
# - mode_info: Metadata del modo
```

### Ejemplo de Prompt Enriquecido

```
[Modo Activo: Arquitecto de Sistemas 🏗️]

Eres un arquitecto de sistemas experimentado...

---

📋 TAREAS PENDIENTES DE ESTA SESIÓN:

1. ⏳ 🔴 Refactorizar módulo X
2. 🔨 🟡 Documentar API Y
3. ⏳ 🟢 Crear tests para Z

Recuerda completar estas tareas antes de finalizar la sesión.

---

Usuario: ¿Qué patrones debería usar?
```

---

## 11.6 API Reference

### Endpoints

#### Modos

```
POST /api/session/mode
{
    "session_id": "string",
    "mode_name": "string",
    "user_id": "string"
}

GET /api/session/mode?session_id=xxx

GET /api/modes

GET /api/modes/{mode_name}

GET /api/session/mode/history?session_id=xxx&limit=10
```

#### Stack

```
GET /api/session/stack?session_id=xxx&include_done=false

POST /api/session/stack/add
{
    "session_id": "string",
    "description": "string",
    "priority": 3,
    "dependencies": []
}

POST /api/session/stack/complete
{
    "session_id": "string",
    "item_id": "string"
}

POST /api/session/stack/remove
{
    "session_id": "string",
    "item_id": "string"
}

POST /api/session/stack/clear
{
    "session_id": "string"
}
```

---

## 11.7 Ejemplos de Uso

### Escenario 1: Debug Complejo

**Usuario**: "Tengo un bug extraño. Primero revisa los logs, luego identifica el módulo problemático, y finalmente propón un fix."

**Sistema**:
1. Detecta modo "debugger" (trigger: "bug")
2. Extrae 3 subtareas
3. Añade al stack
4. Responde con estilo metódico e investigativo

### Escenario 2: Cambio de Contexto

**Usuario**: "Ahora olvida el bug, necesito que diseñes la arquitectura del nuevo módulo."

**Sistema**:
1. Detecta modo "arquitecto" (trigger: "diseñes")
2. Cambia overlay a estilo arquitectónico
3. Las tareas anteriores permanecen en stack (por si vuelve)

### Escenario 3: Completar Tareas

**Usuario**: "✅ Ya revisé los logs"

**Sistema**:
1. Marca "Revisar logs" como completada
2. Muestra tareas restantes del stack
3. "Pendiente: Identificar módulo problemático, Proponer fix"

---

## 11.8 Configuración

### `personality_modes.json`

```json
{
  "modes": {
    "custom_mode": {
      "name": "Mi Modo",
      "description": "Descripción",
      "overlay": "Instrucciones para el LLM...",
      "triggers": ["keyword1", "keyword2"],
      "tone": "descripción del tono",
      "emoji": "🔧",
      "color": "#FF0000",
      "sticky_minutes": 30
    }
  },
  "default_mode": "arquitecto",
  "auto_detection": {
    "enabled": true,
    "min_trigger_matches": 1,
    "sticky_mode_enabled": true
  }
}
```

---

## 11.9 Testing

```bash
# Tests de stack de atención
python -m pytest Core/Tests/test_attention_stack.py -v

# Tests de modos de personalidad
python -m pytest Core/Tests/test_personality_modes.py -v

# Tests de integración
python test_stack_modes_integration.py
```

---

## 11.10 Beneficios

| Aspecto | Mejora |
|---------|--------|
| **Coherencia** | No se pierden subtareas en requests complejos |
| **Contexto** | Personalidad adapta estilo a la situación |
| **Productividad** | Stack visible mantiene foco en prioridades |
| **Flexibilidad** | Modos cambian según necesidad sin perder memoria |

---

*Documento 11 del índice - Stack de Atención y Modos de Personalidad*
