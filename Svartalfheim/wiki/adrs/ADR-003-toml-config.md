---
adr_id: ADR-003
title: TOML como Formato de Config
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🔑 ADR-003: TOML como Formato de Configuración

## Context

Lilith necesita configuración persistente para providers, memoria, tools,Skills y preferencias del usuario. Las opciones eran: JSON (sin comentarios), YAML (complejo, ambiguo), INI (demasiado simple), o TOML (Python-native, PEP 680).

## Decision

Usar **TOML** como formato único de configuración:

1. **Archivo principal**: `~/.lilith/config.toml`
2. **Prioridad**: TOML file > env vars > defaults
3. **PEP 680**: `tomllib` es stdlib en Python 3.11+
4. **Fallback**: `tomli` para Python < 3.11
5. **Schema completo**: LLM providers, chat, tools, skills, memoria, resilience

Ejemplo de config:

```toml
[llm]
default_provider = "auto"
default_model = "auto"

[llm.providers.lm_studio]
type = "local"
base_url = "http://localhost:1234/v1"
model = "auto"

[chat]
max_history = 50
system_prompt = ""

[tools]
timeout = 60
max_calls = 25

[skills]
auto_trigger = true
max_triggered = 3
```

## Consequences

### Positivas
- **Comentarios**: TOML soporta comentarios con `#`
- **Legibilidad**: Sintaxis clara y sin ambigüedades como YAML
- **Python-native**: PEP 680 lo hace stdlib desde 3.11
- **Types**: Soporta strings, integers, floats, booleans, arrays, tables
- **Un archivo**: Config centralizada, no fragmentada

### Negativas
- **Sin exec**: No soporta eval ni funciones (intencional — seguridad)
- **Adopción**: Menos conocido que JSON/YAML fuera de Python
- **Anidación**: Tables anidadas pueden ser verbosas
