# Lilith + Hermes Agent Integration

## Overview

Conecta **Lilith** (control de PC Windows) con **Hermes Agent** (memoria persistente, skills auto-generados, sandboxing).

```
┌──────────────────────────────────────────────┐
│              WINDOWS (Lilith)                 │
│  ┌────────────────────────────────────┐     │
│  │ • Control de PC (mouse, keyboard)  │     │
│  │ • VS Code integration              │     │
│  │ • Windows system tools             │     │
│  └────────────────────────────────────┘     │
│                    │                           │
│         MCP Bridge (stdio)                    │
└────────────────────┼──────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────┐
│              WSL2 (Hermes Agent)              │
│  ┌────────────────────────────────────┐     │
│  │ • Memoria persistente              │     │
│  │ • Auto-generated skills           │     │
│  │ • Docker sandboxing               │     │
│  │ • Web scraping                    │     │
│  └────────────────────────────────────┘     │
└──────────────────────────────────────────────┘
```

## Installation

### 1. Instalar Hermes en WSL2

```bash
# En WSL2
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
```

### 2. Copiar archivos de integración

```bash
# En Windows PowerShell
# Copiar la carpeta Hermes al home de WSL2
wsl cp -r D:/Proyectos/Midgard/Lilith/Hermes ~/.hermes_lilith/
```

### 3. Configurar MCP en Hermes

```bash
# En WSL2
cd ~/.hermes_lilith

# Hacer ejecutable el bridge
chmod +x mcp_bridge.py
```

### 4. Configurar Hermes

```bash
hermes setup
```

Seleccionar:
- Provider: Custom Endpoint
- Endpoint: http://localhost:1234/v1 (LM Studio Windows via WSL)
- Model: google/gemma-4-e4b

### 5. Ejecutar

```bash
# Terminal 1: MCP Bridge (Windows)
python D:\Proyectos\Midgard\Lilith\Hermes\mcp_bridge.py

# Terminal 2: Hermes (WSL2)
hermes
```

## Files

```
Hermes/
├── INSTALL.md        # Guía de instalación paso a paso
├── README.md         # Este archivo
├── mcp_bridge.py    # Bridge MCP (expone tools de Lilith)
└── hermes_config.yaml # Configuración de Hermes
```

## Available Tools

Una vez conectado, estas tools de Lilith estarán disponibles en Hermes:

| Tool | Descripción |
|------|-------------|
| `screenshot` | Captura de pantalla |
| `list_windows` | Lista ventanas abiertas |
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `list_directory` | Lista directorio |
| `run_terminal` | Ejecuta comandos |
| `open_vscode` | Abre VS Code |
| `run_git` | Comandos git |
| `search_in_files` | Busca en archivos |
| `list_processes` | Lista procesos |
| `kill_process` | Mata procesos |
| `get_system_info` | Info del sistema |
| `get_disk_space` | Espacio en disco |
| `ping` | Ping a host |
| `open_url` | Abre URL |
| `search_google` | Busca en Google |

## Benefits

### Con Lilith Standalone
- CLI simple
- Sin externalidades
- Control total

### Con Hermes + Lilith
- **Memoria persistente**: Skills que se auto-generan
- **Auto-mejora**: Aprende de cada tarea
- **Sandboxing**: Aislamiento para código peligroso
- **Skills Hub**: Marketplace de habilidades
- **Web capabilities**: Scraping, browser automation

## Troubleshooting

### Bridge no conecta

```bash
# Verificar que Python de Windows es accesible desde WSL
python.exe --version

# O usar Python de WSL
which python
```

### LM Studio no conecta desde WSL

```bash
# Obtener IP de Windows
cat /etc/resolv.conf
# nameserver 172.x.x.x

# Usar esa IP en Hermes
# Endpoint: http://172.x.x.x:1234/v1
```

## Next Steps

1. Probar con `hermes tools` - ver si aparecen las tools de Lilith
2. Probar con `screenshot` via Hermes
3. Usar comandos de Lilith desde Hermes
4. Dejar que Hermes genere skills automáticamente
