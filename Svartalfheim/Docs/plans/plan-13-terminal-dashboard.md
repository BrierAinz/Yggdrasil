# TerminalDashboard — Plan de Arranque v1.0

> **Estado actual:** 6 modulos, 132 tests (114 pass, 18 fail), TUI funcional con Textual
> **Ubicacion:** `Alfheim/TerminalDashboard`

## Problemas Criticos (Bloqueantes)

### P0.1 — pytest-asyncio faltante (16 tests fallan)
- [ ] Agregar `pytest-asyncio>=0.23` a dev deps en `pyproject.toml`
- [ ] Agregar `[tool.pytest.ini_options]` con `asyncio_mode = "auto"`
- [ ] Verificar que los 14 tests async de `test_app.py` pasan
- [ ] Verificar que los 2 tests async de `test_updater.py` pasan

### P0.2 — Scanner auto-detection roto (1 test falla)
- [ ] Fix: `scanner.py` camina 2 niveles desde `__file__` pero deberia caminar mas
- [ ] Alternativa: hacer que `RealmScanner()` default use `YGGDRASIL_ROOT` env var primero
- [ ] Fix: `test_default_base_path` — ajustar asercion o usar temp path con env var
- [ ] Verificar que todos los 132 tests pasan tras los fixes

### P0.3 — psutil import implicito
- [ ] Agregar `psutil>=5.9` a dependencies en `pyproject.toml`
- [ ] Verificar que `health.py` importa correctamente

## FASE 1 — Estabilizacion (1-2 sesiones)

### 1.1 Test Infrastructure
- [ ] Crear `tests/conftest.py` con fixtures compartidos:
  - `temp_yggdrasil()` — crear arbol temporal de 9 reinos
  - `mock_gpu()` — fixture para nvidia-smi mock
  - `scanner()` — RealmScanner con temp path
- [ ] Agregar `anyio` o `pytest-asyncio` correctamente configurado
- [ ] Todos los 132 tests pasando

### 1.2 CI Pipeline
- [ ] GitHub Actions para TerminalDashboard
- [ ] Test matrix: Python 3.10, 3.11, 3.12
- [ ] Reutilizar workflow pattern de ForgeMaster/Lilith

### 1.3 Coverage Basico
- [ ] `pytest-cov` con umbral minimo (ej. 70%)
- [ ] Agregar config en `pyproject.toml`

## FASE 2 — Features Completas (2-3 sesiones)

### 2.1 Env Config Documentacion
- [ ] Documentar `YGGDRASIL_ROOT` env var en README
- [ ] Crear `.env.example` con defaults
- [ ] Agregar soporte para config file (`~/.yggdrasil/config.yaml`)

### 2.2 Dashboard Features
- [ ] Completar `realm_views.py` — vistas detalladas por reino
- [ ] Agregar vista de actividad git (commits recientes)
- [ ] Agregar vista de dependencias entre reinos
- [ ] Teclas regex para filtrar proyectos en sidebar

### 2.3 Health Monitor Extendido
- [ ] Temperature monitoring (si nvidia-smi lo reporta)
- [ ] Process tree por reino
- [ ] Alerts cuando disco/VRAM supera umbral

## FASE 3 — Polish (1-2 sesiones)

### 3.1 README Completo
- [ ] Instalacion, uso, screenshots, configuracion
- [ ] Gif/asciinema de demo

### 3.2 Completions y Packaging
- [ ] Shell completion para los comandos
- [ ] Version bump a v1.0.0
- [ ] Tag `v1.0.0`

---

*Fecha: 2026-05-03*
