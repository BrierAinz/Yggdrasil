# DocWeaver — Agente que Mantiene Documentación Viva

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Monitorea cambios en el código y actualiza docs automáticamente. Detecta README desactualizados, APIs que cambiaron sin reflejar en docs, genera PRs con fixes.

**Architecture:** Git hook / CI integration → diff analysis → AST comparison → doc staleness detection → auto-fix generation → PR creation via GitHub API.

**Tech Stack:** Python 3.11+, PyGithub, tree-sitter, gitpython, httpx, Typer, Rich.

**Realm:** Vanaheim/DocWeaver/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Vanaheim/DocWeaver/pyproject.toml`
- Create: `Vanaheim/DocWeaver/docweaver/__init__.py`
- Create: `Vanaheim/DocWeaver/docweaver/cli.py`
- Create: `Vanaheim/DocWeaver/tests/__init__.py`

**Commit:** `feat(docweaver): scaffold project`

---

## Task 2: Git diff analysis

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/diff_analyzer.py`
- Create: `Vanaheim/DocWeaver/tests/test_diff_analyzer.py`

```python
class DiffAnalyzer:
    def analyze(self, diff: str) -> DiffReport:
        """Parse git diff and categorize changes."""
        ...

    def extract_changed_symbols(self, diff: str, language: str) -> list[ChangedSymbol]:
        """Extract function/class/method signatures that changed."""
        ...

    def categorize_change(self, change: ChangedSymbol) -> ChangeCategory:
        """Categorize: API change, internal, docs-only, refactor, new-feature."""
        ...
```

Categorías: `api_breaking`, `api_new`, `internal`, `docs_only`, `refactor`, `bug_fix`, `new_feature`.

**Commit:** `feat(docweaver): git diff analysis`

---

## Task 3: Code-doc sync detection

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/sync_checker.py`

Compara funciones/classes en código vs documentación:
- README menciona `def foo(a, b)` pero ahora es `def foo(a, b, c=None)`
- API docs dicen "returns str" pero el código dice `-> int`
- Docstring desactualizado vs firma actual

```python
class SyncChecker:
    def check_readme(self, readme: str, symbols: list[Symbol]) -> list[StalenessIssue]:
        ...

    def check_api_docs(self, docs: str, api_symbols: list[Symbol]) -> list[StalenessIssue]:
        ...

    def check_docstrings(self, source_files: dict) -> list[StalenessIssue]:
        ...
```

**Commit:** `feat(docweaver): code-doc sync detection`

---

## Task 4: AST-based API extraction

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/api_extractor.py`

Extrae API surface de Python/JS:
- Function signatures (name, params, return types)
- Class methods
- Module exports
- Decorator metadata (@property, @staticmethod, @deprecated)

Tree-sitter para Python y JavaScript.

**Commit:** `feat(docweaver): AST API extraction`

---

## Task 5: Auto-fix generation

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/fixer.py`

Genera patches para docs desactualizados:
- Actualizar firmas de funciones
- Añadir parámetros nuevos
- Actualizar return types
- Añadir deprecated warnings
- Regenerar tablas de API

```python
class DocFixer:
    def fix_signature(self, doc_content: str, old_sig: str, new_sig: str) -> str:
        ...

    def fix_readme_api_section(self, readme: str, current_symbols: list[Symbol]) -> str:
        ...

    def generate_api_table(self, symbols: list[Symbol]) -> str:
        ...
```

**Commit:** `feat(docweaver): auto-fix generation`

---

## Task 6: LLM-powered doc writing

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/llm_writer.py`

Cuando AST no puede generar el fix completo, usa LLM (Lilith) para:
- Escribir descripciones de funciones modificadas
- Regenerar secciones enteras de docs
- Generar changelog entries
- Escribir migration guides para breaking changes

**Commit:** `feat(docweaver): LLM doc writing`

---

## Task 7: GitHub PR creation

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/pr_creator.py`

```python
class PRCreator:
    def create_doc_fix_pr(self, repo: str, issues: list[StalenessIssue], fixes: dict[str, str]) -> str:
        """Create a PR with doc fixes."""
        ...

    def create_branch(self, branch_name: str) -> None:
        ...

    def commit_fixes(self, branch: str, fixes: dict[str, str]) -> None:
        ...
```

Branch naming: `docweaver/fix-{timestamp}`, PR title: `📖 docs: update {files} for {change_type}`.

**Commit:** `feat(docweaver): GitHub PR creation`

---

## Task 8: CLI commands

**Files:**
- Modify: `Vanaheim/DocWeaver/docweaver/cli.py`

```bash
docweaver check                    # check current repo for stale docs
docweaver check --repo owner/repo  # check remote repo
docweaver fix                      # auto-fix stale docs locally
docweaver fix --pr                 # auto-fix and create PR
docweaver watch                    # daemon mode, monitor for changes
docweaver init                     # create .docweaver.toml config
```

**Commit:** `feat(docweaver): complete CLI`

---

## Task 9: Configuration

**Files:**
- Create: `Vanaheim/DocWeaver/docweaver/config.py`

```toml
# .docweaver.toml
[check]
readme = true
api_docs = true
docstrings = true
changelog = true

[ignore]
paths = ["vendor/", "generated/"]
extensions = [".py", ".js", ".ts"]

[github]
auto_pr = false
default_branch = "main"
label = "documentation"
```

**Commit:** `feat(docweaver): project configuration`

---

## Task 10: Tests + CI

**Commit:** `ci(docweaver): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Git integration | gitpython |
| AST Analysis | tree-sitter (Python, JS) |
| GitHub API | PyGithub |
| LLM Writing | Lilith (local) |
| CLI | Typer + Rich |
| Config | TOML |
