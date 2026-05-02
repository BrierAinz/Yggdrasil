---
title: Svartalfheim Wiki — Índice
last_updated: 2026-05-02
---

# 🔨 Svartalfheim Wiki — Las Runas del Yggdrasil

> *En las profundidades de Svartalfheim, los Enanos forjan las runas que preservan la sabiduría de los Nueve Mundos.*

---

## 🌍 Reinos del Yggdrasil

| Reino | Propósito | Estado |
|-------|-----------|--------|
| ⚡ [Asgard](asgard.md) | Core tech — Lilith, orquestador, providers | Activo |
| 🌿 [Vanaheim](vanaheim.md) | Agentes de IA — Bots, diplomacia | Activo |
| ✨ [Alfheim](alfheim.md) | Prototipos UI — Dashboards | Activo |
| 🔨 [Svartalfheim](svartalfheim.md) | Documentación — Wiki, ADRs, guías | Activo |
| 🔥 [Muspelheim](muspelheim.md) | Desarrollo WIP — Sprints | Variable |
| ❄️ [Niflheim](niflheim.md) | Recursos — Modelos, datasets | Activo |
| 💀 [Helheim](helheim.md) | Archivo — Legacy | Activo |
| 🏔️ [Jotunheim](jotunheim.md) | Proyectos masivos | Reservado |
| 🌍 [Midgard](midgard.md) | Apps personales | Reservado |

---

## 📋 Architecture Decision Records (ADRs)

| ADR | Título | Decisión |
|-----|--------|----------|
| [ADR-001](adrs/ADR-001-multi-provider-llm.md) | Multi-Provider LLM con Fallback | Múltiples providers con circuit breaker |
| [ADR-002](adrs/ADR-002-sqlite-storage.md) | SQLite como Storage Principal | Zero-ops, FTS5, WAL mode |
| [ADR-003](adrs/ADR-003-toml-config.md) | TOML como Formato de Config | PEP 680, comentarios, legible |
| [ADR-004](adrs/ADR-004-hybrid-memory.md) | Hybrid Memory (Vector + Graph + FTS5) | Triple capa, auto-consolidación |
| [ADR-005](adrs/ADR-005-skills-yaml-triggers.md) | Skills como YAML Templates con trigger_regex | Declarativo, hot-reload, 3 niveles |
| [ADR-006](adrs/ADR-006-swarm-intelligence.md) | Swarm Intelligence con AgentSpawner | Multi-agent, MessageBus, SQLite |
| [ADR-007](adrs/ADR-007-mcp-protocol.md) | MCP Protocol para Tool Discovery | JSON-RPC 2.0, discovery dinámico |
| [ADR-008](adrs/ADR-008-circuit-breaker-retry.md) | Circuit Breaker + Retry para Resilience | CLOSED/OPEN/HALF_OPEN, backoff |
| [ADR-009](adrs/ADR-009-session-store-crash-recovery.md) | Session Store con Crash Recovery | Incremental, embeddings, keyword extraction |
| [ADR-010](adrs/ADR-010-dark-fantasy-identity.md) | Dark Fantasy Aesthetic como Identity | Nomenclatura Norse, docstrings poéticos |

---

## 📖 Runbooks

| Runbook | Descripción |
|---------|-------------|
| ⚔️ [Deploy](runbooks/deploy.md) | Cómo deployar Lilith |
| 🔍 [Debug](runbooks/debug.md) | Cómo debuggear problemas comunes |
| ⚒️ [Contribute](runbooks/contribute.md) | Cómo contribuir al ecosistema |

---

## 🔧 Features y Guías de Referencia

|| Feature | Descripción |
||---------|-------------|
|| 🏭 [Batch Mode](features/batch-mode.md) | Ejecución no-interactiva via CLI |
|| 🌙 [Kimi Code API](features/kimi-code-api.md) | Provider remoto de LLM (fallback) |
|| 🐝 [Swarm Intelligence](features/swarm-intelligence.md) | Multi-agent cooperativo con MessageBus |

---

## 🕸️ Cross-Realm

- [Mapa de Dependencias](cross-realm.md) — Quién depende de quién

## 📖 Glosario

- [Glosario del Ecosistema](glossary.md) — Todos los términos técnicos y mitológicos

---

## 📁 Templates para Nuevos Proyectos

| Template | Uso |
|----------|-----|
| [README-template.md](templates/README-template.md) | README para nuevos proyectos |
| [CONTRIBUTING-template.md](templates/CONTRIBUTING-template.md) | Guía de contribución |
| [.gitignore-template](templates/.gitignore-template) | Gitignore completo |

---

## 📐 Reglas de Forja

1. Todo proyecto nuevo debe asignarse a un reino
2. Los reinos no deben tener dependencias circulares
3. Asgard es el núcleo; otros reinos consumen su API
4. Los ADRs son inmutables una vez aceptados
5. La documentación se versiona junto con el código

*Yggdrasil crece con orden o no crece.* 🌳
