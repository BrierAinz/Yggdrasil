---
title: Deploy de Lilith
category: runbook
severity: standard
last_updated: 2026-05-02
---

# ⚔️ Runbook: Deploy de Lilith

> *Que el Bifröst se abra — es hora de enviar al guerrero al campo de batalla.*

## 📋 Prerrequisitos

- Python 3.11+ instalado
- LM Studio corriendo con un modelo cargado (opcional para modo remoto)
- API key de Kimi/Moonshot (para fallback remoto)
- Git configurado

## 🚀 Paso 1: Clonar y preparar

```bash
# Clonar el monorepo
cd /path/to/Yggdrasil
git pull origin main

# Entrar a Asgard
cd Asgard/Hermes-Lilith

# Verificar dependencias
pip install -r requirements.txt
# o si hay pyproject.toml:
pip install -e .
```

## ⚙️ Paso 2: Configurar

```bash
# Crear directorio de config
mkdir -p ~/.lilith

# Copiar config template
cp config.toml.example ~/.lilith/config.toml

# Editar config con tus providers
# OBLIGATORIO: Agregar API keys si usas providers remotos
nano ~/.lilith/config.toml
```

Config mínima (`~/.lilith/config.toml`):

```toml
[llm]
default_provider = "auto"

[llm.providers.lm_studio]
type = "local"
base_url = "http://localhost:1234/v1"
model = "auto"
api_key = ""

[llm.providers.kimi]
type = "remote"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-2.6"
api_key = "sk-xxx"  # ← TU API KEY AQUÍ
```

## 🗄️ Paso 3: Inicializar bases de datos

```bash
# Las DBs se crean automáticamente al primer run, pero puedes pre-inicializar
python -c "from Lilith.memory.session_store import SessionStore; SessionStore()"
python -c "from Lilith.Swarm.database import SwarmDatabase; SwarmDatabase()"
```

## 🧪 Paso 4: Verificar con tests

```bash
# Run completo de tests
pytest -v

# Tests específicos por módulo
pytest Asgard/Hermes-Lilith/Lilith/Core/tests/ -v
pytest Asgard/Hermes-Lilith/Lilith/MCP/tests/ -v
pytest Asgard/Hermes-Lilith/Lilith/Swarm/tests/ -v

# Verificar providers
python -c "
from Lilith.Core.llm_provider import test_all_providers
import json
print(json.dumps(test_all_providers(), indent=2))
"
```

## 🏃 Paso 5: Ejecutar

```bash
# Modo interactivo
python main.py

# Con provider específico
python main.py --provider lm_studio

# Con dashboard web
python main.py --dashboard
```

## ✅ Verificar deploy

1. **Providers**: Verificar que al menos un provider responde
2. **Memoria**: Enviar un mensaje y verificar que se guarda en `lilith_memory.db`
3. **Skills**: Verificar que los skills se cargan desde `Lilith/skills/`
4. **Dashboard**: Si está activado, verificar en `http://localhost:8000`

## 🔧 Troubleshooting del Deploy

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `ConnectionError: Ningun provider` | LM Studio no corre y no hay API key | Iniciar LM Studio o verificar config |
| `ModuleNotFoundError` | Dependencias faltantes | `pip install -r requirements.txt` |
| `Permission denied: ~/.lilith/` | Directorio sin permisos | `chmod 755 ~/.lilith/` |
| `CircuitBreakerError` | Provider con circuit breaker abierto | Esperar 60s o reiniciar para resetear |
| Tests fallan | Base de datos corrompida | Borrar `*.db` y reinicializar |

## 📊 Post-Deploy Checklist

- [ ] Al menos un provider LLM disponible
- [ ] SessionStore funciona (enviar mensaje y verificar BD)
- [ ] Skills cargan correctamente
- [ ] MCP clients conectan (si se usan)
- [ ] Dashboard accesible (si se habilita)
- [ ] Logs sin errores críticos
