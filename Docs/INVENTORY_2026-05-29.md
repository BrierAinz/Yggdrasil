# Yggdrasil — Inventario Completo
> 2026-05-29

---

## ESTADO POR REALM

### ACTIVO (codigo real, funcionando)

| Proyecto | Realm | Estado | Archivos | Tamano |
|----------|-------|--------|----------|--------|
| Horror-GameMaster | Muspelheim | Fases 1-4 DONE, 2,067 JSONL, 84 tests | 41 | 8.4MB |
| lilith-core | Asgard | Modulos core (config, types, logger, providers) | 8 | 7.8KB |
| lilith-memory | Asgard | Store de memoria | 5 | 3.2KB |
| Knowledge_Base | Svartalfheim | Documentacion Lilith | 101 | 1.1MB |

### ESQUELETO (pyproject.toml + __init__.py, sin logica real)

| Proyecto | Realm | Contenido |
|----------|-------|-----------|
| lilith-api | Asgard | README + __init__ + pyproject |
| lilith-bridge | Asgard | README + __init__ + pyproject + tests/__init__ |
| lilith-cli | Asgard | README + __init__ + pyproject + tests/__init__ |
| lilith-orchestrator | Asgard | README + __init__ + pyproject |
| lilith-skills | Asgard | README + __init__ + pyproject + tests/__init__ |
| lilith-tools | Asgard | README + __init__ + pyproject |
| bifrost | Vanaheim | README + __init__ + pyproject + tests/__init__ |
| vanaheim-framework | Vanaheim | README + __init__ + pyproject + tests/__init__ |

### STUB (solo README)

| Proyecto | Realm | Descripcion |
|----------|-------|-------------|
| AI-Influencer | Muspelheim | "AI-powered social media influencer. Phase 0." |
| AutoSub | Muspelheim | "Automatic subtitle generator. WIP." |
| ForgeMaster | Muspelheim | "ComfyUI workflow manager. WIP." |
| Alfheim | Alfheim | Solo README.md |

### VACIO / OBSOLETO

| Directorio | Tamano | Problema |
|------------|--------|----------|
| tests/ (root) | 0B | Vacio |
| chat_memory/ | 0B | Vacio |
| website-v2/ | 0B | Vacio |
| Niflheim/ | 54B | Solo README |
| Jotunheim/ | 56B | Solo README |
| Midgard/ | 93B | README + scripts/ con 1 archivo |

### DUPLICACION

| Existe en root | Existe en Svartalfheim | Accion sugerida |
|----------------|------------------------|-----------------|
| docs/ (7 files, 57KB) | Docs/ (11 files, 60KB) | Consolidar en Svartalfheim/Docs |
| scripts/ (1 file) | Scripts/ (22 files, 51KB) | Consolidar en Svartalfheim/Scripts |
| wiki/ (31 files, 80KB) | wiki/ (31 files, 80KB) | Mismo contenido, eliminar root |
| plans/ (1 file) | plans/ (23 files, 163KB) | Consolidar en Svartalfheim/plans |
| notes/ (1 file) | — | Mantener o mover a Svartalfheim |

### ARCHIVOS ROOT-LEVEL

| Archivo | Tamano | Descripcion |
|---------|--------|-------------|
| ygg.py | CLI principal de Yggdrasil |
| lilith_agent.py | Agente Lilith |
| lilith_memory.db | Base de datos de memoria |
| REGLAS_YGGDRASIL.md | Reglas globales |

---

## PROBLEMAS IDENTIFICADOS

1. **5 directorios duplicados** entre root y Svartalfheim
2. **3 directorios vacios** (tests, chat_memory, website-v2)
3. **3 stubs en Muspelheim** que no son WIP real (solo README)
4. **8 paquetes esqueleto** en Asgard/Vanaheim sin implementacion
5. **Root-level clutter**: docs, scripts, plans, notes, wiki duplicados
6. **Midgard** casi vacio — 1 archivo en scripts/

---

## PLAN DE LIMPIEZA PROPUESTO

### Paso 1: Consolidar duplicados (safe — solo mover)
- Mover contenido de root docs/ -> Svartalfheim/Docs/
- Mover contenido de root scripts/ -> Svartalfheim/Scripts/
- Mover contenido de root plans/ -> Svartalfheim/plans/
- Mover root notes/ -> Svartalfheim/notes/
- Eliminar root wiki/ (ya existe en Svartalfheim)

### Paso 2: Limpiar vacios (safe — borrar dirs vacios)
- Eliminar tests/ (root, 0B)
- Eliminar chat_memory/ (0B)
- Eliminar website-v2/ (0B)

### Paso 3: Organizar stubs (requiere decision)
- Opcion A: Mover AI-Influencer, AutoSub, ForgeMaster a Helheim/ (archive)
- Opcion B: Mantener en Muspelheim con etiqueta [STUB]
- Opcion C: Eliminar (si no hay planes concretos)

### Paso 4: Paquetes esqueleto (requiere decision)
- Opcion A: Mantener como roadmap visual (saben que existen pero no implementados)
- Opcion B: Mover a Helheim/ hasta que se implementen
- Opcion C: Eliminar y recrear cuando se necesiten
