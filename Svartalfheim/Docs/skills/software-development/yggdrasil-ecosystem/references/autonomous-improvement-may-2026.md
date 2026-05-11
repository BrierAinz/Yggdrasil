# Yggdrasil Autonomous Improvement — May 2026

## Summary

Autonomous session to investigate Hermes Agent improvements and Yggdrasil improvements without user intervention. All changes pushed to main.

## Commits (5 total)

1. `b17830a` — **[ASGARD] ruff: fix 13 lint issues, format yggdrasil_cli.py, track 5 plan files**
   - Unused imports, f-string fixes, reformatting
   - INDEX.md, plan-19 through plan-23 now tracked

2. `32ff44a` — **[MIDGARD] remove stray YggdrasilForge/ from repo root**
   - Canonical location is Alfheim/YggdrasilForge/

3. `f125794` — **[ASGARD] ci: remove continue-on-error from pytest, bump checkout to v6**
   - Removed masking of test failures in CI
   - actions/checkout v4→v6

4. `c825df6` — **[ALFHEIM] workspace: add Alfheim/YggdrasilForge to uv workspace members**
   - Root pyproject.toml now includes Alfheim/YggdrasilForge

5. `7cb59f0` — **[ALFHEIM] track YggdrasilForge source + tests (42 files, 6893 lines)**
   - Refactored .gitignore from blanket `Alfheim/YggdrasilForge/` to specific patterns
   - Added backend source (FastAPI routes, models, config, blender_client)
   - Added frontend source (React+Vite+TS, Tailwind, pages, hooks, components)
   - Added 41 new tests: test_blender_routes (14), test_assets_routes (27)

## Dependabot PRs Closed

- #9 postcss 8.5.8→8.5.14 in /Helheim/Dashboards_legacy/web — archived, won't maintain
- #10 picomatch in same directory
- #11 lodash 4.17.23→4.18.1 in same directory
- #12 esbuild+vite in same directory

## Hardcoded Absolute Paths Audit

**89 tracked files** contain hardcoded `D:\Proyectos\Midgard` or `D:\Proyectos\Yggdrasil` absolute paths. Excluding Helheim/archived = **57 active source files**.

### Critical (Python source):
- `Asgard/Lilith/src/core/tools/builtin/pc_tools.py`
- `Asgard/Lilith/src/core/nl_param_extractor.py`
- `Asgard/Lilith/src/core/pc_macros.py`
- `Asgard/Lilith/src/core/planning/planner.py`
- `Asgard/Lilith/src/core/pc_macro_engine.py`
- `Asgard/Lilith/src/api/server.py`, `docs_api.py`, `v1/asgard.py`
- `Asgard/Lilith/src/core/automode/checkpoint_manager.py`, `progress_reporter.py`
- `Asgard/Lilith/src/core/council/session_recorder.py`
- `Asgard/Lilith/src/core/persona/updater.py`
- `Asgard/Lilith/src/rag/doc_indexer.py`
- `Svartalfheim/Scripts/*.py` (11 files)

### Medium (batch/shell):
- `install.bat`, `update.bat`
- `scripts/bats/Lilith_Launcher.bat`, `scripts/bats/start_lilith.bat`

### Recommendation:
Refactor to `PROJECT_ROOT = Path(__file__).resolve().parents[N]` patterns or extract to `.env` / `pyproject.toml`.

## GitHub Pages

- Configured but **never deployed**
- URL: https://brierainz.github.io/Yggdrasil/
- Workflow: `deploy-website.yml` triggers on `website-v2/**` or `workflow_dispatch`
- To deploy: `gh workflow run deploy-website.yml`

## Security Alerts

10 Dependabot vulnerabilities on default branch (2 high, 8 moderate).
See: https://github.com/BrierAinz/Yggdrasil/security/dependabot

## Unresolved

- CI still failing after fixes (needs debug — likely pyright or test discovery)
- Hermes Agent 691 commits behind v0.13.0 — requires `hermes update` and possible config migration