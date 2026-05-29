# Alfheim Dashboard

HTMX-based web dashboard for the Yggdrasil ecosystem.

## Stack

- **HTMX** – server-driven dynamic UI
- **Alpine.js** – lightweight client-side reactivity
- **Jinja2** – server-side templating

## Getting Started

```bash
uv run poe dashboard
```

The server starts on <http://localhost:8000> with live-reload enabled.

## Project Layout

```
Alfheim/dashboard/
├── alfheim/dashboard/   # Python package (app factory, routes, templates)
├── pyproject.toml        # Package metadata & dependencies
└── README.md
```
