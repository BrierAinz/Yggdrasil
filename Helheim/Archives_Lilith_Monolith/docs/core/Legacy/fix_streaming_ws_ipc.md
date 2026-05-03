# Fix: streaming WebSocket / IPC (EventData)

Documentación del ajuste en el puente IPC → WebSocket para que los eventos genéricos de datos lleguen correctamente al frontend.

---

## Contexto

- **Core (Backend)** se comunica con la **API (FastAPI)** por **IPC** (named pipes en Windows).
- La API reenvía mensajes al **frontend** por **WebSocket** (ws-bridge).
- Antes del fix, algunos eventos del Core (token_stats, pantheon_status, agent_thinking, session_renamed, etc.) no se serializaban bien o el frontend no los reconocía.

---

## Bug

Los mensajes IPC con “datos genéricos” (estadísticas, estado del panteón, sesión, etc.) tenían un formato distinto al resto (EventChatDelta, EventChatFinal, EventStatusUpdate, etc.). El ws-bridge construía un `ws_msg` genérico usando `msg.action` y campos sueltos, y no había un tipo IPC unificado para “solo payload” que el frontend esperara.

---

## Solución: EventData

1. **Nuevo tipo IPC** en `Backend/ipc_messages.py`:

   ```python
   class EventData(BaseIPCMessage):
       """Generic event with payload (token_stats, session_history, pantheon_status, etc.)"""
       type: Literal[IPCMessageType.EVENT] = IPCMessageType.EVENT
       action: Literal["data"] = "data"
       payload: Dict[str, Any] = {}
   ```

   - Siempre `action="data"`.
   - Todo el contenido va en `payload` (incluido un campo `type` interno para distinguir token_stats, pantheon_status, agent_thinking, session_renamed, etc.).

2. **En el ws-bridge** (`Backend/api/server.py`, `route_ipc_to_websocket`):

   - Si el mensaje es `EventData`, **no** se construye `ws_msg` con `msg.action` como tipo.
   - Se hace **broadcast directo de `msg.payload`** al WebSocket, para que el frontend reciba exactamente el objeto que envía el Core (con su `type` y el resto de campos).

   ```python
   elif isinstance(msg, EventData):
       event_type = msg.payload.get("type", "unknown")
       logger.info(f"[ws-bridge] Broadcasting EventData: {event_type} → ...")
       await manager.broadcast_json(msg.payload)
       return
   ```

Así, el streaming y el resto de eventos “de datos” salen del Core por IPC como `EventData` y llegan al cliente WebSocket con la misma estructura que espera el frontend.

---

## Archivos tocados

- `Backend/ipc_messages.py`: definición de `EventData`.
- `Backend/api/server.py`: rama `isinstance(msg, EventData)` en `route_ipc_to_websocket` y broadcast de `msg.payload`.
- `Backend/main.py`: uso de `EventData` (alias o envío de eventos genéricos).
- `Tools/ipc/client.py`: deserialización de IPC a `EventData` cuando corresponda.

---

## Cómo probar

- Con Core y API en marcha, abrir una sesión conversacional por WebSocket.
- Verificar que llegan eventos como `token_stats`, `pantheon_status`, `agent_thinking`, `session_renamed`, etc., con la estructura correcta en el payload (p. ej. en logs del API: “Broadcasting EventData: token_stats → N clients”).
