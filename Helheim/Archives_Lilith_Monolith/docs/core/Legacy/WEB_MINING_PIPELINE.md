# 11 - Pipeline de Minería Web

> **Versión:** 4.2  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Backend/core/web_mining*.py`

---

## 11.1 Visión General

El Pipeline de Minería Web es un sistema automatizado de extracción, limpieza, validación y estructuración de datos desde la web hacia la memoria semántica de Lilith.

### 11.1.1 Arquitectura del Pipeline

```
URL → WebScraperAgent → ContentCleanerAgent → QualityFilterAgent → 
DataStructurerAgent → MemoryStore

     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
     │   Scraper    │───▶│   Cleaner    │───▶│   Filter     │
     │  (Extrae)    │    │   (Limpia)   │    │  (Valida)    │
     └──────────────┘    └──────────────┘    └──────────────┘
                                                    │
     ┌──────────────┐    ┌──────────────┐         │
     │   Memory     │◀───│  Structurer  │◀────────┘
     │   (Almacena) │    │ (Estructura) │
     └──────────────┘    └──────────────┘
```

### 11.1.2 Componentes Principales

| Componente | Archivo | Función |
|------------|---------|---------|
| **Modelos** | `web_mining_models.py` | Dataclasses: ScrapedContent, CleanedContent, QualityScore, etc. |
| **WebScraperAgent** | `web_scraper_agent.py` | Extracción de contenido web |
| **ContentCleanerAgent** | `content_cleaner_agent.py` | Limpieza y normalización |
| **QualityFilterAgent** | `quality_filter_agent.py` | Scoring y filtrado de calidad |
| **DataStructurerAgent** | `data_structurer_agent.py` | Extracción de entidades y estructuración |
| **Orchestrator** | `web_mining_orchestrator.py` | Orquestación del pipeline |
| **SourceMonitor** | `source_monitor.py` | Monitoreo automático de fuentes |

---

## 11.2 Flujo de Datos

### 11.2.1 Modelos de Datos

#### ScrapedContent
```python
@dataclass
class ScrapedContent:
    url: str
    raw_html: str
    text: str
    metadata: Dict[str, Any]
    strategy: ScrapingStrategy
    timestamp: float
```

#### CleanedContent
```python
@dataclass
class CleanedContent:
    url: str
    cleaned_text: str
    original_length: int
    cleaned_length: int
    content_hash: str  # Para detección de duplicados
    metadata: Dict[str, Any]
```

#### QualityScore
```python
@dataclass
class QualityScore:
    score: float  # 0.0 - 1.0
    reasons: List[str]
    details: Dict[str, Any]
    is_accepted: bool
```

#### SemanticFact
```python
@dataclass
class SemanticFact:
    content: str
    source: str
    category: str
    topics: List[str]
    entities: List[str]
    metadata: Dict[str, Any]
```

### 11.2.2 Estrategias de Scraping

| Estrategia | Descripción | Cuándo usar |
|------------|-------------|-------------|
| `full_page` | HTML completo | Fuentes desconocidas o genéricas |
| `article_only` | Solo contenido principal | Blogs, documentación, noticias |
| `structured_data` | JSON-LD, microdata | Sitios con datos estructurados |

---

## 11.3 Uso del Pipeline

### 11.3.1 Minería de URL Individual

```python
from Backend.core.web_mining_orchestrator import WebMiningOrchestrator
from Backend.core.web_mining_models import ScrapingStrategy

# Crear orquestador
orchestrator = WebMiningOrchestrator(base_path=Path("/path/to/lilith"))

# Minar una URL (async)
result = await orchestrator.mine(
    url="https://docs.python.org",
    strategy=ScrapingStrategy.ARTICLE_ONLY,
    store_in_memory=True,
)

if result.success:
    print(f"Generados {len(result.facts)} facts")
    print(f"Calidad: {result.quality_score.score}")
else:
    print(f"Error: {result.error}")
```

### 11.3.2 Batch Mining

```python
# Minar múltiples URLs
urls = [
    "https://docs.python.org",
    "https://react.dev",
    "https://github.com/readme",
]

batch_result = await orchestrator.mine_batch(
    urls=urls,
    delay_seconds=2,  # Rate limiting
    store_in_memory=True,
)

print(f"Total: {batch_result.total}")
print(f"Éxitos: {batch_result.success}")
print(f"Rechazados: {batch_result.rejected}")
print(f"Facts generados: {batch_result.facts_generated}")
```

### 11.3.3 Uso Síncrono

```python
# Para scripts o cuando no se puede usar async
result = orchestrator.mine_sync("https://docs.python.org")
```

### 11.3.4 Callbacks de Progreso

```python
def progress_callback(stage: str, data: Any):
    print(f"[{stage}] {data}")

result = await orchestrator.mine(
    url="https://example.com",
    progress_callback=progress_callback,
)
```

Los stages son: `started`, `scraping`, `scraped`, `cleaning`, `cleaned`, `filtering`, `filtered`, `structuring`, `structured`, `storing`, `stored`, `completed`.

---

## 11.4 Agentes Individuales

### 11.4.1 WebScraperAgent

```python
from Backend.core.web_scraper_agent import WebScraperAgent

agent = WebScraperAgent(base_path)

# Scrapear con parámetros
result = await agent.scrape({
    "url": "https://example.com",
    "strategy": "article_only",
})

scraped_content = result["scraped_content"]
```

### 11.4.2 ContentCleanerAgent

```python
from Backend.core.content_cleaner_agent import ContentCleanerAgent

agent = ContentCleanerAgent(base_path)

# Limpiar contenido scrapeado
cleaned = agent.clean_scraped(scraped_content)

# Detectar duplicados
is_dup, similarity = agent.detect_duplicate(cleaned)
```

### 11.4.3 QualityFilterAgent

```python
from Backend.core.quality_filter_agent import QualityFilterAgent

agent = QualityFilterAgent(base_path)

# Evaluar calidad
quality = agent.assess_quality(cleaned_content)

if quality.is_accepted:
    print(f"Score: {quality.score}")
    print(f"Razones: {quality.reasons}")
```

### 11.4.4 DataStructurerAgent

```python
from Backend.core.data_structurer_agent import DataStructurerAgent

agent = DataStructurerAgent(base_path)

# Estructurar contenido
structured = agent.structure(cleaned_content)

# Generar facts
facts = agent.to_semantic_facts(structured)

# Almacenar en memoria
stored_count = agent.store_facts(facts, memory_store=store)
```

---

## 11.5 Monitoreo de Fuentes

### 11.5.1 Configuración

```json
// Config/source_monitors.json
[
  {
    "id": "python_releases",
    "enabled": true,
    "url": "https://www.python.org/downloads/",
    "interval_hours": 12,
    "strategy": "structured_data",
    "quality_threshold": 0.7,
    "auto_mine": true,
    "store_fact": true,
    "tags": ["python", "releases"]
  }
]
```

### 11.5.2 Uso del SourceMonitor

```python
from Backend.core.source_monitor import SourceMonitorPipeline

# Crear pipeline de monitoreo
monitor = SourceMonitorPipeline(base_path)

# Verificar una fuente
result = await monitor.check_source(monitor_config)

if result.changed:
    print(f"Cambios detectados: {result.facts_generated} facts generados")

# Verificar todas las fuentes configuradas
results = await monitor.check_all()

# Ejecutar en loop continuo (background)
await monitor.run_scheduled()
```

### 11.5.3 Callbacks

```python
def on_change(change_data):
    print(f"Cambio detectado: {change_data}")

def on_mining_complete(result):
    print(f"Minería completada: {result.facts_generated} facts")

monitor.set_callbacks(
    on_change=on_change,
    on_mining_complete=on_mining_complete,
)
```

---

## 11.6 Configuración

### 11.6.1 web_sources.json

```json
{
  "allowed_domains": [],  // Vacío = permitir todos
  "timeout_seconds": 15,
  "max_chars": 80000,
  "rate_limits": {
    "default_delay_seconds": 2,
    "per_domain": {
      "github.com": 1,
      "stackoverflow.com": 1
    }
  },
  "strategies": {
    "high_quality_sources": "article_only",
    "documentation_sites": "structured_data",
    "general": "full_page"
  }
}
```

### 11.6.2 quality_filter.json

```json
{
  "min_score": 0.35,
  "quality_threshold": 0.6,
  "min_length": 100,
  "ideal_min_length": 500,
  "bypass_deterministic": true,
  "bypass_markdown_code": true,
  "high_quality_sources": [
    "wikipedia.org",
    "github.com",
    "stackoverflow.com"
  ],
  "scoring_weights": {
    "length": 0.30,
    "density": 0.35,
    "readability": 0.15,
    "source_quality": 0.20
  }
}
```

### 11.6.3 content_cleaner.json

```json
{
  "remove_patterns": {
    "ads": ["class='ad'", "sponsored"],
    "navigation": ["<nav", "<header", "<footer"],
    "social": ["share-button", "social-media"]
  },
  "min_content_length": 100,
  "max_content_length": 50000,
  "similarity_threshold": 0.9
}
```

### 11.6.4 data_structurer.json

```json
{
  "max_summary_chars": 400,
  "max_entities": 25,
  "max_relations": 15,
  "max_keywords": 10,
  "generate_facts": {
    "summary": true,
    "entities": true,
    "relations": true
  }
}
```

---

## 11.7 Clasificación de Fuentes

### 11.7.1 Fuentes de Alta Calidad

- `wikipedia.org`
- `github.com`
- `stackoverflow.com`
- `docs.python.org`
- `developer.mozilla.org`
- `docs.microsoft.com`
- `kubernetes.io`
- `postgresql.org`

### 11.7.2 Fuentes de Calidad Media

- `medium.com`
- `dev.to`
- `hashnode.com`
- `freecodecamp.org`

### 11.7.3 Uso Programático

```python
from Backend.core.web_mining_models import classify_source_quality

quality = classify_source_quality("https://github.com/repo")
# Retorna: "high", "medium", "low", o "unknown"

# En el orquestador
classified = orchestrator.classify_urls(url_list)
# Retorna: {"high": [...], "medium": [...], "low": [...], "unknown": [...]}
```

---

## 11.8 Testing

### 11.8.1 Ejecutar Tests

```bash
# Desde Lilith/Core/
pytest Tests/test_web_mining.py -v

# Tests específicos
pytest Tests/test_web_mining.py::TestWebMiningModels -v
pytest Tests/test_web_mining.py::TestContentCleaner -v
pytest Tests/test_web_mining.py::TestQualityFilter -v
pytest Tests/test_web_mining.py::TestDataStructurer -v
```

### 11.8.2 Cobertura

Los tests cubren:
- Modelos de datos
- Clasificación de fuentes
- Limpieza de contenido
- Scoring de calidad
- Extracción de entidades
- Pipeline completo (con mocks)

---

## 11.9 Troubleshooting

### 11.9.1 Problemas Comunes

**Contenido rechazado por baja calidad**
```
[QualityFilter] Rejected: score 0.4 < threshold 0.6
```
- Verificar `quality_filter.json`
- Ajustar `quality_threshold` o `min_length`

**Timeout en scraping**
```
[WebScraper] Failed to scrape (timeout)
```
- Aumentar `timeout_seconds` en `web_sources.json`
- Verificar conectividad

**Duplicados detectados**
```
[ContentCleaner] Duplicate detected, skipping
```
- Limpiar cache de hashes si es necesario
- Ajustar `similarity_threshold`

### 11.9.2 Logs

El pipeline genera logs detallados:
```
[WebMining] Starting pipeline for: https://example.com
[WebMining] Scraped: 5000 chars
[WebMining] Cleaned: 5000 → 3000 chars (40.0% reduction)
[WebMining] Quality accepted: score 0.75
[WebMining] Structured: 5 entities, 3 relations
[WebMining] Stored 3 facts in memory
```

---

## 11.10 Referencias

- `02_BACKEND_API_ORQUESTADOR.md` - Backend y orquestación
- `03_SISTEMA_MEMORIA.md` - Sistema de memoria
- `05_PANTEON_AGENTES.md` - El Panteón multi-agente
- `VISION_MINERIA_REFINERIA_WEB.md` - Visión completa (Legacy)

---

*Documento 11 del índice de documentación de Lilith v4.2*
