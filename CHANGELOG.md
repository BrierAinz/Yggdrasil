# Changelog

All notable changes to the Yggdrasil project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.1.0] - 2026-05-04

### Changed
- **Build system**: Migrated all workspace packages from setuptools to hatchling
- **Ruff**: Updated target-version from py39 to py311; auto-fixed UP038/UP007 modernizations
- **CI**: Added Python 3.12 matrix, updated ruff-pre-commit to v0.11.8, added check-toml/check-merge-conflict/detect-private-key hooks
- **pytest.ini**: Removed stale --ignore entries, added TerminalDashboard to testpaths
- **Workspace**: Added TerminalDashboard, AutoSub, ForgeMaster to uv.workspace.members
- **Code quality**: Replaced print() with logging in lilith-api, lilith-orchestrator, ForgeMaster
- **Code quality**: Fixed hardcoded /mnt/d path in ForgeMaster (now uses COMFYUI_MODELS_DIR env var)
- **Code quality**: Replaced TODO comments with NotImplementedError in Alfheim dashboard app.py
- **Code quality**: Added module docstrings to lilith-tools and vanaheim-framework modules

### Fixed
- **lilith-cli**: Version mismatch (pyproject 2.0.0 → 2.1.0 to match __init__.py)
- **lilith-orchestrator**: Added missing gateway/__init__.py
- **Pre-commit**: Updated exclude regex, added check-toml and detect-private-key hooks
- **CI**: Added Alfheim/TerminalDashboard, Muspelheim/AutoSub, ForgeMaster to install steps

### Added
- **pyproject.toml**: Added [project.urls] Repository, license, readme fields to all packages
- **pyproject.toml**: Added README.md to all packages that were missing it

## [Unreleased]

### Added
- MIT License
- Interactive architecture diagram (`docs/architecture.html`)
- GitHub Pages deployment via GitHub Actions
- `CONTRIBUTING.md` with realm-specific guidelines
- `CHANGELOG.md`
- `uninstall.bat` for clean removal of Lilith CLI
- Eir AI Influencer project (Muspelheim) — ComfyUI setup, LoRA pipeline, IG captions
- Swarm lifecycle documentation (dual architecture: v4 legacy + v5 refactored)

### Changed
- **CI**: Fixed ForgeMaster workflow path from `Niflheim/` to `Muspelheim/`
- **Website**: Replaced all `YOUR_USERNAME` placeholders with `BrierAinz`
- **Website**: Updated installation instructions to match current project structure (Asgard/Lilith v5)
- **Website**: Fixed duplicated "Configure environment" step in setup page
- **Website**: Migrated visible references from Hermes to Lilith (HTML, CSS classes, env vars)
- **README**: Rewrote with current ecosystem state — dual Swarm architecture, v5 packages, realm table
- **README**: Updated Quick Start to reference `Asgard/Lilith` instead of `Asgard/Hermes-Lilith`
- **CLI**: Rewrote `install.bat` with PowerShell PATH registration (avoids `setx` truncation bug)
- **CLI**: Added reinstall detection and PowerShell wrapper (`lilith.ps1`)
- **CLI**: Added argparse to `Lilith/main.py` with `--help`, `--version`, `--no-banner`, `--streaming`, `--cwd`
- **README**: Added real badges (License, Python, Stars, Last Commit, Repo Size)
- **README**: Updated all links to point to correct paths
- **TerminalDashboard**: Replaced hardcoded `/mnt/d/Proyectos/Yggdrasil` with env var `YGGDRASIL_ROOT` + auto-detection
- **setup.sh**: Reformatted with proper line breaks for `pip install -e` commands
- **Vanaheim**: Removed duplicate loose agent files (`adan_vanaheim.py`, etc.) — canonical versions in subdirs
- `main` branch renamed from `master`

### Fixed
- **CI**: ForgeMaster test path corrected (`Niflheim/ForgeMaster` → `Muspelheim/ForgeMaster`)
- **Website**: `HERMES_PATH` env var renamed to `LILITH_PATH` in setup page
- **Website**: Code snippets updated from `Asgard/Hermes-Lilith` to `Asgard/Lilith`
- **Dashboards**: Replaced hardcoded `D:\Proyectos\Yggdrasil` paths with relative paths in README

### Removed
- `health-check.py` duplicate (hyphen version, 1533 bytes) — kept `health_check.py` (4532 bytes)
- SQLite database files from git tracking (`chroma.sqlite3`)
- Obsolete `pip install -e Asgard/lilith-core` references from documentation
- Tracked `.pyc` and `__pycache__` files from root and Bots_Lilith_v5
- `.yggdrasil_state.json` removed from git tracking (gitignored)
- Duplicate Vanaheim agents (standalone files superseded by subdirectory versions)
- `.egg-info` and `.pytest_cache` from git tracking

## [2.1.0] - 2026-04-30

### Added
- Enhanced memory system with sentence-transformers embeddings
- Vector storage in SQLite with cosine similarity search
- Automatic compression of old conversation history
- Entity extraction (technologies, projects)
- Error tracking with solutions
- Context injection into orchestrator prompts
- Dynamic CLI banner (shows active model and tool count)
- `config.py` auto-detection for LM Studio models

### Changed
- Memory system migrated to `EnhancedMemory` class
- CLI theme updated with Dark Fantasy ANSI palette

## [2.0.0] - 2026-04-20

### Added
- Initial release of Lilith v2.0
- Plugin system (`Lilith.Plugins`)
- RAG engine for document indexing
- Task scheduler with cron-like syntax
- Sub-agent system (`Lilith.Agents`)
- Notification system (Windows native + console fallback)
- Tool arsenal: 30+ tools across 7 categories
- GitHub integration tools

---

[Unreleased]: https://github.com/BrierAinz/Yggdrasil/compare/v5.1.0...HEAD
[5.1.0]: https://github.com/BrierAinz/Yggdrasil/compare/v2.1.0...v5.1.0
[2.1.0]: https://github.com/BrierAinz/Yggdrasil/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/BrierAinz/Yggdrasil/releases/tag/v2.0.0
