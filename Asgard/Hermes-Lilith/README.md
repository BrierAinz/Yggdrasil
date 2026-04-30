# Midgard - Workspace del Asistente Personal IA

Bienvenido al workspace de tu asistente personal. Este directorio contiene todo lo necesario para que el asistente opere de manera inteligente y aprenda con el tiempo.

## Estructura del Proyecto

```
Midgard/
├── skills/                    # Skills del asistente
│   ├── desktop-ctrl/         # Control de mouse, teclado, ventanas
│   ├── vscode-integrator/     # Integración con VS Code
│   ├── learning-engine/       # Motor de aprendizaje
│   └── automation/           # Automatización de tareas
│
├── workspace/                # Área de trabajo activa
│   ├── proyectos/            # Proyectos del usuario
│   ├── templates/           # Plantillas reutilizables
│   └── logs/                # Logs de actividad
│
├── backups/                  # Backups automáticos
│
├── config/                   # Configuraciones
│   └── config.yaml           # Archivo de configuración principal
│
└── memories/                 # Sistema de memorias (en /memories del sistema)
```

## Sistema de Memorias

El asistente mantiene un sistema de memorias persistente en `/memories/`:

| Archivo | Propósito |
|---------|-----------|
| `persona.md` | Identidad y comportamiento |
| `skill_catalog.md` | Inventario de skills disponibles |
| `conocimiento/historico_tareas.md` | Registro de tareas completadas |
| `conocimiento/preferencias_usuario.md` | Preferencias del usuario |

## Configuración Inicial

### 1. Skills
Las skills están organizadas en `skills/` y se cargan automáticamente. Para agregar una nueva skill:
1. Crear directorio en `skills/[nombre]/`
2. Crear archivo `SKILL.md` con la documentación
3. Reiniciar sesión del asistente

### 2. Variables de Entorno
El asistente usa estas variables:
- `WORKSPACE`: D:\Proyectos\Midgard
- `BACKUP_DIR`: D:\Proyectos\Midgard\backups
- `LOG_DIR`: D:\Proyectos\Midgard\workspace\logs

### 3. Config.yaml
Archivo principal de configuración. Ver `config/config.yaml`.

## Quick Start

### Abrir el Workspace
```powershell
cd D:\Proyectos\Midgard
code .
```

### Comandos Útiles
| Comando | Descripción |
|---------|-------------|
| `code .` | Abrir workspace en VS Code |
| `Get-ChildItem -Recurse` | Ver estructura completa |
| `Get-Content logs/*.md` | Ver logs recientes |

## Patrones de Uso

### Tareas Comunes
1. **Nueva tarea** → Se registra en histórico → Se identifican patrones
2. **Tarea repetitiva** → Se sugiere automatización
3. **Error** → Se documenta → Se crea solución

### Workflow Típico
```
1. Usuario pide tarea
2. Asistente consulta memorias
3. Ejecuta con tools disponibles
4. Documenta resultado
5. Aprende para futuras tareas
```

## Logs

Los logs de actividad se guardan en:
- `workspace/logs/activity/` - Actividad general
- `workspace/logs/errors/` - Errores y soluciones
- `workspace/logs/tasks/` - Tareas completadas

## Backups

Backups automáticos de archivos importantes:
- Ubicación: `backups/`
- Formato: `backup_[tipo]_[fecha]_[hora].zip`
- Retención: 30 días

## Contributing

Para expandir las capacidades del asistente:
1. Agregar nueva skill en `skills/`
2. Documentar en SKILL.md
3. Agregar a `skill_catalog.md`
4. Probar con tarea de ejemplo

---

**Versión**: 1.0.0
**Creado**: 2026-04-20
**Mantenido por**: Midgard Agent
