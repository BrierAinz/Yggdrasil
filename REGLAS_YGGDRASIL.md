# 📜 Reglas de Yggdrasil - El Árbol del Mundo

> **Versión:** 3.0
> **Fecha:** 2026-05-02 (Organización profesional, actualización de realidades)
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
- **Jotunheim**: Máximo 2 gigantes activos
- Cualquier otro reino: Sin límite estricto, pero mantener organizado

---

## 📋 Reglas por Reino

| Reino | Regla Principal | Trigger de Salida |
|-------|-----------------|-------------------|
| **Asgard** | Tecnología core (Lilith, API, Memory, CLI, Gateway) | N/A (permanente) |
| **Alfheim** | Prototipos UI y experimentos visuales | Migrar cuando esté listo |
| **Midgard** | Apps personales terminadas | N/A (destino final) |
| **Svartalfheim** | Documentación, planes, conocimiento | N/A (permanente) |
| **Vanaheim** | Agentes IA, framework, bots | Migrar cuando esté estable |
| **Jotunheim** | Proyectos >1 mes de duración | Completar o a Helheim |
| **Muspelheim** | Máx 4 proyectos, sprint mode | Completar/migrar en 2 semanas |
| **Niflheim** | Recursos, modelos, datasets, assets | N/A (recursos) |
| **Helheim** | Read-only, no desarrollo | N/A (cementerio) |

> **Nota:** Asgard es el reino de la **tecnología core** — no solo dashboards. Contiene Lilith (el agente IA central), los paquetes modulares (lilith-core, lilith-memory, lilith-tools, etc.), el gateway, y los dashboards.

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
5. **Archivar** origen si es necesario

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

### Prohibido:
- Archivos sueltos en raíz del reino (scripts de un solo uso van a Svartalfheim/Scripts/)
- `temp/`, `tmp/`, `borrar/` permanentes
- Duplicados entre reinos
- Binarios grandes sin `.gitignore`
- Tokens, claves API, contraseñas en código (usar `.env` + `.gitignore`)

---

## 🔒 Seguridad y Límites

### Prohibido en todo Yggdrasil:
- Tokens, claves API, contraseñas en código (usar `.env` + `.gitignore`)
- Archivos >100MB sin LFS
- Malware, exploits, contenido ilegal
- Datos personales de terceros

### Requiere aprobación:
- Modificar estructura de reinos
- Eliminar proyecto de Helheim
- Migrar proyecto completado

---

## 📊 Mantenimiento

### Mensual
- Revisar Muspelheim: ¿proyectos estancados?
- Limpiar Niflheim: ¿assets obsoletos?
- Verificar Helheim: ¿algo para resucitar?

### Trimestral
- Revisar todos los READMEs y REGLAS
- Actualizar reglas si es necesario
- Backup de Svartalfheim (Knowledge Base)
- Verificar que la estructura real coincide con la documentada

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

---

**Yggdrasil crece con orden o no crece.** 🌳

*Ultima actualizacion: 2026-05-02*

---

## Historial de Cambios

### v3.0 - 2026-05-02 (Organización profesional)
- **Asgard redefinido:** De "Dashboards/scripts solo" a "Tecnología core" — refleja su rol real
- **Nomenclatura actualizada:** PascalCase para proyectos, snake_case para módulos Python (refleja uso real)
- **Archivos sueltos:** Prohibidos en raíz de reino, scripts van a Svartalfheim/Scripts/
- **Ruta de migración Asgard:** Agregado Muspelheim → Asgard para componentes core
- **Ruta de migración Niflheim:** Agregado Niflheim → Muspelheim para herramientas en desarrollo
- **ForgeMaster:** Migrado de Niflheim a Muspelheim (proyecto en desarrollo activo, no es recurso)
- **Estructura mínima:** Actualizada para incluir pyproject.toml y tests/
- **Sanciones:** Agregada sanción por README desactualizado

### v2.0 - 2026-04-29 (Remasterizacion completa)
- **Limpieza masiva:** Eliminados 60,000+ archivos basura (node_modules, pycache, map, tmp)
- **Cuarentena:** Basura regenerable movida a Helheim/Quarantine_2026-04-29/
- **Legacy archivado:** Codigo muerto de Lilith en Helheim/Archives_Lilith_Legacy_2026-04-29/
- **Consolidacion Vanaheim:** Todos los bots/IA en un solo lugar
- **Activacion Alfheim:** Semilla de UI electronica + orquestador visual
- **Activacion Niflheim:** Assets/Resources centralizados
- **Documentacion Svartalfheim:** Guias tecnicas + README maestros
- **Salud:** De 62,272 archivos a ~1,500 activos (~97% reduccion)
