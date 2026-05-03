# PromptForge — Agente que Optimiza Prompts

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Le das una tarea, y el agente iterativamente genera variantes del prompt, las evalúa con métricas de calidad, y devuelve el prompt optimizado con justificación. Meta-herramienta.

**Architecture:** Task input → prompt generation (base + variants) → LLM evaluation (criteria: clarity, specificity, robustness) → scoring → iterative refinement → final optimized prompt. Integración con Lilith.

**Tech Stack:** Python 3.11+, Lilith (LLM), SQLite (prompt history), Typer, Rich, Textual (TUI).

**Realm:** Vanaheim/PromptForge/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Vanaheim/PromptForge/pyproject.toml`
- Create: `Vanaheim/PromptForge/promptforge/__init__.py`
- Create: `Vanaheim/PromptForge/promptforge/cli.py`
- Create: `Vanaheim/PromptForge/tests/__init__.py`

```toml
[project]
name = "promptforge"
version = "0.1.0"
description = "Iterative prompt optimization agent"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.0",
    "typer>=0.9",
    "textual>=0.40",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
lilith = ["lilith-core>=4.0"]

[project.scripts]
promptforge = "promptforge.cli:app"
```

**Commit:** `feat(promptforge): scaffold project`

---

## Task 2: Prompt model y DB

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/models.py`
- Create: `Vanaheim/PromptForge/promptforge/db.py`
- Create: `Vanaheim/PromptForge/tests/test_db.py`

```python
@dataclass
class PromptVariant:
    id: int | None
    content: str
    strategy: str  # base, concise, detailed, few_shot, chain_of_thought, role_play
    generation: int = 0  # iteration number
    score: float = 0.0
    criteria_scores: dict[str, float] = field(default_factory=dict)
    parent_id: int | None = None  # which variant it evolved from

@dataclass
class OptimizationSession:
    id: int | None
    task: str
    base_prompt: str
    best_prompt: str | None = None
    best_score: float = 0.0
    iterations: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class EvalCriterion:
    name: str
    description: str
    weight: float = 1.0
    # Examples: clarity, specificity, robustness, efficiency, creativity
```

SQLite tablas: `sessions`, `variants`, `evaluations`, `criteria_scores`.

**Commit:** `feat(promptforge): data models and SQLite`

---

## Task 3: Prompt generation strategies

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/strategies.py`
- Create: `Vanaheim/PromptForge/tests/test_strategies.py`

Estrategias de generación:
1. **Base**: el prompt tal cual del usuario
2. **Concise**: versión más corta y directa
3. **Detailed**: añade contexto, constraints, ejemplos
4. **Few-shot**: añade 2-3 ejemplos de input/output
5. **Chain-of-thought**: añade "think step by step"
6. **Role-play**: añade rol y expertise al modelo
7. **Structured**: formato con secciones numeradas
8. **Constraint-based**: añade constraints y edge cases explícitos

```python
class PromptStrategist:
    def generate_variants(self, base_prompt: str, task: str) -> list[PromptVariant]:
        """Generate multiple prompt variants using different strategies."""
        ...

    def refine_from_evaluation(self, variant: PromptVariant, eval_result: EvalResult) -> PromptVariant:
        """Refine a variant based on evaluation feedback."""
        ...
```

**Commit:** `feat(promptforge): prompt generation strategies`

---

## Task 4: Evaluation framework

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/evaluator.py`
- Create: `Vanaheim/PromptForge/tests/test_evaluator.py`

Evalúa prompts en criterios:
- **Clarity** (1-10): ¿Es claro y sin ambigüedad?
- **Specificity** (1-10): ¿Es específico sobre el output deseado?
- **Robustness** (1-10): ¿Funciona bien con edge cases?
- **Efficiency** (1-10): ¿Produce el resultado con mínimo tokens?
- **Creativity** (1-10): ¿Permite respuestas creativas cuando es apropiado?

```python
class PromptEvaluator:
    def evaluate(self, prompt: PromptVariant, task: str, criteria: list[EvalCriterion]) -> EvalResult:
        """Evaluate a prompt variant against criteria."""
        ...

    def compare(self, variants: list[PromptVariant], task: str) -> list[ScoredVariant]:
        """Compare multiple variants and rank them."""
        ...
```

**Commit:** `feat(promptforge): evaluation framework`

---

## Task 5: LLM-based evaluation (Lilith)

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/llm_evaluator.py`

Usa Lilith para evaluar quality del output de cada prompt variant:
1. Ejecutar el prompt contra el LLM
2. Evaluar la calidad del output
3. Comparar con las otras variantes
4. Generar feedback para la siguiente iteración

```python
class LLMEvaluator:
    def run_prompt(self, prompt: str, task: str) -> str:
        """Execute a prompt and get the output."""
        ...

    def evaluate_output(self, output: str, task: str, criteria: list[EvalCriterion]) -> dict[str, float]:
        """Evaluate the quality of an LLM output."""
        ...
```

**Commit:** `feat(promptforge): LLM-based evaluation with Lilith`

---

## Task 6: Iterative optimization loop

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/optimizer.py`

```python
class PromptOptimizer:
    def __init__(self, max_iterations: int = 5, variants_per_iteration: int = 4):
        ...

    def optimize(self, task: str, base_prompt: str, criteria: list[EvalCriterion] = None) -> OptimizationResult:
        """Run the full optimization loop."""
        for i in range(self.max_iterations):
            # 1. Generate variants (or refine from previous best)
            # 2. Evaluate each variant
            # 3. Select best
            # 4. Generate refined variants for next iteration
            ...

    def _select_best(self, results: list[ScoredVariant]) -> PromptVariant:
        ...

    def _refine(self, best: PromptVariant, results: list[ScoredVariant]) -> list[PromptVariant]:
        ...
```

**Commit:** `feat(promptforge): iterative optimization loop`

---

## Task 7: Justification engine

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/justifier.py`

Genera explicación de por qué el prompt optimizado es mejor:
- Qué cambió respecto al base
- Qué criterios mejoraron
- En qué casos falla el base pero funciona el optimizado
- Trade-offs conscientes

```python
class Justifier:
    def justify(self, base: PromptVariant, optimized: PromptVariant, eval_history: list) -> str:
        """Generate human-readable justification for the optimization."""
        ...
```

**Commit:** `feat(promptforge): justification engine`

---

## Task 8: CLI completa

**Files:**
- Modify: `Vanaheim/PromptForge/promptforge/cli.py`

```bash
promptforge optimize "Write a Python function that sorts a list"     # full optimization
promptforge optimize "Explain quantum computing" --iterations 3     # custom iterations
promptforge optimize "Summarize this article" --criteria clarity,specificity
promptforge compare <session_id>                                     # compare all variants
promptforge history                                                   # list past sessions
promptforge export <session_id> --format markdown                    # export results
```

Rich output con tabla comparativa de variantes, scores, y justificación.

**Commit:** `feat(promptforge): complete CLI`

---

## Task 9: TUI Dashboard

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/tui.py`

Dashboard Textual con:
- Panel de iteración actual
- Comparación side-by-side de variantes
- Gráfica de scores por iteración
- Justificación del prompt óptimo

```bash
promptforge dashboard  # interactive TUI
```

**Commit:** `feat(promptforge): Textual TUI dashboard`

---

## Task 10: Template library

**Files:**
- Create: `Vanaheim/PromptForge/promptforge/templates.py`

Biblioteca de templates de prompts por categoría:
- Code generation
- Summarization
- Analysis
- Creative writing
- Q&A
- Translation

```bash
promptforge templates              # list all templates
promptforge templates --category code   # filter by category
promptforge optimize --template code_generation "sort a list"
```

**Commit:** `feat(promptforge): prompt template library`

---

## Task 11: Tests + CI

**Commit:** `ci(promptforge): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| LLM | Lilith (local) |
| Storage | SQLite |
| Evaluation | Custom criteria + LLM |
| Strategies | 8 prompt engineering strategies |
| CLI | Typer + Rich |
| TUI | Textual |
| Templates | Built-in library by category |
