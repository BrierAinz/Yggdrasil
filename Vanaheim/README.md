<<<<<<< HEAD
# Vanaheim

**AI Agents — Frameworks y Agentes Autonomos**

Vanaheim es el reino de la fertilidad y la inteligencia. Aqui viven los frameworks para construir agentes autonomos y los puentes entre sistemas.

## Proyectos

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| **bifrost** | Esqueleto | Puente entre agentes y servicios externos |
| **vanaheim-framework** | Esqueleto | Framework base para agentes autonomos |

## Estructura

```
Vanaheim/
├── bifrost/               # Puente de comunicacion
│   ├── bifrost/__init__.py
│   ├── pyproject.toml
│   └── tests/
└── vanaheim-framework/    # Framework de agentes
    ├── vanaheim/__init__.py
    ├── pyproject.toml
    └── tests/
```

## Estado

Esqueleto — Ambos proyectos tienen pyproject.toml + __init__.py pero sin logica implementada.

---

*Parte del ecosistema Yggdrasil — BrierStudios*
=======
# 🌊 Vanaheim — Reino de los Vanir

> *"Donde los Vanir cultivan la inteligencia que fluye como ríos."*

**Propósito:** Agentes autónomos, bots de plataforma, framework de agentes y Bifrost Gateway de comunicación con Asgard.

**Estado:** ✅ ACTIVO | **Refactoring:** Phase 3 completado 2026-05-21

---

## 📦 Paquetes Activos (Workspace uv)

| Paquete | Versión | Descripción | Dependencias clave |
|---|---|---|---|
| `vanaheim-framework` | v1.0.0 | Framework base para bots Vanir | pydantic, python-dotenv |
| `bifrost` | v2.0.0 | API Gateway con JWT, streaming y Hermes bridge | lilith-core, lilith-orchestrator, fastapi |
| `gamemaster-mcp-server` | v0.1.0 | Servidor MCP para creación de personajes IA (Caveduck, Tipsy Chat) | fastmcp, pydantic-ai, httpx |

### Bifrost Gateway
- **Puerto:** `http://localhost:9000`
- **Endpoints:** `/api/bifrost/health`, `/api/bifrost/agents`, `/api/bifrost/execute`
- **Seguridad:** JWT tokens + circuit breaker + fallback automático
- **Ver:** `README_BIFROST.md`

### GameMaster MCP Server
- **CLI:** `gamemaster-mcp-server` — servidor MCP para personajes de juego
- **Protocolo:** FastMCP + pydantic-ai

---

## ⚠️ Legacy — Directorios Deprecated

Los siguientes directorios están marcados como **LEGACY** (ver `LEGACY_DIRS.md`):

| Directorio Legacy | Reemplazo |
|---|---|
| `Agents/` (Adán, Eva, Mimir, Odin, Shalltear) | `vanaheim-framework/` (sistema modular) |
| `Core/` (API, models, memory, persona, registry) | `lilith-core`, `lilith-api`, `lilith-memory` (en Asgard) |
| `Config/` (agent configs, registry) | Config por paquete (`pyproject.toml`, `.env`) |
| `Bots_Lilith_v5/` (Telegram bot) | `lilith-bridge/` (gateway multi-plataforma, en Asgard) |
| `Council/` (templates) | `lilith-orchestrator/` (sistema de council, en Asgard) |

**Acción planificada:** Mover directorios legacy a `Helheim/Archives_Vanaheim_Legacy/` tras preservar historia git.

**No modificar** los directorios legacy — usar los paquetes workspace en su lugar.

---

## 🧹 Limpieza Phase 3 (2026-05-21)

- ✅ Directorios legacy marcados con `LEGACY_DIRS.md`
- ✅ `__pycache__/`, `.pytest_cache/`, `.egg-info/` limpiados
- ✅ `.gitignore` actualizado con `Vanaheim/bot_registry.json`
- ✅ `venv/` redundante eliminado (~580MB totales entre todos los reinos)

---

## 📂 Árbol

```
Vanaheim/
├── vanaheim-framework/       # v1.0.0 — Framework empaquetado
│   ├── vanaheim/
│   ├── tests/
│   └── pyproject.toml
├── bifrost/                  # v2.0.0 — API Gateway
│   ├── bifrost/
│   ├── tests/
│   ├── pyproject.toml
│   └── README_BIFROST.md
├── gamemaster-mcp-server/    # v0.1.0 — MCP server para personajes
│   ├── src/gamemaster_mcp/
│   ├── pyproject.toml
│   └── README.md
├── Agents/                   # ⚠️ LEGACY — Agentes del Panteón
├── Core/                     # ⚠️ LEGACY — Framework core
├── Config/                   # ⚠️ LEGACY — Configuración
├── Bots_Lilith_v5/           # ⚠️ LEGACY — Bot Telegram
├── Council/                  # ⚠️ LEGACY — Templates
├── bots/                     # Bots simples
├── server.py                 # ⚠️ Legacy entry point (usar bifrost)
├── requirements.txt          # ⚠️ Legacy — usar paquetes workspace
├── LEGACY_DIRS.md            # Documentación de directorios legacy
└── REGLAS.md                 # Reglas del reino
```

---

## 🔗 Enlaces

- [Asgard](../Asgard/) — Núcleo de Lilith (paquetes lilith-*)
- [Muspelheim](../Muspelheim/) — Proyectos de forja (ForgeMaster, AutoSub)
- [Helheim](../Helheim/) — Archivo y registro de caídos

---

*Bifrost arde con la luz de los Nueve Mundos.*
>>>>>>> origin/main
