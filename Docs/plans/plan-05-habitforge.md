# HabitForge — Tracker de Hábitos con Comprensión de Patrones

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** No solo marca X en calendario. Analiza correlaciones, sugiere ajustes, y genera predicciones. Integración con Midgard/habits existente.

**Architecture:** CLI para check-in → SQLite para datos → analyzer de correlaciones (Pearson/ML ligero) → predictor → Rich tables + TUI dashboard.

**Tech Stack:** Python 3.11+, Typer, Rich, Textual, SQLite, numpy, scipy, scikit-learn (lightweight), matplotlib.

**Realm:** Midgard/HabitForge/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Midgard/HabitForge/pyproject.toml`
- Create: `Midgard/HabitForge/habitforge/__init__.py`
- Create: `Midgard/HabitForge/habitforge/cli.py`
- Create: `Midgard/HabitForge/tests/__init__.py`

Dependencies: typer, rich, textual, numpy, scipy, scikit-learn, sqlite3 (stdlib).

**Commit:** `feat(habitforge): scaffold project`

---

## Task 2: Modelo de datos y DB

**Files:**
- Create: `Midgard/HabitForge/habitforge/models.py`
- Create: `Midgard/HabitForge/habitforge/db.py`
- Create: `Midgard/HabitForge/tests/test_db.py`

```python
@dataclass
class Habit:
    id: int | None
    name: str
    description: str = ""
    frequency: str = "daily"  # daily, weekly, custom
    target: int = 1  # times per period
    color: str = "#00ff88"
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CheckIn:
    id: int | None
    habit_id: int
    date: date
    value: int = 1  # 0=miss, 1=done, 2+=multiple
    note: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Correlation:
    habit_a: str
    habit_b: str
    coefficient: float  # Pearson r
    p_value: float
    direction: str  # positive, negative
```

**Commit:** `feat(habitforge): data models and SQLite`

---

## Task 3: CLI de check-in

**Files:**
- Modify: `Midgard/HabitForge/habitforge/cli.py`

```bash
habitforge add "exercise" --frequency daily --target 1
habitforge add "meditate" --frequency daily --target 1
habitforge check "exercise"    # marca hoy
habitforge check "exercise" --date 2026-04-30 --value 2  # retroactivo, doble
habitforge check "meditate" --note "15 min session"
habitforge log  # check-in interactivo de todos los hábitos del día
```

**Commit:** `feat(habitforge): CLI check-in commands`

---

## Task 4: Visualización de streaks y calendar heatmap

**Files:**
- Create: `Midgard/HabitForge/habitforge/visualize.py`

Rich tables para streaks actuales, mejor racha, completion rate. Calendar heatmap en terminal con plotext.

**Commit:** `feat(habitforge): streak and heatmap visualization`

---

## Task 5: Análisis de correlaciones

**Files:**
- Create: `Midgard/HabitForge/habitforge/correlator.py`
- Create: `Midgard/HabitForge/tests/test_correlator.py`

Calcula correlaciones de Pearson entre todos los pares de hábitos:
- "Duermes mejor los días que haces ejercicio" → correlation(habit_exercise, habit_sleep) = 0.72
- "Tu productividad cae antes de deadlines" → correlation(habit_deadline_week, habit_productivity) = -0.58

```python
class HabitCorrelator:
    def correlations(self, habit_data: dict[str, list]) -> list[Correlation]:
        """Compute all pairwise correlations between habits."""
        ...

    def significant_correlations(self, threshold: float = 0.3, p_threshold: float = 0.05) -> list[Correlation]:
        """Return only statistically significant correlations."""
        ...

    def explain(self, correlation: Correlation) -> str:
        """Generate natural language explanation of a correlation."""
        ...
```

**Commit:** `feat(habitforge): correlation analysis`

---

## Task 6: Predicciones y sugerencias

**Files:**
- Create: `Midgard/HabitForge/habitforge/predictor.py`

Usa regresión lineal para predecir:
- Probabilidad de completar un hábito dado el contexto (día de semana, qué otros hábitos completaste)
- Sugerencias: "Los lunes tienes 30% más probabilidad de meditar si yahiciste ejercicio"

```python
class HabitPredictor:
    def predict_completion(self, habit: str, context: dict) -> float:
        """Predict probability of completing a habit given context."""
        ...

    def suggest_adjustments(self) -> list[Suggestion]:
        """Generate actionable suggestions based on patterns."""
        ...
```

**Commit:** `feat(habitforge): predictions and suggestions`

---

## Task 7: Integración con Midgard/habits

**Files:**
- Create: `Midgard/HabitForge/habitforge/bridge.py`

Lee/escribe datos del módulo habits existente en Midgard/. Formato compatible para migración.

**Commit:** `feat(habitforge): bridge to existing habits module`

---

## Task 8: TUI Dashboard con Textual

**Files:**
- Create: `Midgard/HabitForge/habitforge/tui.py`

Dashboard interactivo con Textual: listado de hábitos, calendar view, correlaciones, sugerencias.

```bash
habitforge dashboard  # abre TUI
```

**Commit:** `feat(habitforge): Textual TUI dashboard`

---

## Task 9: Export/import de datos

**Files:**
- Create: `Midgard/HabitForge/habitforge/io.py`

Exportar a JSON/CSV, importar de datos existentes. Formato compatible con apps como Habitica, Loop Habit Tracker.

**Commit:** `feat(habitforge): data import/export`

---

## Task 10: Tests + CI

**Commit:** `ci(habitforge): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Storage | SQLite |
| Analysis | numpy, scipy, scikit-learn |
| CLI | Typer + Rich |
| TUI | Textual |
| Charts | plotext (CLI), matplotlib (web) |
| Correlation | Pearson + p-value |
| Prediction | Linear regression |
