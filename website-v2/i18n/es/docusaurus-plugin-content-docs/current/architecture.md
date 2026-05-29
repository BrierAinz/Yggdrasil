---
sidebar_position: 2
title: Arquitectura
---

# Arquitectura

Yggdrasil sigue una arquitectura modular en capas inspirada en la cosmología nórdica.

## Visión General

```
┌─────────────────────────────────────────────┐
│                 Midgard                      │
│         (CLI, Bots, Aplicaciones)            │
├─────────────────────────────────────────────┤
│              Vanaheim                        │
│         (Framework de Agentes)               │
├──────────┬──────────┬───────────────────────┤
│ lilith   │ lilith   │ lilith    │ lilith     │
│ -core    │ -memory  │ -tools    │ -api       │
├──────────┴──────────┴───────────────────────┤
│                 Asgard                       │
│          (Paquetes Core)                     │
└─────────────────────────────────────────────┘
```

## Capas

### Asgard — Núcleo
Los 8 paquetes `lilith-*` proporcionan la base:
- **lilith-core** — Configuración, tipos, logging, proveedores LLM
- **lilith-memory** — Almacenamiento persistente con SQLite + backends pluggables
- **lilith-tools** — Registro de herramientas y ejecución
- **lilith-api** — API REST con FastAPI
- **lilith-cli** — Interfaz de línea de comandos
- **lilith-bridge** — Puente entre componentes
- **lilith-orchestrator** — Motor de orquestación de agentes
- **lilith-skills** — Sistema de habilidades

### Vanaheim — Framework
`vanaheim-framework` proporciona la abstracción de alto nivel para construir agentes compuestos.

### Alfheim — Interfaces
Herramientas visuales: dashboard terminal, studio web, forge para generación de assets.

### Muspelheim — Generación
Módulos de generación procedural, entrenamiento de modelos y automatización.

## Principios de Diseño

1. **Dependencias unidireccionales** — las capas superiores dependen de las inferiores, nunca al revés
2. **Inyección de dependencias** — los componentes reciben sus dependencias, no las crean
3. **Interfaces sobre implementaciones** — los backends son intercambiables (SQLite, ChromaDB, Mem0)
