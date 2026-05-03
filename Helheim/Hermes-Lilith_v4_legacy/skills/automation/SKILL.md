# Skill: Automation

## Descripción
Sistema de automatización de tareas repetitivas mediante macros, scripts y workflows registrables.

## Concepto
El asistente puede:
1. **Grabar secuencias** de acciones para repetición
2. **Ejecutar macros** predefinidas
3. **Programar tareas** con cron jobs
4. **Encadenar workflows** complejos

## Tipos de Automatización

### 1. Macros Simples
Secuencias de desktop control que se pueden repetir.

### 2. Scripts de Archivo
Operaciones batch en archivos (rename, move, transform).

### 3. Tareas Programadas
Tareas que se ejecutan automáticamente en intervalos definidos.

### 4. Workflows Compuestos
Combinación de múltiples skills en un solo flujo.

## Tools Disponibles

### Scheduling
| Tool | Función |
|------|---------|
| `create_cron_job` | Crear tarea programada |
| `mcp__matrix__bash` | Ejecutar scripts |

### File Operations
| Tool | Función |
|------|---------|
| `Read/Write/Edit` | Manipulación de archivos |
| `mcp__matrix__bash` | Comandos de scripting |

### Desktop Control
| Tool | Función |
|------|---------|
| `desktop_*` | Todas las operaciones de mouse/teclado |

## Estructura de Automatizaciones

```
D:\Proyectos\Midgard\automation\
├── macros/
│   ├── README.md
│   ├── abrir-vscode.md
│   └── daily-report.md
├── scripts/
│   ├── README.md
│   └── batch-rename.ps1
├── workflows/
│   ├── README.md
│   └── setup-proyecto.md
└── cron/
    └── README.md
```

## Formato de Macro
```markdown
# Macro: [Nombre]

## Descripción
[Qué hace esta macro]

## Pasos
1. [Paso 1]
2. [Paso 2]
...

## Condiciones
- Requiere: [Qué se necesita antes]
- Estado inicial: [Estado esperado]

## Uso
```bash
[Cómo ejecutar]
```

## Notas
[Observaciones adicionales]
```

## Ejemplo: Macro de Apertura de VS Code
```markdown
# Macro: Abrir Proyecto en VS Code

## Descripción
Abre VS Code y carga un proyecto específico.

## Pasos
1. desktop_key "super" → Menú inicio
2. desktop_type "code" → Buscar VS Code
3. desktop_key "enter" → Abrir
4. desktop_wait 3 → Esperar carga
5. desktop_key "ctrl+o" → Abrir carpeta
6. desktop_type "D:\Proyectos\[proyecto]" → Ruta
7. desktop_key "enter" → Confirmar

## Condiciones
- VS Code instalado
- Proyecto existe en ruta

## Uso
Ejecutar con la ruta del proyecto como variable.
```

## Ejemplo: Cron Job
```markdown
# Tarea: Backup Diario

## Cron Expression
`0 2 * * *` → Daily at 2:00 AM

## Descripción
Ejecuta backup automático del workspace.

## Instrucciones
1. Copiar archivos del workspace a /backups
2. Comprimir con timestamp
3. Limpiar backups mayores a 30 días

## Output
- Backup en: D:\Proyectos\Midgard\backups\backup_[date].zip
- Log en: D:\Proyectos\Midgard\logs\cron_backup.log
```

## Crear Nueva Automatización

### Paso 1: Identificar Patrón
```
1. Revisar historico_tareas.md
2. Identificar tareas repetitivas
3. Verificar que no existe macro similar
```

### Paso 2: Documentar Secuencia
```
1. Crear archivo en /automation/macros/
2. Documentar cada paso con tool usada
3. Incluir condiciones previas
4. Definir variables configurables
```

### Paso 3: Probar y Refinar
```
1. Ejecutar macro completa
2. Documentar variaciones necesarias
3. Actualizar con edge cases
```

### Paso 4: Integrar con Scheduling
```
1. Si es repetitiva → Crear cron job
2. Definir frecuencia
3. Agregar logging
```

## Variables de Automatización
| Variable | Uso |
|----------|-----|
| `$WORKSPACE` | D:\Proyectos\Midgard |
| `$DATE` | Fecha actual (YYYY-MM-DD) |
| `$TIME` | Tiempo actual (HHMM) |
| `$USER` | Usuario del sistema |

## Mejores Prácticas

### Seguridad
- **Nunca hardcodear passwords** en macros
- **Usar confirmaciones** para operaciones destructivas
- **Limitar alcance** de operaciones batch
- **Loggear todo** para auditoría

### Eficiencia
- **Combinar herramientas**: No usar desktop control donde Read/Write sirve
- **Mínimo de pasos**: Simplificar secuencias
- **Reusar patrones**: Crear macros modulares
- **Validar resultados**: Siempre verificar output

### Mantenimiento
- **Versionar macros** con fecha
- **Documentar cambios** en historial
- **Revisar mensualmente** para optimización

## Integración con Learning Engine

El sistema de automatización se retroalimenta con el learning engine:

```
Task Repetitiva → Learning Engine detecta → Crea Macro → Automatización disponible
```

### Flujo
1. **Detección**: Task aparece 3+ veces en histórico
2. **Propuesta**: Suggest creación de macro
3. **Creación**: Generar macro desde histórico
4. **Validación**: Probar con supervisión
5. **Activación**: Disponible para uso futuro

## Notas
- Las automatizaciones son **complementarias**, no reemplazan juicio
- Siempre pedir confirmación para **operaciones destructivas**
- Los **logs** son esenciales para debugging

---
**Versión**: 1.0.0
**Última actualización**: 2026-04-20
