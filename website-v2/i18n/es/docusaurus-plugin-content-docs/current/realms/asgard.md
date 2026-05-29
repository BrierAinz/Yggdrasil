---
sidebar_position: 1
title: Asgard
---

# ᚨ Asgard — El Dominio de los Dioses

Asgard es el reino superior, sede de los paquetes core que forman la base de todo Yggdrasil.

## Paquetes

### lilith-core
Configuración central, tipos de datos, logging y proveedores LLM.

### lilith-memory
Almacenamiento persistente con SQLite. Backends pluggables: SQLite, ChromaDB, Mem0.

### lilith-tools
Registro de herramientas con decorador `@tool`. Ejecución segura con validación de parámetros.

### lilith-api
API REST construida con FastAPI. Endpoints para chat, memoria, herramientas y estado del sistema.

### lilith-cli
Interfaz de línea de comandos interactiva. REPL con autocompletado y historial.

### lilith-bridge
Puente entre componentes síncronos y asíncronos. Facilita la integración entre capas.

### lilith-orchestrator
Motor de orquestación de agentes. Gestiona flujos de trabajo, delegación y estado.

### lilith-skills
Sistema de habilidades cargables. Los skills son scripts reutilizables que extienden las capacidades del agente.

## Principios

- Cada paquete tiene sus propios tests
- Las dependencias son unidireccionales
- Los tipos son la documentación
