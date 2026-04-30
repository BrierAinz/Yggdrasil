# Vanaheim - Reino de los Vanir

> **Estado:** ACTIVO
> **Tamano:** 442 KB | 64 Python
> **Remasterizado:** 2026-04-29

## Proposito

Todos los bots, agentes autonomos y experimentos de IA en un solo lugar.

## Proyectos

| Bot | Lenguaje | Estado | Proposito |
|-----|----------|--------|-----------|
| vanaheim-bot | Python | Beta | Bot base con herramientas |
| plantilla-bot | Python | Template | Plantilla para nuevos bots |
| bot_telegram | Python | WIP | Bot para Telegram |
| llm_agente_2026 | Python | Experimental | Agente LLM con tools |
| conversation_bot | Python | Experimental | Bot de conversacion |
| scraper_bot | Python | Experimental | Scraping + IA |

## Estructura

```
Vanaheim/
├── Bots/
│   ├── vanaheim-bot/       # Bot principal
│   ├── plantilla-bot/      # Plantilla
│   ├── bot_telegram/       # Telegram
│   ├── llm_agente_2026/    # Agente LLM
│   ├── conversation_bot/   # Conversacion
│   └── scraper_bot/        # Scraper
└── [libs compartidas]
```

## Notas Post-Remasterizacion

- Consolidados todos los bots que estaban dispersos en Yggdrasil
- Cada bot tiene su propio entorno virtual (recomendado)
- Posible unificacion de dependencias futura (requirements unificado)
