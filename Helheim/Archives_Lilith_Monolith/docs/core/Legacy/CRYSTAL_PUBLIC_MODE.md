# Crystal - Modo Público para Discord

**Versión:** 4.2
**Fecha:** 2026-03-23
**Área:** Discord (Crystal + Público)

---

## ¿Qué es Crystal?

Crystal es una versión limitada y sandboxeada de Lilith diseñada específicamente para usuarios públicos en Discord. **(v4.2)** Ahora usa la API de Kimi directamente (`kimi-for-coding`) con fallback a Ollama local, en lugar de OpenRouter.

### Diferencias clave con Lilith

| Característica | Lilith (Owner/Trusted) | Crystal (Público) |
|----------------|----------------------|-------------------|
| Modelo | Kimi (`kimi-for-coding`) | Kimi (`kimi-for-coding`) |
| Memoria | Persistente (MuninnDB) | Ephemeral (TTL 1h) |
| Rate Limit | 60 msg/hr | 10 msg/hr |
| Filesystem | ✅ Acceso controlado | ❌ Sin acceso |
| Ejecución | ✅ Con confirmación | ❌ Bloqueado |
| Tools avanzadas | ✅ Disponibles | ❌ Limitadas |
| Costo | API Key dedicada | API Key dedicada |

---

## Arquitectura (v4.2)

```
Usuario Público (Discord)
    ↓
[Discord Bot] → Detecta rol "public"
    ↓
[DiscordRouter] → Decide usar Crystal
    ↓
[Crystal Agent] → Aplica restricciones
    ├── [Input Sanitizer] → Bloquea inyecciones
    ├── [Rate Limiter] → 10 msg/hr
    ├── [Ephemeral Memory] → TTL 1h
    ↓
[KimiClient] → API directa a Kimi
    ├── Retry con backoff
    ├── Headers x-api-key
    └── Modelo: kimi-for-coding
    ↓
[Fallback Ollama] → Si Kimi falla
    └── Modelo: llama3.2:latest
    ↓
[Output Sanitizer] → Redacta secretos
    ↓
Respuesta al usuario
```

---

## Historial de cambios

### v4.2 (2026-03-23) - Migración a Kimi API

**Cambio principal:** Crystal migra de OpenRouter a Kimi API directa.

| Aspecto | Antes (OpenRouter) | Ahora (Kimi) |
|---------|-------------------|--------------|
| Backend | OpenRouter proxy | Kimi API directa |
| Modelos | Haiku, GPT-4o-mini | kimi-for-coding |
| Variable env | `OPENROUTER_API_KEY` | `CRYSTAL_KIMI_API_KEY` |
| Latencia | Mayor (proxy) | Menor (directo) |
| Fallback | Ollama | Ollama (igual) |

**Motivación del cambio:**
- Menor latencia al eliminar el proxy intermedio
- Mayor control sobre el modelo utilizado
- Consistencia con Lilith (mismo backend Kimi)
- Simplificación de la infraestructura

**Archivos modificados:**
- `Core/Backend/core/agents/crystal_agent.py` - Ahora usa `KimiClient` directamente
- `Discord/handlers/chat_handler.py` - Quitada dependencia de `get_openrouter_client`
- `.env` - Nueva variable `CRYSTAL_KIMI_API_KEY`

---

## Configuración

### 1. Variables de Entorno (v4.2)

```bash
# Kimi API Key para Crystal (requerido)
CRYSTAL_KIMI_API_KEY=sk-kimi-...

# Opcional: Override de modelo
CRYSTAL_MODEL=kimi-for-coding
```

**Nota de migración (v4.2):** La variable `OPENROUTER_API_KEY` ya no se usa para Crystal. Usa `CRYSTAL_KIMI_API_KEY`.

### 2. Archivo de Configuración (`Core/Config/crystal.json`)

```json
{
  "enabled": true,
  "default_model": "anthropic/claude-3-haiku",
  "fallback_models": ["openai/gpt-4o-mini"],
  "max_tokens": 1000,
  "temperature": 0.7,
  "rate_limit": {
    "max_messages_per_hour": 10,
    "max_tokens_per_day": 50000,
    "cooldown_seconds": 60
  },
  "ephemeral_memory": {
    "enabled": true,
    "ttl_seconds": 3600,
    "max_facts_per_user": 20
  }
}
```

### 3. Configuración de Roles (`Core/Config/discord_roles.json`)

```json
{
  "public": ["charla", "chiste", "meme", "crystal_chat"],
  "_config": {
    "public": {
      "persona": "crystal",
      "use_openrouter": true,
      "rate_limit": {
        "max_messages_per_hour": 10
      },
      "memory_type": "ephemeral"
    }
  }
}
```

---

## Componentes

### Kimi Client (`Core/Backend/llm/kimi_client.py`)

Cliente HTTP para API de Kimi (protocolo Anthropic Messages):

```python
from Backend.llm.kimi_client import KimiClient

client = KimiClient(api_key="sk-kimi-...")
response = client.generate_text(
    prompt="Hola",
    system_prompt="Eres Crystal, asistente amigable",
    model="kimi-for-coding"
)
```

Características:
- **API Key dedicada**: Variable `CRYSTAL_KIMI_API_KEY`
- **Modelo**: `kimi-for-coding` (262k context)
- **Retry**: Backoff exponencial en errores
- **Fallback**: Ollama local si Kimi falla

**Nota:** Crystal usa `KimiClient` directamente desde v4.2. OpenRouter ya no es el backend.

### Cost Tracker (`Core/Backend/llm/cost_tracker.py`)

Tracking de costos en SQLite:

```python
from Backend.llm.cost_tracker import track_crystal_usage, get_cost_tracker

# Trackear uso
cost = track_crystal_usage(
    user_id="user123",
    model="anthropic/claude-3-haiku",
    input_tokens=1000,
    output_tokens=500
)

# Ver estadísticas
tracker = get_cost_tracker()
stats = tracker.get_user_stats("user123")
print(f"Total gastado: ${stats['total_cost']}")
```

**Endpoints de stats:**
- `GET /api/crystal/stats` - Estadísticas del usuario autenticado
- `GET /api/crystal/stats/global` - Estadísticas globales (owner)

### Ephemeral Memory (`Core/Backend/core/ephemeral_memory.py`)

Memoria temporal en RAM:

```python
from Backend.core.ephemeral_memory import EphemeralMemoryForCrystal

memory = EphemeralMemoryForCrystal()

# Almacenar (TTL automático 1h)
memory.store("user123", "Le gusta Python", tags=["preference"])

# Recuperar
facts = memory.retrieve("user123")

# Contexto para prompt
context = memory.retrieve_context_block("user123")
```

Características:
- ✅ No persiste en disco
- ✅ Expira automáticamente (TTL)
- ✅ Thread-safe
- ✅ Límite de facts por usuario

### Rate Limiter (`Core/Backend/core/rate_limiter.py`)

Rate limiting con sliding window:

```python
from Backend.core.rate_limiter import check_user_rate_limit, record_message_usage

# Verificar antes de procesar
allowed, block_message = check_user_rate_limit(
    user_id="user123",
    estimated_tokens=500
)

if allowed:
    # Procesar mensaje
    response = await process_message(...)
    # Registrar uso
    record_message_usage("user123", len(message), tokens_used)
else:
    return block_message  # "⏱️ Límite alcanzado..."
```

Límites configurables:
- Mensajes por hora: 10 (default)
- Tokens por día: 50,000
- Cooldown entre mensajes: 60s

### Abuse Logger (`Core/Backend/core/abuse_logger.py`)

Logging de comportamiento sospechoso:

```python
from Backend.core.abuse_logger import get_abuse_logger, ViolationType

logger = get_abuse_logger()

# Loggear violación
logger.log(
    user_id="user123",
    violation_type=ViolationType.FORBIDDEN_TOOL_ATTEMPT,
    details={"tool": "exec_command"},
    severity="high"
)

# Dashboard
violations = logger.get_recent_violations(limit=100)
risk_score = logger.get_user_risk_score("user123")
```

Tipos de violación:
- `FORBIDDEN_TOOL_ATTEMPT` - Intento de usar tool prohibida
- `PROMPT_INJECTION_ATTEMPT` - Intento de inyección
- `RATE_LIMIT_VIOLATION` - Intento de bypass de rate limit
- `SUSPICIOUS_PATTERN` - Patrón sospechoso detectado

### Input Sanitizer (`Core/Backend/core/input_sanitizer.py`)

Sanitización de entrada para público:

```python
from Backend.core.input_sanitizer import sanitize_public_input, sanitize_public_output

# Sanitizar entrada
text, block_info = sanitize_public_input(
    user_message,
    user_id="user123"
)

if block_info:
    # Mensaje bloqueado
    logger.warning(f"Blocked: {block_info['reason']}")
    return block_info['message']

# Sanitizar salida (redactar secretos, truncar)
output = sanitize_public_output(
    raw_response,
    max_length=1000
)
```

Patrones bloqueados:
- `ignore previous instructions`
- `developer mode`
- `jailbreak`
- `you are now...`
- `new instructions:`

---

## Seguridad

### Defensa contra Prompt Injection

1. **Detección de patrones** - Lista de patrones conocidos
2. **Sanitización de entrada** - Limpieza de caracteres de control
3. **Validación de longitud** - Límite de 2000 caracteres
4. **Detección de spam** - Bloqueo de contenido repetitivo

### Aislamiento de Memoria

```python
# Público usa EphemeralMemory
if user_role == "public":
    memory = EphemeralMemoryForCrystal()
else:
    memory = MuninnMemory(base_path)
```

### Tools Prohibidas

```python
FORBIDDEN_FOR_PUBLIC = [
    "list_directory",
    "exec_command",
    "file_read",
    "file_write",
    "file_edit",
    "pc_agent_*",
    "delegate_cursor",
    "delegate_kimi_cli",
    "delegate_albedo",
    "memory_write",
    "memory_read"
]
```

Intento de uso → Log en `abuse_logs.db` + JSONL

---

## API Endpoints

### Estadísticas

```
GET /api/crystal/stats?user_id={id}&days=30
Response:
{
  "user_id": "123",
  "total_cost": 0.0234,
  "total_calls": 15,
  "by_model": [
    {"model": "claude-3-haiku", "calls": 10, "cost": 0.015}
  ]
}
```

### Logs de Abuso

```
GET /api/crystal/abuse-logs?limit=100&type=forbidden_tool_attempt
Response:
{
  "violations": [
    {
      "id": 1,
      "timestamp": "2026-03-21T10:30:00Z",
      "user_id": "123",
      "violation_type": "forbidden_tool_attempt",
      "severity": "high",
      "details": {"tool": "exec_command"}
    }
  ]
}
```

### Status de Rate Limit

```
GET /api/crystal/rate-limit?user_id={id}
Response:
{
  "user_id": "123",
  "messages_used": 5,
  "messages_remaining": 5,
  "tokens_used": 2500,
  "tokens_remaining": 47500,
  "is_blocked": false
}
```

---

## Testing

### Ejecutar Tests

```bash
cd Lilith/Core

# Tests de Crystal + OpenRouter
pytest Tests/test_crystal_openrouter.py -v

# Tests de Sandboxing
pytest Tests/test_public_sandbox.py -v

# Todos los tests
pytest Tests/ -v --tb=short
```

### Tests Incluidos

- `test_crystal_openrouter.py` - Client, cost tracking, persona
- `test_public_sandbox.py` - Ephemeral memory, rate limiting, tools prohibidas

---

## Troubleshooting

### "Crystal no disponible: CRYSTAL_KIMI_API_KEY ausente"

```bash
export CRYSTAL_KIMI_API_KEY=sk-kimi-...
```

**Nota:** En v4.2, Crystal usa Kimi directamente. La variable `OPENROUTER_API_KEY` ya no se usa para Crystal.

### Rate limit muy agresivo

Editar `Core/Config/crystal.json`:
```json
"rate_limit": {
  "max_messages_per_hour": 20  // Aumentar de 10
}
```

### Crystal responde con error de conexión

Verificar que la API key de Kimi sea válida:
```bash
curl -H "x-api-key: $CRYSTAL_KIMI_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     https://api.kimi.com/coding/v1/models
```

### Memoria no funciona

Ephemeral memory es en RAM - se pierde al reiniciar. Esto es intencional.

---

## Roadmap

- [x] ~~OpenRouter client con retry~~ → **Migado a Kimi API directa (v4.2)**
- [x] Kimi client con retry
- [x] Ephemeral memory
- [x] Rate limiting
- [x] Abuse logging
- [x] Input/output sanitization
- [x] Tests
- [ ] Dashboard web de abuso
- [ ] Alertas automáticas de uso

---

## Referencias

- `Core/Config/crystal.json` - Configuración principal
- `Core/Config/discord_roles.json` - Configuración de roles
- `Core/Backend/core/agents/crystal_agent.py` - Agente Crystal (v4.2 usa Kimi)
- `Core/Backend/llm/kimi_client.py` - Cliente Kimi
- `Core/Backend/core/ephemeral_memory.py` - Memoria temporal
- `Core/Backend/core/rate_limiter.py` - Rate limiting
- `Core/Backend/core/abuse_logger.py` - Logs de abuso
- `Core/Backend/core/input_sanitizer.py` - Sanitización
