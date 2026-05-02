---
adr_id: ADR-008
title: Circuit Breaker + Retry para Resilience
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🛡️ ADR-008: Circuit Breaker + Retry para Resilience

## Context

Los LLM providers son inherentemente inestables: timeouts, rate limits (429), errores de servidor (500/502/503), y caídas de red ocurren frecuentemente. Sin protección, estos errores se propagan al usuario y pueden causar cascading failures si se reintenta ciegamente.

## Decision

Implementar **Circuit Breaker + Retry con backoff exponencial**:

1. **Circuit Breaker** (por provider):
   - `CLOSED`: Funcionamiento normal — requests pasan libremente
   - `OPEN`: Bloqueado — después de N fallos consecutivos (`failure_threshold=3`), el circuito se abre
   - `HALF_OPEN`: Probando — tras `recovery_timeout=60s`, permite llamadas de prueba limitadas
   - Thread-safe con `threading.Lock`
   - Estadísticas expuestas via `stats` property

2. **Retry con Backoff** (`retry_with_backoff`):
   - `max_retries=3` por defecto
   - `base_delay=1.0s`, `backoff_factor=2.0`, `max_delay=30.0s`
   - Retry solo en errores "transitorios": 429, 500, 502, 503, 504, timeouts, connection errors
   - Errores de cliente (4xx except 429) NO se reintentan

3. **Integración**: Cada `LLMProvider` tiene su propio `CircuitBreaker` y `RetryConfig`

Decoración mitológica en el código:
- CLOSED = "El camino de Midgard fluye libremente"
- OPEN = "Las puertas de Muspelheim sellan el paso"
- HALF_OPEN = "Un susurro de Niflheim prueba si el puente resiste"

## Consequences

### Positivas
- **Graceful degradation**: Si un provider falla, no se satura con retries
- **Fail-fast**: Circuit breaker OPEN evita llamadas inútiles
- **Auto-recovery**: HALF_OPEN permite pruebas automatizadas de recuperación
- **Thread-safe**: Funciona correctamente con múltiples hilos
- **Observable**: Stats del circuit breaker para monitoreo

### Negativas
- **Config tuning**: Los thresholds pueden necesitar ajuste por provider
- **Cold start**: Al iniciar, si el circuito está OPEN, hay que esperar recovery_timeout
- **False positives**: Un burst de errores temporales puede abrir el circuito innecesariamente
