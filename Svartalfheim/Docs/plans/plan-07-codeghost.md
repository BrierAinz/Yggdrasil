# CodeGhost — Agente de Code Review Autónomo

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Conecta a un repo, revisa PRs con criterios configurables (seguridad, performance, estilo, arquitectura), comenta inline, y aprende de los patrones del proyecto.

**Architecture:** GitHub webhook/event polling → PR diff fetch → AST analysis + rule engine + LLM review → inline comments via GitHub API → learning from feedback. Integrable con Lilith en Asgard.

**Tech Stack:** Python 3.11+, PyGithub, tree-sitter (AST), Lilith (LLM), SQLite (rules cache), Typer, Rich.

**Realm:** Vanaheim/CodeGhost/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Vanaheim/CodeGhost/pyproject.toml`
- Create: `Vanaheim/CodeGhost/codeghost/__init__.py`
- Create: `Vanaheim/CodeGhost/codeghost/cli.py`
- Create: `Vanaheim/CodeGhost/tests/__init__.py`

```toml
[project]
name = "codeghost"
version = "0.1.0"
description = "Autonomous code review agent"
requires-python = ">=3.11"
dependencies = [
    "PyGithub>=2.1",
    "tree-sitter>=0.20",
    "tree-sitter-python>=0.20",
    "tree-sitter-javascript>=0.20",
    "rich>=13.0",
    "typer>=0.9",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
lilith = ["lilith-core>=4.0"]

[project.scripts]
codeghost = "codeghost.cli:app"
```

**Commit:** `feat(codeghost): scaffold project`

---

## Task 2: GitHub integration — PR fetching

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/github_client.py`
- Create: `Vanaheim/CodeGhost/tests/test_github.py`

```python
class GitHubClient:
    def __init__(self, token: str, repo: str):
        self.gh = Github(token)
        self.repo = self.gh.get_repo(repo)

    def get_open_prs(self) -> list[PullRequest]:
        """Fetch all open PRs."""
        ...

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff/patch for a PR."""
        ...

    def get_pr_files(self, pr_number: int) -> list[PRFile]:
        """Get changed files with patch data."""
        ...

    def post_comment(self, pr_number: int, file: str, line: int, body: str) -> None:
        """Post inline review comment on a PR."""
        ...

    def post_summary(self, pr_number: int, summary: str) -> None:
        """Post a summary comment on the PR."""
        ...
```

**Commit:** `feat(codeghost): GitHub PR fetching and commenting`

---

## Task 3: AST analysis con tree-sitter

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/analyzer.py`
- Create: `Vanaheim/CodeGhost/tests/test_analyzer.py`

```python
class CodeAnalyzer:
    def analyze(self, file_path: str, content: str, language: str) -> AnalysisResult:
        """Analyze a single file using tree-sitter AST."""
        ...

    def detect_complexity(self, tree) -> list[ComplexityIssue]:
        """Detect high-complexity functions."""
        ...

    def detect_security_patterns(self, tree) -> list[SecurityIssue]:
        """Detect common security anti-patterns."""
        ...

    def detect_style_issues(self, tree) -> list[StyleIssue]:
        """Detect style/formatting issues."""
        ...
```

Reglas AST para: funciones >50 líneas, nesting >4 niveles, eval/exec, hardcoded secrets, SQL injection patterns, missing error handling.

**Commit:** `feat(codeghost): AST code analysis`

---

## Task 4: Review rules engine

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/rules/`
- Create: `Vanaheim/CodeGhost/codeghost/rules/__init__.py`
- Create: `Vanaheim/CodeGhost/codeghost/rules/security.py`
- Create: `Vanaheim/CodeGhost/codeghost/rules/performance.py`
- Create: `Vanaheim/CodeGhost/codeghost/rules/style.py`
- Create: `Vanaheim/CodeGhost/codeghost/rules/architecture.py`

Cada rule set es una clase con método `check(diff, files, analysis) -> list[Issue]`. Configurable por proyecto via `.codeghost.toml`.

```python
# codeghost/rules/security.py
SECURITY_RULES = [
    "no-hardcoded-secrets",
    "no-sql-injection",
    "no-eval-exec",
    "no-unsafe-deserialize",
    "no-shell-injection",
]
```

**Commit:** `feat(codeghost): configurable review rules engine`

---

## Task 5: Configuración por proyecto (.codeghost.toml)

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/config.py`

```toml
# .codeghost.toml
[review]
rules = ["security", "performance", "style", "architecture"]
severity_threshold = "warning"  # info, warning, error
max_line_length = 120
max_function_lines = 50
max_nesting = 4

[security]
forbidden_functions = ["eval", "exec", "__import__"]
required_error_handling = true

[architecture]
max_file_lines = 300
require_type_hints = true
require_docstrings = true

[llm]
enabled = true
provider = "lilith"
model = "local"
```

**Commit:** `feat(codeghost): project configuration TOML`

---

## Task 6: LLM-powered deep review

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/llm_reviewer.py`

Integración con Lilith para review semántico que AST no detecta: architecture issues, naming, docsQuality, logical errors.

```python
class LLMReviewer:
    def review_pr(self, diff: str, files: list[PRFile], analysis: AnalysisResult) -> list[ReviewComment]:
        """Use LLM to review PR for issues AST can't catch."""
        prompt = f"""Review this PR diff for:
        1. Architectural concerns
        2. Logical errors
        3. Missing edge cases
        4. Documentation quality

        Diff: {diff}
        AST findings: {analysis}
        """
        ...
```

**Commit:** `feat(codeghost): LLM-powered semantic review`

---

## Task 7: Learning de patrones del proyecto

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/learner.py`
- Create: `Vanaheim/CodeGhost/codeghost/db.py`

Almacena patrones aprendidos: naming conventions, architecture patterns, common issues. SQLite con tablas: `learned_patterns`, `review_history`, `feedback`.

```python
class PatternLearner:
    def learn_from_review(self, pr_number: int, comments: list, feedback: str) -> None:
        """Learn from human feedback on reviews."""
        ...

    def get_project_patterns(self) -> ProjectPatterns:
        """Retrieve learned patterns for this project."""
        ...
```

**Commit:** `feat(codeghost): pattern learning from feedback`

---

## Task 8: Pipeline completo — review un PR

**Files:**
- Modify: `Vanaheim/CodeGhost/codeghost/cli.py`

```bash
codeghost review --repo owner/repo --pr 42
codeghost review --repo owner/repo --pr 42 --rules security,performance
codeghost review --repo owner/repo --all  # review all open PRs
codeghost watch --repo owner/repo  # daemon mode, review new PRs
```

Rich output con resumen: X issues found, Y security, Z style, W architecture.

**Commit:** `feat(codeghost): full review pipeline CLI`

---

## Task 9: Review report y summary

**Files:**
- Create: `Vanaheim/CodeGhost/codeghost/report.py`

Genera review en formato GitHub comment: summary table, inline comments by severity, suggestions con código fix.

**Commit:** `feat(codeghost): review report generation`

---

## Task 10: Tests + CI

**Commit:** `ci(codeghost): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| GitHub API | PyGithub |
| AST Analysis | tree-sitter (Python, JS) |
| Rules Engine | Custom rule classes |
| LLM Review | Lilith (local) |
| Learning | SQLite pattern storage |
| CLI | Typer + Rich |
| Config | TOML |
