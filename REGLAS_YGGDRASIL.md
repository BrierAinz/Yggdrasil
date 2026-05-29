<<<<<<< HEAD
# Reglas de Yggdrasil

Leyes fundamentales del ecosistema. Todos los realms las obedecen.

---

## Reglas del Monorepo

1. **Cada realm tiene un proposito.** No mezclar responsabilidades entre reinos.
2. **Svartalfheim es la fuente de verdad.** Toda documentacion vive ahi. Los READMEs de otros realms son resumenes.
3. **Los paquetes lilith-* son modulares.** Cada paquete tiene su propio pyproject.toml y puede instalarse independientemente.
4. **Los scripts van en Scripts/ o Svartalfheim/Scripts/.** No scripts sueltos en la raiz.
5. **Los planes siguen el formato plan-NN-*.md.** Se archivan en plans/ con numeracion secuencial.
6. **Los proyectos muertos van a Helheim.** No se eliminan, se archivan con razon y fecha.
7. **.env nunca se commitea.** El .gitignore lo excluye. Usar .env.example como plantilla.
8. **Los modelos y datasets van a Niflheim.** Excluidos de git por .gitignore.
9. **Python >=3.11.** El ecosistema requiere Python 3.11 o superior.
10. **Commits con prefijo de realm.** Formato: `[REALM] tipo: descripcion`

---

## Convenciones de Commits

```
[ASGARD] feat: nuevo modulo en lilith-core
[MUSPELHEIM] fix: corregir generacion de dataset
[SVARTALFHEIM] docs: actualizar documentacion de API
[ALL] chore: actualizar dependencias
```

**Tipos:** feat, fix, docs, style, refactor, test, chore

---

## Organizacion por Realm

| Realm | Contenido permitido | No permitido |
|-------|-------------------|--------------|
| Asgard | Paquetes lilith-*, pyproject.toml | Docs, scripts sueltos |
| Vanaheim | Frameworks de agentes | Implementaciones especificas |
| Alfheim | UIs, dashboards | Logica de backend |
| Svartalfheim | Docs, scripts, planes, wiki, notes | Codigo ejecutable de aplicaciones |
| Muspelheim | Proyectos WIP, experimentos | Proyectos estables (van a su realm) |
| Niflheim | Modelos, datasets, assets | Codigo |
| Helheim | Archivos muertos, cuarentena | Proyectos activos |
| Jotunheim | Proyectos de gran escala | Proyectos pequenos |
| Midgard | Proyectos personales | Proyectos del ecosistema |

---

## Reglas de Documentacion

1. **README.md en cada realm.** Minimo: descripcion, estructura, estado.
2. **README.md en cada paquete.** Minimo: nombre, version, descripcion.
3. **CHANGELOG.md en root.** Formato Keep a Changelog.
4. **REGLAS.md en Svartalfheim.** Leyes especificas del reino de documentacion.

---

## Reglas de Seguridad

1. **Nunca commitear credenciales.** API keys, tokens, passwords van en .env.
2. **Los agentes tienen permisos limitados.** Definidos en agent_permissions.json.
3. **Helheim es solo lectura.** Los archivos archivados no se modifican.
4. **Los datasets grandes van a Niflheim.** Excluidos de git.

---

*Reglas actualizadas: 2026-05-29*
=======
# 📜 Reglas de Yggdrasil - El Árbol del Mundo

> **Versión:** 4.0
> **Fecha:** 2026-05-21 (Refactoring Fases 1-4)
> **Aplicable a:** Todo el ecosistema Yggdrasil

---

## 🌳 Principios Fundamentales

### 1. Un Proyecto, Un Reino
Cada proyecto reside en **exactamente un reino** en todo momento. No hay duplicados.

### 2. Flujo de Vida
Todo proyecto sigue el ciclo:
```
Idea → Muspelheim → [Reino Destino] → Helheim (si muere)
```

### 3. Límite de Proyectos Activos
- **Muspelheim**: Máximo 4 proyectos simultáneos
- **Asgard**: Paquetes modulares workspace (lilith-*, bifrost, vanaheim-framework)
- **Jotunheim**: Máximo 2 gigantes activos
- Cualquier otro reino: Sin límite estricto, pero mantener organizado

### 4. Legado Marcado, No Eliminado
Todo código legacy debe llevar un `LEGACY.md` o `LEGACY_DIRS.md` que explique qué lo reemplaza. La eliminación física a Helheim requiere migración git (commit de movimiento).

---

## 📋 Reglas por Reino

| Reino | Propósito | Paquetes/Proyectos Activos | Legado |
|-------|-----------|---------------------------|--------|
| **Asgard** | Tecnología core (Lilith modular) | lilith-core v2.0, lilith-memory v2.0, lilith-tools v2.0, lilith-orchestrator v2.0, lilith-api v2.2, lilith-cli v3.0, lilith-skills v1.0, lilith-bridge v1.0 | ⚠️ `Lilith/` monolito v5.0 (LEGACY.md) |
| **Alfheim** | Prototipos UI | TerminalDashboard, dashboard (HTMX), YggdrasilForge, YggdrasilStudio | VSCode_Extension_Lilith |
| **Midgard** | Apps personales | Mínimo (10 .py) | — |
| **Svartalfheim** | Documentación, planes | Docs/, plans/ | — |
| **Vanaheim** | Agentes IA, framework | vanaheim-framework v1.0, bifrost v2.0, gamemaster-mcp-server v0.1 | ⚠️ Agents/, Core/, Config/, Bots_Lilith_v5/, Council/ (LEGACY_DIRS.md) |
| **Jotunheim** | Proyectos >1 mes | `.gitkeep` (vacío, aguarda) | — |
| **Muspelheim** | WIP, sprint mode | ForgeMaster v1.0.0 (238 tests), AutoSub v0.1, AI-Influencer (Fase 0) | ⚠️ kohya_ss eliminado (6.9 GB) |
| **Niflheim** | Assets, modelos, datasets | Modelos (4 GB), Datasets (341 MB) | gitignored |
| **Helheim** | Cementerio read-only | Graveyard.md, epitafios | Archivos legacy archivados |

---

## 🔄 Reglas de Migración

### Cuándo Migrar

| Desde | Hacia | Condición |
|-------|-------|-----------|
| Muspelheim | Asgard | Componente core maduro |
| Muspelheim | Midgard | App personal lista |
| Muspelheim | Jotunheim | Proyecto crece >1 mes |
| Muspelheim | Helheim | Falla o abandono |
| Alfheim | Midgard/Jotunheim | Prototipo validado |
| Vanaheim | Svartalfheim | Conocimiento maduro |
| Vanaheim | Asgard/Midgard | Agente/IA lista para producción |
| Niflheim | Muspelheim | Herramienta en desarrollo activo |
| Cualquiera | Helheim | Proyecto muere |

### Proceso de Migración

1. **Último commit** en origen con `[MIGRATING to X]`
2. **Copiar** a destino (no mover, preservar historial)
3. **Actualizar README** en destino
4. **Añadir enlace** en origen: `Migrated to ../X/project`
5. **Archivar** origen si es necesario (añadir LEGACY.md)

### Proceso para Código Legacy

1. **Marcar** con `LEGACY.md` o `LEGACY_DIRS.md` indicando qué paquete lo reemplaza
2. **Añadir a .gitignore** patrones de runtime data (Data/, cache, logs)
3. **Registrar** en `Helheim/Graveyard.md` con fecha, causa, y tamaño
4. **No eliminar** sin migración git — preservar historial

---

## 📝 Convenciones de Nomenclatura

### Proyectos
```
PascalCase para proyectos principales, snake_case para módulos Python.

Ejemplos:
- AI-Influencer/          # Proyecto principal
- AutoSub/                # Proyecto principal
- ForgeMaster/            # Proyecto principal
- lilith-core/            # Módulo Python
- lilith-memory/          # Módulo Python
- vanaheim-framework/     # Framework Python
```

### Paquetes Python
```
snake_case con guión para dirs, sin guión para imports.

Ejemplos:
- Dir: lilith-core/  → Import: from lilith_core import ...
- Dir: vanaheim-framework/  → Import: from vanaheim import ...
```

### Archivos
```
snake_case para código Python, PascalCase para docs importantes.

Ejemplos:
- memory_store.py
- REGLAS.md, README.md
- plan-01-autosub.md
```

### Commits
```
[REINO] [tipo]: descripcion

Ejemplos:
- [ASGARD] feat(lilith-core): add memory store
- [MUSPELHEIM] feat: implement checkpointing
- [SVARTALFHEIM] docs: add RAG guide
- [MIDGARD] fix: piano autoplayer delay
- [NIFLHEIM] feat(forgemaster): add model manager
```

---

## 🗂️ Estructura de Carpetas

### Todo proyecto debe tener:
```
proyecto/
├── README.md              # Obligatorio — descripción, estado, cómo usar
├── pyproject.toml         # Paquetes Python (si aplica)
├── tests/                 # Tests (si aplica)
├── src/                   # Código fuente (si aplica)
└── docs/                  # Documentación adicional (opcional)
```

### Raíz del monorepo:
```
Yggdrasil/
├── pyproject.toml         # Workspace root (uv workspace)
├── ruff.toml              # Linter/formatter config
├── pytest.ini             # Test runner config
├── package.json            # Node workspaces (Alfheim frontends)
├── yggdrasil_cli.py       # Ecosystem CLI
├── health_check.py        # Health check script
├── scripts/               # Utility scripts + bats/
│   ├── bats/              # Windows .bat launchers
│   ├── setup_yggdrasil.py # Setup script
│   ├── clean.py           # Cache cleaner
│   └── bump-version.py    # Version bumper
├── Asgard/                # Core (lilith-* packages)
├── Alfheim/               # UI prototypes
├── Vanaheim/              # Agents/framework
├── Muspelheim/            # WIP/sprints
├── Niflheim/              # Assets (gitignored)
├── Svartalfheim/          # Docs/plans
├── Midgard/               # Personal apps
├── Helheim/               # Archive/cemetery
└── Jotunheim/             # Mega projects (awaiting)
```

### Prohibido:
- Archivos sueltos en raíz del reino (scripts van a `scripts/`)
- `temp/`, `tmp/`, `borrar/` permanentes
- Duplicados entre reinos
- Binarios grandes sin `.gitignore`
- Tokens, claves API, contraseñas en código (usar `.env` + `.gitignore`)
- Clones de repos externos con su propio `.git` (usar submódulos o clonar fuera)
- `.venv/` dentro de paquetes workspace (usar el .venv raíz del monorepo)

---

## 🔒 Seguridad y Límites

### Prohibido en todo Yggdrasil:
- Tokens, claves API, contraseñas en código (usar `.env` + `.gitignore`)
- Archivos >100MB sin LFS
- Malware, exploits, contenido ilegal
- Datos personales de terceros
- Clones de repos externos dentro del árbol (usar git submodules o referenciar externamente)

### Requiere aprobación:
- Modificar estructura de reinos
- Eliminar proyecto de Helheim
- Migrar proyecto completado
- Mover código legacy a Helheim (requiere preserving git history)

---

## 📊 Mantenimiento

### Mensual
- Revisar Muspelheim: ¿proyectos estancados?
- Limpiar Niflheim: ¿assets obsoletos?
- Verificar Helheim: ¿algo para resucitar?
- Ejecutar `scripts/clean.py` para purgar caches

### Trimestral
- Revisar todos los READMEs y REGLAS
- Actualizar reglas si es necesario
- Backup de Svartalfheim (Knowledge Base)
- Verificar que la estructura real coincide con la documentada
- Auditar `LEGACY.md` marcadores — ¿migrar código muerto a Helheim?

---

## 🎯 Decision Tree

```
¿Qué estoy creando?
│
├─→ Agente IA core / API / CLI → Asgard
├─→ Prototipo UI/visual → Alfheim
├─→ App para mi uso → Midgard
├─→ Documentación/planes/conocimiento → Svartalfheim
├─→ Agente experimental / bot → Vanaheim
├─→ Proyecto grande >1 mes → Jotunheim
├─→ Desarrollo activo/sprint → Muspelheim
├─→ Assets/modelos/datasets → Niflheim
└─→ Proyecto muerto/archivar → Helheim
```

---

## ⚖️ Sanciones (Humorístico)

| Violación | Consecuencia |
|-----------|--------------|
| Dejar `temp/` permanente | 1 semana sin Muspelheim |
| Proyecto >2 semanas en Muspelheim | Migración forzosa |
| Sin README | Proyecto invisible hasta que lo tenga |
| Duplicar entre reinos | Eliminación del duplicado |
| Token expuesto | 1 mes de purgatorio en Helheim |
| README desactualizado >1 mes | Reescritura obligatoria |
| Clon de repo externo en el árbol | Exilio a fuera del monorepo |
| `.venv/` en sub-paquete | Ejecutar `scripts/clean.py` |

---

**Yggdrasil crece con orden o no crece.** 🌳

*Ultima actualizacion: 2026-05-21*

---

## Historial de Cambios

### v4.0 - 2026-05-21 (Refactoring Fases 1-4)
- **Fase 1 Cleanup:** kohya_ss eliminado (6.9 GB, 10,827 .py), caches purgadas (~280 MB), node_modules raíz eliminado (135 MB), .venvs redundantes eliminados (~500 MB), .egg-info limpiado
- **Fase 2 Audit:** Asgard/Lilith monolito marcado LEGACY (477 .py, 83 MB), 8 lilith-* paquetes verificados activos, LEGACY.md creado con tabla de migración, .gitignore actualizado
- **Fase 3 Consolidation:** Vanaheim legacy dirs marcados con LEGACY_DIRS.md, scripts/.bat movidos a scripts/bats/, package.json workspace arreglado (packages/* → rutas reales), Helheim Graveyard actualizado con kohya_ss y Lilith monolito
- **Fase 4 Docs:** READMEs actualizados (Asgard, Muspelheim, Vanaheim), REGLAS_YGGDRASIL.md v4.0, CI verificado (.github/workflows/ci.yml)
- **Nueva regla:** Clones de repos externos prohibidos dentro del árbol (usar submodules)
- **Nueva regla:** `.venv/` en sub-paquetes workspace prohibido (usar el .venv raíz)
- **Nueva regla:** LEGACY.md obligatorio para código muerto antes de archivar a Helheim
- **Estructura raíz:** .bat files movidos a scripts/bats/, setup.sh movido a scripts/

### v3.1 - 2026-05-03 (Refinamiento post-limpieza)
- **CI corregido:** ForgeMaster path de Niflheim a Muspelheim
- **Paths hardcodeados eliminados:** TerminalDashboard usa env var + auto-detect
- **Website actualizado:** Hermes → Lilith en paths, env vars, comandos
- **Vanaheim limpiado:** Agentes duplicados eliminados (subdirs son canónicos)
- **Archivos basura:** health-check.py, __pycache__, .pyc, .egg-info, bot_registry.json eliminados del tracking
- **REGLAS actualizadas:** Swarm dual architecture documentada, proyectos activos en Muspelheim
- **README reescrito:** Refleja estado actual del ecosistema (v5, dual Swarm, realm table)
- **CHANGELOG completado:** Entrada Unreleased con todos los fixes recientes

### v3.0 - 2026-05-02 (Organización profesional)
- **Asgard redefinido:** De "Dashboards/scripts solo" a "Tecnología core"
- **Nomenclatura actualizada:** PascalCase para proyectos, snake_case para módulos Python
- **Archivos sueltos:** Prohibidos en raíz de reino
- **ForgeMaster:** Migrado de Niflheim a Muspelheim
- **Estructura mínima:** Actualizada para incluir pyproject.toml y tests/

### v2.0 - 2026-04-29 (Remasterizacion completa)
- **Limpieza masiva:** Eliminados 60,000+ archivos basura
- **Cuarentena:** Basura regenerable movida a Helheim
- **Legacy archivado:** Codigo muerto de Lilith en Helheim
- **Consolidacion Vanaheim:** Todos los bots/IA en un solo lugar
- **Salud:** De 62,272 archivos a ~1,500 activos (~97% reduccion)
>>>>>>> origin/main
