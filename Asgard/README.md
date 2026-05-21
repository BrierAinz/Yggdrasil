# 🏛️ Asgard — El Reino del Núcleo

> *"Donde el trono de Lilith gobierna los Nueve Mundos."*

**Propósito:** Núcleo del ecosistema Yggdrasil. Contiene el engine de Lilith como paquetes modulares workspace, el CLI interactivo, y el gateway de comunicación.

**Estado:** ✅ ACTIVO | **Refactoring:** Phase 1–3 completado 2026-05-21

---

## 📦 Paquetes Activos (Workspace uv)

| Paquete | Versión | Descripción | Dependencias clave |
|---|---|---|---|
| `lilith-core` | v2.0.0 | Engine central de Lilith | requests, pydantic, litellm |
| `lilith-memory` | v2.0.0 | Sistema de memoria (working, semantic, episodic) | mem0, chromadb (optional) |
| `lilith-tools` | v2.0.0 | Sistema de herramientas y tool router | lilith-core |
| `lilith-orchestrator` | v2.0.0 | Motor de orquestación y gateway FastAPI | lilith-core, lilith-tools, lilith-memory |
| `lilith-api` | v2.2.0 | REST API para Lilith | lilith-core, lilith-orchestrator, fastapi |
| `lilith-cli` | v3.0.0 | CLI interactivo (REPL + TUI) | textual, cyclopts, rich, prompt-toolkit |
| `lilith-bridge` | v1.0.0 | Gateway bidireccional con Hermes/MCP | lilith-core, lilith-skills, fastapi, httpx |
| `lilith-skills` | v1.0.0 | Cargador de skills y registro YAML | pydantic, pyyaml |

Todos los paquetes usan `uv workspace` con dependencias bare-name entre sí.

---

## ⚠️ Legacy

### `Lilith/` — Monolito v5.0 (DEPRECATED)

- **Estado:** LEGACY — marcado con `LEGACY.md` (2026-05-21)
- **Contenido:** 477 archivos `.py`, ~83MB de código legacy (`Core/`, `src/`, `scripts/`, `Data/`)
- **Destino:** `Helheim/Archives_Lilith_Legacy/` (pendiente migración con git)
- **No importar** desde este directorio — usar los paquetes `lilith-*` en su lugar

| Módulo Legacy | Reemplazo |
|---|---|
| `Core/` (Destrezas, Workspace, Tools) | `lilith-core`, `lilith-tools` |
| `src/memory/` | `lilith-memory` |
| `src/api/` | `lilith-api` |
| CLI / REPL | `lilith-cli` |
| `src/` orchestrator | `lilith-orchestrator` |
| `src/` bridge | `lilith-bridge` |
| Skills | `lilith-skills` |

---

## 🧹 Limpieza Phase 1–3 (2026-05-21)

- ✅ `.bat` launchers movidos a `Lilith/scripts/bats/`
- ✅ 4 `.venv` redundantes eliminados (lilith-tools, AutoSub, ForgeMaster, TerminalDashboard, YggdrasilForge — ~580MB liberados)
- ✅ `__pycache__/`, `.pytest_cache/`, `.coverage`, `.egg-info/`, `.ruff_cache/` limpiados
- ✅ `.gitignore` actualizado con `.ruff_cache/`, `Asgard/Lilith/Data/`, `Asgard/Lilith/Core/`

---

## 📂 Árbol

```
Asgard/
├── lilith-core/         # v2.0.0 — Engine central
├── lilith-memory/       # v2.0.0 — Memoria multicapa
├── lilith-tools/        # v2.0.0 — Herramientas y router
├── lilith-orchestrator/ # v2.0.0 — Orquestación y gateway
├── lilith-api/          # v2.2.0 — REST API
├── lilith-cli/          # v3.0.0 — CLI interactivo
├── lilith-bridge/       # v1.0.0 — Gateway MCP/Hermes
├── lilith-skills/       # v1.0.0 — Skills YAML
└── Lilith/              # ⚠️ LEGACY v5.0 — No modificar
    ├── LEGACY.md
    ├── Core/
    ├── src/
    ├── scripts/
    └── Data/
```

---

## 🔗 Enlaces

- [Vanaheim](../Vanaheim/) — Agentes y Bifrost Gateway
- [Muspelheim](../Muspelheim/) — Proyectos de forja
- [Helheim](../Helheim/) — Archivo y registro de caídos

---

*El trono de Asgard se sostiene sobre pilares modulares.*
