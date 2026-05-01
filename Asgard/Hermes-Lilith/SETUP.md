# Lilith - Instalacion Rapida

## Requisitos

1. **Python 3.11+** - python.org (marcar "Add to PATH")
2. **LM Studio** - lmstudio.ai
3. **Windows 10/11**

## Instalacion en 3 pasos

### Paso 1: LM Studio

1. Abrir LM Studio
2. Descargar un modelo (ej: Gemma 4 E4B, Qwen 3, Mistral, etc.)
3. Ir a la pestana **Local Server**
4. Click en **Start Server** (por defecto en puerto 1234)
5. Verificar que dice "Server running on http://localhost:1234"

### Paso 2: Instalar Lilith

Abrir CMD en la carpeta del proyecto y ejecutar:

```cmd
D:
cd D:\Proyectos\Yggdrasil\Asgard\Hermes-Lilith
install.bat
```

Esto hace:
- Instala dependencias (httpx, winrt)
- Crea el comando global `lilith`
- Agrega al PATH de Windows
- Crea carpetas necesarias

### Paso 3: Usar

**Reiniciar CMD** (necesario para que el PATH nuevo se cargue).

Luego desde cualquier carpeta:

```cmd
lilith
```

### Opciones de linea de comandos

| Flag | Descripcion |
|------|-------------|
| `lilith --help` | Mostrar ayuda completa |
| `lilith --version` | Mostrar version |
| `lilith --no-banner` | Iniciar sin banner |
| `lilith --streaming` | Iniciar con streaming activado |
| `lilith --no-streaming` | Iniciar con streaming desactivado |
| `lilith --cwd <path>` | Cambiar directorio antes de iniciar |

### Desinstalar

```cmd
cd D:\Proyectos\Yggdrasil\Asgard\Hermes-Lilith
uninstall.bat
```

## Comandos disponibles dentro de Lilith

| Comando | Descripcion |
|---------|-------------|
| `help` | Mostrar ayuda |
| `tools` | Ver herramientas disponibles |
| `clear` | Limpiar pantalla |
| `history` | Ver historial |
| `reset` | Reiniciar conversacion |
| `status` | Estado del sistema |
| `memory` | Ver memorias |
| `agents` | Ver sub-agentes |
| `tasks` | Ver tareas programadas |
| `index <ruta>` | Indexar archivos para RAG |
| `search <query>` | Buscar en documentos indexados |
| `exit` | Salir |

## Configuracion avanzada

Variables de entorno (opcional):

```cmd
set LILITH_MODEL=google/gemma-4-e4b
set LILITH_LM_URL=http://localhost:1234/v1
set LILITH_WORKSPACE=D:\Proyectos\Midgard
```

O editar directamente: `Lilith/Core/config.py`

## Troubleshooting

**"No puedo conectar con LM Studio"**
- Verificar que LM Studio este abierto
- Verificar que el Local Server este activado
- Probar en navegador: http://localhost:1234/v1/models

**"El comando 'lilith' no se reconoce"**
- Reiniciar CMD
- Verificar PATH: `echo %PATH%` debe contener `%LOCALAPPDATA%\Lilith\bin`

**"Python no encontrado"**
- Reinstalar Python marcando "Add Python to PATH"
