# Plan de Organización Yggdrasil — Mega Cleanup & Professionalización

> **Objetivo**: Dejar el repo impecable — consistente, profesional, sin basura, sin duplicados, con READMEs actualizados y la marca "Lilith" (sin "Hermes") limpia en toda la documentación visible.

---

## FASE A: Auditoría y Limpieza de Git (Prioridad ALTA)

### A1. Remover archivos binarios/sucios de git tracking
- [ ] Remover `Asgard/Hermes-Lilith/memory/lilith_memory.db` (384KB SQLite DB)
- [ ] Remover `Asgard/Lilith/Data/attention_stack.db` (20KB)
- [ ] Remover `Asgard/Lilith/Data/memory/sessions.db` (44KB)
- [ ] Remover `Asgard/Lilith/Data/memory/user_profiles.db`
- [ ] Remover `Asgard/Lilith/Data/personality_modes.db`
- [ ] Actualizar `.gitignore`: añadir `**/*.db`, `**/*.sqlite`, `**/*.sqlite3`, `Asgard/Lilith/Data/**/*.db`
- [ ] `git rm --cached` en cada archivo, luego commit

### A2. Remover .minimax/ (skill de herramienta externa, no pertenece al repo)
- [ ] Añadir `.minimax/` al `.gitignore`
- [ ] `git rm -r --cached Asgard/Hermes-Lilith/.minimax/`
- [ ] Commit: `[ASGARD] chore: remove .minimax skills from tracking`

### A3. Remover tar.gz backup antiguo
- [ ] `Asgard/Lilith_backup_pre_refactor_20260403_145209.tar.gz` — ya está en .gitignore pero verificar
- [ ] Si está tracked: `git rm --cached` + añadir patrón al .gitignore

### A4. Remover build artifacts del VSCode extension
- [ ] `Alfheim/VSCode_Extension_Lilith/out/extension.js` — build artifact
- [ ] `Alfheim/VSCode_Extension_Lilith/lilith-assistant-0.1.0.vsix` — packaged extension
- [ ] Añadir `out/` y `*.vsix` al .gitignore de Alfheim
- [ ] `git rm --cached` en ambos

### A5. Limpiar Vanaheim raíz
- [ ] `Vanaheim/server.log` — no debería estar tracked
- [ ] `Vanaheim/bot_registry.json` — duplicado de Config/
- [ ] `Vanaheim/launch.py`, `Vanaheim/launcher.py`, `Vanaheim/server.py` — deprecated si existe vanaheim-framework
- [ ] Evaluar si `Vanaheim/bots/echo_bot.py` es legacy

### A6. Limpiar Svartalfheim/Scripts obsolete
- [ ] Evaluar scripts en `Svartalfheim/Scripts/` — muchos son tests temporales (`test_*.py`)
- [ ] Mover tests válidos a un directorio `tests/`
- [ ] Eliminar scripts de debug temporal (test_api_env.py, test_kimi_*.py, etc.)

---

## FASE B: Actualizar READMEs (Prioridad ALTA)

### B1. README.md raíz — Actualizaciones críticas
- [ ] Reemplazar "Hermes-Lilith" → "Lilith" en texto visible (mantener paths)
  - Línea 30: "Hermes-Lilith" → "Lilith"
  - Línea 109: tabla de reinos "Hermes-Lilith" → "Lilith"
  - Línea 135: diagrama "Hermes-Lilith (Orchestrator)" → "Lilith (Orchestrator)"
  - Línea 148: "## Hermes-Lilith Features" → "## Lilith Features"
  - Línea 166: "Hermes-Lilith is now..." → "Lilith is now..."
  - Línea 186: link hermes-lilith.html (mantener URL, solo cambiar anchor text)
- [ ] Actualizar Hardware Requirements: RTX 3060 12GB (dice 4GB!)
- [ ] Actualizar Quick Start: reflejar estructura modular actual
- [ ] Añadir sección de agentes (Pantheon) con enlace a la web
- [ ] Añadir mención de AutoSub, ForgeMaster, Eir

### B2. Asgard/README.md — Desactualizado
- [ ] "4.5 GB | 516 Python" — verificar tamaño actual
- [ ] Lista de proyectos incluye "ObsidianConnect" y "Web-AI-Chat" que NO EXISTEN
- [ ] "Hermes-Lilith" → "Lilith" en texto visible (mantener paths)
- [ ] Estructura de carpetas obsoleta — actualizar a modular packages
- [ ] Añadir lilith-core, lilith-memory, lilith-tools, lilith-orchestrator, lilith-api, lilith-cli
- [ ] Añadir sección de Launcher (LILITH.bat)

### B3. REGLAS_YGGDRASIL.md — Revisar consistencia
- [ ] La nomenclatura `[tipo]_[nombre]_[estado]/` no se sigue en ningún proyecto real
- [ ] Los nombres actuales usan PascalCase (AutoSub, ForgeMaster) no snake_case
- [ ] Decidir: ¿actualizar regla a PascalCase o renombrar proyectos?
- [ ] Verificar que los reinos listados coincidan con los directorios reales
- [ ] Actualizar conteos de Archivos (ya no son 62,272)

### B4. Realm READMEs — Armonizar formato
Todos los realm READMEs deben tener formato consistente:
```markdown
# 🏰 Nombre del Reino — Emoji

> **Propósito:** Una línea clara
> **Estado:** ACTIVO / ARCHIVO / VACÍO

## Proyectos

| Proyecto | Estado | Descripción |
|----------|--------|-------------|

## Reglas Específicas
- Regla 1
- Regla 2

## Notas
- Cualquier nota importante
```

- [ ] Asgard/README.md — Reescribir completamente
- [ ] Alfheim/README.md — Actualizar con dashboard HTMX
- [ ] Vanaheim/README.md — Actualizar con vanaheim-framework modular
- [ ] Muspelheim/README.md — Añadir AI-Influencer, AutoSub, docs
- [x] Niflheim/README.md — Actualizar con ForgeMaster movido a Muspelheim
- [ ] Midgard/README.md — Actualizar con Finanzas, Habits, Recipes
- [ ] Helheim/README.md — Republicar Graveyard actualizado
- [ ] Jotunheim/README.md — Actualizar estado (vacío pero con propósito)
- [ ] Svartalfheim/README.md — Actualizar knowledge base

---

## FASE C: Estructura y Consistencia (Prioridad MEDIA)

### C1. Resolver duplicado Asgard/Lilith vs Asgard/Hermes-Lilith
- [ ] **NO RENOMBRAR** — mantener ambos directorios como están
- [ ] Añadir `Asgard/Hermes-Lilith/README.md` nota: "Legacy monolith, superseded by modular packages (lilith-core, lilith-memory, etc.)"
- [ ] Añadir `Asgard/Lilith/README.md` nota: "Legacy v5 monolith, refactored into Hermes-Lilith v4.x modular"
- [ ] Verificar que .gitignore excluye ambos adecuadamente

### C2. Asgard/Dashboards — Legacy o activo?
- [ ] Evaluar: `Asgard/Dashboards/web/` (React) vs `Alfheim/dashboard/` (HTMX)
- [ ] Si Dashboards está muerto: mover a Helheim
- [ ] Si se mantiene: actualizar README de Asgard

### C3. Vanaheim duplicados
- [ ] `Vanaheim/bots/` vs `Vanaheim/Bots_Lilith_v5/` — ¿cuál es el activo?
- [ ] `Vanaheim/bot_registry.json` vs `Vanaheim/Config/bifrost.json` — consolidar
- [ ] `Vanaheim/server.py`, `Vanaheim/launch.py`, `Vanaheim/launcher.py` — deprecated?
- [ ] Limpiar o archivar los que sean legacy

### C4. Limpiar Niflheim/Datasets
- [ ] `Niflheim/Datasets/cifar-10-batches-py/` — ¿debería estar en git?
- [ ] `Niflheim/Datasets/cifar-10-python.tar.gz` — 163MB en git???
- [ ] Añadir `Niflheim/Datasets/` al .gitignore (ya está pero verificar)
- [ ] Evaluar si Models/Lilith_v5_models/ está correctamente ignorado

### C5. docs/ raíz
- [ ] `docs/API.md` — ¿está actualizado con la API modular?
- [ ] `docs/ARCHITECTURE.md` — ¿refleja la estructura modular v4?
- [ ] `docs/TUTORIALS.md` — ¿existe y está actualizado?
- [ ] `docs/github-presence-guide.md` —ántelo o integre en CONTRIBUTING
- [ ] `docs/profile-readme.md` — ¿para GitHub profile? Mantener o mover

### C6. Raíz archivos sueltos
- [ ] `scripts/__pycache__/` — añadir al .gitignore o limpiar
- [ ] `scripts/bump-version.py` — mantener, útil
- [ ] `scripts/clean.py` — mantener, útil
- [ ] `.yggdrasil_state.json` — ¿es necesario en git?

---

## FASE D: Branding "Lilith" consistente (Prioridad ALTA)

### D1. README.md raíz — Ya listado en B1
### D2. Website — Ya completado en sesiones anteriores
### D3. Docs internos
- [ ] `docs/ARCHITECTURE.md` — reemplazar "Hermes-Lilith" visible
- [ ] `docs/API.md` — verificar referencias
- [ ] `SECURITY.md` — verificar referencias
- [ ] `CONTRIBUTING.md` — verificar referencias
- [ ] `CODEOWNERS` — verificar
- [ ] `CODE_OF_CONDUCT.md` — verificar

### D4. Package naming
- [ ] Los packages Python se llaman `lilith-*` (correcto, no cambiar)
- [ ] El directorio se llama `Hermes-Lilith/` (no renombrar, rompe URLs)
- [ ] Verificar que todos los README usan "Lilith" como nombre visible del agente

---

## FASE E: .gitignore robusto (Prioridad ALTA)

### E1. Actualizar .gitignore raíz
Añadir:
```
# Data files (never track DBs)
**/*.db
**/*.sqlite
**/*.sqlite3
**/*.db-journal

# AI/ML generated outputs
Muspelheim/AI-Influencer/outputs/**/*.png
Muspelheim/AI-Influencer/outputs/**/*.jpg
Muspelheim/AI-Influencer/outputs/**/*.webp

# Skills cache (tool-specific)
.minimax/
.claude/
.hermes/

# Legacy archives
Asgard/**/*.tar.gz
Helheim/Archives_*/
Helheim/Quarantine_*/

# VS Code extension build
Alfheim/VSCode_Extension_Lilith/out/
Alfheim/VSCode_Extension_Lilith/*.vsix

# Vanaheim runtime
Vanaheim/server.log
Vanaheim/**/*.pyc

# Scripts cache
__pycache__/
scripts/__pycache__/

# State files
.yggdrasil_state.json
```

### E2. `git rm --cached` todos los archivos que ahora ignora
```bash
git rm -r --cached Asgard/Hermes-Lilith/.minimax/
git rm --cached Asgard/Hermes-Lilith/memory/lilith_memory.db
git rm --cached Asgard/Lilith/Data/attention_stack.db
git rm --cached Asgard/Lilith/Data/memory/sessions.db
git rm --cached Asgard/Lilith/Data/memory/user_profiles.db
git rm --cached Asgard/Lilith/Data/personality_modes.db
git rm --cached Alfheim/VSCode_Extension_Lilith/lilith-assistant-0.1.0.vsix
git rm --cached Alfheim/VSCode_Extension_Lilith/out/extension.js
```

---

## FASE F: Calidad final (Prioridad BAJA)

### F1. Pre-commit hooks
- [ ] Verificar que `.pre-commit-config.yaml` incluye black, isort, ruff, trailing whitespace
- [ ] `ruff.toml` — ¿Existe? Si no, crear con config básica
- [ ] Ejecutar `pre-commit run --all-files` y corregir resultados

### F2. CI/CD
- [ ] `.github/workflows/ci.yml` — verificar que testea los packages modulares
- [ ] `.github/workflows/deploy-website.yml` — verificar que deploya correctamente
- [ ] `.github/workflows/release.yml` — verificar que crea releases correctamente

### F3. GitHub metadata
- [ ] `CODEOWNERS` — actualizar con @BrierAinz
- [ ] `SECURITY.md` — verificar que está actualizado
- [ ] `CONTRIBUTING.md` — actualizar con convenciones Lilith
- [ ] Issue templates — verificar que están correctos
- [ ] PR template — verificar

### F4. Commits de limpieza
Después de cada fase, hacer un commit con prefijo de realm:
```bash
[ASGARD] chore: remove DB files from tracking, update .gitignore
[ALFHEIM] chore: remove VSCode extension build artifacts
[SVARTALFHEIM] docs: update all READMEs, rebrand Hermes-Lilith → Lilith
[VANAHEIM] chore: clean up duplicate directories, deprecate legacy files
[MIDGARD] docs: update Midgard README with current projects
[HEIMHEIM] chore: git rm cached cleanup
```

---

## ORDEN DE EJECUCIÓN

1. **FASE A** (Git cleanup) — 30 min
2. **FASE E** (.gitignore) — 10 min
3. **FASE D** (Branding Lilith) — 30 min
4. **FASE B** (README updates) — 60 min
5. **FASE C** (Structure consistency) — 45 min
6. **FASE F** (Quality final) — 30 min

**Total estimado**: ~3.5 horas

---

*Plan generado para la instancia de organización de Yggdrasil.*
