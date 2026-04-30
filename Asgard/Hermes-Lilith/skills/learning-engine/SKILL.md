# Skill: Learning Engine

## Descripción
Motor de aprendizaje que permite al asistente aprender de las tareas realizadas y mejorar su eficiencia con el tiempo.

## Concepto
El asistente aprende mediante:
1. **Registro de tareas**: Cada tarea completada se documenta
2. **Identificación de patrones**: Secuencias repetitivas se extraen
3. **Aplicación de memorias**: El conocimiento se usa en tareas futuras

## Sistema de Memorias

### Estructura de Memorias
```
/memories/
├── persona.md                    # Identidad del asistente
├── skill_catalog.md             # Inventario de skills
└── conocimiento/
    ├── historico_tareas.md      # Registro de tareas
    ├── preferencias_usuario.md  # Preferencias del usuario
    └── patrones/                # Patrones identificados
```

### Flujo de Aprendizaje
```
Nueva Tarea → Analizar → Buscar en memorias → Ejecutar → Documentar → Actualizar patrones
```

## Tools Disponibles

### Gestión de Memorias
| Tool | Función |
|------|---------|
| `create_memory` | Crear nueva memoria |
| `str_replace_memory` | Actualizar memoria existente |
| `view_memory` | Leer memorias |
| `delete_memory` | Eliminar memorias |
| `rename_memory` | Mover/renombrar memorias |

### Búsqueda y Análisis
| Tool | Función |
|------|---------|
| `mcp__matrix__Grep` | Buscar en memorias |
| `mcp__matrix__Glob` | Encontrar archivos de memoria |

## Proceso de Aprendizaje

### 1. Antes de Tarea
```
1. view_memory("/memories/conocimiento/historico_tareas.md")
2. view_memory("/memories/conocimiento/patrones/")
3. Si existe patrón relevante → Usar como guía
4. Si no existe → Continuar con mejor esfuerzo
```

### 2. Después de Tarea
```
1. Registrar en historico_tareas.md
2. Identificar patrones nuevos
3. Actualizar preferendas_usuario.md si hay cambios
4. Crear memoria en /patrones/ si es reutilizable
```

### 3. Formato de Registro
```markdown
## [Fecha] - [Categoría]
### Tarea: [Descripción]
### Pasos: [Lista de pasos realizados]
### Resultado: [Éxito/Fallido/Parcial]
### Tiempo: [Duración]
### Patrones: [Patrones usados/aprendidos]
### Notas: [Observaciones]
```

## Tipos de Patrones

### Patrones de Archivo
| Nombre | Descripción |
|--------|-------------|
| `backup-before-edit` | Crear backup antes de editar |
| `triple-read` | Leer archivo 3 veces antes de editar |
| `atomic-write` | Escribir archivo completo, no parciales |

### Patrones de Código
| Nombre | Descripción |
|--------|-------------|
| `modular-first` | Crear módulos reutilizables primero |
| `test-before-refactor` | Probar antes de optimizar |
| `dry-code` | Don't Repeat Yourself |

### Patrones de Desktop
| Nombre | Descripción |
|--------|-------------|
| `screenshot-verify` | Screenshot después de cada acción |
| `confirm-critical` | Confirmar acciones destructivas |
| `window-focus-first` | Asegurar foco antes de interactuar |

## Metricas de Aprendizaje

### Tracking
- **Tareas completadas**: Contador total
- **Tasa de éxito**: Porcentaje de tareas exitosas
- **Tiempo promedio**: Efficiency del asistente
- **Patrones activos**: Número de patrones disponibles

### Mejora Continua
1. **Semanal**: Revisar histórico, identificar nuevos patrones
2. **Mensual**: Actualizar skill catalog con nuevas capacidades
3. **Trimestral**: Refactorizar sistema de memorias si necesario

## Archivo de Configuración
```yaml
learning:
  enabled: true
  auto_document: true
  pattern_threshold: 3  # Veces antes de crear patrón
  backup_before_edit: true
  confirm_destructive: true
```

## Ejemplo de Uso

### Aprender Nuevo Comando
```
1. Usuario pide: "Abre VS Code y crea un archivo test.py"
2. Buscar en memorias → No existe patrón
3. Ejecutar tarea
4. Documentar en historico_tareas.md:
   - Pasos usados
   - Tiempotaken
   - Comandos ejecutados
5. Crear patrón en /patrones/open-vscode.md
```

### Aplicar Patrón Existente
```
1. Usuario pide tarea similar
2. view_memory("/memories/conocimiento/patrones/open-vscode.md")
3. Ejecutar pasos del patrón directamente
4. Actualizar patrón si hubo variaciones
```

## Integración con otras Skills

| Skill | Cómo contribuye al aprendizaje |
|-------|-------------------------------|
| `desktop-ctrl` | Registra secuencias de UI |
| `vscode-integrator` | Registra comandos y atajos |
| `file-ops` | Registra operaciones de archivo |

## Notas
- El sistema de memorias persiste entre sesiones
- Cada sesión nueva hereda el conocimiento previo
- Los patrones se refinan con el uso repetido

---
**Versión**: 1.0.0
**Última actualización**: 2026-04-20
