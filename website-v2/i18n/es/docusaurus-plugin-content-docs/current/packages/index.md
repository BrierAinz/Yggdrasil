---
sidebar_position: 1
title: Referencia de Paquetes
---

# Referencia de Paquetes

Yggdrasil se construye sobre 8 paquetes modulares, cada uno viviendo en su propio reino bajo `Asgard/`.

## Resumen

| Paquete | Versión | Descripción |
|---------|---------|-------------|
| [lilith-core](./lilith-core) | 2.1.0 | Configuración, tipos, logging, proveedores LLM |
| [lilith-memory](./lilith-memory) | 1.0.0 | Almacenamiento persistente con backends pluggables |
| [lilith-tools](./lilith-tools) | 1.0.0 | Registro y ejecución de herramientas |
| [lilith-api](./lilith-api) | 1.0.0 | API REST con FastAPI |
| [lilith-cli](./lilith-cli) | 1.0.0 | CLI interactiva |
| [lilith-bridge](./lilith-bridge) | 1.0.0 | Puente entre componentes |
| [lilith-orchestrator](./lilith-orchestrator) | 1.0.0 | Motor de orquestación de agentes |
| [lilith-skills](./lilith-skills) | 1.0.0 | Sistema de carga de skills |

## Instalación

Todos los paquetes son parte del workspace de Yggdrasil:

```bash
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil
uv sync --all-packages --dev
```
