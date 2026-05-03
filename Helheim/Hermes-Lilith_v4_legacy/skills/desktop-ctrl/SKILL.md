# Skill: Desktop Control

## Descripción
Control completo del escritorio de Windows: mouse, teclado, ventanas, screenshots y más.

## Capabilidades
- Movimiento y click de mouse (izq/der/doble)
- Escritura de texto y presión de teclas
- Control de ventanas (mover, resize, focus, minimize)
- Capturas de pantalla (global y por región)
- Scroll y hover
- Clipboard operations

## Tools Disponibles

### Mouse Operations
| Tool | Función |
|------|---------|
| `desktop_mouse_move` | Mover cursor a coordenadas específicas |
| `desktop_left_click` | Click izquierdo simple |
| `desktop_right_click` | Click derecho |
| `desktop_double_click` | Doble click |
| `desktop_left_click_drag` | Arrastrar con mouse |
| `desktop_scroll` | Scroll vertical/horizontal |

### Keyboard Operations
| Tool | Función |
|------|---------|
| `desktop_type` | Escribir texto |
| `desktop_key` | Presionar tecla individual |
| `desktop_hold_key` | Mantener tecla presionada |
| `desktop_press_key` | Presionar Enter, Tab, Escape, etc. |

### Window Operations
| Tool | Función |
|------|---------|
| `desktop_window_list` | Listar ventanas abiertas |
| `desktop_window_focus` | Traer ventana al frente |
| `desktop_window_minimize` | Minimizar ventana |
| `desktop_window_move_resize` | Mover o redimensionar |

### Visual Operations
| Tool | Función |
|------|---------|
| `desktop_screenshot` | Captura de pantalla completa |
| `desktop_screenshot_region` | Captura de región específica |
| `look_picture` | Analizar imagen capturada |

### Clipboard
| Tool | Función |
|------|---------|
| `desktop_clipboard_read` | Leer contenido del clipboard |
| `desktop_clipboard_write` | Escribir al clipboard |

## Patrones de Uso

### Abrir Aplicación
```
1. desktop_window_list → Encontrar si ya está abierta
2. Si no existe: Usar shell para abrir app
3. desktop_window_focus → Traer al frente
```

### Escribir en Campo de Texto
```
1. desktop_left_click → Posicionar cursor
2. desktop_type → Escribir texto
3. desktop_key "enter" → Confirmar (si necesario)
```

### Seguir Tutorial en Pantalla
```
1. desktop_screenshot → Capturar estado actual
2. look_picture → Identificar elementos a clickear
3. Iterar: click → screenshot → analizar → click siguiente
```

## Notas de Seguridad
- **Confirmar acciones destructivas**: Siempre pedir confirmación antes de Delete, rm, format
- **Backup antes de editar**: Usar Trash o crear backup antes de modificar archivos
- **Evitar comandos irreversibles**: No ejecutar rm -rf, format, diskpart sin confirmación explícita

## Ejemplo de Workflow Completo
```markdown
Tarea: Crear nuevo archivo Python en VS Code

1. desktop_key "super" → Abrir menú inicio
2. desktop_type "vscode" → Buscar VS Code
3. desktop_key "enter" → Abrir VS Code
4. desktop_key "ctrl+n" → Nuevo archivo
5. desktop_type "# Nuevo Script Python" → Escribir header
6. desktop_key "ctrl+s" → Guardar
7. desktop_type "nuevo_script.py" → Nombre del archivo
8. desktop_key "enter" → Confirmar guardado
```

## Integración con Learning Engine
Esta skill reporta cada tarea completada al learning engine para registrar patrones.

---
**Versión**: 1.0.0
**Última actualización**: 2026-04-20
