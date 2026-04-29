# Yggdrasil Phase 2: La Gran Forja

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Transformar Yggdrasil de un ecosistema ordenado pero monolitico en una plataforma distribuida, testeada, modular y conectada.

**Architecture:** Separar el monolito Lilith (123k LOC) en paquetes pip independientes, unificar Vanaheim bajo un framework de bots, activar Alfheim como dashboard real conectado via API, e instalar infraestructura de testing y control de versiones en todo el arbol.

**Tech Stack:** Python 3.11+, pytest, Electron + React, WebSocket, SQLite, git, pre-commit, GitHub Actions (local act), pip packaging.

**Estimacion:** 80+ tareas | 8-12 horas de trabajo | 4-6 sesiones

---

## FASE 1: Infraestructura de Control (Git, Tests, CI)

### Task 1.1: Inicializar monorepo git en raiz Yggdrasil

**Objective:** Crear repositorio git unico para todo el ecosistema con .gitignore global.

**Files:**
- Create: `Yggdrasil/.gitignore`

**Step 1: Crear .gitignore maestro**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.env
.venv/
env/
venv/
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
npm-debug.log
yarn-error.log
.pnpm-debug.log
.next/
dist/
build/
*.map

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Yggdrasil specific
Helheim/Quarantine_*/
*.log
logs/
tmp/
temp/
```

**Step 2: Inicializar git y primer commit**

Run:
```bash
cd D:\Proyectos\Yggdrasil
git init
git add REGLAS_YGGDRASIL.md README.md .gitignore setup_yggdrasil.py yggdrasil_cli.py
git add Asgard/ Vanaheim/ Alfheim/ Svartalfheim/ Muspelheim/ Niflheim/ Jotunheim/ Midgard/
git commit -m "feat: Yggdrasil v2.0 post-remasterizacion"
```

---

### Task 1.2: Instalar pre-commit hooks

**Objective:** Instalar hooks de calidad que corran antes de cada commit.

**Files:**
- Create: `Yggdrasil/.pre-commit-config.yaml`

**Step 1: Crear configuracion de pre-commit**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]
```

**Step 2: Instalar y probar**

Run:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Expected: Puede fallar en archivos existentes, es normal. Corregir solo los de la Fase 1.

---

### Task 1.3: Crear estructura de tests global

**Objective:** Establecer pytest como test runner unico para todo Yggdrasil.

**Files:**
- Create: `Yggdrasil/pytest.ini`
- Create: `Yggdrasil/tests/__init__.py`
- Create: `Yggdrasil/tests/conftest.py`

**Step 1: Crear pytest.ini**

```ini
[pytest]
testpaths = tests Asgard Vanaheim Svartalfheim
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

**Step 2: Crear conftest.py base**

```python
# tests/conftest.py
import pytest
import sys
from pathlib import Path

YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()

# Agregar reinos al path para imports
for realm in ["Asgard", "Vanaheim", "Svartalfheim"]:
    realm_path = YGGDRASIL_ROOT / realm
    if realm_path.exists() and str(realm_path) not in sys.path:
        sys.path.insert(0, str(realm_path))


@pytest.fixture
def yggdrasil_root():
    return YGGDRASIL_ROOT
```

**Step 3: Commit**

```bash
git add pytest.ini tests/ .pre-commit-config.yaml
git commit -m "infra: testing infrastructure and pre-commit hooks"
```

---

### Task 1.4: Test de sanidad para CLI

**Objective:** Primer test real — verificar que yggdrasil_cli.py no se rompe.

**Files:**
- Create: `Yggdrasil/tests/test_cli_sanity.py`

**Step 1: Escribir test**

```python
import subprocess
import sys
from pathlib import Path

YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()
CLI = YGGDRASIL_ROOT / "yggdrasil_cli.py"


def test_cli_status_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "status"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "Yggdrasil Health Check" in result.stdout


def test_cli_tree_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "tree"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "Asgard/" in result.stdout
```

**Step 2: Correr test**

Run: `pytest tests/test_cli_sanity.py -v`
Expected: 2 passed

**Step 3: Commit**

```bash
git add tests/test_cli_sanity.py
git commit -m "test: CLI sanity checks"
```

---

## FASE 2: Modularizacion de Lilith (El Gran Refactor)

### Task 2.1: Auditar estructura src/ de Hermes-Lilith

**Objective:** Documentar todos los modulos existentes antes de tocar nada.

**Files:**
- Create: `Yggdrasil/Svartalfheim/docs/lilith_module_audit.md`

**Step 1: Generar auditoria automatica**

Run script que recorra `Asgard/Hermes-Lilith/src/` y liste:
- Cada directorio y su cantidad de archivos .py
- Cada archivo .py >500 lineas (candidatos a dividir)
- Dependencias entre modulos (imports cruzados)

**Step 2: Commit del audit**

```bash
git add Svartalfheim/docs/lilith_module_audit.md
git commit -m "docs: Lilith src module audit pre-refactor"
```

---

### Task 2.2: Crear paquete `lilith-core`

**Objective:** Extraer la logica fundamental de Lilith a un paquete pip instalable independiente.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-core/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-core/lilith_core/__init__.py`
- Create: `Yggdrasil/Asgard/lilith-core/lilith_core/config.py`
- Create: `Yggdrasil/Asgard/lilith-core/lilith_core/exceptions.py`

**Step 1: Crear pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lilith-core"
version = "2.0.0"
description = "Core engine for the Lilith AI agent"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.28.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black", "isort", "mypy"]

[tool.setuptools.packages.find]
where = ["."]
include = ["lilith_core*"]
```

**Step 2: Crear estructura base**

```python
# lilith_core/__init__.py
"""Lilith Core - Motor fundamental del agente CLI."""
__version__ = "2.0.0"

from .config import Config
from .exceptions import LilithError, ToolError, LLMError

__all__ = ["Config", "LilithError", "ToolError", "LLMError"]
```

```python
# lilith_core/exceptions.py
class LilithError(Exception):
    """Error base de Lilith."""
    pass

class ToolError(LilithError):
    """Error en ejecucion de tool."""
    pass

class LLMError(LilithError):
    """Error en comunicacion con LLM."""
    pass
```

**Step 3: Commit**

```bash
git add Asgard/lilith-core/
git commit -m "feat: lilith-core package scaffolding"
```

---

### Task 2.3: Migrar Config a lilith-core

**Objective:** Mover la logica de configuracion del monolito a lilith-core.

**Files:**
- Modify: `Asgard/Hermes-Lilith/config.py` (si existe)
- Modify: `Asgard/lilith-core/lilith_core/config.py`
- Create: `Asgard/lilith-core/tests/test_config.py`

**Step 1: Extraer config a paquete**

Leer `Asgard/Hermes-Lilith/config.py` o `Asgard/Hermes-Lilith/src/config.py` y migrar a:

```python
# lilith_core/config.py
from pathlib import Path
from typing import Optional
import json
import os


class Config:
    """Configuracion centralizada de Lilith."""

    def __init__(self, root_path: Optional[Path] = None):
        self.root = root_path or Path.home() / ".lilith"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_file = self.root / "config.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.config_file.exists():
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        return self._defaults()

    def _defaults(self) -> dict:
        return {
            "model": "auto",
            "lm_studio_url": "http://localhost:1234/v1",
            "max_context": 8192,
            "temperature": 0.7,
        }

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self._save()

    def _save(self):
        self.config_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
```

**Step 2: Test**

```python
# tests/test_config.py
import pytest
from lilith_core.config import Config


def test_config_defaults():
    c = Config(root_path=pytest.tmp_path)
    assert c.get("model") == "auto"
    assert c.get("nonexistent", "fallback") == "fallback"


def test_config_persistence(tmp_path):
    c1 = Config(root_path=tmp_path)
    c1.set("test_key", "test_value")

    c2 = Config(root_path=tmp_path)
    assert c2.get("test_key") == "test_value"
```

**Step 3: Commit**

```bash
git add Asgard/lilith-core/
git commit -m "feat: migrate Config to lilith-core with tests"
```

---

### Task 2.4: Crear paquete `lilith-tools`

**Objective:** Extraer todas las tools de Lilith a un paquete independiente y registrables.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-tools/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-tools/lilith_tools/__init__.py`
- Create: `Yggdrasil/Asgard/lilith-tools/lilith_tools/registry.py`
- Create: `Yggdrasil/Asgard/lilith-tools/lilith_tools/base.py`

**Step 1: Crear base class para tools**

```python
# lilith_tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str = ""


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = None

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass

    def validate(self, params: Dict[str, Any]) -> bool:
        if not self.parameters:
            return True
        for key, config in self.parameters.items():
            if config.get("required", False) and key not in params:
                return False
        return True
```

**Step 2: Crear registry**

```python
# lilith_tools/registry.py
from typing import Dict, Type
from .base import BaseTool


class ToolRegistry:
    _tools: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> Type[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        return {name: tool_class.description for name, tool_class in cls._tools.items()}

    @classmethod
    def clear(cls):
        cls._tools.clear()
```

**Step 3: Commit**

```bash
git add Asgard/lilith-tools/
git commit -m "feat: lilith-tools package with BaseTool and registry"
```

---

### Task 2.5: Migrar tools existentes al nuevo sistema

**Objective:** Convertir las tools actuales de Lilith en clases que hereden de BaseTool.

**Files:**
- Create: `Asgard/lilith-tools/lilith_tools/system.py`
- Create: `Asgard/lilith-tools/lilith_tools/filesystem.py`
- Create: `Asgard/lilith-tools/lilith_tools/network.py`
- Create: `Asgard/lilith-tools/tests/test_tools.py`

**Step 1: Migrar cada categoria de tool**

Por cada tool existente en `Hermes-Lilith/src/`:
1. Identificar la funcion tool
2. Crear clase que herede BaseTool
3. Registrar con @ToolRegistry.register

Ejemplo para system:

```python
# lilith_tools/system.py
from .base import BaseTool, ToolResult
from .registry import ToolRegistry


@ToolRegistry.register
class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Obtiene informacion del sistema"
    parameters = {}

    def execute(self, **kwargs) -> ToolResult:
        import platform
        data = {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
        }
        return ToolResult(success=True, data=data)
```

**Step 2: Test de registro**

```python
# tests/test_tools.py
from lilith_tools.registry import ToolRegistry
from lilith_tools.system import SystemInfoTool


def test_tool_registration():
    assert "system_info" in ToolRegistry.list_tools()


def test_system_info_tool():
    tool = SystemInfoTool()
    result = tool.execute()
    assert result.success
    assert "os" in result.data
```

**Step 3: Commit**

```bash
git add Asgard/lilith-tools/
git commit -m "feat: migrate existing tools to lilith-tools package"
```

---

### Task 2.6: Crear paquete `lilith-memory`

**Objective:** Extraer el sistema de memoria (EnhancedMemory) a paquete independiente.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-memory/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-memory/lilith_memory/__init__.py`
- Create: `Yggdrasil/Asgard/lilith-memory/lilith_memory/store.py`
- Create: `Yggdrasil/Asgard/lilith-memory/lilith_memory/embeddings.py`
- Create: `Yggdrasil/Asgard/lilith-memory/tests/test_memory.py`

**Step 1: Extraer logica de memoria**

Migrar desde `Hermes-Lilith/src/memory/` o donde viva EnhancedMemory.

```python
# lilith_memory/store.py
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import json


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT,
                    timestamp REAL DEFAULT (unixepoch())
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON memories(timestamp)")

    def add(self, content: str, embedding: Optional[bytes] = None, metadata: Optional[Dict] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
                (content, embedding, json.dumps(metadata) if metadata else None)
            )

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        # Por ahora busqueda simple LIKE, despues vectorial
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            return [dict(row) for row in rows]
```

**Step 2: Test**

```python
# tests/test_memory.py
import pytest
from lilith_memory.store import MemoryStore


def test_add_and_search(tmp_path):
    store = MemoryStore(tmp_path / "test.db")
    store.add("Hola mundo", metadata={"source": "test"})
    results = store.search("mundo")
    assert len(results) == 1
    assert results[0]["content"] == "Hola mundo"
```

**Step 3: Commit**

```bash
git add Asgard/lilith-memory/
git commit -m "feat: lilith-memory package with SQLite store"
```

---

### Task 2.7: Crear paquete `lilith-orchestrator`

**Objective:** Motor de orquestacion que une core + tools + memory + LLM.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-orchestrator/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-orchestrator/lilith_orchestrator/__init__.py`
- Create: `Yggdrasil/Asgard/lilith-orchestrator/lilith_orchestrator/engine.py`
- Create: `Yggdrasil/Asgard/lilith-orchestrator/tests/test_engine.py`

**Step 1: Crear engine**

```python
# lilith_orchestrator/engine.py
from typing import List, Dict, Any
from lilith_core.config import Config
from lilith_tools.registry import ToolRegistry
from lilith_memory.store import MemoryStore


class LilithEngine:
    def __init__(self, config: Config, memory_store: MemoryStore):
        self.config = config
        self.memory = memory_store
        self.tools = ToolRegistry

    def process(self, user_input: str) -> Dict[str, Any]:
        # 1. Buscar contexto relevante en memoria
        context = self.memory.search(user_input, limit=3)

        # 2. Construir prompt con contexto
        prompt = self._build_prompt(user_input, context)

        # 3. Detectar si se necesita tool
        tool_call = self._detect_tool(user_input)

        return {
            "prompt": prompt,
            "context": context,
            "tool_call": tool_call,
            "response": None,  # Se llena despues de llamar al LLM
        }

    def _build_prompt(self, user_input: str, context: List[Dict]) -> str:
        ctx_str = "\n".join([c["content"] for c in context]) if context else ""
        return f"Contexto previo:\n{ctx_str}\n\nUsuario: {user_input}\n\nAsistente:"

    def _detect_tool(self, user_input: str) -> Dict:
        # Placeholder para deteccion de tool
        return {}
```

**Step 2: Test de integracion**

```python
# tests/test_engine.py
import pytest
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine


def test_engine_process(tmp_path):
    config = Config(root_path=tmp_path)
    memory = MemoryStore(tmp_path / "mem.db")
    engine = LilithEngine(config, memory)

    result = engine.process("Hola")
    assert "prompt" in result
    assert "context" in result
```

**Step 3: Commit**

```bash
git add Asgard/lilith-orchestrator/
git commit -m "feat: lilith-orchestrator engine package"
```

---

### Task 2.8: Crear `lilith-cli` entry point

**Objective:** Nuevo entry point que usa los paquetes modulares en lugar del monolito.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-cli/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-cli/lilith_cli/main.py`
- Create: `Yggdrasil/Asgard/lilith-cli/lilith_cli/__init__.py`

**Step 1: Crear CLI nuevo**

```python
# lilith_cli/main.py
import argparse
import sys
from pathlib import Path

from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine


def main():
    parser = argparse.ArgumentParser(description="Lilith CLI v2.0")
    parser.add_argument("--config", type=Path, help="Path to config directory")
    parser.add_argument("--model", help="Override model")
    args = parser.parse_args()

    config = Config(root_path=args.config)
    if args.model:
        config.set("model", args.model)

    db_path = (args.config or Path.home() / ".lilith") / "memory.db"
    memory = MemoryStore(db_path)
    engine = LilithEngine(config, memory)

    print("Lilith v2.0 lista. Escribe /salir para terminar.")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input in ("/salir", "/quit", "/exit"):
            break

        result = engine.process(user_input)
        print(f"[DEBUG] Prompt: {result['prompt'][:200]}...")
        # Aqui iria la llamada al LLM


if __name__ == "__main__":
    main()
```

**Step 2: Instalar en modo editable y probar**

Run:
```bash
cd Asgard/lilith-cli
pip install -e .
lilith --help
```

Expected: Muestra help del CLI.

**Step 3: Commit**

```bash
git add Asgard/lilith-cli/
git commit -m "feat: lilith-cli v2.0 entry point"
```

---

### Task 2.9: Deprecar monolito gradualmente

**Objective:** Marcar el codigo viejo como deprecated sin romper nada.

**Files:**
- Modify: `Asgard/Hermes-Lilith/lilith.py`

**Step 1: Agregar warning de deprecation**

Al inicio de `lilith.py`:

```python
import warnings
warnings.warn(
    "Este entry point es legacy. Usa 'lilith' (v2.0) o Asgard/lilith-cli/",
    DeprecationWarning,
    stacklevel=2
)
```

**Step 2: Commit**

```bash
git add Asgard/Hermes-Lilith/lilith.py
git commit -m "chore: mark legacy lilith.py as deprecated"
```

---

## FASE 3: Framework Vanaheim (Unificacion de Bots)

### Task 3.1: Crear `vanaheim-framework`

**Objective:** Base comun para todos los bots: config, logging, lifecycle, y conexion a LLM.

**Files:**
- Create: `Yggdrasil/Vanaheim/vanaheim-framework/pyproject.toml`
- Create: `Yggdrasil/Vanaheim/vanaheim-framework/vanaheim/__init__.py`
- Create: `Yggdrasil/Vanaheim/vanaheim-framework/vanaheim/bot.py`
- Create: `Yggdrasil/Vanaheim/vanaheim-framework/vanaheim/config.py`

**Step 1: Base Bot class**

```python
# vanaheim/bot.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging


class BaseBot(ABC):
    name: str = "unnamed_bot"
    version: str = "0.1.0"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.name)
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def handle_message(self, message: str) -> str:
        pass
```

**Step 2: Commit**

```bash
git add Vanaheim/vanaheim-framework/
git commit -m "feat: vanaheim-framework base bot class"
```

---

### Task 3.2: Migrar bots existentes al framework

**Objective:** Convertir cada bot para que herede de BaseBot.

**Files:**
- Modify: `Vanaheim/Bots/vanaheim-bot/`
- Modify: `Vanaheim/Bots/bot_telegram/`
- Modify: `Vanaheim/Bots/llm_agente_2026/`
- Modify: `Vanaheim/Bots/conversation_bot/`
- Modify: `Vanaheim/Bots/scraper_bot/`

**Step 1: Por cada bot**

1. Agregar `from vanaheim.bot import BaseBot`
2. Crear clase `MiBot(BaseBot)`
3. Implementar `run()` y `handle_message()`
4. Agregar `if __name__ == "__main__": MiBot().run()`

**Step 2: Crear launcher unificado**

```python
# Vanaheim/launcher.py
import sys
from pathlib import Path
from importlib import import_module

sys.path.insert(0, str(Path(__file__).parent / "vanaheim-framework"))

BOTS = {
    "vanaheim": "Bots.vanaheim-bot.main",
    "telegram": "Bots.bot_telegram.main",
    "agente": "Bots.llm_agente_2026.main",
    "conversation": "Bots.conversation_bot.main",
    "scraper": "Bots.scraper_bot.main",
}

if __name__ == "__main__":
    bot_name = sys.argv[1] if len(sys.argv) > 1 else "vanaheim"
    module_path = BOTS.get(bot_name)
    if not module_path:
        print(f"Bot desconocido: {bot_name}")
        print(f"Disponibles: {', '.join(BOTS.keys())}")
        sys.exit(1)
    module = import_module(module_path)
    module.main()
```

**Step 3: Commit**

```bash
git add Vanaheim/
git commit -m "feat: migrate all bots to vanaheim-framework with unified launcher"
```

---

### Task 3.3: Requirements unificado para Vanaheim

**Objective:** Un solo requirements.txt para todo Vanaheim + framework.

**Files:**
- Create: `Yggdrasil/Vanaheim/requirements.txt`

**Step 1: Consolidar dependencias**

```
# Vanaheim/requirements.txt
# Framework
pydantic>=2.0
requests>=2.28.0
python-dotenv>=1.0

# Bots
python-telegram-bot>=20.0
beautifulsoup4>=4.12
lxml>=4.9
selenium>=4.15
```

**Step 2: Commit**

```bash
git add Vanaheim/requirements.txt
git commit -m "infra: unified Vanaheim requirements"
```

---

## FASE 4: Alfheim Live (Dashboard Real)

### Task 4.1: API REST para Lilith

**Objective:** Servir Lilith via FastAPI para que Alfheim pueda conectarse.

**Files:**
- Create: `Yggdrasil/Asgard/lilith-api/pyproject.toml`
- Create: `Yggdrasil/Asgard/lilith-api/lilith_api/main.py`

**Step 1: Crear API**

```python
# lilith_api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine

app = FastAPI(title="Lilith API", version="2.0.0")

config = Config()
memory = MemoryStore(config.root / "memory.db")
engine = LilithEngine(config, memory)


class ChatRequest(BaseModel):
    message: str
    model: str = None


class ChatResponse(BaseModel):
    response: str
    context_used: list


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = engine.process(req.message)
    # TODO: Integrar llamada real al LLM
    return ChatResponse(
        response=f"Echo: {req.message}",
        context_used=[c["content"] for c in result["context"]]
    )


@app.get("/tools")
async def list_tools():
    from lilith_tools.registry import ToolRegistry
    return ToolRegistry.list_tools()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
```

**Step 2: Test**

Run: `cd Asgard/lilith-api && pip install -e . && uvicorn lilith_api.main:app --reload`
Expected: Servidor levanta en localhost:8000

**Step 3: Commit**

```bash
git add Asgard/lilith-api/
git commit -m "feat: Lilith FastAPI for Alfheim integration"
```

---

### Task 4.2: Conectar Alfheim UI a la API

**Objective:** La semilla Electron debe poder hablar con Lilith API.

**Files:**
- Modify: `Alfheim/ui-seed/preload.js`
- Modify: `Alfheim/ui-seed/renderer/index.html`
- Create: `Alfheim/ui-seed/renderer/app.js`

**Step 1: Actualizar preload.js**

```javascript
// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lilithAPI', {
    chat: (message) => ipcRenderer.invoke('chat', message),
    getTools: () => ipcRenderer.invoke('get-tools'),
});
```

**Step 2: Crear app.js**

```javascript
// renderer/app.js
async function sendMessage() {
    const input = document.getElementById('message-input');
    const chat = document.getElementById('chat-history');
    const msg = input.value.trim();
    if (!msg) return;

    chat.innerHTML += `<div class="user">${msg}</div>`;
    input.value = '';

    try {
        const res = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        chat.innerHTML += `<div class="bot">${data.response}</div>`;
    } catch (e) {
        chat.innerHTML += `<div class="error">Error: ${e.message}</div>`;
    }
}
```

**Step 3: Actualizar HTML**

```html
<!-- renderer/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Lilith Dashboard</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #1a1a1a; color: #eee; }
        #chat-history { height: 400px; overflow-y: auto; border: 1px solid #444; padding: 10px; margin-bottom: 10px; }
        .user { color: #4fc3f7; }
        .bot { color: #81c784; }
        .error { color: #e57373; }
        input { width: 80%; padding: 8px; background: #333; color: #eee; border: 1px solid #555; }
        button { padding: 8px 16px; background: #4fc3f7; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Lilith Dashboard v2.0</h1>
    <div id="chat-history"></div>
    <input id="message-input" type="text" placeholder="Escribe a Lilith...">
    <button onclick="sendMessage()">Enviar</button>
    <script src="app.js"></script>
</body>
</html>
```

**Step 4: Commit**

```bash
git add Alfheim/
git commit -m "feat: Alfheim dashboard connected to Lilith API"
```

---

## FASE 5: Niflheim Inteligente

### Task 5.1: Gestor de modelos LLM

**Objective:** Sistema para descargar, verificar y gestionar modelos GGUF.

**Files:**
- Create: `Yggdrasil/Niflheim/scripts/model_manager.py`
- Create: `Yggdrasil/Niflheim/models/registry.json`

**Step 1: Crear gestor**

```python
# scripts/model_manager.py
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
import urllib.request

NIFLHEIM = Path(__file__).parent.parent
MODELS_DIR = NIFLHEIM / "Models"
REGISTRY = NIFLHEIM / "models" / "registry.json"


def load_registry() -> Dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {}


def save_registry(registry: Dict):
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def add_model(name: str, url: str, size: int, checksum: str = ""):
    registry = load_registry()
    registry[name] = {
        "url": url,
        "size": size,
        "checksum": checksum,
        "path": str(MODELS_DIR / name),
    }
    save_registry(registry)


def verify_model(name: str) -> bool:
    registry = load_registry()
    entry = registry.get(name)
    if not entry:
        return False
    path = Path(entry["path"])
    if not path.exists():
        return False
    if entry.get("checksum"):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        return sha == entry["checksum"]
    return True


def list_models():
    registry = load_registry()
    for name, info in registry.items():
        exists = Path(info["path"]).exists()
        verified = verify_model(name) if exists else False
        status = "OK" if verified else "PRESENT" if exists else "MISSING"
        print(f"  [{status}] {name} ({info.get('size', 0) / 1024**3:.1f} GB)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python model_manager.py [list|add|verify]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_models()
    elif cmd == "verify" and len(sys.argv) > 2:
        print(verify_model(sys.argv[2]))
```

**Step 2: Commit**

```bash
git add Niflheim/
git commit -m "feat: Niflheim model manager with registry"
```

---

## FASE 6: Inter-Reino API (Bus de Mensajes)

### Task 6.1: Crear `yggdrasil-bus`

**Objective:** Sistema liviano de pub/sub para que los reinos se comuniquen.

**Files:**
- Create: `Yggdrasil/Svartalfheim/yggdrasil-bus/pyproject.toml`
- Create: `Yggdrasil/Svartalfheim/yggdrasil-bus/yggdrasil_bus/__init__.py`
- Create: `Yggdrasil/Svartalfheim/yggdrasil-bus/yggdrasil_bus/bus.py`

**Step 1: Implementar bus SQLite-based**

```python
# yggdrasil_bus/bus.py
import sqlite3
import json
import threading
from pathlib import Path
from typing import Callable, Dict, Any
from datetime import datetime


class YggdrasilBus:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._subscribers: Dict[str, list] = {}

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT DEFAULT (datetime('now')),
                    delivered INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON messages(topic)")

    def publish(self, topic: str, payload: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (topic, payload) VALUES (?, ?)",
                (topic, json.dumps(payload))
            )
        # Notificar suscriptores en memoria
        for callback in self._subscribers.get(topic, []):
            try:
                callback(payload)
            except Exception:
                pass

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def get_history(self, topic: str, limit: int = 50) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM messages WHERE topic = ? ORDER BY id DESC LIMIT ?",
                (topic, limit)
            ).fetchall()
            return [dict(row) for row in rows]
```

**Step 2: Commit**

```bash
git add Svartalfheim/yggdrasil-bus/
git commit -m "feat: yggdrasil-bus inter-realm message bus"
```

---

## FASE 7: Observabilidad y Seguridad

### Task 7.1: Logging centralizado

**Objective:** Todos los reinos escriben a un log unico rotativo.

**Files:**
- Create: `Yggdrasil/Svartalfheim/yggdrasil-logger/pyproject.toml`
- Create: `Yggdrasil/Svartalfheim/yggdrasil-logger/yggdrasil_logger/__init__.py`

**Step 1: Logger compartido**

```python
# yggdrasil_logger/__init__.py
import logging
import logging.handlers
from pathlib import Path


def get_logger(name: str, log_dir: Path = None) -> logging.Logger:
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            log_dir / "yggdrasil.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
```

**Step 2: Commit**

```bash
git add Svartalfheim/yggdrasil-logger/
git commit -m "feat: centralized Yggdrasil logging"
```

---

### Task 7.2: Secret scanning

**Objective:** Script que escanee todo Yggdrasil en busca de secrets expuestos.

**Files:**
- Create: `Yggdrasil/yggdrasil_cli.py` (agregar comando `scan`)

**Step 1: Agregar comando scan**

```python
# En yggdrasil_cli.py, dentro de cmd_scan():

def cmd_scan():
    print("[SCAN] Buscando secrets expuestos...")
    patterns = [
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub PAT'),
        (r'[A-Za-z0-9_]{20,}@[A-Za-z0-9]+\.[A-Za-z]{2,}', 'Possible credential'),
        (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
    ]
    import re
    found = 0
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        for fpath in rpath.rglob("*"):
            if not fpath.is_file() or fpath.stat().st_size > 1024 * 1024:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content):
                        line = content[:match.start()].count('\n') + 1
                        print(f"  [WARN] {desc} in {fpath.relative_to(YGGDRASIL_ROOT)}:{line}")
                        found += 1
            except Exception:
                pass
    print(f"\n[{'FAIL' if found else 'OK'}] {found} potential secrets found")
```

**Step 2: Commit**

```bash
git add yggdrasil_cli.py
git commit -m "feat: secret scanning in yggdrasil_cli"
```

---

## FASE 8: Documentacion y Cierre

### Task 8.1: Generar documentacion de API

**Objective:** Auto-generar OpenAPI docs desde lilith-api.

**Files:**
- Create: `Yggdrasil/Svartalfheim/docs/api/openapi.json`

**Step 1: Exportar OpenAPI spec**

Run:
```bash
cd Asgard/lilith-api
pip install -e .
python -c "from lilith_api.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > ../../Svartalfheim/docs/api/openapi.json
```

**Step 2: Commit**

```bash
git add Svartalfheim/docs/api/
git commit -m "docs: auto-generated OpenAPI spec for Lilith API"
```

---

### Task 8.2: Actualizar ARQUITECTURA_YGGDRASIL.md

**Objective:** Documentar la nueva arquitectura modular post-Phase 2.

**Files:**
- Modify: `Yggdrasil/Svartalfheim/docs/ARQUITECTURA_YGGDRASIL.md`

**Step 1: Agregar seccion "Fase 2 - La Gran Forja"**

Incluir:
- Diagrama de paquetes (lilith-core, lilith-tools, lilith-memory, lilith-orchestrator, lilith-api, lilith-cli)
- Diagrama de Vanaheim framework
- Diagrama de comunicacion Alfheim <-> Lilith API
- Diagrama del bus de mensajes inter-reino

**Step 2: Commit**

```bash
git add Svartalfheim/docs/ARQUITECTURA_YGGDRASIL.md
git commit -m "docs: architecture v2.0 with modular packages"
```

---

### Task 8.3: Tag de release v2.0

**Objective:** Marcar el estado final de Phase 2.

**Step 1: Crear tag**

Run:
```bash
git tag -a v2.0 -m "Yggdrasil Phase 2: La Gran Forja - Modular, Testeada, Conectada"
git log --oneline -20
```

**Step 2: Generar CHANGELOG.md**

```markdown
# Changelog

## v2.0 - 2026-04-29 - La Gran Forja

### Lilith
- [feat] lilith-core: Config, exceptions, base classes
- [feat] lilith-tools: BaseTool + registry + tools migradas
- [feat] lilith-memory: SQLite vector store
- [feat] lilith-orchestrator: Motor de procesamiento
- [feat] lilith-api: FastAPI REST para integracion
- [feat] lilith-cli: Entry point v2.0

### Vanaheim
- [feat] vanaheim-framework: BaseBot unificado
- [feat] Launcher centralizado para todos los bots
- [feat] requirements.txt unificado

### Alfheim
- [feat] Dashboard Electron conectado a Lilith API

### Niflheim
- [feat] Model manager con registry SHA256

### Infraestructura
- [feat] Monorepo git con pre-commit hooks
- [feat] pytest global con conftest
- [feat] yggdrasil-bus: Pub/sub inter-reino SQLite
- [feat] yggdrasil-logger: Logging centralizado
- [feat] Secret scanning en CLI
```

**Step 3: Commit final**

```bash
git add CHANGELOG.md
git commit -m "chore: release v2.0 - La Gran Forja"
```

---

## RESUMEN DE ENTREGABLES

| Fase | Entregable | Complejidad |
|------|-----------|-------------|
| 1 | Git monorepo + pre-commit + pytest | Media |
| 2.1-2.3 | lilith-core + Config | Media |
| 2.4-2.5 | lilith-tools + registry | Media |
| 2.6 | lilith-memory | Media |
| 2.7 | lilith-orchestrator | Alta |
| 2.8 | lilith-cli v2.0 | Media |
| 2.9 | Deprecacion graceful | Baja |
| 3.1-3.3 | Vanaheim framework + migracion | Alta |
| 4.1-4.2 | Lilith API + Alfheim dashboard | Alta |
| 5.1 | Niflheim model manager | Media |
| 6.1 | yggdrasil-bus | Media |
| 7.1-7.2 | Logger + secret scan | Media |
| 8.1-8.3 | Docs + release v2.0 | Baja |

**Total estimado:** 80+ tareas | 8-12 horas | 4-6 sesiones de trabajo

---

**Yggdrasil crece con orden o no crece.**
