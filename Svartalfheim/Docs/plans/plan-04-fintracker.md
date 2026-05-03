# FinTracker — Dashboard Financiero Personal

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Agrega datos financieros de múltiples fuentes (CSVs bancarios, crypto wallets, gastos manuales), clasifica con IA, muestra proyecciones. CLI-first con dashboards web opcionales.

**Architecture:** CLI con Typer para input/consulta → SQLite como store central → módulos de import por fuente → clasificador LLM local → projecting module → Rich output + web dashboard opcional.

**Tech Stack:** Python 3.11+, Typer, Rich, SQLite, Plotext/matplotlib, pandas, httpx (crypto APIs), Textual (TUI).

**Realm:** Midgard/FinTracker/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Midgard/FinTracker/pyproject.toml`
- Create: `Midgard/FinTracker/fintracker/__init__.py`
- Create: `Midgard/FinTracker/fintracker/cli.py`
- Create: `Midgard/FinTracker/tests/__init__.py`

Dependencias: typer, rich, pandas, sqlite3 (stdlib), plotext, httpx, textual.

**Commit:** `feat(fintracker): scaffold project`

---

## Task 2: Modelo de datos y DB Schema

**Files:**
- Create: `Midgard/FinTracker/fintracker/models.py`
- Create: `Midgard/FinTracker/fintracker/db.py`
- Create: `Midgard/FinTracker/tests/test_db.py`

```python
@dataclass
class Transaction:
    id: int | None
    date: date
    amount: float
    currency: str = "USD"
    category: str = ""
    subcategory: str = ""
    description: str = ""
    source: str = ""  # bank, crypto, manual
    source_file: str = ""
    classified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Budget:
    id: int | None
    category: str
    monthly_limit: float
    current_spent: float = 0.0
```

SQLite tablas: `transactions`, `budgets`, `accounts`, `projections`. Índices en date, category, source.

**Commit:** `feat(fintracker): data models and SQLite schema`

---

## Task 3: Import CSV bancarios

**Files:**
- Create: `Midgard/FinTracker/fintracker/importers/bank_csv.py`
- Create: `Midgard/FinTracker/tests/test_bank_csv.py`

Soporta formatos: bancolombia, BBVA, Santander, generic CSV. Auto-detecta formato por headers. Mapea columnas a modelo Transaction.

```python
class BankCSVImporter:
    def import_file(self, path: str, format: str = "auto") -> list[Transaction]:
        """Import transactions from bank CSV file."""
        ...

    def detect_format(self, headers: list[str]) -> str:
        """Auto-detect CSV format from headers."""
        ...

    def normalize_amount(self, raw: str, format: str) -> float:
        """Normalize amount string to float (handle commas, parens for negatives)."""
        ...
```

**Commit:** `feat(fintracker): bank CSV importer`

---

## Task 4: Import crypto wallets

**Files:**
- Create: `Midgard/FinTracker/fintracker/importers/crypto.py`

Importa desde: Binance CSV export, MetaMask transaction list, CoinGecko API para precios actuales. Convierte todo a USD.

**Commit:** `feat(fintracker): crypto wallet importer`

---

## Task 5: Input manual de gastos

**Files:**
- Create: `Midgard/FinTracker/fintracker/importers/manual.py`
- Modify: `Midgard/FinTracker/fintracker/cli.py`

```bash
fintracker add --amount 25.50 --category food --description "lunch at cafe"
fintracker add --amount -150.00 --category rent --date 2026-05-01
```

Interactive mode con Rich prompts si no se pasan flags.

**Commit:** `feat(fintracker): manual expense input`

---

## Task 6: Clasificación con IA

**Files:**
- Create: `Midgard/FinTracker/fintracker/classifier.py`

Clasifica transacciones por categoría usando:
1. Reglas determinísticas (regex en descripción)
2. LLM local (Lilith/faster-whisper para embeddings)
3. Fallback a "uncategorized"

Aprende de correcciones del usuario. Guarda mapping descripción→categoría en SQLite.

```python
class TransactionClassifier:
    def classify(self, transaction: Transaction) -> Transaction:
        ...

    def learn(self, description: str, category: str) -> None:
        """Learn from user corrections."""
        ...
```

**Commit:** `feat(fintracker): AI-powered transaction classification`

---

## Task 7: Proyecciones y análisis

**Files:**
- Create: `Midgard/FinTracker/fintracker/analyzer.py`

```python
class FinancialAnalyzer:
    def monthly_summary(self, month: date) -> MonthlySummary:
        ...

    def spending_by_category(self, start: date, end: date) -> dict[str, float]:
        ...

    def project_balance(self, months_ahead: int = 6) -> list[ProjectionPoint]:
        """Project future balance based on spending patterns."""
        ...

    def detect_anomalies(self) -> list[Transaction]:
        """Flag unusual transactions."""
        ...
```

**Commit:** `feat(fintracker): financial analysis and projections`

---

## Task 8: CLI completa con reportes

**Files:**
- Modify: `Midgard/FinTracker/fintracker/cli.py`

Comandos:
- `fintracker import <file>` — importa CSV/crypto
- `fintracker add` — añade gasto manual
- `fintracker summary [--month YYYY-MM]` — resumen mensual
- `fintracker categories` — breakdown por categoría
- `fintracker project [--months 6]` — proyección
- `fintracker budget set <category> <amount>` — presupuesto
- `fintracker budget status` — estado presupuestos

Rich tables con colores (rojo para gastos, verde para ingresos).

**Commit:** `feat(fintracker): complete CLI with reports`

---

## Task 9: Dashboard web (opcional)

**Files:**
- Create: `Midgard/FinTracker/fintracker/dashboard.py`
- Create: `Midgard/FinTracker/fintracker/templates/`

FastAPI + HTMX + Chart.js. Dark theme Yggdrasil. Endpoints: `/`, `/api/transactions`, `/api/summary`, `/api/projection`.

**Commit:** `feat(fintracker): optional web dashboard`

---

## Task 10: Tests + CI

**Commit:** `ci(fintracker): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Storage | SQLite |
| Data processing | pandas |
| Import | CSV parsers, httpx (crypto) |
| Clasificación | regex + LLM local |
| CLI | Typer + Rich |
| TUI | Textual (opcional) |
| Charts | plotext (CLI), Chart.js (web) |
| Web | FastAPI + HTMX (opcional) |
