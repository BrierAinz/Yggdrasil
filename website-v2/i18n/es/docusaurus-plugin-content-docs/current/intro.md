---
sidebar_position: 1
title: Yggdrasil — Ecosistema de los Nueve Reinos
slug: /intro
---

# Yggdrasil

**Nueve Reinos. Un Árbol. Posibilidades Infinitas.**

Yggdrasil es un ecosistema modular de agentes de IA construido alrededor de una arquitectura de nueve reinos. Cada reino encapsula una responsabilidad distinta — desde el núcleo de configuración hasta la orquestación de agentes, pasando por frameworks de aplicaciones y generación procedural.

## ᚨ Los Nueve Reinos

Cada paquete `lilith-*` vive dentro de su reino correspondiente:

- **Asgard** — Dominio de los paquetes core (`lilith-core`, `lilith-memory`, `lilith-tools`, `lilith-api`, `lilith-cli`, `lilith-bridge`, `lilith-orchestrator`, `lilith-skills`)
- **Vanaheim** — Framework de agentes (`vanaheim-framework`, `bifrost`)
- **Alfheim** — Interfaces de usuario (`YggdrasilStudio`, `YggdrasilForge`, `TerminalDashboard`)
- **Muspelheim** — Dominio del fuego: generación procedural, entrenamiento, automatización
- **Niflheim** — Dominio del hielo: repositorio de modelos y datos
- **Svartalfheim** — Forja de skills y herramientas
- **Midgard** — Puente al mundo humano: CLI, bots, aplicaciones
- **Helheim** — Archivos muertos y código legacy
- **Jotunheim** — Infraestructura y DevOps

## ᚹ Filosofía

> *"Nueve Reinos. Un Árbol. Posibilidades Infinitas."*

El diseño sigue tres principios:

1. **Modularidad radical** — cada paquete es independiente, versionable, testeable
2. **Composición sobre herencia** — los agentes se construyen combinando capabilities
3. **Observabilidad primero** — cada decisión del agente es auditable y trazable

## ᛏ Comenzar

Ver [Instalación](/docs/setup) para configurar tu entorno de desarrollo.
