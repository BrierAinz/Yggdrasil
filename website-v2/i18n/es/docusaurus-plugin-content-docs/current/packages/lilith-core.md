---
sidebar_position: 2
title: lilith-core
---

# lilith-core

Paquete base: configuración, tipos, logging y abstracciones de proveedores LLM.

## Inicio Rápido

```python
from lilith_core import YggdrasilConfig, get_config, setup_logger, get_logger

# Cargar config desde defaults (~/.lilith/)
config = get_config()

# O especificar un root personalizado
config = YggdrasilConfig(root_path="/ruta/al/proyecto")

# Acceder a valores
print(config.model)          # "auto"
print(config.lm_studio_url)  # "http://localhost:1234/v1"
print(config.max_context)    # 8192

# Get/set (persistido en config.json)
config.set("temperature", 0.5)
temp = config.get("temperature")  # 0.5

# Logging
setup_logger(level="INFO")
logger = get_logger(__name__)
logger.info("Sistema listo")
```

## YggdrasilConfig

Configuración basada en dataclass con soporte para YAML, JSON y variables de entorno.

### Campos

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `root` | Path | `~/.lilith` | Directorio raíz del proyecto |
| `model` | str | `"auto"` | Modelo LLM por defecto |
| `temperature` | float | `0.7` | Temperatura del LLM |
| `max_context` | int | `8192` | Ventana de contexto máxima |
| `log_level` | str | `"INFO"` | Nivel de logging |

### Métodos

- `get(key, default=None)` — Obtener un valor
- `set(key, value)` — Establecer y persistir
- `load(path)` — Método de clase: cargar desde YAML
- `config_file` — Propiedad: ruta a config.json
