# 🜏 Lilith — Dark Fantasy CLI Agent

![Python 3.12](https://img.shields.io/badge/Python-3.12-4B0082?style=flat-square&logo=python)
![Tests](https://img.shields.io/badge/Tests-330%20passing-00C853?style=flat-square&logo=pytest)
![License](https://img.shields.io/badge/License-Proprietary-8B0000?style=flat-square)

> *Desde los abismos de Yggdrasil, donde los ecos del Más Allá danzan con los susurros de criaturas antiguas, surge Lilith — tu interfaz con lo desconocido. Un agente CLI de estética dark fantasy que invoca el poder de LLMs locales y remotos para ejecutar tu voluntad en el reino digital.*

## ⛧ El Portal

```
╔═══════════════════════════════════════════════════════╗
║  🜏  L I L I T H  —  Dark Fantasy CLI Agent         ║
║      v3.0 · El Ecosistema Yggdrasil                  ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  [El Oráculo] LM Studio (local) ✓                     ║
║  [Invocaciones] 35+ tools nativas registradas        ║
║  [Ecos] Memoria híbrida (vectorial + grafo + FTS)   ║
║  [Enjambre] Agentes especializados: OFF               ║
║  [Grimorio] TOML unificado ✓                         ║
║                                                       ║
║  > Invoca tu voluntad, viajero...                     ║
╚═══════════════════════════════════════════════════════╝
```

## ✦ Características

- **El Oráculo** — Multi-provider LLM con fallback automático (LM Studio local, Kimi remoto, cualquier OpenAI-compatible)
- **Invocaciones** — 35+ tools nativas (archivos, sistema, red, coding, browser, desktop, Windows) + MCP servers
- **Ecos del Más Allá** — Memoria híbrida: embeddings vectoriales, keyword search (FTS5), grafo de conocimiento, consolidación automática
- **El Enjambre** — Sistema de agentes especializados (investigador, programador, escritor, crítico) con delegación de tareas
- **Los Reinos** — Skills con hot-reload, sub-agentes, RAG, scheduling, plugins extensibles
- **El Grimorio** — Configuración unificada en TOML (`~/.lilith/config.toml`), prioridad: TOML > env vars > defaults
- **Portales Dimensionales** — Integración MCP (Model Context Protocol) para conectar servidores de herramientas externos
- **Visualización** — Dashboard web en tiempo real (aiohttp + WebSocket)
- **Estética Dark Fantasy** — ANSI colors, terminología nórdica/lovecraftiana, inmersión total

## ⚡ Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone <repo-url> && cd Hermes-Lilith

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python3 -m Lilith.main
```

Para el modo desarrollo o instalación editable:

```bash
pip install -e .
python3 -m Lilith.main
```

## 📜 El Grimorio (~/.lilith/config.toml)

Lilith usa un único archivo TOML como fuente de verdad. Se crea automáticamente en el primer arranque.

```toml
[llm]
default_provider = "lm_studio"  # Proveedor primario
max_tool_calls = 25             # Límite de iteraciones tool-calling
streaming = false               # Streaming por defecto

[llm.providers.lm_studio]
base_url = "http://localhost:1234/v1"
model = ""                      # Auto-detect vía /models
is_local = true

[llm.providers.kimi]
base_url = "https://api.moonshot.cn/v1"
model = "kimi-2.6"
api_key = ""                    # O usar KIMI_API_KEY env var
is_local = false

[memory]
max_history = 50
auto_compress = true

[skills]
dir = "~/.lilith/skills"
hot_reload = true
auto_trigger = true
max_triggered = 3

[dashboard]
host = "localhost"
port = 8765

[mcp]
servers = []  # Lista de servidores MCP (stdio/HTTP)
```

**Prioridad de configuración:** TOML > variables de entorno > valores por defecto.

## 🗡️ Uso Básico

### Sesión interactiva

```bash
# Iniciar Lilith
python3 -m Lilith.main

# Sin banner de intro
python3 -m Lilith.main --no-banner

# Con streaming activado
python3 -m Lilith.main --streaming

# Especificar directorio de trabajo
python3 -m Lilith.main --cwd /ruta/al/proyecto
```

### Conversación

```
> Hola, ¿quién eres?
> Ayúdame a listar archivos en mi proyecto
> Busca en los archivos la palabra "config"
> Escribe un script Python que ordene una lista
```

### Comandos CLI

| Comando | Descripción |
|---------|-------------|
| `/help` | Muestra el grimorio de comandos |
| `/status` | Estado completo del reino (proveedor, tools, memoria, agentes) |
| `/memory` | Ver episodios recientes de memoria |
| `/recall <consulta>` | Buscar en memorias por similitud semántica |
| `/compact` | Comprimir memorias antiguas |
| `/tools` | Listar tools disponibles (nativas + MCP) |
| `/skills` | Listar skills registrados |
| `/agents` | Ver sub-agentes especializados |
| `/swarm <cmd>` | Gestión del enjambre (spawn, status, kill, save, load, history) |
| `/mcp` | Estado de servidores MCP |
| `/dashboard` | Iniciar/detener dashboard web |
| `/tasks` | Tareas programadas |
| `/index <ruta>` | Indexar archivos/carpeta para RAG |
| `/search <consulta>` | Buscar en documentos indexados |
| `/plugins` | Listar plugins instalados |
| `/stream` | Activar/desactivar modo streaming |
| `/reset` | Reiniciar la conversación |
| `/quit` | Salir del reino |

## 🏗️ Arquitectura

Lilith se organiza en **Seis Reinos** interconectados. Para detalles completos, ver [ARCHITECTURE.md](ARCHITECTURE.md).

```
                    ┌─────────────────┐
                    │     CLI (main)   │
                    │  El Portal       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Orchestrator    │
                    │  El Nexus        │
                    └────────┬────────┘
                             │
        ┌──────────┬─────────┼─────────┬──────────┐
        │          │         │         │          │
   ┌────▼───┐ ┌───▼──┐ ┌───▼───┐ ┌──▼───┐ ┌──▼────┐
   │ Memory  │ │ LLM  │ │ Tools │ │Swarm │ │  MCP  │
   │ Ecos   │ │Orac. │ │Invoc. │ │Enjmb │ │Portl  │
   └────────┘ └──────┘ └───────┘ └──────┘ └───────┘
```

Para documentación detallada de API interna, ver [API.md](API.md).

## 🔮 Proveedores LLM Soportados

| Proveedor | Tipo | API | Notas |
|-----------|------|-----|-------|
| **LM Studio** | Local | OpenAI-compatible | Primario. Auto-detecta modelo vía `/models` |
| **Kimi (Moonshot)** | Remoto | OpenAI-compatible | Fallback. API key requerida |
| **Cualquier OpenAI-compatible** | Local/Remoto | OpenAI API | Configurar en `config.toml` |

El sistema tiene **fallback automático**: si el proveedor primario no responde, intenta con los proveedores alternativos en orden.

## 🧪 Testing

```bash
# Ejecutar todos los tests
python3 -m pytest tests/ -v

# Tests por módulo
python3 -m pytest tests/test_core.py -v        # Core
python3 -m pytest tests/test_memory.py -v      # Memoria
python3 -m pytest tests/test_swarm.py -v       # Enjambre
python3 -m pytest tests/test_mcp.py -v         # MCP
python3 -m pytest tests/test_dashboard.py -v   # Dashboard
python3 -m pytest tests/test_toml_config.py -v # Config TOML
python3 -m pytest tests/test_e2e.py -v         # E2E
```

**330 tests** pasando (Core, Memory, Swarm, MCP, Dashboard, TOML Config, E2E).

## 🤝 Contributing

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/nuevo-reino`)
3. Seguir la estética dark fantasy en código y UI
4. Escribir tests para nuevas funcionalidades
5. Commit y push (`git push origin feature/nuevo-reino`)
6. Crear Pull Request

**Convenciones:**
- Comentarios en español (coherente con el proyecto)
- Terminología nórdica/lovecraftiana en la UI y nombres de módulos
- `python3` (no `python`)
- Tests obligatorios para nuevos módulos

## 📜 License

Proprietario — Proyecto del ecosistema Yggdrasil.

---

*«En los submundos donde brillan las raíces de Yggdrasil, cada invocación es un pacto, cada tool un arma, cada conversación un eco que persiste más allá del olvido.»*
