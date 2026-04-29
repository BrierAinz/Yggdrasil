# Memoria Episódica Enriquecida + Indexación por Temas

> **Versión:** 1.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/MEMORIA_EPISODICA_INDEXADA.md`  
> **Estado:** final

---

## 1. Visión General

Sistema de memoria episódica extendida con metadatos (proyecto, outcome, tags emocionales) e indexación temática para búsquedas semánticas más precisas.

### 1.1 Motivación

| Problema Anterior | Solución Implementada |
|-------------------|----------------------|
| Episodios planos (solo texto + timestamp) | Episodios enriquecidos con contexto completo |
| Búsquedas generales sin filtros | Consultas filtradas por proyecto/outcome/tema |
| Sin tracking de resultados | Outcome tracking (success/failure/partial) |
| Tags manuales | Auto-tagging con detección de proyecto |

### 1.2 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPISODIOS ENRIQUECIDOS                        │
├─────────────────────────────────────────────────────────────────┤
│ Episode                                                          │
│  ├── timestamp, summary, source                                  │
│  ├── project_id: "lilith" | "nazarick" | "personal"              │
│  ├── outcome: "success" | "failure" | "partial"                  │
│  ├── tags: ["refactor", "bug_fix", "deployment"]                 │
│  ├── emotional_tag: "frustrating" | "successful" | "exciting"   │
│  └── context_snapshot: {...}                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INDEXACIÓN POR TEMAS                          │
├─────────────────────────────────────────────────────────────────┤
│ Taxonomía:                                                       │
│   ├── codigo (backend, frontend, testing)                        │
│   ├── discord (commands, handlers, roles)                        │
│   ├── documentacion (arquitectura, API, usuario)                 │
│   ├── infraestructura (muninn, scheduler, backups)               │
│   ├── memoria (episodica, semantica, cognitiva)                  │
│   └── proyecto, configuracion                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Componentes

### 2.1 EpisodicStore

**Ubicación:** `Core/Backend/core/episodic_store.py`

Almacén de episodios enriquecidos en formato JSONL.

#### 2.1.1 Schema de Episode

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `timestamp` | str | ISO 8601 UTC |
| `summary` | str | Descripción del episodio |
| `project_id` | str | Proyecto asociado |
| `outcome` | str | "success" \| "failure" \| "partial" |
| `tags` | List[str] | Tags automáticos |
| `source` | str | Origen (investiga, chat, etc.) |
| `emotional_tag` | str | Tag emocional opcional |
| `context_snapshot` | dict | Estado relevante del momento |
| `tool_used` | str | Tool utilizada |
| `user_id` | str | Usuario asociado |
| `id` | str | UUID único |

#### 2.1.2 Uso Básico

```python
from Backend.core.episodic_store import EpisodicStore, Episode
from datetime import datetime, timezone

store = EpisodicStore(base_path)

# Crear episodio
episode = Episode(
    timestamp=datetime.now(timezone.utc).isoformat(),
    summary="Refactor del sistema de memoria",
    project_id="lilith",
    outcome="success",
    tags=["refactor", "optimization"],
    source="investiga",
    emotional_tag="successful",
    context_snapshot={"files_changed": 5},
    tool_used="delegate_eva"
)

# Guardar
store.append(episode)
```

#### 2.1.3 Consultas Avanzadas

```python
# Por outcome
failures = store.query_by_outcome(
    outcome="failure",
    project_id="lilith",
    limit=5
)

# Timeline de proyecto
episodes = store.query_by_project(
    project_id="lilith",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Estadísticas
stats = store.get_stats_by_project("lilith")
# Retorna: total, outcomes, success_rate, emotional_breakdown, top_tags
```

---

### 2.2 EpisodeTagger

**Ubicación:** `Core/Backend/core/episode_tagger.py`

Sistema de auto-tagging para enriquecimiento automático de episodios.

#### 2.2.1 Capabilities

| Función | Descripción | Accuracy |
|---------|-------------|----------|
| `auto_tag()` | Detecta tags desde contenido | ~80% |
| `detect_project()` | Identifica proyecto por patterns | ~90% |
| `detect_outcome()` | Determina success/failure/partial | ~85% |
| `suggest_emotional_tag()` | Sugiere tag emocional | Heurístico |

#### 2.2.2 Tags Automáticos

| Tag | Patrones Detectados |
|-----|---------------------|
| `refactor` | "refactor", "reestructura", "limpiar código" |
| `bug_fix` | "bug", "error", "fix", "arregla", "debug" |
| `deployment` | "deploy", "despliegue", "release", "prod" |
| `documentation` | "docs", "README", "documentación" |
| `testing` | "test", "prueba", "spec", "cobertura" |
| `optimization` | "optimiza", "performance", "mejora" |
| `security` | "seguridad", "vulnerabilidad", "auth" |
| `api_change` | "api", "endpoint", "route", "schema" |
| `database` | "database", "db", "sql", "migration" |
| `ui_ux` | "ui", "ux", "interfaz", "diseño", "frontend" |

#### 2.2.3 Uso

```python
from Backend.core.episode_tagger import auto_tag_episode

content = "Refactor del Core/Backend para usar async/await"
tool_result = {"returncode": 0}

enriched = auto_tag_episode(content, tool_result)

# Resultado:
# {
#     "project_id": "lilith",
#     "outcome": "success",
#     "tags": ["refactor", "optimization"],
#     "emotional_tag": "successful"
# }
```

---

### 2.3 TopicClassifier

**Ubicación:** `Core/Backend/core/topic_classifier.py`

Clasificador de contenido por temas usando taxonomía definida.

#### 2.3.1 Taxonomía de Temas

| Tema | Subtopics | Keywords Principales |
|------|-----------|---------------------|
| `codigo` | backend, frontend, testing | refactor, bug, function, class |
| `discord` | commands, handlers, roles | discord, bot, slash, embed |
| `documentacion` | arquitectura, API, usuario | docs, README, guía, manual |
| `infraestructura` | muninn, scheduler, backups | deploy, server, database |
| `memoria` | episodica, semantica, cognitiva | memoria, episodios, facts |
| `proyecto` | planificacion, ejecucion | roadmap, milestone, tarea |
| `configuracion` | environment, dependencies | config, env, requirements |

#### 2.3.2 Uso

```python
from Backend.core.topic_classifier import classify_content, classify_with_confidence

# Clasificación simple
topics = classify_content("Implementé slash commands para Discord")
# Resultado: ["discord", "codigo"]

# Con scores de confianza
results = classify_with_confidence("Documenté la API en el README")
# Resultado: [
#     {"topic_id": "documentacion", "confidence": 0.95, "name": "Documentación"},
#     ...
# ]
```

---

### 2.4 RetrospectiveGenerator

**Ubicación:** `Core/Backend/core/retrospective_generator.py`

Genera retrospectivas automáticas basadas en episodios del proyecto.

#### 2.4.1 Períodos Soportados

| Período | Descripción |
|---------|-------------|
| `last_day` | Últimas 24 horas |
| `last_week` | Última semana |
| `last_2_weeks` | Últimas 2 semanas |
| `last_month` | Último mes |
| `last_3_months` | Último trimestre |

#### 2.4.2 Uso

```python
from Backend.core.retrospective_generator import generate_retrospective

retro = generate_retrospective("lilith", period="last_week")

# Contenido:
# {
#     "project_id": "lilith",
#     "period": "last_week",
#     "total_episodes": 25,
#     "stats": {
#         "success_rate": 76.0,
#         "outcomes": {"success": 19, "failure": 3, "partial": 3},
#         "most_common_tags": [["refactor", 8], ["bug_fix", 5]],
#         "emotional_breakdown": {"successful": 15, "frustrating": 5}
#     },
#     "insights": [
#         "🟢 Excelente tasa de éxito: 76%",
#         "🏷️ Tags más frecuentes: refactor, bug_fix",
#         "😤 Alta frustación detectada (5 episodios)"
#     ],
#     "recommendations": [
#         "Considerar revisar procesos de desarrollo",
#         "Incrementar tiempo dedicado a testing"
#     ]
# }
```

---

## 3. Configuración

### 3.1 episodic.json

**Ubicación:** `Core/Config/episodic.json`

```json
{
  "enrichment": {
    "auto_tag_enabled": true,
    "auto_detect_project": true,
    "auto_detect_outcome": true,
    "emotional_tagging": "manual"
  },
  "projects": {
    "lilith": {
      "name": "Lilith Core",
      "patterns": ["Core/", "Discord/", "Backend/"],
      "keywords": ["lilith", "bot", "agente"]
    }
  },
  "tags": {
    "auto_tags": [
      "refactor", "bug_fix", "deployment", "documentation",
      "testing", "optimization", "security", "api_change"
    ]
  },
  "retention": {
    "max_episodes": 5000,
    "retention_days": 90
  }
}
```

### 3.2 memory_topics.json

**Ubicación:** `Core/Config/memory_topics.json`

Define la taxonomía completa de temas para clasificación.

---

## 4. Comandos Discord

### 4.1 /episodios

Lista episodios recientes con filtros.

```
/episodios [proyecto:lilith] [outcome:success] [limite:5]
```

### 4.2 /episode_tag

Etiqueta episodio con tag emocional.

```
/episode_tag episodio_id:<timestamp> tag_emocional:Exitoso
```

**Opciones de tag_emocional:**
- 😤 Frustrante
- ✨ Exitoso  
- 📋 Rutinario
- 🎉 Emocionante

### 4.3 /retrospectiva

Genera retrospectiva del proyecto.

```
/retrospectiva proyecto:lilith periodo:"Última semana"
```

### 4.4 /stats_proyecto

Muestra estadísticas del proyecto.

```
/stats_proyecto proyecto:lilith
```

### 4.5 /memoria_por_tema

Busca en memoria filtrando por tema.

```
/memoria_por_tema query:"cómo crear comandos" tema:Discord
```

**Temas disponibles:**
- Código
- Discord
- Documentación
- Infraestructura
- Memoria
- Proyecto

---

## 5. Flujo de Uso Completo

```python
# 1. Crear episodio con auto-tagging
from Backend.core.episodic_store import EpisodicStore, Episode
from Backend.core.episode_tagger import auto_tag_episode
from datetime import datetime, timezone

store = EpisodicStore(base_path)

content = "Refactor del Core/Backend para usar async/await"
enriched = auto_tag_episode(content, tool_result={"returncode": 0})

episode = Episode(
    timestamp=datetime.now(timezone.utc).isoformat(),
    summary=content,
    **enriched  # project_id, outcome, tags, emotional_tag
)
store.append(episode)

# 2. Clasificar para indexación temática
from Backend.core.topic_classifier import classify_content

topics = classify_content(content)
# topics = ["codigo", "backend"]

# 3. Guardar en memoria semántica con topics
from Backend.core.memory_store import SemanticMemory, MemoryStore

mem = SemanticMemory(
    domain="codigo",
    entity="refactor",
    fact=content,
    topics=topics  # Indexado por temas
)

memory_store = MemoryStore()
memory_store.upsert_memory(mem)

# 4. Buscar por tema
results = memory_store.search_by_topic(
    query="async await",
    topics=["codigo"],
    k=5
)

# 5. Generar retrospectiva
from Backend.core.retrospective_generator import generate_retrospective

retro = generate_retrospective("lilith", "last_week")
print(f"Tasa de éxito: {retro['stats']['success_rate']}%")
```

---

## 6. Testing

```bash
# Tests de episodios enriquecidos
pytest Core/Tests/test_episodic_enriched.py -v

# Tests de indexación por temas  
pytest Core/Tests/test_topic_indexing.py -v
```

**Cobertura:** 26 tests
- EpisodicStore: 5 tests
- EpisodeTagger: 7 tests
- TopicClassifier: 13 tests
- Integración: 1 test

---

## 7. Referencias

| Documento | Descripción |
|-----------|-------------|
| `03_SISTEMA_MEMORIA.md` | Documentación principal del sistema de memoria |
| `REGLAS_DOCUMENTACION.md` | Reglas de documentación del proyecto |
| `Core/Config/episodic.json` | Configuración de episodios |
| `Core/Config/memory_topics.json` | Taxonomía de temas |

---

*Documentación del sistema de memoria episódica enriquecida - Lilith v4.2*
