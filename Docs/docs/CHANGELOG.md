# Changelog

Historial de versiones de Yggdrasil.

---

## v5.1.0 — 2026-05-04

### Cambios

- **Build system:** Migracion de todos los paquetes de setuptools a hatchling
- **Ruff:** target-version actualizado de py39 a py311; auto-fix UP038/UP007
- **CI:** Python 3.12 matrix, ruff-pre-commit v0.11.8, hooks adicionales
- **pytest:** Entradas stale eliminadas, TerminalDashboard agregado a testpaths
- **Workspace:** TerminalDashboard, AutoSub, ForgeMaster agregados a uv.workspace.members
- **Code quality:** Reemplazado print() con logging en lilith-api, lilith-orchestrator, ForgeMaster
- **Code quality:** Path hardcoded /mnt/d reemplazado con COMFYUI_MODELS_DIR env var en ForgeMaster
- **Code quality:** TODO comments reemplazados con NotImplementedError en Alfheim dashboard
- **Code quality:** Docstrings de modulo agregados a lilith-tools y vanaheim-framework

### Fixes

- **lilith-cli:** Version mismatch (pyproject 2.0.0 -> 2.1.0 para coincidir con __init__.py)
- **lilith-orchestrator:** gateway/__init__.py faltante agregado
- **Pre-commit:** Regex de exclude actualizado, hooks check-toml y detect-private-key agregados
- **CI:** Alfheim/TerminalDashboard, Muspelheim/AutoSub, ForgeMaster agregados a install steps

### Agregados

- **pyproject.toml:** [project.urls] Repository, license, readme fields en todos los paquetes
- **pyproject.toml:** README.md agregado a paquetes que lo tenian faltante

---

## v5.0.0 — 2026-04

### Breaking Changes

- **Monolito roto:** Lilith v5.0 monolitico (83 MB) dividido en 8 paquetes lilith-* modulares
- **Asgard:** Nuevo realm con los 8 paquetes
- **Paquetes:**
  - lilith-core (tipos, config, logger, providers)
  - lilith-memory (store de memoria SQLite)
  - lilith-api (FastAPI Gateway)
  - lilith-bridge (Telegram/Discord)
  - lilith-cli (terminal interface)
  - lilith-orchestrator (agent coordination)
  - lilith-skills (skill management)
  - lilith-tools (PC control, browser, RAG)

### Migracion

- Archivo monolitico `lilith.py` (83 MB) reemplazado por modulos independientes
- Cada paquete tiene su propio `pyproject.toml`
- Dependencias compartidas via `uv.workspace`

---

## v4.x — 2026-03/04

### Features

- **CLI Nordic Frost:** Tema visual con Elder Futhark runes
- **Animaciones:** Banner animado, spinner, mensajes tematicos
- **Prompt personalizado:** Estilo runico con bordes decorativos
- **Respuestas estilizadas:** Lilith en rojo, texto en italic, separadores gold
- **Memoria avanzada:** Embeddings con Sentence Transformers
- **Busqueda semantica:** Busqueda por similitud, no texto exacto
- **Automejora:** Analisis de patrones y mejoras automaticas
- **Skill Creator:** Creacion automatica de skills desde conversaciones

---

## v3.x — 2026-02/03

### Features

- **Lilith Agent v2:** Agente de codigo completo
- **Memoria SQLite:** Persistencia de conversaciones
- **Multi-provider:** Soporte para OpenAI, Anthropic, etc.
- **Horror GameMaster:** Inicio del proyecto en Muspelheim

---

## v2.x — 2026-01/02

### Features

- **9 Realms:** Arquitectura de 9 reinos definida
- **Svartalfheim:** Documentacion centralizada
- **Scripts:** Automatizacion de tareas comunes
- **Knowledge Base:** Base de conocimiento Lilith

---

## v1.x — 2025-12 / 2026-01

### Features

- **Primera version:** CLI basico de Yggdrasil
- **Estructura:** Organizacion inicial por realms
- **Git:** Repositorio con historial completo

---

## Versiones Futuras (Roadmap)

### v6.0 (Planificado)

- **As:** Asgard packages implementados (lilith-api, lilith-bridge, etc.)
- **Vanaheim:** Framework de agentes autonomo funcional
- **Alfheim:** Dashboard web con React
- **i18n:** Soporte completo en ingles y espanol

### v7.0 (Vision)

- **Jotunheim:** Primer proyecto de gran escala
- **Swarm Intelligence:** Coordinacion multi-agente
- **Cloudflare Workers:** API distribuida
