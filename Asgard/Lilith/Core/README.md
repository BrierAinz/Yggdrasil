# Lilith v2.1 ðŸ˜ˆ

> **Operator-class AI Assistant for Software Development**
>
> *Previously known as "LILITH"*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-117%20passing-green.svg)]()

---

## ðŸŒŸ Overview

LILITH is an autonomous AI assistant designed specifically for software development. It combines natural language understanding with a powerful ecosystem of 11 autonomous skills to help developers manage code, dependencies, documentation, and more.

### Key Features

- ðŸŽ¯ **11 Autonomous Skills** - From file management to graph visualization
- ðŸ’¬ **Natural Language Interface** - 42 conversational intents
- ðŸ›¡ï¸ **Trust Score System** - Automatic execution for safe operations
- ðŸŒ **Modern Web Interface** - Real-time dashboard with graph visualization
- ðŸ“Š **Graph Visualization** - Dependency analysis and metrics charts
- ðŸ”’ **Safety First** - Built-in protections and risk assessment

---

## ðŸš€ Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/LILITH.git
cd LILITH

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running LILITH

```bash
# Start the web server
python start_server.py

# Or with hot-reload for development
python start_server.py --dev
```

Access the web interface at: **http://localhost:8000**

---

## ðŸ’» Usage Examples

### File Operations

```
User: "Lee el archivo main.py"
LILITH: [Displays file content with syntax highlighting]

User: "Lista los archivos en Backend/"
LILITH: [Shows directory listing]

User: "Busca archivos que contengan 'TODO'"
LILITH: [Found 3 files with matches]
```

### Code Analysis

```
User: "Analiza la cobertura de tests"
LILITH: Coverage: 78%, 3 files below 50% threshold
        - backend/api/routes.py: 45%
        - backend/utils/helpers.py: 32%
        - backend/models/user.py: 28%

User: "Muestra el grafo de dependencias"
LILITH: [Displays interactive graph]
```

### Git Operations

```
User: "Status del repo"
LILITH: On branch main
        3 files modified, 2 staged
        1 commit ahead of origin/main

User: "Haz commit con mensaje 'fix auth bug'"
LILITH: âœ“ Created commit 4a5b6c7
        - 2 files changed, 15 insertions(+), 3 deletions(-)
```

### Documentation

```
User: "Genera el README"
LILITH: âœ“ Created README.md
        Sections: Overview, Installation, Usage, API

User: "Agrega docstrings faltantes"
LILITH: âœ“ Added 12 docstrings
        - 5 functions documented
        - 3 classes documented
```

---

## ðŸ› ï¸ Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [FileManager](docs/SKILLS.md#filemanager) | File operations with safety | âœ… |
| [ProjectScanner](docs/SKILLS.md#projectscanner) | Project analysis & detection | âœ… |
| [TaskTracker](docs/SKILLS.md#tasktracker) | Multi-step task planning | âœ… |
| [CodeRefactor](docs/SKILLS.md#coderefactor) | AST-based transformations | âœ… |
| [TestRunner](docs/SKILLS.md#testrunner) | Test execution & coverage | âœ… |
| [DependencyManager](docs/SKILLS.md#dependencymanager) | Package management | âœ… |
| [GitTools](docs/SKILLS.md#gittools) | Git operations | âœ… |
| [WebBrowser](docs/SKILLS.md#webbrowser) | Web navigation | âœ… |
| [Research](docs/SKILLS.md#research) | Information synthesis | âœ… |
| [DocManager](docs/SKILLS.md#docmanager) | Documentation generation | âœ… |
| [GraphManager](docs/SKILLS.md#graphmanager) | Visualization & graphs | âœ… |

---

## ðŸ—ï¸ Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    PRESENTATION LAYER                        â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  Web UI    â”‚  â”‚   Chat     â”‚  â”‚  Graph Visualization   â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼ HTTP/WebSocket
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      API LAYER (FastAPI)                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  REST API  â”‚  â”‚  WebSocket â”‚  â”‚    Static Files        â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        CORE LAYER                            â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚   Intent   â”‚  â”‚    Tool    â”‚  â”‚     Trust Score        â”‚ â”‚
â”‚  â”‚  Detector  â”‚  â”‚  Registry  â”‚  â”‚      Engine            â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      TOOL LAYER (11 Skills)                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”    â”‚
â”‚  â”‚ File   â”‚ â”‚  Git   â”‚ â”‚  Test  â”‚ â”‚  Web   â”‚ â”‚  Doc   â”‚    â”‚
â”‚  â”‚Manager â”‚ â”‚ Tools  â”‚ â”‚ Runner â”‚ â”‚Browser â”‚ â”‚Manager â”‚    â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”    â”‚
â”‚  â”‚ Projectâ”‚ â”‚  Code  â”‚ â”‚Depend. â”‚ â”‚Researchâ”‚ â”‚ Graph  â”‚    â”‚
â”‚  â”‚Scanner â”‚ â”‚Refactorâ”‚ â”‚Manager â”‚ â”‚        â”‚ â”‚Manager â”‚    â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design documentation.

---

## ðŸ“Š Project Statistics

### Code Metrics

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~15,000+ |
| Python Files | 25+ |
| Frontend Files | 8 |
| Skills Implemented | 11/11 |
| Tools Registered | 19 |

### Test Coverage

| Category | Tests | Pass Rate |
|----------|-------|-----------|
| FileManager | 6 | 100% |
| TaskTracker | 6 | 100% |
| CodeRefactor | 5 | 100% |
| TestRunner | 5 | 100% |
| DependencyManager | 9 | 100% |
| GitTools | 19 | 100% |
| WebBrowser | 14 | 100% |
| Research | 17 | 100% |
| DocManager | 17 | 100% |
| GraphManager | 19 | 100% |
| **Total** | **117** | **100%** |

### Conversational Patterns

| Metric | Value |
|--------|-------|
| Intents | 42 |
| Regex Patterns | 300+ |
| Tool Mappings | 19 |

---

## ðŸ”’ Safety & Trust Score

LILITH implements a sophisticated trust scoring system:

### Risk Levels

| Level | Score | Execution | Examples |
|-------|-------|-----------|----------|
| ðŸŸ¢ LOW | â‰¥0.75 | Automatic | file_read, git_status |
| ðŸŸ¡ MEDIUM | 0.40-0.75 | Confirmation | file_write, git_commit |
| ðŸ”´ HIGH | <0.40 | Blocked | delete, git_push |

### Safety Features

- âœ… Path traversal protection
- âœ… File size limits
- âœ… Protected extensions (.env, .pem, .key)
- âœ… Sandbox directory restriction
- âœ… Operation backups
- âœ… User confirmation for risky operations

---

## ðŸŽ¨ Frontend Features

### Web Interface

- **Chat Interface** - Real-time messaging with WebSocket
- **Skills Dashboard** - Visual cards for all 11 skills
- **Graph Visualization** - Interactive SVG graphs
- **Plans Panel** - Visual task execution tracking
- **History View** - Operation log with filters
- **Trust Score Display** - Real-time trust metrics

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Focus chat input |
| `Ctrl + /` | Toggle right panel |
| `Esc` | Close modals |
| `@` | Mention tool |
| `#` | Reference file |

---

## ðŸ“– Documentation

- [API Documentation](docs/API.md) - REST and WebSocket API reference
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and components
- [Skills Reference](docs/SKILLS.md) - Detailed skill documentation
- [Contributing Guide](docs/CONTRIBUTING.md) - How to contribute

---

## ðŸ¤ Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details on:

- Code style guidelines
- Development setup
- Testing requirements
- Pull request process

### Quick Start for Contributors

```bash
# Fork and clone
git clone https://github.com/yourusername/LILITH.git
cd LILITH

# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate
pip install -r requirements.txt

# Run tests
pytest Backend/tests/ -v

# Start development server
python start_server.py --dev
```

---

## ðŸ—ºï¸ Roadmap

### Phase C - Memory & Context
- [ ] Persistent memory between sessions
- [ ] Long-term conversation context
- [ ] Semantic search with embeddings

### Phase D - Advanced Autonomy
- [ ] Chain-of-thought reasoning
- [ ] Automatic error recovery
- [ ] Hierarchical planning

### Phase E - IDE Integration
- [ ] VS Code extension
- [ ] JetBrains plugin
- [ ] CLI standalone tool

---

## ðŸ“„ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ðŸ™ Acknowledgments

- FastAPI for the excellent web framework
- All contributors who helped improve LILITH
- The open-source community for inspiration

---

## ðŸ“ž Support

- ðŸ’¬ [Discussions](https://github.com/yourusername/LILITH/discussions)
- ðŸ› [Issues](https://github.com/yourusername/LILITH/issues)
- ðŸ“§ Email: support@example.com

---

<p align="center">
  <strong>LILITH v2.1</strong> - Operator-class AI Assistant<br>
  Built with â¤ï¸ for developers<br>
  <br>
  <a href="https://github.com/yourusername/LILITH">GitHub</a> â€¢
  <a href="docs/README.md">Documentation</a> â€¢
  <a href="docs/CONTRIBUTING.md">Contribute</a>
</p>
