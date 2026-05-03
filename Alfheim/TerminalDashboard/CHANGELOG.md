# Changelog

All notable changes to TerminalDashboard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-03

### Added

- **Typer CLI** (`tui/cli.py`) with shell completion support for Bash, Zsh,
  Fish, and PowerShell via `--install-completion` / `--show-completion`.
- `--version` / `-v` flag on the CLI to print the dashboard version.
- Comprehensive README.md with installation, usage, configuration,
  architecture overview, shell completion instructions, and Rich console
  markup screenshot previews.
- CHANGELOG.md for tracking release history.
- Norse dark-fantasy branding throughout: gold accent (#c8a23e), realm icons,
  rune motifs, Tokyonight-inspired palette.

### Changed

- Entry point changed from `tui.app:main` to `tui.cli:app` (Typer app).
  The dashboard is now launched via `yggdrasil-dashboard` which delegates
  to the Typer CLI, providing completion and version flags.
- Version bumped from 0.1.0 to **1.0.0**.
- `typer>=0.9.0` added as a core dependency.

### Fixed

- All 182 tests pass with the new entry point and CLI module.

---

## [0.1.0] - 2025-04-01

### Added

- Initial release of Yggdrasil Terminal Dashboard.
- Textual-based TUI with 9-realm sidebar navigation and detail views.
- `RealmScanner` for discovering projects under Yggdrasil realm directories.
- `HealthMonitor` for system health (CPU, RAM, GPU, disk, Python processes).
- `DashboardUpdater` with async auto-refresh and change detection + flash.
- `QuickActions` for keyboard-driven operations (tests, git, health, vscode, docs).
- `GitActivity` helpers for per-realm git log and status.
- Per-realm detail panels (`RealmDetailView`) with git activity and
  realm-specific sections.
- System health panel with Rich renderables and progress indicators.
- Dark Norse theme CSS (`styles.tcss`) with gold accents and dark backgrounds.
- Sidebar filter with regex support for quick realm search.
- Number keys 1-9 for direct realm switching.
- Refresh action (`r`) to rescan all realms.
- 182 unit and integration tests with ≥70% coverage requirement.

[1.0.0]: https://github.com/user/yggdrasil/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/user/yggdrasil/releases/tag/v0.1.0
