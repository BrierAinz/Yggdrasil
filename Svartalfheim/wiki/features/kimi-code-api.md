---
title: Kimi Code API — Provider Remoto
last_updated: 2026-05-02
version: v4.0.0+
category: feature
adr: ADR-001
---

# 🌙 Kimi Code API — Provider Remoto de LLM

> *Cuando los vientos del norte no alcanzan, los mensajeros de Kimi traen las runas desde lejos.*

## Resumen

Kimi Code (anteriormente Moonshot) es el provider remoto de fallback en el ecosistema Lilith. Usa el modelo `kimi-for-coding` optimizado para tareas de código y razonamiento técnico.

## Configuración

### Endpoint

```
URL: https://api.kimi.com/coding/v1
Modelo: kimi-for-coding
```

**IMPORTANTE**: El endpoint correcto es `api.kimi.com/coding/v1`, NO `api.moonshot.cn/v1`. El dominio moonshot es legacy y no funciona.

### Header Obligatorio

Todas las requests a Kimi Code deben incluir:

```
X-Client: claude-code
```

Sin este header, la API rechazará las peticiones con error 401/403.

### Configuración en `lilith_config.toml`

```toml
[llm.providers.kimi]
name = "Kimi Code"
base_url = "https://api.kimi.com/coding/v1"
model = "kimi-for-coding"
api_key = "env:KIMI_API_KEY"
required_headers = ["X-Client: claude-code"]
priority = 2  # Fallback después de LM Studio
```

### Variable de Entorno

```bash
# En .env (NUNCA commitear)
KIMI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

## Flujo de Fallback

```
Usuario → Lilith → LM Studio (localhost:1234/v1)
                    ↓ (si cae o no responde)
                    Kimi Code (api.kimi.com/coding/v1)
                    ↓ (si también cae)
                    Error con reporte de health
```

El `CircuitBreaker` (ver ADR-008) gestiona automáticamente:
- **CLOSED**: Provider activo, requests fluyen
- **OPEN**: Provider caído, requests van directo al siguiente
- **HALF_OPEN**: Testing recovery, requests limitadas

## Características del Modelo

| Característica | Detalle |
|---------------|---------|
| Modelo | `kimi-for-coding` |
| Contexto | ~128k tokens |
| Especialización | Código, razonamiento técnico |
| Latencia típica | 2-5 segundos (dependiendo de red) |
| Rate limits | Configurable en dashboard Kimi |
| Stream | Soportado (SSE) |
| Tools | Soportado (function calling) |

## Uso Programático

```python
from Lilith.Core.llm_provider import LLMProvider

provider = LLMProvider()
provider.configure("kimi")

# Automático via orquestador (recomendado)
response = provider.chat(
    messages=[{"role": "user", "content": "Analiza este código"}],
    stream=True
)

# Directo (para debugging)
response = provider.chat(
    messages=[...],
    model="kimi-for-coding",
    extra_headers={"X-Client": "claude-code"}
)
```

## Troubleshooting

### Error 401/403
- Verificar que el header `X-Client: claude-code` está presente
- Verificar que `KIMI_API_KEY` está configurada
- Confirmar que la API key no ha expirado

### Error de conexión
- Verificar conectividad a `api.kimi.com`
- El circuit breaker saltará automáticamente al siguiente provider
- Revisar logs en `lilith.log`

### Modelo no encontrado
- Usar exactamente `kimi-for-coding` (no `moonshot-v1` ni otros)
- El modelo está en el endpoint `/coding/v1`, no en `/v1`

## Relación con Otros Providers

| Provider | Tipo | Prioridad | Uso |
|----------|------|-----------|-----|
| LM Studio | Local | 1 (primary) | Desarrollo, privacidad, sin costo |
| Kimi Code | Remoto | 2 (fallback) | Cuando LM Studio cae, producción |
| OpenAI | Remoto | 3 (opcional) | Modelos GPT, production avanzada |

## Ver También

- [ADR-001: Multi-Provider LLM](adrs/ADR-001-multi-provider-llm.md)
- [ADR-008: Circuit Breaker + Retry](adrs/ADR-008-circuit-breaker-retry.md)
- [Batch Mode](features/batch-mode.md) — Usa Kimi Code como provider para agents
