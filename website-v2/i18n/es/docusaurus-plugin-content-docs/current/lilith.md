---
sidebar_position: 5
title: Lilith v5.1
---

# Lilith v5.1

Lilith es la IA táctica de Yggdrasil — el agente orquestador que coordina los Nueve Reinos.

## Capacidad

- **Orquestación** — Coordina múltiples agentes y herramientas
- **Memoria persistente** — Recuerda contexto entre sesiones via SQLite
- **Herramientas registradas** — Ejecuta tools del ecosistema
- **Multi-proveedor** — Soporta OpenAI, LM Studio, LiteLLM, y más

## Arquitectura

```
Lilith
├── lilith-core      # Config, tipos, providers
├── lilith-memory    # SQLite + backends pluggables
├── lilith-tools     # Registro de herramientas
├── lilith-api       # REST API (FastAPI)
├── lilith-cli       # CLI interactiva
├── lilith-bridge    # Puente entre componentes
├── lilith-orchestrator  # Motor de orquestación
└── lilith-skills    # Sistema de habilidades
```

## Paquetes Implementados

| Paquete | Versión | Descripción |
|---------|---------|-------------|
| lilith-core | 2.1.0 | Configuración, tipos, logging |
| lilith-memory | 1.0.0 | Almacenamiento persistente |
| lilith-tools | 1.0.0 | Registro y ejecución de tools |
| lilith-api | 1.0.0 | API REST |
| lilith-cli | 1.0.0 | Interfaz de línea de comandos |
| lilith-bridge | 1.0.0 | Puente entre componentes |
| lilith-orchestrator | 1.0.0 | Motor de orquestación |
| lilith-skills | 1.0.0 | Sistema de habilidades |

## Próximos Pasos

- Integración con vector stores (ChromaDB, Mem0)
- Pipeline de aprendizaje continuo
- Dashboard de monitoreo en tiempo real
