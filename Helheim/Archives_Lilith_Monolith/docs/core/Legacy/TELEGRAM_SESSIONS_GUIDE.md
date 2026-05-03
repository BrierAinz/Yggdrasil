# Guía de Sesiones Persistentes en Telegram (F.16)

## Resumen

Las sesiones persistentes permiten que Telegram tenga un contexto aislado de Discord, con memoria propia y gestión de estado por usuario.

## Arquitectura

### Vaults Separados (MuninnDB)

```json
// Core/Config/muninn.json
{
  "transport_vaults": {
    "discord": "default",
    "telegram": "telegram"
  }
}
```

- **Discord** usa el vault `default` (compartido con el sistema general)
- **Telegram** usa el vault `telegram` (exclusivo para Ainz)

### Session Manager

El `TelegramSessionManager` gestiona:
- Historial conversacional por usuario
- Confirmaciones pendientes
- Estado de macros en ejecución
- TTL de 24 horas para sesiones inactivas

## Uso

### Inicializar sesión

```python
from Backend.core.telegram_session import get_session_manager

sm = get_session_manager(base_path)
session = sm.get_session(user_id="1192920957", chat_id="1192920957")
```

### Añadir mensaje al historial

```python
sm.add_message(user_id, chat_id, role="user", content="Hola")
sm.add_message(user_id, chat_id, role="assistant", content="¡Hola Ainz!")
```

### Obtener historial formateado

```python
history_block = sm.format_history_for_prompt(user_id, chat_id, limit=5)
```

### Guardar estado de macro

```python
sm.set_macro_state(user_id, chat_id, "backup_proyecto", {
    "params": {"project_path": "D:/Proyectos/Yggdrasil/Asgard/Lilith"},
    "steps_count": 2
})
```

## Persistencia

Las sesiones se guardan en:
```
Core/Data/telegram_sessions.json
```

Formato:
```json
{
  "1192920957": {
    "user_id": "1192920957",
    "chat_id": "1192920957",
    "conversation_history": [...],
    "active_confirmations": {},
    "pc_agent_state": null,
    "macro_state": null,
    "created_at": 1711000000.0,
    "last_activity": 1711003600.0
  }
}
```

## Limpieza Automática

Las sesiones expiradas (>24h de inactividad) se limpian:
1. Al cargar el SessionManager (startup)
2. Periódicamente cuando hay >100 sesiones activas

## Logs

```
[TelegramSessionManager] Inicializado. Sessions file: ...
[TelegramSessionManager] Cargadas 5 sesiones activas
[TelegramSessionManager] Nueva sesión para usuario 1192920957
[TelegramSessionManager] Eliminando sesión expirada: 1192920957
```

## Integración con telegram_api.py

El API usa el SessionManager automáticamente:

```python
# Al recibir mensaje
_append_history(chat_id, "user", text)

# El historial se inyecta en el system prompt
_hist_block = _format_history(chat_id, limit=10)
if _hist_block:
    system_prompt = system_prompt + f"\n\n[Historial reciente]\n{_hist_block}"
```

## Configuración

### TTL de sesiones

Editar en `telegram_session.py`:
```python
self.ttl_hours = 24  # Cambiar a 12, 48, etc.
```

### Límite de historial

```python
self.max_history = 10  # Mensajes a mantener por sesión
```
