# Lilith — Resumen del proyecto

**Ruta:** `D:\Proyectos\Yggdrasil\Asgard\Lilith`

---

## ¿Qué es?

**Lilith** es un asistente de IA con memoria persistente, orquestador de herramientas y **bot para Discord**. Funciona como monorepo: Core (API, backend, configuración, memoria), bot Discord y opcionalmente extensión/entorno VSCode.

---

## ¿Para qué sirve?

- Ofrecer un asistente conversacional en Discord con roles (owner, trusted, public).
- Orquestar herramientas (lectura/edición de archivos, delegación a agentes como Eva, Adán, Lucifer, minería web) y memoria semántica, episódica y procedimental.
- En la línea 4.0: flujo de minería web (scrape → limpieza → filtro de calidad → estructuración → guardado en memoria) y ecosistema de agentes (AgentRegistry, WebScraper, ContentCleaner, QualityFilter, DataStructurer).

---

## Cómo arrancarlo

- **Recomendado (API + bot Discord):** desde `Lilith/` ejecutar `arranque_lilith.bat`.
- **Solo API (desarrollo):** desde `Lilith/Core/`, `python -m Backend.api.server`.
- **Solo bot:** desde `Lilith/Discord/`, `python bot.py` (con la API en marcha).

Documentación detallada: **README.md** en la raíz de Lilith y `Core/Docs/`, `Core/Config/README.md`.

---

## Estructura resumida

```
Lilith/
├── README.md, RESUMEN.md
├── arranque_lilith.bat, cerrar_lilith.bat
├── Core/          # Núcleo: API, Backend, Config, Data, Docs, Memory, Scripts, Tests, Tools, Frontend, Workspace
├── Discord/       # Bot Discord (bot.py, handlers)
└── VSCode/        # Extensión/entorno VSCode (opcional)
```
