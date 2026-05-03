# Plugin System — Guía de desarrollo (E.13)

**Versión:** 4.1
**Archivo principal:** `Core/Backend/core/plugin_manager.py`

---

## ¿Qué es el Plugin System?

El Plugin System de Lilith 4.1 permite añadir nuevas **tools**, **personas del Panteón** y **transportes** (WhatsApp, Slack, etc.) sin modificar el código core ni reiniciar el servidor.

Los plugins son archivos Python que heredan de `BasePlugin` y se cargan/recargan/descargan en caliente.

---

## Estructura de un plugin

```python
# Core/Backend/plugins/mi_plugin.py

import logging
from Backend.core.plugin_manager import BasePlugin, PluginManager

logger = logging.getLogger("lilith.plugin.mi_plugin")


def _mi_tool_func(params: dict) -> dict:
    """Implementación de la tool."""
    resultado = params.get("parametro", "")
    # ... lógica ...
    return {"response": f"Resultado: {resultado}"}


class Plugin(BasePlugin):
    name = "mi_plugin"          # Nombre único (snake_case)
    version = "1.0.0"           # Semver
    description = "Descripción breve del plugin"

    def on_load(self, manager: PluginManager) -> None:
        """Se ejecuta al cargar. Registrar tools/personas aquí."""
        schema = {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Descripción del parámetro"
                }
            },
            "required": ["parametro"]
        }
        manager.register_tool(
            plugin_name=self.name,
            tool_name="nombre_de_la_tool",
            tool_func=_mi_tool_func,
            schema=schema,
        )
        logger.info("[MiPlugin] Tool registrada.")

    def on_unload(self) -> None:
        """Se ejecuta al descargar. Liberar recursos."""
        logger.info("[MiPlugin] Descargada.")
```

**Regla crítica:** La clase principal del plugin DEBE llamarse `Plugin` o ser una subclase directa de `BasePlugin` (el manager la detecta automáticamente).

---

## API REST de gestión

Todos los endpoints requieren estar en la red interna (no expuestos públicamente).

### Listar plugins activos
```http
GET /api/plugins/list
```
```json
{
  "plugins": [
    {
      "name": "mi_plugin",
      "version": "1.0.0",
      "description": "...",
      "status": "active",
      "tools": ["nombre_de_la_tool"],
      "personas": []
    }
  ],
  "total": 1
}
```

### Cargar plugin
```http
POST /api/plugins/load
Content-Type: application/json

{"name": "mi_plugin"}
```

### Hot-reload (sin reiniciar)
```http
POST /api/plugins/reload
Content-Type: application/json

{"name": "mi_plugin"}
```

### Descargar plugin
```http
POST /api/plugins/unload
Content-Type: application/json

{"name": "mi_plugin"}
```

### Estado de un plugin
```http
GET /api/plugins/status/mi_plugin
```

---

## Registrar una tool

```python
manager.register_tool(
    plugin_name=self.name,
    tool_name="get_weather",        # Nombre que usará el Planner en Steps
    tool_func=_get_weather,         # Callable(params: dict) -> dict
    schema={...},                   # JSON Schema de los parámetros
)
```

La tool queda disponible inmediatamente en `ToolRegistryV3` y el Planner puede usarla en planes.

---

## Registrar una persona del Panteón

```python
manager.register_persona(
    plugin_name=self.name,
    persona_config={
        "name": "hermes",
        "role": "mensajero",
        "description": "Especialista en comunicaciones y APIs externas",
        "model": "kimi-k2.5",
        "system_prompt": "Eres Hermes, dios mensajero...",
    }
)
```

La persona se escribe en `Config/personas.json` y queda disponible para el Orquestador.

---

## Registrar un transporte

```python
manager.register_transport(
    plugin_name=self.name,
    transport_class=WhatsAppTransport,  # Clase con transport_name attr
)
```

El plugin es responsable de iniciar el transporte en `on_load()` y detenerlo en `on_unload()`.

---

## Seguridad

El PluginManager valida cada plugin antes de cargarlo:

### Imports prohibidos (bloqueados por AST)
```
os.system, subprocess, pty, commands, popen,
ctypes, winreg, msvcrt
```

Si un plugin intenta importar cualquiera de estos, la carga falla:
```
[PluginManager] Security violation en 'plugin_malicioso': Import prohibido: subprocess
```

### Checksum SHA256
Si `plugins.json` tiene `"verify_checksum": true`, el manager verifica que el archivo no haya sido modificado desde la última carga. Útil para entornos de producción.

```json
{
  "security": {
    "verify_checksum": true,
    "disallowed_imports": ["os.system", "subprocess"]
  }
}
```

---

## Auto-load al arranque

Para cargar plugins automáticamente cuando Lilith inicia, añadirlos a `Config/plugins.json`:

```json
{
  "enabled": true,
  "auto_load": ["example_weather_plugin", "mi_plugin"],
  "plugins": {}
}
```

El PluginManager llama a `auto_load()` durante el arranque del servidor.

---

## Plugin de ejemplo: get_weather

Incluido en `Core/Backend/plugins/example_weather_plugin.py`.

Registra la tool `get_weather(location: str)` usando la API pública wttr.in (sin API key).

```python
# Uso desde el Planner
Step(tool_name="get_weather", params={"location": "Madrid"})
# → {"response": "Madrid: ⛅ +18°C"}
```

---

## Hot-reload en desarrollo

Durante desarrollo, puedes modificar el archivo del plugin y recargar sin reiniciar:

```bash
# Desde curl
curl -X POST http://localhost:8000/api/plugins/reload \
  -H "Content-Type: application/json" \
  -d '{"name": "mi_plugin"}'

# Respuesta
{"success": true, "message": "Plugin 'mi_plugin' cargado."}
```

El hot-reload:
1. Llama a `on_unload()` del plugin anterior
2. Limpia `sys.modules` (cache de Python)
3. Invalida cache de importlib
4. Carga el archivo modificado desde disco
5. Llama a `on_load()` del nuevo plugin
6. Actualiza checksum en `plugins.json`

Las conversaciones activas **no se interrumpen** durante el reload.

---

## Ciclo de vida completo

```
Arranque Lilith
    → PluginManager.auto_load()
        → load_plugin("mi_plugin")
            → validate_security(path)       ✓ AST scan
            → verify_checksum(name, path)   ✓ SHA256
            → importlib.load_module()
            → Plugin().on_load(manager)     ← registra tools/personas
            → guardar checksum en plugins.json

Uso normal
    → Planner genera Step(tool_name="nombre_de_la_tool", ...)
    → Executor llama a _mi_tool_func(params)

Hot-reload (desarrollo/actualización)
    → POST /api/plugins/reload
        → unload_plugin() → Plugin().on_unload()
        → load_plugin() → Plugin().on_load()

Apagado Lilith
    → (opcional) unload_plugin() para cada plugin activo
```

---

## Buenas prácticas

| ✅ Hacer | ❌ Evitar |
|----------|-----------|
| Importar solo librerías estándar seguras | `import subprocess`, `import os.system` |
| Liberar recursos en `on_unload()` | Dejar threads o conexiones abiertas |
| Usar logging con nombre de plugin | `print()` directo |
| Validar params antes de llamar APIs externas | Llamadas sin timeout |
| Retornar `{"response": ..., "error": False}` | Lanzar excepciones sin capturar |
| Documentar el schema de la tool | Schema vacío o incorrecto |

---

## Troubleshooting

**"Security violation: Import prohibido"**
→ El plugin usa un import bloqueado. Refactoriza para no necesitarlo o usa la API de Lilith.

**"No define clase 'Plugin'"**
→ Asegúrate de que la clase principal se llame `Plugin` y herede de `BasePlugin`.

**"Plugin 'X' ya está cargado"**
→ Usa `reload_plugin` en lugar de `load_plugin`.

**"Checksum mismatch"**
→ El archivo fue modificado. Si es intencional, desactiva temporalmente `verify_checksum` o usa reload (que actualiza el checksum automáticamente).
