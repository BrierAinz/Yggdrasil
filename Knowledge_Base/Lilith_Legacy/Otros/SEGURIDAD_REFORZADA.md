# Seguridad Reforzada — Lilith 4.1

Documentación de las mejoras de seguridad B.4, B.5, B.6: Rate Limiting, Audit Trail y Secrets Management.

---

## 📋 Índice

1. [B.4 - Rate Limiting por Usuario](#b4---rate-limiting-por-usuario)
2. [B.5 - Audit Trail Mejorado](#b5---audit-trail-mejorado)
3. [B.6 - Secrets Management](#b6---secrets-management)
4. [Integración y Testing](#integración-y-testing)

---

## B.4 - Rate Limiting por Usuario

### Arquitectura

El sistema de rate limiting V2 implementa:
- **Sliding Window**: Ventana deslizante de 1 hora y 1 minuto
- **Per-role limits**: Límites configurables por rol (owner, trusted, public)
- **User overrides**: Overrides personalizados por usuario
- **SQLite persistence**: Persistencia de requests en base de datos

### Configuración

Archivo: `Core/Config/rate_limits.json`

```json
{
  "global": {
    "enabled": true,
    "default_window_seconds": 3600,
    "default_max_requests": 100
  },
  "by_role": {
    "owner": {
      "max_requests_per_hour": 1000,
      "max_requests_per_minute": 60,
      "bypass_rate_limit": false
    },
    "trusted": {
      "max_requests_per_hour": 100,
      "max_requests_per_minute": 10
    },
    "public": {
      "max_requests_per_hour": 10,
      "max_requests_per_minute": 2
    }
  },
  "user_overrides": {}
}
```

### Uso Básico

```python
from Backend.core.rate_limiter_v2 import get_rate_limiter_v2

limiter = get_rate_limiter_v2()

# Verificar si se permite request
allowed, metadata = limiter.is_allowed("user_id", role="public")

# Response headers
# X-RateLimit-Limit: 10
# X-RateLimit-Remaining: 8
# X-RateLimit-Reset: 1711000000
```

### Crear Override

```python
# Override temporal para usuario específico
limiter.create_override(
    user_id="special_user",
    max_requests_per_hour=200,
    max_requests_per_minute=20,
    reason="Temporary elevated access",
    duration_hours=24
)
```

### Middleware FastAPI

```python
from fastapi import Request, HTTPException
from Backend.core.rate_limiter_v2 import check_rate_limit

async def rate_limit_middleware(request: Request, call_next):
    user_id = request.headers.get("X-User-ID", "anonymous")
    role = request.headers.get("X-User-Role", "public")
    
    allowed, metadata = check_rate_limit(user_id, role)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after_seconds": metadata.get("retry_after", 60)
            }
        )
    
    response = await call_next(request)
    
    # Añadir headers
    response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
    response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
    
    return response
```

### API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/rate-limits/stats` | GET | Estadísticas globales |
| `/api/rate-limits/user/{user_id}` | GET | Historial de usuario |
| `/api/rate-limits/override` | POST | Crear override temporal |

---

## B.5 - Audit Trail Mejorado

### Arquitectura

El sistema de auditoría implementa:
- **HMAC-SHA256**: Firma digital de cada entrada
- **Inmutabilidad**: Detección de modificaciones
- **Export forense**: Exportación con checksums
- **SQLite metadata**: Indexación para consultas

### Configuración

Archivo: `Core/Config/audit.json`

```json
{
  "enabled": true,
  "log_path": "Core/Data/audit_trail.jsonl",
  "signing_enabled": true,
  "secret_key": "${AUDIT_SECRET_KEY}",
  "retention_days": 365,
  "integrity_check": {
    "enabled": true,
    "schedule": "weekly"
  }
}
```

### Uso Básico

```python
from Backend.core.audit_logger import get_audit_logger, audit_log

audit = get_audit_logger()

# Loguear evento
audit.log("filesystem_operation", {
    "operation": "delete",
    "path": "/tmp/file.txt",
    "user_id": "user123"
}, level="info")

# Función conveniencia
audit_log("command_execution", {"cmd": "ls -la"})
```

### Eventos Auditados

| Evento | Descripción |
|--------|-------------|
| `filesystem_operation` | Operaciones de PC Agent |
| `command_execution` | Comandos ejecutados |
| `confirmation_requested` | Solicitud de confirmación |
| `confirmation_resolved` | Confirmación aprobada/rechazada |
| `rate_limit_exceeded` | Límite de rate limit excedido |
| `forbidden_tool_attempt` | Intento de usar tool prohibida |
| `security_alert` | Alerta de seguridad |

### Verificación de Integridad

```python
# Verificar todo el audit trail
total, valid, invalid = audit.verify_integrity()
print(f"Total: {total}, Válidos: {valid}, Inválidos: {len(invalid)}")

# Verificar rango específico
from datetime import datetime
total, valid, invalid = audit.verify_integrity(
    start_time=datetime(2024, 1, 1).timestamp(),
    end_time=datetime(2024, 3, 1).timestamp()
)
```

### Export Forense

```python
# Exportar rango de fechas
export_path = audit.export_forensic(
    start_date="2024-01-01T00:00:00Z",
    end_date="2024-03-21T00:00:00Z",
    event_types=["filesystem_operation", "command_execution"]
)

# El ZIP contiene:
# - audit_trail.jsonl: Logs filtrados
# - checksums.txt: SHA256 de cada entrada
# - metadata.json: Info del export
```

### Formato de Entrada

```json
{
  "timestamp": "2024-03-21T10:30:00+00:00",
  "event_type": "filesystem_operation",
  "level": "info",
  "details": {
    "operation": "delete",
    "path": "/tmp/file.txt",
    "user_id": "user123"
  },
  "sequence": 1711002600000000,
  "signature": "a1b2c3d4e5f6...",
  "hash": "sha256_hash_of_content"
}
```

---

## B.6 - Secrets Management

### Arquitectura

El vault de secrets implementa:
- **Fernet (AES-128 + HMAC)**: Cifrado simétrico
- **PBKDF2HMAC**: Derivación de key desde master password
- **Rotación automática**: Rotación cada 90 días (configurable)
- **Audit logging**: Log de cada acceso

### Configuración

Archivo: `Core/Config/secrets.json`

```json
{
  "vault_path": "Core/Config/secrets.vault",
  "master_key_env": "LILITH_MASTER_KEY",
  "auto_rotate": true,
  "rotation_interval_days": 90,
  "auto_rotate_secrets": [
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY"
  ],
  "access_logging": true,
  "access_rate_limit": {
    "max_accesses_per_minute": 100
  }
}
```

### Setup Inicial

```bash
# 1. Set master key
export LILITH_MASTER_KEY="your-secure-master-key"

# 2. Migrar secrets desde .env
python -c "
from Backend.core.secrets_vault import get_secrets_vault
vault = get_secrets_vault()
vault.migrate_from_env()
"
```

### Uso Básico

```python
from Backend.core.secrets_vault import get_secrets_vault, get_secret, set_secret

vault = get_secrets_vault()

# Guardar secret
vault.set_secret("API_KEY", "sk-abc123", {
    "description": "OpenAI API Key",
    "environment": "production"
})

# Leer secret
api_key = vault.get_secret("API_KEY")

# Función conveniencia
api_key = get_secret("API_KEY", default="fallback")
```

### Rotación de Secrets

```python
# Rotar manualmente
vault.rotate_secret("API_KEY", "sk-new456")

# Verificar si necesita rotación
if vault.needs_rotation("API_KEY"):
    print("API_KEY necesita rotación")

# Verificar todos
needs_rotation = vault.check_all_rotations()
for secret_key, needed in needs_rotation:
    print(f"{secret_key}: {'Sí' if needed else 'No'}")
```

### Migración desde .env

```python
# Migrar automáticamente
results = vault.migrate_from_env()

# Migrar solo keys específicas
results = vault.migrate_from_env(
    secret_keys=["API_KEY", "TOKEN", "SECRET"]
)

# Resultado: {"API_KEY": True, "TOKEN": True, "OTHER": False}
```

### Backup del Vault

```python
# Crear backup
backup_path = vault.backup()
# → Core/Data/secrets_backup/secrets_backup_20240321_103000.vault

# Retención automática (configurable)
# Mantiene los últimos 3 backups por defecto
```

### Acceso con Auditoría

```python
# Acceso logueado
api_key = vault.get_secret(
    "API_KEY",
    module="llm_client",
    function="generate_response"
)

# Ver logs de acceso
logs = vault.get_access_log("API_KEY", hours=24)
for log in logs:
    print(f"{log['timestamp']}: {log['module']}.{log['function']}")
```

---

## Integración y Testing

### Ejecutar Tests

```bash
# Rate Limiting
cd D:\Proyectos\Yggdrasil\Asgard\Lilith
python -m pytest Core/Tests/test_rate_limiting_v2.py -v

# Audit Trail
python -m pytest Core/Tests/test_audit_trail.py -v

# Secrets Vault (requiere cryptography)
python -m pytest Core/Tests/test_secrets_vault.py -v

# Todos
python -m pytest Core/Tests/ -k "rate_limit or audit or secrets" -v
```

### Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `LILITH_MASTER_KEY` | Master key para secrets vault | Sí (B.6) |
| `AUDIT_SECRET_KEY` | Secret key para firmas HMAC | No (generado automáticamente) |

### Estructura de Archivos

```
Core/
├── Config/
│   ├── rate_limits.json      # Config rate limiting
│   ├── audit.json            # Config audit trail
│   ├── secrets.json          # Config secrets vault
│   ├── secrets.vault         # Vault cifrado (generado)
│   ├── .master_key           # Master key (protegido)
│   └── .audit_key            # Audit key (protegido)
├── Backend/
│   └── core/
│       ├── rate_limiter_v2.py    # Rate limiter
│       ├── audit_logger.py       # Audit trail
│       └── secrets_vault.py      # Secrets management
├── Data/
│   ├── rate_limit_history.db     # SQLite rate limits
│   ├── audit_trail.jsonl         # Logs de auditoría
│   ├── audit_metadata.db         # Metadata de auditoría
│   ├── secrets_access.db         # Logs de acceso a secrets
│   └── secrets_backup/           # Backups del vault
└── Tests/
    ├── test_rate_limiting_v2.py
    ├── test_audit_trail.py
    └── test_secrets_vault.py
```

---

## 🔒 Mejores Prácticas

### Rate Limiting
1. Monitorear logs de bloqueos
2. Usar overrides temporales, no permanentes
3. Ajustar límites según patrones de uso

### Audit Trail
1. Verificar integridad semanalmente
2. Exportar logs antes de limpieza
3. No modificar archivos de log manualmente

### Secrets
1. Rotar keys cada 90 días
2. Usar `LILITH_MASTER_KEY` fuerte
3. Hacer backup antes de rotaciones
4. No commitear el vault al repo

---

## 📚 Referencias

- [DEFENSA_INYECCION_PROMPTS.md](DEFENSA_INYECCION_PROMPTS.md) - Seguridad de prompts
- [ROLES_Y_PERMISOS.md](ROLES_Y_PERMISOS.md) - Sistema de roles
- [MISION_AUDITORIA_DECISIONES_A_Z.md](MISION_AUDITORIA_DECISIONES_A_Z.md) - Auditoría de decisiones

---

*Última actualización: 2026-03-21*
*Versión: Lilith 4.1*
