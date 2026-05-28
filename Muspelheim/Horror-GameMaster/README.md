# Horror GameMaster — Procedural Terror Engine

> **Estado:** Fase 0 — Concepto
> **Realm:** Muspelheim (WIP)
> **Creado:** 2026-05-27

## Concepto

Un LLM fine-tuned/embedded que actúa como **GameMaster de terror**.

### La Idea

1. **Prólogo** — Captura la personalidad del jugador mediante sus decisiones
2. **Análisis de patrones** — El LLM identifica miedos, comportamientos, y debilidades
3. **Generación procedural** — El juego se modifica en tiempo real para causar:
   - Incomodidad
   - Miedo
   - Misterio
   - Tensión psicológica

### Arquitectura

```
┌─────────────────────────────────────────────┐
│              HORROR GAMEMASTER               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │ Player   │───▶│ Pattern  │───▶│ LLM    ││
│  │ Actions  │    │ Analyzer │    │ Engine ││
│  └──────────┘    └──────────┘    └────────┘│
│       │                            │        │
│       │              ┌─────────────┘        │
│       ▼              ▼                      │
│  ┌──────────────────────────┐               │
│  │   Procedural Generator   │               │
│  │  ┌────────┐ ┌────────┐  │               │
│  │  │Events  │ │Scenes  │  │               │
│  │  └────────┘ └────────┘  │               │
│  │  ┌────────┐ ┌────────┐  │               │
│  │  │NPCs    │ │Items   │  │               │
│  │  └────────┘ └────────┘  │               │
│  └──────────────────────────┘               │
│                                             │
└─────────────────────────────────────────────┘
```

### Componentes

| Componente | Descripción | Estado |
|-----------|-------------|--------|
| Pattern Analyzer | Analiza acciones del jugador para detectar miedos | Pendiente |
| LLM Engine | Modelo fine-tuned para narrativa de terror | Pendiente |
| Procedural Generator | Genera eventos, escenas, NPCs basados en patrones | Pendiente |
| Personality Profiler | Crea perfil psicológico del jugador | Pendiente |
| Tension Manager | Controla ritmo y intensidad del terror | Pendiente |

### Stack

- **LLM:** Modelo local (Ollama/LM Studio) fine-tuned con dataset de terror
- **Embeddings:** nomic-embed-text para memoria semántica
- **Framework:** Python + FastAPI
- **Frontend:** Terminal-based o Web (por definir)

### Dataset Necesario

- Narrativa de terror psicológico
- Patrones de miedo comunes
- Escenarios procedurales
- Dialogos de NPCs de terror
- Eventos trigger por patrón de jugador

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
