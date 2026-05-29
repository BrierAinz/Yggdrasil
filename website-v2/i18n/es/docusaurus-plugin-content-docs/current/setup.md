---
sidebar_position: 3
title: Instalación
---

# Instalación

## Requisitos Previos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)
- Node.js 18+ (solo para la documentación)

## Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# Instalar dependencias con uv
uv sync --all-packages --dev

# Verificar la instalación
uv run python -c "from lilith_core import YggdrasilConfig; print(YggdrasilConfig())"
```

## Estructura del Workspace

El proyecto usa un workspace de `uv` con múltiples paquetes:

```toml
[tool.uv.workspace]
members = [
    "Asgard/lilith-core",
    "Asgard/lilith-memory",
    "Asgard/lilith-tools",
    # ... más paquetes
]
```

## Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# LLM Provider
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# O usar LM Studio local
LM_STUDIO_URL=http://localhost:1234/v1
```

## Ejecutar Tests

```bash
# Todos los tests
uv run pytest Asgard/*/tests -q

# Paquete específico
uv run pytest Asgard/lilith-core/tests -q
```

## Documentación

```bash
cd website-v2
npm install
npm start  # Servidor de desarrollo en localhost:3000
```
