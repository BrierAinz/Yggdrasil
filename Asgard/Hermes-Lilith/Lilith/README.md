# Lilith - Asistente Personal con IA Local

## Descripción

Lilith es un asistente personal que corre **100% local** usando LM Studio + Gemma 4 E4B. Maneja tu PC, hace coding en VS Code, aprende de tareas, y tiene memoria híbrida.

## Características

### 🧠 Memoria Híbrida
- **Local**: Episodios, procedimientos, errores en JSON
- **RAG**: Indexa tus archivos para búsqueda semántica
- **Preparado para**: Mem0, Zep, Qdrant

### 🤖 Sub-Agentes (estilo Vanaheim)
- Investigador
- Programador
- Escritor
- Explicador
- Crítico
- Planificador
- Lluvia de Ideas

### ⏰ Scheduler de Tareas
- Expresiones cron para scheduling
- Presets: minutely, hourly, daily, weekly, monthly
- Historial de ejecuciones

### 🔌 Sistema de Plugins
- Extensible con nuevos plugins
- Plugins incluidos: GitHub integration (ejemplo)

### 📁 RAG sobre Archivos
- Indexa código, docs, notas
- Búsqueda semántica
- Contexto para conversaciones

### 🔔 Notificaciones Windows
- Toast notifications
- Registro de historial

### ⚡ Auto-arranque
- Iniciar con Windows
- Configurable

## Requisitos

- **Windows 10/11**
- **Python 3.12+**
- **LM Studio** con Gemma 4 E4B cargado
- **48GB RAM** (recomendado)
- **RTX 3060 12GB** (para acelerar inferencia)

## Instalación

```powershell
# 1. Clonar o navegar al proyecto
cd D:\Proyectos\Midgard\Lilith

# 2. Instalar dependencias
pip install requests psutil Pillow

# 3. Instalar dependencias opcionales
pip install croniter

# 4. Abrir LM Studio y cargar Gemma 4 E4B
#    - Seleccionar modelo
#    - Click "Local Server"
#    - Asegurar que esté en puerto 1234

# 5. Ejecutar
python main.py
```

O usar el launcher:
```powershell
.\launch_lilith.ps1
```

## Comandos CLI

| Comando | Descripción |
|---------|-------------|
| `help` | Mostrar ayuda |
| `status` | Estado completo del sistema |
| `tools` | Listar herramientas disponibles |
| `history` | Ver historial de conversación |
| `reset` | Reiniciar conversación |
| `memory` | Ver memorias guardadas |
| `recall <query>` | Buscar en memorias |
| `agents` | Ver sub-agentes |
| `tasks` | Ver tareas programadas |
| `index <path>` | Indexar archivos/carpeta para RAG |
| `search <query>` | Buscar en documentos indexados |
| `plugins` | Ver plugins instalados |
| `autostart` | Configurar auto-arranque |
| `notify` | Probar notificaciones |
| `exit` | Salir |

## Estructura del Proyecto

```
Lilith/
├── Core/               # Nucleo - LLM, orchestrator
├── tools/              # Herramientas del sistema
├── memory/             # Sistema de memoria
│   └── hybrid.py       # Memoria híbrida
├── Agents/             # Sub-agentes
├── Scheduler/          # Programador de tareas
├── RAG/                # Motor RAG
├── Plugins/            # Sistema de plugins
│   └── github/         # Plugin de ejemplo
├── Data/               # Datos persistentes
│   ├── memory/         # Episodios, errores, procedimientos
│   ├── rag/           # Índice RAG
│   ├── agents/        # Config de agentes
│   └── scheduler/     # Tareas programadas
├── main.py             # CLI principal
├── notifications.py    # Notificaciones
├── auto_start.py      # Auto-arranque
└── requirements.txt    # Dependencias
```

## Tools Disponibles (35+)

### Dominio del PC
- `screenshot` - Captura de pantalla
- `get_cursor_position` - Posición del cursor
- `list_windows` - Ventanas abiertas

### Archivos
- `read_file`, `write_file`, `list_directory`
- `file_exists`, `search_in_files`

### Sistema
- `run_terminal` - Ejecutar comandos
- `open_vscode` - Abrir VS Code
- `open_application` - Abrir apps

### Coding
- `run_git`, `run_npm`, `run_python_script`
- `get_git_status`, `list_git_branches`

### Windows
- `list_processes`, `kill_process`
- `get_system_info`, `get_disk_space`
- `list_services`, `start_service`, `stop_service`

### Browser
- `open_url`, `search_google`
- `clipboard_read`, `clipboard_write`
- `type_text`, `press_key`

### Red
- `ping`, `check_port`, `get_network_info`
- `download_file`, `check_internet`

## Programar Tareas

```python
from Lilith.Scheduler.task_scheduler import get_scheduler

scheduler = get_scheduler()
scheduler.create_task(
    name="Daily Backup",
    description="Respaldar proyectos",
    command="python backup.py",
    schedule="0 0 * * *"  # Daily at midnight
)
```

Presets: `minutely`, `hourly`, `daily`, `weekly`, `monthly`

## Crear un Plugin

```python
# Plugins/mi_plugin/plugin.py
from Lilith.Plugins.plugin_manager import Plugin, PluginCapability

def get_plugin():
    return Plugin(
        id="mi_plugin",
        name="Mi Plugin",
        version="1.0.0",
        description="Descripción del plugin",
        author="Tu Nombre",
        capabilities=[PluginCapability.TOOL],
        tools=[...],  # Definición de tools
        config={}
    )
```

## Configurar Auto-arranque

```powershell
# En Lilith CLI
autostart enable    # Habilitar
autostart disable   # Deshabilitar
autostart status    # Ver estado
```

## RAG - Indexar Documentos

```powershell
# Indexar carpeta completa
index D:\Proyectos\Midgard

# Indexar archivo
index D:\Proyectos\Midgard\Lilith\README.md

# Buscar en documentos
search "como instalar python"
```

## Integración Futura

### Mem0 (Memoria Episódica)
```python
# Preparado para conectar con Mem0
from mem0 import Memory
memory = Memory()
```

### Zep (Memoria a Largo Plazo)
```python
# Preparado para Zep
from zep_python import ZepClient
client = ZepClient()
```

### Qdrant (Vector Store)
```python
# Para embeddings reales
import qdrant_client
```

## Troubleshooting

### LM Studio no conecta
1. Abre LM Studio
2. Carga Gemma 4 E4B
3. Click "Local Server"
4. Verifica puerto 1234
5. Click "Start Server"

### Memory errors
```powershell
# Reiniciar memoria
rm -rf D:\Proyectos\Midgard\Lilith\Data\memory\*
```

### Scheduler no ejecuta
```powershell
# Ver logs
Get-Content D:\Proyectos\Midgard\Lilith\logs\scheduler.log
```

## Autor

Matrix Agent - 2026
