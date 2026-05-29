---
sidebar_position: 6
title: Registro de cambios
---

# Registro de cambios

## v5.1.0 — Refactorización Modular

### Nuevo
- **8 paquetes lilith-\*** implementados como workspace de uv
- **lilith-memory** — Almacenamiento SQLite con backends pluggables (SQLite, ChromaDB, Mem0)
- **lilith-tools** — Registro de herramientas con decorador `@tool`
- **lilith-api** — API REST con FastAPI y DI
- **lilith-bridge** — Puente entre componentes async/sync
- **lilith-orchestrator** — Motor de orquestación de agentes
- **lilith-skills** — Sistema de habilidades cargables

### Mejorado
- **YggdrasilConfig** — Dataclass con carga desde YAML, JSON y env vars
- **Logging** — Logger estructurado con `structlog`-style API
- **Providers** — Interfaz unificada para LLM providers

### Corregido
- Ruff lint: 674 errores → 0
- CI: Todos los tests pasando (1007+ tests)
- Dependabot: 8 PRs consolidados
- Seguridad: urllib3, serialize-javascript, uuid actualizados

### Infraestructura
- GitHub Actions CI con lint, test, type-check
- Deploy automático a GitHub Pages
- Custom domain: docs.brierstudios.com
