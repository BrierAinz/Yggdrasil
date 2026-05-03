# Skill: VS Code Integration

## Descripción
Integración completa con Visual Studio Code para desarrollo de software.

## Capabilidades
- Apertura y control de VS Code
- Creación y edición de archivos de código
- Ejecución de comandos del terminal integrado
- Navegación por archivos y proyectos
- Intellisense y autocompletado (via Copilot si disponible)

## Tools Disponibles

### File Operations (Built-in)
| Tool | Función |
|------|---------|
| `Read` | Leer archivos de código |
| `Write` | Crear/sobreescribir archivos |
| `Edit` | Modificar secciones específicas |
| `Glob` | Buscar archivos por patrón |
| `Grep` | Buscar texto en archivos |

### Terminal Operations
| Tool | Función |
|------|---------|
| `mcp__matrix__bash` | Ejecutar comandos shell |
| `mcp__matrix__bash_output` | Obtener output de procesos |

### Desktop Control
| Tool | Función |
|------|---------|
| `desktop_*` | Todas las operaciones de Desktop Control |

## Workflows Comunes

### 1. Abrir Proyecto Existente
```
1. bash: cd a /ruta/del/proyecto
2. bash: code . → Abrir VS Code con proyecto
3. desktop_window_focus → Asegurar que VS Code tiene foco
```

### 2. Crear Nuevo Archivo de Código
```
1. Write: Crear archivo con extensión correcta
2. bash: code --goto /ruta/archivo:linea → Abrir en VS Code
3. desktop_key "ctrl+shift+p" → Command Palette
4. desktop_type "format document" → Formatear
```

### 3. Buscar y Reemplazar en Proyecto
```
1. Grep: Buscar texto en proyecto
2. Read: Leer archivos afectados
3. Edit/MultiEdit: Aplicar cambios
4. Write: Guardar archivos
```

### 4. Ejecutar Tests/Build
```
1. desktop_key "ctrl+shift+`" → Abrir terminal
2. desktop_type "npm run test" o "python -m pytest"
3. mcp__matrix__bash_output → Ver resultados
```

### 5. Git Operations
```
1. Grep: Ver archivos modificados
2. bash: git status → Ver estado
3. desktop_type → Escribir comandos git
4. desktop_key "enter" → Ejecutar
```

## Integración con Desktop Control
VS Code requiere coordinación entre file operations y desktop control:

| Acción | Herramienta |
|--------|------------|
| Escribir código | `Write`/`Edit` (más seguro) |
| Navegar UI de VS | `desktop_*` (mouse/teclado) |
| Ejecutar comandos | `bash` (terminal) |
| Ver archivos | `Glob`/`Grep` |

## Patrones de Coding

### Python Project
```python
# Estructura típica
proyecto/
├── src/
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt
├── setup.py
└── README.md
```

### JavaScript/TypeScript Project
```javascript
// Estructura típica
proyecto/
├── src/
│   ├── index.ts
│   └── utils/
├── dist/
├── node_modules/
├── package.json
├── tsconfig.json
└── .gitignore
```

## Configuraciones Recomendadas

### Extensiones Esenciales para VS Code
- Python (Microsoft)
- Prettier - Code formatter
- ESLint
- GitLens
- GitHub Copilot (o alternativa)
- Live Share
- Thunder Client (API testing)

### Settings.json Recomendados
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "python.linting.enabled": true,
  "terminal.integrated.fontSize": 14
}
```

## Notas de Seguridad
- **Siempre backup antes de editar** archivos existentes
- **Confirmar antes de Delete** archivos o carpetas
- **Usar Trash** para eliminación segura (no rm/del permanente)

## Aprendizaje Continuo
Registrar en `/memories/conocimiento/historico_tareas.md`:
- Comandos git usados frecuentemente
- Patrones de debugging
- Scripts de automatización descubiertos

---
**Versión**: 1.0.0
**Última actualización**: 2026-04-20
