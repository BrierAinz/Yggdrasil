# Plan: FASE 1 - Skills Framework v2.0

## Goal
Implementar un sistema de skills con hot-reload, auto-trigger y formato YAML+Markdown (inspirado en Superpowers + jcode).

## Scope
- IN: Skill parser, registry, hot-reload, auto-trigger, migracion de skills existentes
- OUT: Dashboard UI para skills, skill marketplace, skill versioning avanzado

## Files
- `Lilith/Core/skill_parser.py` - Parsear skills YAML+Markdown
- `Lilith/Core/skill_registry.py` - Registro con hot-reload
- `Lilith/Core/skill_watcher.py` - File watcher con watchdog
- `Lilith/Core/tests/test_skill_parser.py` - Tests parser
- `Lilith/Core/tests/test_skill_registry.py` - Tests registry
- `Lilith/Core/orchestrator.py` - Modificar para auto-trigger
- `Lilith/Core/config.py` - Agregar skills_dir
- `~/.lilith/skills/` - Directorio de skills del usuario
- `docs/superpowers/skills/` - Skills del proyecto (ya creados)

## Dependencies
- Ninguna (Foundation ya completa)

## Tasks
- [ ] Task 1: Instalar watchdog en requirements.txt (5 min)
- [ ] Task 2: Crear skill_parser.py con YAML frontmatter + markdown body (30 min)
- [ ] Task 3: Crear skill_registry.py con carga inicial (30 min)
- [ ] Task 4: Crear skill_watcher.py con watchdog para hot-reload (20 min)
- [ ] Task 5: Integrar auto-trigger en orchestrator.py (20 min)
- [ ] Task 6: Actualizar config.py con skills_dir (10 min)
- [ ] Task 7: Migrar skills de docs/superpowers/skills/ a formato nuevo (15 min)
- [ ] Task 8: Crear tests para parser y registry (30 min)
- [ ] Task 9: Probar hot-reload manualmente (15 min)
- [ ] Task 10: Commit (5 min)

## Tests
- skill_parser: parsear skill valido, skill invalido, skill sin frontmatter
- skill_registry: cargar skills, buscar por trigger, hot-reload detecta cambios
- orchestrator: skills se inyectan en contexto
- integration: modificar archivo skill, verificar reload en <1s

## Rollback
- Revert commit o restaurar archivos originales de orchestrator.py y config.py

## Notes
- watchdog usa threads, no asyncio. Usar asyncio.run_in_executor si es necesario.
- Los skills del proyecto estan en docs/superpowers/skills/ (formato antiguo)
- Los skills del usuario iran en ~/.lilith/skills/ (formato nuevo)
- Auto-trigger: escanear triggers contra input del usuario
