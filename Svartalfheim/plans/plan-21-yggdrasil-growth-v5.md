# Plan 21: Yggdrasil Growth Strategy v5

> **Estatus**: Activo  
> **Fecha**: 2026-05-07  
> **Reino**: Cross-realm / Infrastructure  
> **Prioridad**: P0 (crítico) → P3 (nice-to-have)

---

## Resumen Ejecutivo

Plan maestro para hacer crecer el ecosistema Yggdrasil basado en investigación de tendencias GitHub, estado actual del repo, y oportunidades de integración. El objetivo es pasar de un proyecto con 0 stars/0 forks a un ecosistema robusto con adoptabilidad real.

**Estado actual**: 76 commits, 0 estrellas, 0 bifurcaciones, 1 colaborador, CI arreglando (lint pasa, tests pendientes verificar).

---

## Acciones Inmediatas (Completadas)

- [x] Instalar gh CLI v2.67.0 en WSL
- [x] Arreglar 250+ ruff lint errors → 0 errors (CI lint job ahora pasa)
- [x] Agregar per-file-ignores para B904/TRY301 (patrones FastAPI legítimos)
- [x] Commit y push de fixes: `b840be3`
- [x] PR template ya existe y es completo (9 realms, REGLAS compliance, testing checklist)
- [x] Release workflow ya existe (`.github/workflows/release.yml`)
- [x] 4 tags existentes (v1.0.0-forgemaster, v1.0.0-terminal-dashboard, v3.0.0, v4.0.0)

---

## Acciones Pendientes (requieren gh auth)

- [ ] Mergear 8 Dependabot PRs
- [ ] Crear GitHub Release formal para v5.0.0 (o próximo tag)
- [ ] Habilitar GitHub Discussions
- [ ] Configurar Dependabot automerge para patches

---

## Fase 1: Foundation Strengthening (P0 — Esta Semana)

### 1.1 LiteLLM Multi-Model Backbone
**Reino**: Asgard (Core Tech) → Midgard (API Gateway)  
**Impacto**: Alto — permite intercambiar modelos sin refactor  
**Referencia**: [LiteLLM](https://github.com/BerriAI/litellm) (46k★)

```
Asgard/lilith-core/lilith_core/providers/litellm_provider.py
```

**Integración**:
- Agregar `litellm` como dependencia en lilith-core
- Crear LiteLLMProvider que wrappe `litellm.completion()` / `litellm.acompletion()`
- Soportar 100+ modelos (OpenAI, Anthropic, Groq, Together, Ollama-local)
- Fallback automático si el modelo primario falla
- Streaming nativo vía SSE

**Dependencias**: `pip install litellm`

### 1.2 mem0 Capa de Memoria Persistente
**Reino**: Asgard → Vanaheim (Agents)  
**Impacto**: Alto — agentes con contexto entre sesiones  
**Referencia**: [mem0](https://github.com/mem0ai/mem0) (55k★)

```
Asgard/lilith-memory/lilith_memory/backends/mem0_backend.py
```

**Integración**:
- Agregar `mem0ai` como dependencia en lilith-memory
- Implementar Mem0Backend como backend alternativo al existente
- Soporte para memoria a corto plazo (sesión) y largo plazo (persistente)
- Búsqueda semántica de memorias vía embeddings
- Integración con lilith-core como MemoryProvider

**Dependencias**: `pip install mem0ai`

### 1.3 CI Full Green
**Reino**: Helheim (Infrastructure)  
**Impacto**: Crítico — sin CI verde no hay confianza de contribuidores

- [x] Lint (ruff) → PASSED
- [ ] Tests (pytest) → Verificar que pasan
- [ ] Type check (pyright) → continue-on-error=true, fix gradual

---

## Fase 2: Feature Growth (P1 — Próximas 2 Semanas)

### 2.1 ComfyUI WebSocket Bridge (YggdrasilStudio)
**Reino**: Alfheim → Svartalfheim  
**Impacto**: Alto — progreso en tiempo real sin polling  
**Referencia**: YggdrasilStudio ya usa ComfyUI client

**Mejoras**:
- Reemplazar polling HTTP con WebSocket para progreso de generación
- Notificaciones push al frontend cuando una imagen termina
- Reconnection handling automático
- Queue depth monitoring en tiempo real

### 2.2 YggdrasilForge v0.2 — 3D Asset Pipeline
**Reino**: Alfheim (UI Prototypes)  
**Impacto**: Medio — portfolio project visible y usable

- Sketchfab search/download integrado (ya funciona vía MCP)
- Hunyuan3D text-to-3D (ya funciona vía MCP)
- Hyper3D Rodin image-to-3D (ya funciona vía MCP)
- PolyHaven textures (ya funciona vía MCP)
- Gallery de assets generados con thumbnails
- Export pipeline (GLB/OBJ/FBX)

### 2.3 Khoj Self-Hosted Knowledge Base
**Reino**: Svartalfheim (Knowledge)  
**Impacto**: Medio — RAG local sin APIs externas  
**Referencia**: [Khoj](https://github.com/khoj-ai/khoj) (34.4k★)

- Deploy Khoj como servicio en Niflheim
- Indexar documentación Yggdrasil (REGLAS, README, docs)
- Chatbot que responde preguntas sobre el ecosistema
- Integración con lilith-memory como knowledge backend

---

## Fase 3: Architecture Evolution (P2 — Mes 2)

### 3.1 Photon WASM Runtime
**Reino**: Midgard (API Gateway) → Alfheim (UI)  
**Impacto**: Medio — modularidad y portabilidad  
**Referencia**: [Photon](https://github.com/silverity/photon) (3.4k★)

- Compilar componentes de lilith-core a WASM
- Ejecutar agentes en browser sin servidor
- Edge computing para respuestas rápidas
- Sandbox de seguridad nativo

### 3.2 Mimir Deep Research Agent
**Reino**: Vanaheim (AI Agents)  
**Impacto**: Medio — investigación autónoma  

- Agente especializado en investigación profunda
- Integración con arxiv, searxng, blogwatcher skills
- Generación de reportes en markdown
- Guardado automático en Svartalfheim/Knowledge/

### 3.3 Turborepo Monorepo Build
**Reino**: Helheim (Infrastructure)  
**Impacto**: Medio — builds más rápidos y consistentes  
**Referencia**: [Turborepo](https://github.com/vercel/turbo) (30.3k★)

- Migrar frontend builds a Turborepo
- Shared configs entre Alfheim packages
- Cache de builds para CI más rápido
- Dev servers paralelos

---

## Fase 4: Scale & Visibility (P3 — Mes 3+)

### 4.1 one-api Gateway (Go)
**Reino**: Midgard (API Gateway)  
**Impacto**: Bajo-Medio — alternativa Python-only a LiteLLM  
**Referencia**: [one-api](https://github.com/songquanpeng/one-api) (33k★)

- API Gateway en Go para manejar múltiples LLM providers
- Rate limiting, key rotation, load balancing
- Compatible con OpenAI API format
- Dashboard de uso y costos

### 4.2 Archon Agent Framework
**Reino**: Vanaheim (AI Agents)  
**Impacto**: Medio — meta-agent que construye agentes  
**Referencia**: [Archon](https://github.com/coleam00/Archon) (20.9k★)

- Framework para construir agentes AI automáticamente
- Generación de código de agentes basada en especificaciones
- Integración con vanaheim-framework como agent factory

### 4.3 GitHub Visibility Campaign
**Reino**: Cross-realm  
**Impacto**: Alto para adopción

- Agregar topics/tags al repo (ai, agents, norse, multi-model, etc.)
- Crear FEATURED.md con screenshots y demos
- CONTRIBUTING.md
- Forma de comunicarse: Discussions + Discord/Telegram community
- Badges en README (CI status, version, license)
- Demo videos/GIFs en descripción

---

## Tabla de Prioridades

| # | Feature | Prioridad | Esfuerzo | Impacto | Dependencia |
|---|---------|-----------|----------|---------|-------------|
| 1 | LiteLLM Integration | P0 | 2-3d | Alto | Ninguna |
| 2 | mem0 Memory Layer | P0 | 2-3d | Alto | Ninguna |
| 3 | CI Full Green | P0 | 1d | Crítico | Ninguna |
| 4 | Dependabot Merge | P0 | 1h | Crítico | gh auth |
| 5 | ComfyUI WS Bridge | P1 | 3-4d | Alto | YggdrasilStudio |
| 6 | YggdrasilForge v0.2 | P1 | 3-4d | Medio | Blender MCP |
| 7 | Khoj Knowledge Base | P1 | 2-3d | Medio | Docker |
| 8 | Mimir Research Agent | P2 | 3-5d | Medio | Vanaheim |
| 9 | Photon WASM | P2 | 5-7d | Medio | Rust/WASM |
| 10 | Turborepo | P2 | 2-3d | Medio | Node.js |
| 11 | one-api Gateway | P3 | 5-7d | Bajo | Go |
| 12 | Archon Integration | P3 | 5-7d | Medio | Vanaheim |
| 13 | GitHub Visibility | P3 | 1-2d | Alto | Ninguna |

---

## Arquitectura Post-Integración

```
                    ┌─────────────────────────────────────┐
                    │           MIDGARD (Gateway)           │
                    │  ┌─────────┐  ┌──────────────────┐  │
                    │  │ one-api  │  │  LiteLLM Router   │  │
                    │  │  (Go)    │  │  (Python/100+ LLM)│  │
                    │  └─────────┘  └──────────────────┘  │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                     │                    │
    ┌─────────▼─────────┐ ┌────────▼───────┐ ┌────────▼─────────┐
    │     ASGARD         │ │   VANAHEIM      │ │   ALFHEIM        │
    │  ┌───────────────┐│ │ ┌────────────┐ │ │ ┌──────────────┐│
    │  │ lilith-core   ││ │ │  Agents     │ │ │ │  Studio UI   ││
    │  │ + LiteLLM     ││ │ │  + Archon   │ │ │ │  + Forge UI  ││
    │  └───────────────┘│ │ └────────────┘ │ │ └──────────────┘│
    │  ┌───────────────┐│ │ ┌────────────┐ │ │ ┌──────────────┐│
    │  │ lilith-memory ││ │ │  Mimir      │ │ │ │  Photon WASM ││
    │  │ + mem0        ││ │ │  Research   │ │ │ │  Runtime      ││
    │  └───────────────┘│ │ └────────────┘ │ │ └──────────────┘│
    └───────────────────┘ └────────────────┘ └──────────────────┘
              │                     │                    │
    ┌─────────▼─────────────────────▼────────────────────▼──┐
    │              SVARTALFHEIM (Knowledge)                  │
    │  ┌──────────┐ ┌─────────┐ ┌─────────────┐           │
    │  │   Khoj   │ │  Docs   │ │  ComfyUI    │           │
    │  │   RAG    │ │  Wiki   │ │  WS Bridge  │           │
    │  └──────────┘ └─────────┘ └─────────────┘           │
    └───────────────────────────────────────────────────────┘
```

---

## Criterios de Éxito

1. **CI 100% verde** — lint, tests, type-check todos pasando
2. **0 Dependabot PRs abiertos** — todos mergeados
3. **LiteLLM funcionando** — al menos 3 modelos intercambiables
4. **mem0 integrado** — agentes recuerdan contexto entre sesiones
5. **GitHub Release formal** — v5.0.0 con release notes
6. **Primeros 10 stars** — campaign de visibilidad
7. **1 contribuidor externo** — CONTRIBUTING.md claro

---

*Este plan será actualizado conforme se completen las fases. Consultar REGLAS_YGGDRASIL.md para las reglas de migración entre reinos.*