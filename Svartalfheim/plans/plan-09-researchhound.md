# ResearchHound — Agente de Investigación Autónomo

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Le das un tema, busca arxiv, papers, blogs, foros, y genera un briefing estructurado: estado del arte, actores clave, gaps, oportunidades. Con memoria entre sesiones.

**Architecture:** Topic input → search strategy → multi-source search (arxiv, semantic scholar, web) → paper download/parsing → synthesis engine → structured briefing → SQLite memory. CLI-first.

**Tech Stack:** Python 3.11+, httpx (async), arxiv.py, semantic-scholar API, BeautifulSoup4, PyPDF2, Lilith (LLM), SQLite, Typer, Rich.

**Realm:** Vanaheim/ResearchHound/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Vanaheim/ResearchHound/pyproject.toml`
- Create: `Vanaheim/ResearchHound/researchhound/__init__.py`
- Create: `Vanaheim/ResearchHound/researchhound/cli.py`
- Create: `Vanaheim/ResearchHound/tests/__init__.py`

```toml
[project]
name = "researchhound"
version = "0.1.0"
description = "Autonomous research agent with cross-session memory"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.25",
    "arxiv>=2.1",
    "beautifulsoup4>=4.12",
    "PyPDF2>=3.0",
    "rich>=13.0",
    "typer>=0.9",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "pytest-cov"]
lilith = ["lilith-core>=4.0"]

[project.scripts]
researchhound = "researchhound.cli:app"
```

**Commit:** `feat(researchhound): scaffold project`

---

## Task 2: Modelo de datos y SQLite

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/models.py`
- Create: `Vanaheim/ResearchHound/researchhound/db.py`
- Create: `Vanaheim/ResearchHound/tests/test_db.py`

```python
@dataclass
class Paper:
    id: int | None
    title: str
    authors: list[str]
    abstract: str
    url: str
    source: str  # arxiv, semantic_scholar, web
    published: date | None
    citation_count: int = 0
    relevance_score: float = 0.0
    topics: list[str] = field(default_factory=list)

@dataclass
class ResearchSession:
    id: int | None
    topic: str
    query: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    papers: list[Paper] = field(default_factory=list)
    briefing: str = ""
    status: str = "pending"  # pending, searching, analyzing, complete

@dataclass
class Briefing:
    topic: str
    state_of_art: str
    key_actors: list[str]
    gaps: list[str]
    opportunities: list[str]
    references: list[Paper]
    generated_at: datetime
```

SQLite tablas: `papers`, `sessions`, `briefings`, `topics` (para memoria cross-session).

**Commit:** `feat(researchhound): data models and SQLite`

---

## Task 3: Arxiv collector

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/collectors/arxiv.py`
- Create: `Vanaheim/ResearchHound/tests/test_arxiv.py`

```python
class ArxivCollector:
    async def search(self, query: str, max_results: int = 20) -> list[Paper]:
        """Search arxiv for papers matching query."""
        ...

    async def download_pdf(self, paper: Paper, output_dir: str) -> str:
        """Download paper PDF."""
        ...
```

Usa arxiv.py library para búsqueda y descarga. Filtra por fecha, relevancia, y citation count.

**Commit:** `feat(researchhound): arxiv collector`

---

## Task 4: Semantic Scholar collector

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/collectors/semantic_scholar.py`

API de Semantic Scholar para: búsqueda por keyword, paper details, citations, references, influential citations.

**Commit:** `feat(researchhound): Semantic Scholar collector`

---

## Task 5: Web/blog collector

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/collectors/web.py`

Scraping de blogs técnicos, Medium, Dev.to, Hacker News. httpx + BS4. Extrae título, autor, fecha, contenido clave.

**Commit:** `feat(researchhound): web/blog collector`

---

## Task 6: Search strategy engine

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/strategy.py`

Dado un tema, genera estrategia de búsqueda:
1. Keywords primarios y secundarios
2. Queries por fuente
3. Filtros (fecha, idioma, tipo)
4. Prioridad de fuentes

```python
class SearchStrategy:
    def generate(self, topic: str, depth: str = "standard") -> SearchPlan:
        """Generate search plan for a topic."""
        ...

    def refine(self, initial_results: list[Paper]) -> SearchPlan:
        """Refine strategy based on initial results."""
        ...
```

**Commit:** `feat(researchhound): search strategy engine`

---

## Task 7: PDF parsing y analysis

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/parser.py`

```python
class PaperParser:
    def parse_pdf(self, path: str) -> PaperContent:
        """Extract text, figures, references from PDF."""
        ...

    def extract_key_points(self, content: PaperContent) -> list[KeyPoint]:
        """Extract key contributions, methods, results."""
        ...

    def extract_references(self, content: PaperContent) -> list[str]:
        """Extract reference list from paper."""
        ...
```

**Commit:** `feat(researchhound): PDF parsing and analysis`

---

## Task 8: LLM-powered synthesis

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/synthesizer.py`

Usa Lilith (o LLM local) para generar el briefing estructurado:
- State of the art summary
- Key actors and their contributions
- Gaps in current research
- Opportunities for future work
- Connections to previous sessions (cross-memory)

```python
class BriefingSynthesizer:
    def synthesize(self, papers: list[Paper], topic: str, previous_sessions: list[Briefing] = None) -> Briefing:
        """Generate structured briefing from research results."""
        ...
```

**Commit:** `feat(researchhound): LLM briefing synthesis`

---

## Task 9: Cross-session memory

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/memory.py`

Memoria entre sesiones: topics previos, papers ya vistos, preferencias de usuario, conexiones temáticas.

```python
class ResearchMemory:
    def save_session(self, session: ResearchSession) -> None:
        ...

    def recall_related(self, topic: str) -> list[Briefing]:
        """Find previous briefings related to this topic."""
        ...

    def is_duplicate(self, paper: Paper) -> bool:
        """Check if paper was already analyzed."""
        ...
```

**Commit:** `feat(researchhound): cross-session memory`

---

## Task 10: CLI completa

**Files:**
- Modify: `Vanaheim/ResearchHound/researchhound/cli.py`

```bash
researchhound search "transformer attention mechanisms"    # full research
researchhound search "RLHF" --depth deep --max 50         # deep search
researchhound search "GNN" --sources arxiv,scholar        # specific sources
researchhound brief <session_id>                           # view briefing
researchhound history                                      # list past sessions
researchhound related "attention"                           # find related past research
researchhound export <session_id> --format markdown        # export briefing
```

**Commit:** `feat(researchhound): complete CLI`

---

## Task 11: Report generation (Markdown, HTML)

**Files:**
- Create: `Vanaheim/ResearchHound/researchhound/report.py`

Genera briefing en Markdown (con citations) y HTML (dark theme Yggdrasil). Formato académico con abstract, sections, references.

**Commit:** `feat(researchhound): report generation`

---

## Task 12: Tests + CI

**Commit:** `ci(researchhound): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Arxiv | arxiv.py |
| Academic search | Semantic Scholar API |
| Web search | httpx + BS4 |
| PDF parsing | PyPDF2 |
| LLM synthesis | Lilith (local) |
| Storage | SQLite |
| CLI | Typer + Rich |
| Memory | SQLite cross-session |
