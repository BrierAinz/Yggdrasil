---
adr_id: ADR-001
title: Multi-Provider LLM con Fallback
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🔮 ADR-001: Multi-Provider LLM con Fallback

## Context

Lilith necesita comunicarse con modelos de lenguaje para generar respuestas. Históricamente, dependía de un único endpoint (LM Studio local). Esto creaba un punto único de fallo: si LM Studio se caía, todo el sistema quedaba inoperativo. Los LLM providers pueden fallar por timeout, rate limits (429), errores internos (500/502/503), o simples caídas de red.

## Decision

Implementar un sistema de **multi-provider con fallback automático**:

1. **Provider Registry**: Registro global de providers (LM Studio local, Kimi/Moonshot remoto, futuros)
2. **Fallback automático**: Si un provider falla, se intenta el siguiente en la lista
3. **Circuit Breaker por provider**: Cada provider tiene su propio circuit breaker (ver ADR-008)
4. **Auto-detección de modelo**: La config `"model": "auto"` detecta modelos disponibles
5. **Config TOML**: Los providers se definen en `~/.lilith/config.toml`

```toml
[llm]
default_provider = "auto"

[llm.providers.lm_studio]
type = "local"
base_url = "http://localhost:1234/v1"
model = "auto"

[llm.providers.kimi]
type = "remote"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-2.6"
```

## Consequences

### Positivas
- **Resiliencia**: Si LM Studio cae, Kimi toma el relevo automáticamente
- **Flexibilidad**: Se pueden agregar nuevos providers sin código
- **Observabilidad**: Cada provider reporta estado, errores y circuit breaker stats

### Negativas
- **Latencia**: El fallback agrega latencia en el primer intento fallido
- **Complejidad**: Más código para mantener (registry, health checks, failover)
- **Divergencia de respuestas**: Diferentes modelos pueden dar respuestas inconsistentes
- **Costo**: Providers remotos (Kimi) tienen costo por token
