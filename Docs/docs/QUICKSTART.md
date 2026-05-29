# Quick Start

Guia rapida para poner en marcha Yggdrasil en tu maquina.

## Requisitos

- **Python** 3.11 o superior
- **Git**
- **pip** (incluido con Python)

Opcional:
- **uv** — Gestor de paquetes ultrarapido
- **Node.js** — Solo para el frontend de Alfheim

## Instalacion

```bash
# 1. Clonar el repositorio
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Ejecutar el CLI
python ygg.py
```

## Primeros Pasos

Una vez instalado, puedes explorar el ecosistema:

```bash
# Ver el estado de los 9 realms
python ygg.py status

# Ver el arbol de proyectos
python ygg.py tree

# Ver el tamano por reino
python ygg.py size

# Verificar salud del ecosistema
python ygg.py health

# Ejecutar tests
python ygg.py test
```

## CLI Principal: ygg.py

El CLI principal usa el tema Nordic Frost con Elder Futhark runes.

```
python ygg.py                    # Menu interactivo
python ygg.py status             # Estado de los reinos
python ygg.py tree               # Arbol de proyectos
python ygg.py size               # Tamano por reino
python ygg.py clean              # Limpiar archivos regenerables
python ygg.py backup             # Backup de Svartalfheim + configs
python ygg.py health             # Verificar README.md en cada reino
python ygg.py migrate            # Migrar proyecto entre reinos
python ygg.py update             # Git pull + deps
```

## Agente Lilith

Para iniciar el agente de IA:

```bash
python lilith_agent.py
```

Lilith es un agente de codigo completo con memoria persistente, skills, y ejecucion de comandos.

## Chat con Lilith

```bash
python lilith_cli.py chat
```

Comandos del chat:
- `ayuda` — Mostrar ayuda
- `resumen` — Resumen de la conversacion
- `memoria` — Ultimas entradas de memoria
- `borrar` — Borrar memoria
- `salir` — Terminar

## Configuracion

Copia el archivo de ejemplo y edita con tus credenciales:

```bash
cp .env.example .env
# Editar .env con tu editor favorito
```

Variables importantes:
- `OPENAI_API_KEY` — Para OpenAI
- `ANTHROPIC_API_KEY` — Para Claude
- `MIMO_API_KEY` — Para MiMo

## Siguiente Paso

- [Realm Overview](REALMS.md) — Conoce los 9 realms
- [Lilith Guide](LILITH.md) — Guia completa de Lilith
- [API Reference](API.md) — Documentacion de la API
