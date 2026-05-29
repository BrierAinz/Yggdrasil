---
sidebar_position: 6
title: Changelog
---

# Changelog

## v5.1.0 — 2026-05-04

### Changed
- Build system: Migrated all packages from setuptools to hatchling
- Ruff: Updated target-version to py311
- CI: Added Python 3.12 matrix
- Code quality: Replaced print() with logging across packages

### Fixed
- lilith-cli: Version mismatch (pyproject 2.0.0 -> 2.1.0)
- lilith-orchestrator: Missing gateway/__init__.py

### Added
- pyproject.toml: [project.urls] fields for all packages
- README.md for all packages

## v5.0.0 — 2026-04

### Breaking Changes
- Monolith (83 MB) broken into 8 lilith-* packages
- Each package has its own pyproject.toml
- uv workspace for dependency management

## v4.x — 2026-03/04

### Features
- Nordic Frost CLI with Elder Futhark runes
- Animated banner, custom prompt, styled responses
- Advanced memory with Sentence Transformers
- Semantic search across sessions
- Auto-improvement system
- Skill Creator

## v3.x — 2026-02/03

### Features
- Lilith Agent v2 with code execution
- SQLite memory persistence
- Multi-provider LLM support
- Horror GameMaster project started

## v2.x — 2026-01/02

### Features
- Nine Realms architecture defined
- Centralized documentation (Svartalfheim)
- Automation scripts
- Knowledge Base

## Roadmap

### v6.0 (Planned)
- All Asgard packages fully implemented
- Vanaheim autonomous agent framework
- Alfheim React dashboard
- Full i18n (English + Spanish)
