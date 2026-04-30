# 📜 Reglas de Yggdrasil - El Árbol del Mundo

> **Versión:** 2.0
> **Fecha:** 2026-04-29 (Remasterizacion completa)
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
- **Muspelheim**: Máximo 3 proyectos simultáneos
- **Jotunheim**: Máximo 2 gigantes activos
- Cualquier otro reino: Sin límite estricto, pero mantener organizado

---

## 📋 Reglas por Reino

| Reino | Regla Principal | Trigger de Salida |
|-------|-----------------|-------------------|
| **Asgard** | Dashboards/scripts solo | N/A (permanente) |
| **Alfheim** | Todo es experimental | Migrar cuando esté listo |
| **Midgard** | Solo proyectos personales | N/A (destino final) |
| **Svartalfheim** | Solo conocimiento/docs | N/A (permanente) |
| **Vanaheim** | Experimentos de IA/agentes | Migrar cuando esté estable |
| **Jotunheim** | Proyectos >1 mes de duración | Completar o a Helheim |
| **Muspelheim** | Máx 3 proyectos, sprint mode | Completar/migrar en 2 semanas |
| **Niflheim** | Assets/configs sin código | N/A (recursos) |
| **Helheim** | Read-only, no desarrollo | N/A (cementerio) |

---

## 🔄 Reglas de Migración

### Cuándo Migrar

| Desde | Hacia | Condición |
|-------|-------|-----------|
| Muspelheim | Midgard | App personal lista |
| Muspelheim | Jotunheim | Proyecto crece >1 mes |
| Muspelheim | Helheim | Falla o abandono |
| Alfheim | Midgard/Jotunheim | Prototipo validado |
| Vanaheim | Svartalfheim | Conocimiento maduro |
| Vanaheim | Midgard | Agente/IA lista |
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
[tipo]_[nombre]_[estado]/

Ejemplos:
- app_piano_autoplayer/
- engine_story_v2/
- exp_ml_vision_wip/
- lib_utils_stable/
```

### Archivos
```
[fecha]_[tipo]_[descripcion].[ext]

Ejemplos:
- 20260321_design_api_v2.md
- 20260320_bugfix_memory.py
- 20260319_checkpoint_001.json
```

### Commits
```
[REINO] [tipo]: descripcion

Ejemplos:
- [MUSPELHEIM] feat: implement checkpointing
- [SVARTALFHEIM] docs: add RAG guide
- [MIDGARD] fix: piano autoplayer delay
```

---

## 🗂️ Estructura de Carpetas

### Todo proyecto debe tener:
```
proyecto/
├── README.md              # Obligatorio
├── REGLAS.md             # Reglas específicas (opcional)
├── src/ o código/        # Implementación
├── docs/                 # Documentación
└── archive/              # Versiones viejas
```

### Prohibido:
- Archivos sueltos en raíz del reino
- `temp/`, `tmp/`, `borrar/` permanentes
- Duplicados entre reinos
- Binarios sin código fuente

---

## 🔒 Seguridad y Límites

### Prohibido en todo Yggdrasil:
- Tokens, claves API, contraseñas (usar .env o Config/)
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
- Revisar todos los READMEs
- Actualizar reglas si es necesario
- Backup de Svartalfheim (Knowledge Base)

---

## 🎯 Decision Tree

```
¿Qué estoy creando?
│
├─→ Dashboard/monitoreo → Asgard
├─→ Prototipo UI/visual → Alfheim
├─→ App para mi uso → Midgard
├─→ Documentación/conocimiento → Svartalfheim
├─→ Experimento IA/agente → Vanaheim
├─→ Proyecto grande >1 mes → Jotunheim
├─→ Desarrollo activo/sprint → Muspelheim
├─→ Assets/configs/templates → Niflheim
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

---

**Yggdrasil crece con orden o no crece.** 🌳

*Ultima actualizacion: 2026-04-29*

---

## Historial de Cambios

### v2.0 - 2026-04-29 (Remasterizacion completa)
- **Limpieza masiva:** Eliminados 60,000+ archivos basura (node_modules, pycache, map, tmp)
- **Cuarentena:** Basura regenerable movida a Helheim/Quarantine_2026-04-29/
- **Legacy archivado:** Codigo muerto de Lilith en Helheim/Archives_Lilith_Legacy_2026-04-29/
- **Consolidacion Vanaheim:** Todos los bots/IA en un solo lugar
- **Activacion Alfheim:** Semilla de UI electronica + orquestador visual
- **Activacion Niflheim:** Assets/Resources centralizados
- **Documentacion Svartalfheim:** Guias tecnicas + README maestros
- **Salud:** De 62,272 archivos a ~1,500 activos (~97% reduccion)
