# Macros de PC Agent (F.17)

## Resumen

Las macros permiten ejecutar flujos complejos de operaciones PC con **1 sola confirmación**, optimizando la UX para tareas repetitivas.

## Macros Disponibles

| Macro | Descripción | Operaciones |
|-------|-------------|-------------|
| `backup_proyecto` | Respalda carpeta de proyecto | mkdir → copy |
| `compilar_y_test` | Build + tests | exec (npm run build) → exec (npm test) |
| `setup_proyecto_python` | Setup inicial Python | exec (venv) → exec (pip install) |
| `limpiar_temp` | Limpia archivos temporales | exec (del temp) → exec (rmdir cache) |
| `git_commit_push` | Git workflow completo | exec (add) → exec (commit) → exec (push) |
| `crear_estructura_web` | Estructura base web | mkdir → mkdir → mkdir → write_file |

## Uso desde Telegram

### Lenguaje natural

```
Ainz: backup proyecto Lilith
Lilith: 🔧 Macro detectada: backup_proyecto
        _Respalda carpeta de proyecto_
        
        **Operaciones:**
        1. mkdir: `D:/Backups/Lilith_2024-03-21_10-30-00`
        2. copy: `D:/Proyectos/Yggdrasil/Asgard/Lilith` → `D:/Backups/Lilith_2024-03-21_10-30-00/`
        
        **Parámetros:**
        - project_path: `D:/Proyectos/Yggdrasil/Asgard/Lilith`
        - project_name: `Lilith`
        
        [✅ Ejecutar] [❌ Cancelar]
```

### Comando explícito

```
Ainz: /macro backup_proyecto path=D:/Proyectos/Yggdrasil/Asgard/Lilith name=Lilith
```

## Configuración de Macros

### Archivo: `Core/Config/pc_agent_macros.json`

```json
{
  "macros": {
    "mi_macro": {
      "description": "Descripción de la macro",
      "requires_confirmation": true,
      "steps": [
        {
          "operation": "mkdir",
          "path": "{project_path}/nueva_carpeta"
        },
        {
          "operation": "exec",
          "command": "npm install",
          "cwd": "{project_path}"
        }
      ],
      "params": {
        "project_path": {
          "type": "path",
          "description": "Ruta del proyecto",
          "required": true
        }
      }
    }
  },
  "detection_keywords": {
    "mi_macro": ["mi macro", "keyword1", "keyword2"]
  }
}
```

### Tipos de parámetros

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `path` | Ruta de archivo/carpeta | `D:/Proyectos/Yggdrasil/Asgard/Lilith` |
| `string` | Texto libre | `"mensaje de commit"` |
| `auto` | Valor automático | `{{auto_timestamp}}` |

### Valores automáticos

- `{{auto_timestamp}}` → `2024-03-21_10-30-00`
- `{{auto_date}}` → `2024-03-21`

### Placeholders en steps

Los parámetros se reemplazan usando `{param_name}`:

```json
{
  "operation": "copy",
  "source": "{project_path}",
  "destination": "D:/Backups/{project_name}_{timestamp}/"
}
```

## API del Motor de Macros

### Detectar macro

```python
from Backend.core.pc_macro_engine import get_macro_engine

engine = get_macro_engine(base_path)
result = engine.detect_macro("backup proyecto Lilith")
# → ("backup_proyecto", 0.85) o None
```

### Extraer parámetros

```python
params = engine.extract_params("backup proyecto Lilith", "backup_proyecto")
# → {"project_path": "D:/Proyectos/Yggdrasil/Asgard/Lilith", "project_name": "Lilith", "timestamp": "..."}
```

### Validar parámetros

```python
is_valid, error = engine.validate_params("backup_proyecto", params)
# → (True, "") o (False, "Parámetro requerido 'project_path' no proporcionado")
```

### Construir steps

```python
steps = engine.build_batch_steps("backup_proyecto", params)
# → [{"op": "mkdir", "path": "..."}, {"op": "copy", "source": "...", "destination": "..."}]
```

## Seguridad

### Validaciones automáticas

1. **Paths**: No permiten `..`, `~`, `$`, `|`, `;`, `&&`, `||`
2. **Confirmación**: Todas las macros requieren confirmación explícita
3. **Rate limiting**: Heredado del sistema PC Agent (30 ops/hora)

### Expansión de atajos

Los atajos de ruta se expanden automáticamente:
- `proyectos` → `D:/Proyectos`
- `lilith` → `D:/Proyectos/Yggdrasil/Asgard/Lilith`
- `desktop` → `C:/Users/Game_/Desktop`

## Crear una Nueva Macro

1. Editar `Core/Config/pc_agent_macros.json`
2. Agregar entrada en `macros`
3. Agregar keywords en `detection_keywords`
4. Reiniciar el backend

### Ejemplo: Macro personalizada

```json
{
  "macros": {
    "deploy_docker": {
      "description": "Build y deploy de imagen Docker",
      "requires_confirmation": true,
      "steps": [
        {"operation": "exec", "command": "docker build -t {image_name} .", "cwd": "{project_path}"},
        {"operation": "exec", "command": "docker push {image_name}", "cwd": "{project_path}"}
      ],
      "params": {
        "project_path": {"type": "path", "required": true},
        "image_name": {"type": "string", "required": true, "default": "miapp:latest"}
      }
    }
  },
  "detection_keywords": {
    "deploy_docker": ["deploy docker", "docker push", "subir imagen"]
  }
}
```

Uso:
```
Ainz: deploy docker de Lilith con imagen lilith:v2
```

## Troubleshooting

### Macro no detectada
- Verificar keywords en `detection_keywords`
- Revisar logs: `[PCMacroEngine] Detectada macro...`

### Parámetros inválidos
- Verificar que los parámetros requeridos estén presentes
- Revisar que los paths no contengan caracteres peligrosos

### Macro no aparece
- Reiniciar el backend para recargar configuración
- Verificar formato JSON del archivo de macros
