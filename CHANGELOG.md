# Changelog

All notable changes to the Yggdrasil project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MIT License
- Interactive architecture diagram (`docs/architecture.html`)
- GitHub Pages deployment via GitHub Actions
- `CONTRIBUTING.md` with realm-specific guidelines
- `CHANGELOG.md`
- `uninstall.bat` for clean removal of Lilith CLI

### Changed
- **Website**: Replaced all `YOUR_USERNAME` placeholders with `BrierAinz`
- **Website**: Updated installation instructions to match current project structure
- **Website**: Fixed duplicated "Configure environment" step in setup page
- **CLI**: Rewrote `install.bat` with PowerShell PATH registration (avoids `setx` truncation bug)
- **CLI**: Added reinstall detection and PowerShell wrapper (`lilith.ps1`)
- **CLI**: Added argparse to `Lilith/main.py` with `--help`, `--version`, `--no-banner`, `--streaming`, `--cwd`
- **README**: Added real badges (License, Python, Stars, Last Commit, Repo Size)
- **README**: Updated all links to point to correct paths
- `main` branch renamed from `master`

### Removed
- SQLite database files from git tracking (`chroma.sqlite3`)
- Obsolete `pip install -e Asgard/lilith-core` references from documentation

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

[Unreleased]: https://github.com/BrierAinz/Yggdrasil/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/BrierAinz/Yggdrasil/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/BrierAinz/Yggdrasil/releases/tag/v2.0.0
