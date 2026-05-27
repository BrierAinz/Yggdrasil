# Contributing to Yggdrasil

Thank you for your interest in the Yggdrasil ecosystem. This document provides guidelines for contributing to any of the 9 realms.

## Code of Conduct

Be respectful. All contributions are reviewed with the same care regardless of experience level.

## How to Contribute

### Reporting Bugs

Open an issue with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, GPU)

### Suggesting Features

Open an issue using the `enhancement` label. Describe:
- The problem you're solving
- Your proposed solution
- Impact on existing realms

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/realm-description`
3. Make your changes
4. Run tests if available
5. Commit with clear messages (English or Spanish accepted)
6. Push and open a PR against `main`

## Realm-Specific Guidelines

### Asgard (Core Infrastructure)

Changes to `install.bat`, `uninstall.bat`, or the CLI entry point require testing on Windows CMD and PowerShell.

### Vanaheim (AI Agents)

Agent logic changes should include:
- Updated capability descriptions
- Test scenarios in `tests/`

### Lilith (CLI Agent)

Python code follows PEP 8 with these exceptions:
- Line length: 100 characters
- Type hints encouraged but not required
- Docstrings in English for public APIs

## Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(lilith): add --no-banner flag`
- `fix(memory): handle empty embedding fallback`
- `docs(website): update install instructions`

## Questions?

Open a discussion or reach out via the project's communication channels.
