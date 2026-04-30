# Bifrost de Vanaheim

Protocolo de comunicación bidireccional entre Asgard (Lilith) y Vanaheim.

## Arquitectura

```
┌─────────────┐      Bifrost Protocol      ┌─────────────┐
│   Asgard    │  ═══════════════════════►  │  Vanaheim   │
│  (Lilith)   │      HTTP/WebSocket        │  (Agents)   │
└─────────────┘                            └─────────────┘
```

## Componentes

### Vanaheim (Este servidor)

- **gateway.py**: FastAPI con endpoints `/api/bifrost/*`
- **auth.py**: Validación de tokens compartidos
- **agents/**: Agentes del Panteón ejecutándose localmente
  - `adan_vanaheim.py`: Código/Refactor (Ollama/qwen2.5-coder)
  - `eva_vanaheim.py`: Análisis (xAI/Grok) - placeholder
  - `odin_vanaheim.py`: Investigación (Kimi) - placeholder

### Asgard (Cliente)

- **bifrost_client.py**: Cliente con circuit breaker y retry
- **bifrost.json**: Configuración de URL, token, timeouts

## Uso

### Iniciar Vanaheim

```bash
cd Yggdrasil/Vanaheim
pip install -r requirements.txt
python server.py
```

El servidor inicia en `http://localhost:9000`

### Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/bifrost/health` | GET | Health check |
| `/api/bifrost/agents` | GET | Lista agentes disponibles |
| `/api/bifrost/execute` | POST | Ejecutar tarea en agente |

### Ejemplo de llamada desde Asgard

```python
from Backend.core.bifrost_client import get_bifrost_client

client = get_bifrost_client(base_path)
result = await client.execute(
    agent="adan",
    task="refactor this function to use list comprehensions",
    context="def old_func(): ..."
)
print(result["response"])
```

## Flujo de Delegación

1. **Albedo:Sombra** clasifica la tarea
2. Si `route=vanaheim` y `confidence > threshold`:
   - **BifrostClient** envía request a Vanaheim
   - **BifrostGateway** valida token y routea al agente
   - **Agente** ejecuta y retorna resultado
3. Si Vanaheim falla → **fallback** a Asgard automático

## Configuración

### Vanaheim (`config/bifrost.json`)

```json
{
  "server": {"host": "0.0.0.0", "port": 9000},
  "auth": {"tokens": ["shared_secret_token"]},
  "agents": {
    "adan": {"model": "qwen2.5-coder:7b", "timeout": 60}
  }
}
```

### Asgard (`Core/Config/bifrost.json`)

```json
{
  "enabled": true,
  "url": "http://localhost:9000",
  "token": "shared_secret_token",
  "circuit_breaker": {"failure_threshold": 3}
}
```

## Seguridad

- Tokens compartidos en ambos lados
- Circuit breaker previene fallos en cascada
- Fallback automático si Vanaheim no responde
