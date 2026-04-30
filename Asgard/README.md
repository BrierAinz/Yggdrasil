# Asgard - Reino de los Aesir

> **Estado:** ACTIVO
> **Tamano:** 4.5 GB | 516 Python | 4 JS
> **Remasterizado:** 2026-04-29

## Proyectos

| Proyecto | Tipo | Estado |
|----------|------|--------|
| Hermes-Lilith | Agente CLI Python | **Produccion** |
| Lilith (legacy) | Monolito Python | **Refactor en progreso** |
| ObsidianConnect | Conector Obsidian | Beta |
| Web-AI-Chat | Chat web LM Studio | Beta |

## Estructura

```
Asgard/
├── Hermes-Lilith/          # Agente CLI principal (comando: lilith)
│   ├── lilith.py           # Entry point
│   ├── setup.py            # Instalador global
│   ├── config.py           # Configuracion
│   ├── src/                # Modulos (123k LOC, refactor progresivo)
│   └── requirements.txt    # Dependencias
├── Lilith/                 # Monolito legacy (src/, logs/, etc.)
├── ObsidianConnect/        # Conector Obsidian -> LM Studio
└── Web-AI-Chat/            # Chat web para LM Studio
```

## Uso Rapido

```bash
# Desde cualquier lugar en Windows
cd Asgard/Hermes-Lilith && python lilith.py

# O si esta instalado globalmente
lilith
```

## Notas Post-Remasterizacion

- Legacy code movido a Helheim/Archives_Lilith_Legacy_2026-04-29/
- Basura limpiada (pycache, node_modules, .map)
- setup.py configurado para instalacion global via PATH
