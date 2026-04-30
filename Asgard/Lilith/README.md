# Lilith

Asistente AI con memoria persistente, orquestador de herramientas y bot para Discord. Proyecto en formato monorepo.

---

## Estructura del proyecto

```
Lilith/
├── arranque_lilith.bat    # Arranque rápido: API + bot Discord
├── cerrar_lilith.bat      # Cierre de procesos
├── Core/                  # Núcleo: API, Backend, Config, memoria, tests
│   ├── Backend/           # Lógica (orchestrator, planner, tools_v3, agents, LLM)
│   ├── Config/            # security.json, memory.json, discord_roles.json, etc.
│   ├── Data/              # Cache, auditoría, feedback (generado en runtime)
│   ├── Docs/              # Misiones 3.x, defensa inyección, estructura
│   ├── Memory/            # Memoria semántica/episódica/procedimental (datos)
│   ├── Scripts/           # Utilidades (verify_*, audit_lilith, etc.)
│   ├── Tests/             # Tests (raíz y subcarpeta fases/)
│   ├── Tools/             # IPC client, load_env (usado por la API)
│   ├── Frontend/          # SPA (opcional)
│   └── Workspace/         # Destrezas, Taller
├── Discord/               # Bot Discord (bot.py, handlers, auth)
└── VSCode/                # Extensión/entorno VSCode (opcional)
```

---

## Cómo arrancar

### Opción recomendada: API + Discord

Desde la raíz del proyecto (`Lilith/`):

```batch
arranque_lilith.bat
```

- Abre dos ventanas: **API** (FastAPI en `http://localhost:8000`) y **bot Discord**.
- El bot usa la API por HTTP; no hace falta levantar el proceso Core (main.py) para el flujo normal.

### Opción completa: Core + API

Desde `Lilith/Core/`:

```batch
launch_lilith.bat
```

- Primero inicia el proceso Core (IPC, orquestador), luego la API. Útil si usas funciones que dependen del IPC.

### Solo API (desarrollo)

Desde `Lilith/Core/` (con `PYTHONPATH=Lilith\Core` o desde `Core`):

```batch
python -m Backend.api.server
```

### Solo bot Discord

Desde `Lilith/Discord/`:

```batch
python bot.py
```

Requiere que la API esté levantada en `http://localhost:8000` (o la URL configurada en `.env`).

---

## Puntos de entrada

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| API REST + WebSocket | `Core/Backend/api/server.py` | FastAPI, endpoints Discord, dashboard |
| Proceso Core (IPC) | `Core/Backend/main.py` | Motor IPC, orquestador (opcional) |
| Bot Discord | `Discord/bot.py` | Bot con slash commands, roles owner/trusted/public |

---

## Documentación

- **Misiones y diseño:** `Core/Docs/` (MISION_LILITH_3.x.md, HORIZONTE_4.0.md, DEFENSA_INYECCION_PROMPTS.md).
- **Configuración:** `Core/Config/README.md` y `Core/Config/discord_roles_checklist.md`.
- **Estructura detallada:** `Core/Docs/ESTRUCTURA_PROYECTO.md`.

---

## Tests

Desde `Lilith/Core/`:

```batch
pytest Tests/ -v
```

Los tests están en `Tests/` y en `Tests/fases/`; ver `Core/Tests/README.md` para la organización.
