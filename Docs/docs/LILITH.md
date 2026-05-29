# Lilith Guide

Guia completa del agente Lilith — la diosa que habita Yggdrasil.

---

## Que es Lilith

Lilith es un agente de codigo completo inspirado en Hermes Agent y Claude Code. Tiene:

- **Memoria persistente** — SQLite con embeddings para busqueda semantica
- **Skills** — Procedimientos reutilizables almacenados como markdown
- **Ejecucion de codigo** — Terminal integrado para comandos del sistema
- **Acceso web** — Busquedas y navegacion
- **Tema Nordic Frost** — Interfaz con Elder Futhark runes

---

## Arquitectura

```
Yggdrasil/
├── lilith_agent.py      # Agente principal (v2)
├── lilith_cli.py        # CLI de chat con Lilith
├── ygg.py               # CLI principal (Nordic theme)
├── yggdrasil_cli.py     # CLI de gestion
├── advanced_memory.py   # Memoria con embeddings
├── auto_improvement.py  # Sistema de automejora
├── skill_creator.py     # Autocreacion de skills
└── agent_permissions.json  # Permisos del agente
```

### Componentes Principales

| Componente | Archivo | Descripcion |
|-----------|---------|-------------|
| Agente | `lilith_agent.py` | Motor principal del agente IA |
| Chat CLI | `lilith_cli.py` | Interfaz de chat interactiva |
| CLI Principal | `ygg.py` | Nordic Frost CLI con Rich |
| Gestion | `yggdrasil_cli.py` | Admin del ecosistema |
| Memoria | `advanced_memory.py` | Embeddings + busqueda semantica |
| Skills | `skill_creator.py` | Creacion automatica de skills |
| Automejora | `auto_improvement.py` | Analisis y mejora continua |
| Permisos | `agent_permissions.json` | Control de acceso del agente |

---

## Sistema de Memoria

### Almacenamiento

La memoria usa SQLite con embeddings de Sentence Transformers:

```python
# Estructura de la memoria
{
    "id": "uuid",
    "content": "texto de la entrada",
    "metadata": {"type": "user|assistant"},
    "embedding": [0.1, 0.2, ...],  # Vector de 384 dimensiones
    "timestamp": "2026-05-29T12:00:00"
}
```

### Busqueda Semantica

La memoria permite encontrar entradas por similitud semantica, no solo texto exacto:

```python
# Buscar memorias similares
results = memory.search("como configurar el CLI", limit=5)
```

### Comandos de Memoria (en chat)

| Comando | Descripcion |
|---------|-------------|
| `memoria` | Ver las ultimas 10 entradas |
| `resumen` | Resumen estadistico de la conversacion |
| `borrar` | Borrar toda la memoria (con confirmacion) |

---

## Sistema de Skills

Los skills son procedimientos reutilizables almacenados como archivos markdown:

```
~/.hermes/skills/
├── category/
│   └── skill-name/
│       └── SKILL.md
```

### Crear un Skill

```bash
# Desde el agente
# Lilith puede crear skills automaticamente desde conversaciones

# Manualmente
python skill_creator.py
```

### Estructura de un Skill

```markdown
---
name: my-skill
description: Que hace este skill
trigger: Cuando cargarlo
tags: [tag1, tag2]
---

# My Skill

## Pasos

1. Hacer X
2. Hacer Y
3. Verificar Z

## Pitfalls

- No hacer A porque B
```

---

## Proveedores LLM

Lilith soporta multiples proveedores a traves de `lilith-core/providers.py`:

| Proveedor | Modelos | Config |
|-----------|---------|--------|
| OpenAI | GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5 | `ANTHROPIC_API_KEY` |
| MiMo | MiMo-V2.5-Pro | `MIMO_API_KEY` |
| BytePlus | Seed 2.0, DeepSeek | `BYTEPLUS_API_KEY` |

### Configuracion

```bash
# En .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MIMO_API_KEY=tp-...
```

---

## Permisos del Agente

Los permisos estan definidos en `agent_permissions.json`:

```json
{
    "read_files": {
        "allowed": true,
        "scope": "Limited to Yggdrasil project files"
    },
    "run_commands": {
        "allowed": true,
        "scope": "Limited to project-related commands"
    },
    "access_web": {
        "allowed": true,
        "scope": "API calls only"
    }
}
```

---

## Uso del Chat

```bash
python lilith_cli.py chat
```

### Comandos Disponibles

| Comando | Descripcion |
|---------|-------------|
| `ayuda` | Mostrar ayuda |
| `resumen` | Resumen de la conversacion |
| `memoria` | Ver ultimas entradas de memoria |
| `borrar` | Borrar memoria |
| `salir` / `quit` | Terminar conversacion |

### Ejemplo de Sesion

```
$ python lilith_cli.py chat
╭───• Tu •───╮ ¿Como creo un nuevo realm?
Lilith: Para crear un nuevo realm, sigue estos pasos...

╭───• Tu •───╮ resumen
Lilith: Resumen: 5 mensajes, 1,234 tokens, 2 min...
```

---

## Servicios

| Servicio | Puerto | Descripcion |
|----------|--------|-------------|
| API Gateway | 8000 | REST API principal |
| Model Orchestrator | 8001 | Gestion de modelos LLM |
| Memory Service | 8002 | Servicio de memoria vectorial |

Para iniciar los servicios:

```bash
./start_services.sh
```

---

## Desarrollo

### Ejecutar Tests

```bash
pytest
# o
python ygg.py test
```

### Linting

```bash
ruff check .
ruff format .
```

### Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```
