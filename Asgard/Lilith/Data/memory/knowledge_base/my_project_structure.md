# Estructura del Proyecto: Yggdrasil IA

## VisiÃ³n General (The Realms)
El proyecto se divide en reinos mitolÃ³gicos que representan capas lÃ³gicas:

- **Yggdrasil (Root):** La carpeta raÃ­z y orquestador conceptual.
- **Sebas Core (The Brain):** El backend Python que maneja la lÃ³gica, IPC y ejecuciÃ³n. (Rebranded: Lilith KERNEL).
- **Midgard (The Client):** El frontend de usuario (Tauri/React) para el Launcher y dashboard.
- **Valhalla (The Testing Grounds):** Entorno de pruebas y validaciÃ³n.
- **Svartalfheim (The Forge):** Herramientas de desarrollo, scripts utilitarios, GUIs auxiliares y capacidades experimentales.
- **Jotunheim (The Memory):** Almacenamiento de datos, datasets y modelos (Memory/Knowledge Base).

## Directorios Clave

### `d:\Proyectos\Proyectos Alpha\Yggdrasil IA\`
- `sebas_core/`: `main.py`, `ipc_server.py`, `core/` logic.
- `Svartalfheim/`: `capabilities/` (scripts ejecutables), `gui/`.
- `memory/`: `knowledge_base/` (este directorio), `stats.json`, `config/`.
- `tests/`: Tests de integraciÃ³n y harnesses.

## Convenciones
- **Python:** Type hinting estricto, Pydantic para validaciÃ³n de datos.
- **IPC:** NDJSON sobre Named Pipes (Windows).
- **Git:** Commits atÃ³micos.

## FilosofÃ­a de CÃ³digo
"Measure twice, cut once."
- Planificar antes de implementar (`implementation_plan.md`).
- Documentar cambios en `task.md`.
- No romper la build principal.
