# TrendRadar — Monitor de Tendencias Multi-Plataforma

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Scraping periódico de TikTok, Twitter/X, Reddit trending, Google Trends. Genera reportes con scoring de "ventana de oportunidad".

**Architecture:** Scheduler que ejecuta collectors periódicamente → normaliza datos → scoring → almacenamiento SQLite → reportes CLI/HTML. Daemon mode con Typer.

**Tech Stack:** Python 3.11+, httpx (async scraping), BeautifulSoup4, SQLite, Rich, Typer, APScheduler, matplotlib/plotext.

**Realm:** Muspelheim/TrendRadar/

---

## Task 1: Scaffold del proyecto

**Objective:** Estructura base con pyproject.toml y módulos.

**Files:**
- Create: `Muspelheim/TrendRadar/pyproject.toml`
- Create: `Muspelheim/TrendRadar/trendradar/__init__.py`
- Create: `Muspelheim/TrendRadar/trendradar/cli.py`
- Create: `Muspelheim/TrendRadar/trendradar/collectors/__init__.py`
- Create: `Muspelheim/TrendRadar/tests/__init__.py`

```toml
[project]
name = "trendradar"
version = "0.1.0"
description = "Multi-platform trend monitor with opportunity scoring"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.25",
    "beautifulsoup4>=4.12",
    "rich>=13.0",
    "typer>=0.9",
    "apscheduler>=3.10",
    "plotext>=5.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "pytest-cov"]

[project.scripts]
trendradar = "trendradar.cli:app"
```

**Commit:** `feat(trendradar): scaffold project`

---

## Task 2: Modelo de datos y SQLite

**Objective:** Esquema de DB para trends, snapshots, y scoring.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/models.py`
- Create: `Muspelheim/TrendRadar/trendradar/db.py`
- Create: `Muspelheim/TrendRadar/tests/test_db.py`

```python
# trendradar/models.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Trend:
    id: int | None = None
    keyword: str = ""
    platform: str = ""  # reddit, tiktok, twitter, google
    score: float = 0.0
    volume: int = 0
    velocity: float = 0.0  # rate of change
    source_url: str = ""
    metadata: dict = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class TrendSnapshot:
    id: int | None = None
    trend_id: int = 0
    score: float = 0.0
    volume: int = 0
    captured_at: datetime = field(default_factory=datetime.utcnow)
```

SQLite con tablas: `trends`, `snapshots`, `reports`. Índices en keyword + platform + captured_at.

**Commit:** `feat(trendradar): data models and SQLite storage`

---

## Task 3: Collector — Reddit

**Objective:** Scraper de Reddit trending (r/all, r/popular, subreddits configurables).

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/collectors/reddit.py`
- Create: `Muspelheim/TrendRadar/tests/test_reddit_collector.py`

Usa httpx + BeautifulSoup para scraping (sin API oficial para evitar rate limits). Extrae: título, upvotes, comentarios, subreddit, trending status.

```python
class RedditCollector:
    async def collect(self, subreddits: list[str] = None) -> list[Trend]:
        """Collect trending posts from Reddit."""
        ...
```

**Commit:** `feat(trendradar): Reddit collector`

---

## Task 4: Collector — Google Trends

**Objective:** Scraping de Google Trends daily/hourly.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/collectors/google.py`

Usa httpx para `trends.google.com/trending/rss` y parsing XML/JSON.

**Commit:** `feat(trendradar): Google Trends collector`

---

## Task 5: Collector — Twitter/X

**Objective:** Collect trends de Twitter/X trending topics.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/collectors/twitter.py`

Usa Nitter instances (públicas) como proxy para evitar auth. Fallback a scraping directo.

**Commit:** `feat(trendradar): Twitter/X collector`

---

## Task 6: Collector — TikTok

**Objective:** Collect trending hashtags y videos de TikTok.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/collectors/tiktok.py`

Scraping de la página trending de TikTok con httpx + BS4. Extrae hashtag, views, categoría.

**Commit:** `feat(trendradar): TikTok collector`

---

## Task 7: Scoring y "Opportunity Window"

**Objective:** Algoritmo que puntúa trends con scoring de ventana de oportunidad.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/scorer.py`
- Create: `Muspelheim/TrendRadar/tests/test_scorer.py`

Factores de scoring:
- **Velocidad**: qué tan rápido está creciendo (Δscore/Δtime)
- **Volumen**: alcance actual
- **Novedad**: qué tan nuevo es el trend
- **Cruzado**: aparece en múltiples plataformas = mejor score
- **Decaimiento**: penalizar trends que ya están decayendo

Opportunity Window = momento óptimo para subirse al trend, estimado con derivada del score.

```python
class OpportunityScorer:
    def score(self, trends: list[Trend], history: list[TrendSnapshot]) -> list[ScoredTrend]:
        ...

    def opportunity_window(self, trend: Trend, history: list[TrendSnapshot]) -> WindowEstimate:
        """Estimate when to act on this trend."""
        ...
```

**Commit:** `feat(trendradar): opportunity scoring algorithm`

---

## Task 8: Scheduler periódico

**Objective:** Daemon que ejecuta collectors en intervalos configurables.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/scheduler.py`

```python
@app.command()
def daemon(
    interval: int = typer.Option(60, "--interval", "-i", help="Minutes between collections"),
    platforms: list[str] = typer.Option(["reddit", "google", "twitter", "tiktok"], "--platforms", "-p"),
):
    """Run TrendRadar as a daemon collecting periodically."""
    ...
```

APScheduler con interval configurable. Cada collector corre secuencialmente con retry.

**Commit:** `feat(trendradar): periodic scheduler daemon`

---

## Task 9: Reportes CLI y HTML

**Objective:** Generar reportes visuales de trends detectados.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/report.py`

Rich console table para CLI + generar HTML standalone con CSS dark theme. Mostrar: keyword, plataformas, score, velocity, oportunidad.

**Commit:** `feat(trendradar): CLI and HTML report generation`

---

## Task 10: Comando `scan` (one-shot)

**Objective:** Comando para ejecutar una sola recolección sin daemon.

```python
@app.command()
def scan(
    platforms: list[str] = typer.Option(["all"], "--platforms", "-p"),
    output: str = typer.Option("console", "--output", "-o", help="console, html, json"),
):
    """One-shot trend collection and report."""
    ...
```

**Commit:** `feat(trendradar): one-shot scan command`

---

## Task 11: Dashboard web simple

**Objective:** Servidor web minimalista para ver trends en navegador.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/dashboard.py`

FastAPI + Jinja2 templates con CSS dark theme de Yggdrasil. Endpoint `/api/trends` para JSON.

**Commit:** `feat(trendradar): web dashboard`

---

## Task 12: Config TOML + CLI completa

**Objective:** Archivo config con plataformas, intervalos, subreddits, keywords.

**Files:**
- Create: `Muspelheim/TrendRadar/trendradar/config.py`

**Commit:** `feat(trendradar): TOML configuration`

---

## Task 13: Tests de integración + CI

**Objective:** Tests completos y CI.

**Commit:** `ci(trendradar): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| HTTP Client | httpx (async) |
| Parsing | BeautifulSoup4 |
| Storage | SQLite |
| Scoring | numpy (derivadas, cruces) |
| Scheduling | APScheduler |
| CLI | Typer + Rich |
| Reports | HTML + plotext (terminal charts) |
| Dashboard | FastAPI + Jinja2 |
| Config | TOML |
