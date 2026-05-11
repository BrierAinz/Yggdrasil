# Yggdrasil Cleanup & Refinement — May 2026

## Summary

Three commits across two sessions (cleanup + refinement). All pushed to main.

## Commits

1. `32f768b` — `chore: limpieza y correcciones Yggdrasil`
   - CI: ForgeMaster path Niflheim→Muspelheim in `.github/workflows/ci.yml`
   - Removed `health-check.py` (hyphen, 1533 bytes) — `health_check.py` (underscore) is canonical
   - Removed 4 duplicate Vanaheim agents (`adan_vanaheim.py`, etc. — subdirectory versions are canonical)
   - Updated `.yggdrasil_state.json` with real git-tracked file counts
   - Website: 3 HTML files updated (paths from Asgard/Hermes-Lilith→Asgard/Lilith)
   - Removed tracked cache files (__pycache__, .egg-info, .pytest_cache from git)

2. `0f604a2` — `refactor: refinamiento del ecosistema Yggdrasil`
   - README.md rewritten: v5 architecture, realm table, Swarm dual, quickstart
   - CHANGELOG.md: Unreleased section with 20+ items
   - REGLAS_YGGDRASIL.md: v3.1, Swarm dual documented, Muspelheim projects listed
   - TerminalDashboard scanner.py: env var YGGDRASIL_ROOT + auto-detect instead of hardcoded path
   - Dashboards README: relative paths instead of D:\
   - SETUP.md: LILITH_WORKSPACE corrected from Midgard to Yggdrasil
   - setup.sh: reformatted for readability
   - .yggdrasil_state.json: removed from git tracking (gitignored)
   - Midgard __pycache__ cleaned

3. `5f21401` — `docs: planes de arranque + legacy disclaimer`
   - Hermes-Lilith LEGACY.md created (stale paths documented, migration map)
   - Hermes-Lilith README.md tagged as "Legacy v4"
   - ForgeMaster plan-18 created (3 phases to v1.0)
   - TerminalDashboard plan-13 created (P0 fixes + 3 phases)

## Git GC Result

`git gc --aggressive --prune=now` ran for ~10 minutes:
- Before: `.git` = 1.9 GB
- After: `.git` = 7.1 MB

## Key Decisions

- **Website stays as static HTML** — Docusaurus migration deferred, not needed for 4 pages
- **Hermes-Lilith legacy paths NOT changed** — 16 files with `D:\Proyectos\Midgard` left as-is since it's a frozen archive, documented in LEGACY.md
- **ForgeMaster v1.0 blockers**: LICENSE, README, config file support, type checking
- **TerminalDashboard P0**: pytest-asyncio missing (16 test failures), scanner auto-detect broken (1 failure), psutil not in deps

## Stale Paths in Hermes-Lilith (Legacy v4)

These files contain `D:\Proyectos\Midgard` references but are NOT being changed (frozen archive):

| File | Stale Path |
|------|-----------|
| `Lilith/Hermes/hermes_config.yaml` | `D:\Proyectos\Midgard\Lilith\Hermes\mcp_bridge.py` |
| `Lilith/Hermes/README.md` | `D:\Proyectos\Midgard\Lilith\Hermes\mcp_bridge.py` |
| `Lilith/README.md` | `cd D:\Proyectos\Midgard\Lilith` |
| `Lilith/launch_lilith.ps1` | `$ProjectRoot = "D:\Proyectos\Midgard"` |
| `SETUP.md` | Fixed: `D:\Proyectos\Yggdrasil` |
| `skills/automation/SKILL.md` | `D:\Proyectos\Midgard\automation\` |