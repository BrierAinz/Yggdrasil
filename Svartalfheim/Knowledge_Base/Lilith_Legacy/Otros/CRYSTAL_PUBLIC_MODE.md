# Crystal - Modo Público para Discord

**Versión:** 4.1  
**Fecha:** 2026-03-21  
**Área:** Discord (Crystal + Público)

---

## ¿Qué es Crystal?

Crystal es una versión limitada y sandboxeada de Lilith diseñada específicamente para usuarios públicos en Discord. Funciona como un proxy de OpenRouter, utilizando modelos económicos (Claude Haiku, GPT-4o-mini) para mantener los costos controlados mientras proporciona acceso seguro.

### Diferencias clave con Lilith

| Característica | Lilith (Owner/Trusted) | Crystal (Público) |
|----------------|----------------------|-------------------|
| Modelo | Claude Opus/GPT-4 | Claude Haiku/GPT-4o-mini |
| Memoria | Persistente (MuninnDB) | Ephemeral (TTL 1h) |
| Rate Limit | 60 msg/hr | 10 msg/hr |
| Filesystem | ✅ Acceso controlado | ❌ Sin acceso |
| Ejecución | ✅ Con confirmación | ❌ Bloqueado |
| Tools avanzadas | ✅ Disponibles | ❌ Limitadas |
| Costo | $$$ | $ |

---

## Arquitectura

```
Usuario Público (Discord)
    ↓
[Discord Bot] → Detecta rol "public"
    ↓
[Crystal Agent] → Aplica restricciones
    ├── [Input Sanitizer] → Bloquea inyecciones
    ├── [Rate Limiter] → 10 msg/hr
    ├── [Ephemeral Memory] → TTL 1h
    ↓
[OpenRouter Client]
    ├── Retry con backoff
    ├── Headers X-RateLimit-*
    └── Cost tracking
    ↓
Modelo OpenRouter (Haiku/Mini)
    ↓
[Output Sanitizer] → Redacta secretos
    ↓
Respuesta al usuario
```

---

## Configuración

### 1. Variables de Entorno

```bash
# OpenRouter API Key (requerido)
OPENROUTER_API_KEY=sk-or-v1-...

# Opcional: Override de modelo
CRYSTAL_MODEL=anthropic/claude-3-haiku
```

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

### OpenRouter Client (`Core/Backend/llm/openrouter_client.py`)

Cliente HTTP async con:
- **Rate limiting**: Respeta headers `X-RateLimit-*`
- **Retry**: Backoff exponencial en errores 429/5xx
- **Fallback**: Cambio automático a modelos alternativos
- **Cost tracking**: Registro automático de costos

```python
from Backend.llm.openrouter_client import OpenRouterClient

client = OpenRouterClient(api_key="sk-or-v1-...")
response = await client.chat_async(
    messages=[{"role": "user", "content": "Hola"}],
    user_id="discord_user_id",
    guild_id="discord_guild_id"
)
```

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

### "Crystal no disponible: OPENROUTER_API_KEY ausente"

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

### Rate limit muy agresivo

Editar `Core/Config/crystal.json`:
```json
"rate_limit": {
  "max_messages_per_hour": 20  // Aumentar de 10
}
```

### Costos inesperados

Verificar en dashboard:
```bash
curl http://localhost:8000/api/crystal/stats/global
```

### Memoria no funciona

Ephemeral memory es en RAM - se pierde al reiniciar. Esto es intencional.

---

## Roadmap

- [x] OpenRouter client con retry
- [x] Cost tracking SQLite
- [x] Ephemeral memory
- [x] Rate limiting
- [x] Abuse logging
- [x] Input/output sanitization
- [x] Tests
- [ ] Dashboard web de abuso
- [ ] Alertas automáticas de costos
- [ ] Más modelos fallback

---

## Referencias

- `Core/Config/crystal.json` - Configuración principal
- `Core/Config/discord_roles.json` - Configuración de roles
- `Core/Backend/llm/openrouter_client.py` - Cliente OpenRouter
- `Core/Backend/llm/cost_tracker.py` - Tracking de costos
- `Core/Backend/core/ephemeral_memory.py` - Memoria temporal
- `Core/Backend/core/rate_limiter.py` - Rate limiting
- `Core/Backend/core/abuse_logger.py` - Logs de abuso
- `Core/Backend/core/input_sanitizer.py` - Sanitización
- `Core/Tests/test_crystal_openrouter.py` - Tests
- `Core/Tests/test_public_sandbox.py` - Tests de sandboxing
