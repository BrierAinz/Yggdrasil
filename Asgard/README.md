# Asgard

**Core Infrastructure — Los 8 paquetes lilith-***

Asgard es el corazon de Yggdrasil. Aqui viven los paquetes modulares que forman la infraestructura base del ecosistema Lilith.

## Paquetes

| Paquete | Version | Estado | Descripcion |
|---------|---------|--------|-------------|
| lilith-core | 2.1.0 | Activo | Tipos base, configuracion, logging, proveedores LLM |
| lilith-memory | 1.0.0 | Activo | Store de memoria vectorial con backend SQLite |
| lilith-api | 1.0.0 | Esqueleto | FastAPI Gateway con soporte WebSocket |
| lilith-bridge | 1.0.0 | Esqueleto | Puente entre Lilith y servicios externos |
| lilith-cli | 3.0.0 | Esqueleto | Interfaz de terminal para el ecosistema |
| lilith-orchestrator | 1.0.0 | Esqueleto | Coordinacion de agentes y orquestacion |
| lilith-skills | 1.0.0 | Esqueleto | Gestion y descubrimiento de skills |
| lilith-tools | 1.0.0 | Esqueleto | Control de PC, automatizacion, RAG |

## Estructura

```
Asgard/
├── lilith-core/         # Tipos, config, logger, providers
│   └── lilith_core/
│       ├── config.py
│       ├── types.py
│       ├── logger.py
│       └── providers.py
├── lilith-memory/       # Memoria vectorial SQLite
│   └── lilith_memory/
│       └── store.py
├── lilith-api/          # FastAPI Gateway
├── lilith-bridge/       # Puente a Telegram/Discord
├── lilith-cli/          # Terminal interface
├── lilith-orchestrator/ # Orquestacion de agentes
├── lilith-skills/       # Gestion de skills
└── lilith-tools/        # PC control, browser, RAG
```

## Estado

- **Activo:** lilith-core, lilith-memory (codigo real, funcionando)
- **Esqueleto:** Los 6 paquetes restantes (pyproject.toml + __init__.py, sin logica)

---

*Parte del ecosistema Yggdrasil — BrierStudios*
