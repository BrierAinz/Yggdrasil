# Council — Sistema Deliberativo Multi-Agente

> **Versión**: 1.0
> **Fecha**: 2026-03-21
> **Reino**: Vanaheim/Council/
> **Misión**: 2

---

## ¿Qué es el Council?

El Council es un sistema que permite a los agentes del Panteón **debatir y votar** decisiones arquitectónicas complejas. En lugar de que Lilith o el owner decidan solos, múltiples perspectivas especializadas evalúan opciones y generan un **ADR** (Architecture Decision Record) documentado.

### Participantes por defecto

| Agente | Especialidad | Peso mayor |
|--------|-------------|-----------|
| **Eva** | Análisis, documentación, research | research × 1.5 |
| **Adán** | Código, testing, refactor | code × 1.5 |
| **Odín** | Arquitectura, planificación, estrategia | architecture × 1.5 |
| **Archivero** | Documentación técnica, conocimiento histórico | documentation × 1.5 |

---

## Flujo de una Sesión

```
Owner/Planner
    ↓
Propuesta (título + contexto + pregunta + opciones)
    ↓
FASE 1: Análisis Individual
  Eva    → evalúa A y B desde su perspectiva
  Adán   → evalúa A y B desde su perspectiva
  Odín   → evalúa A y B desde su perspectiva
  Archivero → evalúa A y B desde su perspectiva
    ↓
FASE 2: Debate
  Detectar desacuerdos → cada agente argumenta su posición
    ↓
FASE 3: Votación Final
  Score ponderado por especialidad + confianza
    ↓
DECISIÓN + ADR generado en Vanaheim/Council/decisions/
```

---

## Cómo Activar

### 1. Via Discord

```
/council titulo:"¿FastAPI o Flask?" pregunta:"¿Cuál framework para la nueva API REST?"
```

El comando genera opciones A/B básicas. Para opciones detalladas, usa la API.

### 2. Via API REST

```http
POST http://localhost:8000/api/council/activate
Content-Type: application/json

{
  "title": "Selección de framework web",
  "context": "Necesitamos una API REST de alto rendimiento para el backend de Lilith.",
  "question": "¿Cuál framework se adapta mejor?",
  "options": [
    {
      "id": "A",
      "title": "FastAPI",
      "description": "Framework moderno asíncrono.",
      "pros": ["Alto rendimiento", "Tipado automático"],
      "cons": ["Ecosistema más joven"],
      "implications": ["Requiere Python 3.8+"]
    },
    {
      "id": "B",
      "title": "Flask",
      "description": "Framework maduro y minimalista.",
      "pros": ["Ecosistema amplio"],
      "cons": ["Sin async nativo"],
      "implications": ["Compatible con stack actual"]
    }
  ],
  "participants": ["eva", "odin"]
}
```

**Respuesta:**
```json
{
  "ok": true,
  "data": {
    "decision": "A",
    "participants": ["eva", "odin"],
    "consensus_reached": true,
    "session_file": "D:/...Vanaheim/Council/sessions/2026-03-21_143022_selección_de_framework_web.json",
    "adr_file": "D:/...Vanaheim/Council/decisions/ADR-001_selección_de_framework_web.md",
    "opinions_count": 4
  }
}
```

### 3. Via Planner (tool)

El planner puede invocar el Council automáticamente:

```
Tool: activate_council
Params:
  title: "Decisión sobre X"
  context: "..."
  question: "¿A o B?"
  options: [...]
```

---

## Opciones de Voto

| Valor | Nombre | Score |
|-------|--------|-------|
| ✅✅ | STRONGLY_FAVOR | +2 |
| ✅ | FAVOR | +1 |
| ➖ | NEUTRAL | 0 |
| ❌ | AGAINST | -1 |
| ❌❌ | STRONGLY_AGAINST | -2 |

El score final se calcula como: `voto × confianza × peso_especialidad`

---

## Archivos Generados

### Session JSON (`Vanaheim/Council/sessions/`)

Registro completo de la sesión incluyendo todas las opiniones individuales, el log de deliberación y la decisión final.

### ADR Markdown (`Vanaheim/Council/decisions/`)

Architecture Decision Record formato estándar. Incluye contexto, opciones con pros/cons, deliberación resumida y decisión con razones.

**Formato del nombre:** `ADR-001_nombre_de_la_propuesta.md`

### Votes JSONL (`Vanaheim/Council/voting_records/votes.jsonl`)

Una línea JSON por sesión. Permite análisis histórico de patrones de votación.

---

## Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/council/activate` | Inicia sesión de deliberación |
| GET | `/api/council/decisions` | Lista ADRs existentes |
| GET | `/api/council/sessions` | Estadísticas de sesiones |

---

## Arquitectura de Archivos

```
Core/Backend/core/council/
├── __init__.py              # Exports públicos
├── models.py                # VoteOption, AgentOpinion, CouncilProposal, CouncilSession
├── deliberation_engine.py   # Motor de 3 fases
└── session_recorder.py      # Persistencia en Vanaheim

Core/Backend/core/tools_v3/
└── council_tool.py          # ActivateCouncilTool (LilithTool)

Core/Backend/api/
└── council_api.py           # Router FastAPI /api/council/

Discord/commands/
└── council_command.py       # Slash command /council

Core/Tests/
└── test_council.py          # Suite de tests

Vanaheim/Council/
├── sessions/                # JSONs de sesiones
├── decisions/               # ADRs en Markdown
├── voting_records/          # votes.jsonl
└── templates/               # ADR template
```

---

## Extensión Futura

- **Pesos dinámicos por dominio**: el motor puede detectar el dominio de la pregunta y ajustar pesos automáticamente
- **Ronda de réplica**: agentes con posición STRONGLY_AGAINST pueden generar un contra-argumento estructurado
- **Integración MuninnDB**: guardar decisiones en vault "decisions" para consulta semántica
- **Dashboard en Asgard**: visualización de tendencias de votación y ADRs
