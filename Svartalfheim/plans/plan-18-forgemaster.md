# ForgeMaster — Plan de Arranque v1.0

> **Estado actual:** v0.1.0, 176 tests pasando, 8 comandos CLI funcionales
> **Ubicacion:** `Muspelheim/ForgeMaster`

## FASE 1 — Release Blockers (2-3 sesiones)

### 1.1 LICENSE + CHANGELOG
- [ ] Crear `LICENSE` (MIT, igual que pyproject.toml)
- [ ] Crear `CHANGELOG.md` con entrada v0.1.0

### 1.2 README Completo
- [ ] Instalacion (`pip install -e .`)
- [ ] Comandos con ejemplos (`forgemaster scan`, `forgemaster gpu`, etc.)
- [ ] Configuracion (paths por defecto, GPU profiles)
- [ ] Screenshots/salida de ejemplo con Rich

### 1.3 Config File Support
- [ ] Crear `forgemaster/config.py` con carga de `~/.forgemaster/config.yaml`
- [ ] Defaults: scan_dirs, gpu_profile, catalog_path
- [ ] Comando `forgemaster config` para ver/editar

### 1.4 Test Infrastructure
- [ ] Crear `tests/conftest.py` con fixtures compartidos
- [ ] Agregar `pytest-asyncio` a dev deps (si se necesita async)

### 1.5 Type Checking
- [ ] Agregar `mypy` o `pyright` a dev deps
- [ ] Crear `pyproject.toml` config para type checking
- [ ] Ejecutar y corregir errores

## FASE 2 — Feature Gaps (2-3 sesiones)

### 2.1 Structured Logging
- [ ] Modulo `forgemaster/logging.py` con Rich handler
- [ ] Log levels: DEBUG, INFO, WARNING, ERROR
- [ ] Opcion `--verbose` / `--quiet` en CLI

### 2.2 Model Metadata desde Archivos
- [ ] Leer GGUF headers para architecture real
- [ ] Leer safetensors metadata
- [ ] Leer config.json de HuggingFace
- [ ] Fallback a filename parsing (actual)

### 2.3 Download --list-only
- [ ] Flag `forgemaster download --list-only <model_id>`
- [ ] Mostrar archivos disponibles sin descargar

### 2.4 CI Pipeline
- [ ] GitHub Actions: lint (ruff), type-check, test
- [ ] Reutilizar workflow existente de Yggdrasil

## FASE 3 — Polish (1-2 sesiones)

### 3.1 Shell Completion
- [ ] Configurar Typer shell completions (bash, zsh, fish)

### 3.2 Cross-Platform GPU
- [ ] Fallback para AMD (rocm-smi) y Apple Silicon
- [ ] Mensaje graceful quando nvidia-smi no disponible

### 3.3 Progress Bars
- [ ] Rich progress para SHA256 en dupes scan
- [ ] Rich progress para download (ya existe parcial)

### 3.4 Version Bump
- [ ] Actualizar `__init__.py` y `pyproject.toml` a v1.0.0
- [ ] Tag `v1.0.0` en git

---

*Fecha: 2026-05-03*
