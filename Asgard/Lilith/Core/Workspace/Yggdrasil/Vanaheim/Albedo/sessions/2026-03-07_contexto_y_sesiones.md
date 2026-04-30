# Sesión: 2026-03-07 — Contexto Persistente y Límite de Tokens

## Misión
Implementar sistema de persistencia de conversaciones con historial visible y seguimiento de uso de contexto (2M tokens).

## Ejecutado

### Backend — Session Management
1. **SessionManager** (`Backend/memory/session_manager.py`)
   - Guarda sesiones en `Memory/sessions/{id}.json`
   - Genera resúmenes automáticos vía Grok cuando >10 mensajes
   - Compresión automática al 70% de uso de tokens
   - Carga contexto relevante de ChromaDB (24-48h window)

2. **MemoryManager** (`Backend/memory/memory_manager.py`)
   - `get_relevant_context()` con filtro temporal
   - `format_context_for_prompt()` para inyectar contexto al LLM

3. **main.py** — Integración completa
   - Variables globales: `_global_session_manager`, `_current_session_id`, `_current_messages`
   - Eventos nuevos: `session_history`, `load_session`, `new_session`, `get_token_stats`
   - Guardado automático al cerrar (Ctrl+C)
   - Inyección de contexto relevante en cada mensaje
   - Envío de estadísticas de tokens al frontend

### Frontend — UI Updates

1. **StatusBar** (`components/Layout/StatusBar.jsx`)
   - Barra de progreso de uso de tokens
   - Colores: Verde (<80%) → Oro (80-95%) → Crimson (>95%)
   - Listener de eventos `token_stats` vía WebSocket

2. **SessionList** (`components/Sidebar/SessionList.jsx`)
   - Carga historial desde backend vía `session_history`
   - Muestra sesiones guardadas con badge "Guardada"
   - Carga sesión seleccionada vía `load_session`
   - Nueva sesión vía `new_session`
   - Integración con `onEvent` del connection store

3. **Store** (`store/index.js`)
   - Sistema de eventos: `emitEvent()`, `onEvent()`
   - Event listeners globales para WebSocket

4. **useWebSocket** (`hooks/useWebSocket.js`)
   - Emite eventos: `session_loaded`, `session_history`, `token_stats`
   - Manejo de `session_created` y `session_loaded`

## API Endpoints WebSocket

| Action | Tipo | Descripción |
|--------|------|-------------|
| `session_history` | COMMAND | Solicitar lista de sesiones guardadas |
| `load_session` | COMMAND | Cargar sesión específica |
| `new_session` | COMMAND | Crear nueva sesión |
| `get_token_stats` | COMMAND | Obtener estadísticas de tokens |
| `token_stats` | EVENT | Respuesta con {used, max, percentage} |
| `session_history` | EVENT | Lista de sesiones del backend |
| `session_loaded` | EVENT | Sesión cargada con mensajes |

## Decisiones Clave

1. **Formato de sesión**: JSON con {session_id, messages[], summary, created_at, updated_at, message_count}

2. **Auto-summary**: Se genera automáticamente cuando hay >10 mensajes, usando Grok para crear resumen conciso

3. **Compresión**: Al 70% de uso de tokens, se comprimen los mensajes más antiguos en un resumen

4. **Contexto relevante**: ChromaDB provee contexto semántico de las últimas 24-48h, se inyecta en el prompt

5. **Persistencia dual**: Sesiones en RAM (_current_messages) + JSON en disco + ChromaDB para búsqueda semántica

## Bug Fixes

### Fix 1: session_history no responde

**Problema:** El evento `session_history` no respondía al frontend, causando loop de carga infinita.

**Causa:** En `ipc_server.py`, el método `_process_raw_message()` solo permitía acciones específicas predefinidas (`send_message`, `get_status`, etc.) y descartaba silenciosamente cualquier otra acción.

**Fix:** Agregar `CommandGeneric` en `ipc_messages.py` y handler en `ipc_server.py`.

### Fix 2: NameError '_current_messages' is not defined

**Problema:** Al enviar un mensaje, el backend crashea con:
```
NameError: name '_current_messages' is not defined
```

**Causa:** Las variables globales `_global_session_manager`, `_current_session_id`, `_current_messages` se usaban en `main()` pero nunca fueron definidas a nivel de módulo.

**Fix:** Agregar inicialización en la sección "Global state":
```python
# Session management globals
_global_session_manager = None
_current_session_id = None
_current_messages = []
```

### Fix 3: NameError 'get_token_stats' is not defined

**Problema:** La función `get_token_stats()` se usa en múltiples lugares pero nunca fue definida.

**Fix:** Agregar función junto con `estimate_token_usage()`:
```python
def estimate_token_usage(messages, system_prompt=None):
    total_chars = 0
    if system_prompt:
        total_chars += len(system_prompt)
    for msg in messages:
        total_chars += len(msg.get("content", ""))
    return total_chars // 4

def get_token_stats():
    usage = estimate_token_usage(_current_messages, _system_prompt)
    return {
        "used": usage,
        "max": MAX_CONTEXT_TOKENS,
        "percentage": min(100, int((usage / max_tokens) * 100))
    }
```

### Fix 4: Model nomic-embed-text not found

**Problema:** Ollama reporta que el modelo `nomic-embed-text` no existe, solo `nomic-embed-text:latest`.

**Fix:** Cambiar en `embedding_service.py`:
```python
self.model = "nomic-embed-text:latest"  # Antes: "nomic-embed-text"
```

### Fix 5: Panel de sesiones "Cargando..." indefinidamente

**Problema:** El frontend queda en estado de carga infinito porque no recibe el evento `session_history` correctamente.

**Causa:** El backend envía mensajes con estructura IPC:
```json
{"type": "event", "action": "data", "payload": {"type": "session_history", "sessions": []}}
```

Pero el frontend esperaba `data.type` directamente, sin extraer el payload.

**Fix:**
1. `useWebSocket.js` - Extraer payload de mensajes envueltos:
```javascript
if (rawData.type === 'event' && rawData.action === 'data' && rawData.payload) {
  data = rawData.payload
}
```

2. `SessionList.jsx` - Agregar timeout de seguridad y logs de debug:
```javascript
// Safety timeout - clear loading state after 5 seconds if no response
const timeout = setTimeout(() => setLoading(false), 5000)
```

### Fix 6: SessionManager usa ruta incorrecta

**Problema:** Las sesiones se guardan en `C:\Users\Game_\.Lilith\sessions` en lugar de `D:\Proyectos\Yggdrasil\Asgard\Lilith\Memory\sessions`.

**Causa:** Hay DOS clases SessionManager:
1. `Backend.core.session_manager.SessionManager` → usa `~/.Lilith/sessions`
2. `Backend.memory.session_manager.SessionManager` → usa `D:\Proyectos\Yggdrasil\Asgard\Lilith\Memory\sessions`

En `main.py` no se importaba ni inicializaba el SessionManager correcto.

**Fix:**
```python
# Importar el correcto
from Backend.memory.session_manager import SessionManager

# Inicializar en main()
_global_session_manager = SessionManager()
```

### Fix 7: SessionManager usa ruta incorrecta (core vs memory)

**Problema:** El API server usa `Backend.core.session_manager` que guarda en `~/.Lilith/sessions`.

**Fix:** Cambiar el default path en `Backend/core/session_manager.py`:
```python
project_root = Path(__file__).parent.parent.parent
default_path = project_root / "Memory" / "sessions"
self.storage_path = Path(storage_path or default_path)
```

### Fix 8: session_history no responde / timeout

**Problema:** El frontend envía `session_history` pero el API server no tiene handler para mensajes tipo `COMMAND`.

**Causa:** El API server solo maneja `message`, `ping`, `approval`, `status`. Los comandos nuevos (`session_history`, `load_session`, etc.) no están implementados.

**Fix:** Agregar handler en `Backend/api/server.py`:
```python
elif msg_type == 'COMMAND':
    action = message.get('action', '')
    if action == 'session_history':
        sessions = session_manager.list_sessions()
        await websocket.send_json({'type': 'session_history', 'sessions': sessions})
    elif action == 'load_session':
        # Forward to Core via IPC
        ...
```

### Fix 9: Unknown message type: status_update

**Problema:** El frontend no tiene handler para mensajes `status_update` del backend.

**Fix:** Agregar en `useWebSocket.js`:
```javascript
case 'status_update':
  console.log('Status update:', data.state || data)
  break
```

### Fix 10: Historial llega vacío - formatos incompatibles

**Problema:** `list_sessions()` retorna lista vacía porque busca archivos `.info.json` pero `memory/session_manager` guarda archivos `.json` simples.

**Causa:** Dos SessionManager con formatos diferentes:
- `core/session_manager` → guarda `.info.json` + `.json.gz`
- `memory/session_manager` → guarda `.json` simple

**Fix:** Modificar `core/session_manager.list_sessions()` para leer ambos formatos:
```python
def list_sessions(self, limit: int = 20):
    # Buscar .info.json (formato core)
    info_files = self.storage_path.glob("*.info.json")

    # También buscar .json (formato memory)
    json_files = self.storage_path.glob("*.json")
    # Convertir al formato esperado
```

### Fix 11: Auto-guardado después de cada mensaje

**Problema:** Las sesiones solo se guardan al cerrar con Ctrl+C.

**Fix:** Agregar auto-guardado en `handle_chat_request` después de `chat_final`:
```python
# Auto-save session after each completed message
if _global_session_manager and _current_session_id and _current_messages:
    try:
        _global_session_manager.save_session(_current_messages, _current_session_id)
        logger.info(f"[auto-save] Session saved ({len(_current_messages)} messages)")
    except Exception as e:
        logger.error(f"[auto-save] Error: {e}")
```

## Bug Fixes

**Problema:** El evento `session_history` no respondía al frontend, causando loop de carga infinita.

**Causa:** En `ipc_server.py`, el método `_process_raw_message()` solo permitía acciones específicas predefinidas (`send_message`, `get_status`, etc.) y descartaba silenciosamente cualquier otra acción con un warning "Unknown message action".

**Fix aplicado:**

1. **ipc_messages.py** — Nueva clase `CommandGeneric`:
```python
class CommandGeneric(BaseIPCMessage):
    type: Literal[IPCMessageType.COMMAND] = IPCMessageType.COMMAND
    action: str
    payload: Dict[str, Any] = {}
```

2. **ipc_server.py** — Handler para acciones de sesión:
```python
elif action in ("session_history", "load_session", "new_session", "get_token_stats"):
    validated_msg = CommandGeneric(**data)
```

**Verificación:**
```python
>>> sm = SessionManager()
>>> sm.list_sessions()
[]  # Lista vacía válida
```

## Estado del Build

```
vite v5.4.21 ✓ built in 9.78s
dist/index.html         1.26 kB │ gzip:   0.56 kB
dist/js/index.js      1,037.37 kB │ gzip: 351.72 kB
```

Build exitoso. Warning de chunk size esperado para SPA completa.

## Próxima Misión

1. Probar flujo completo de guardado/carga de sesiones
2. Verificar auto-compresión al alcanzar 70% de tokens
3. Validar inyección de contexto relevante desde ChromaDB
4. Ajustar UI de SessionList según feedback de uso
