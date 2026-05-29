---
sidebar_position: 9
title: Jotunheim
---

# ᛒ Jotunheim — El Reino de los Gigantes

Jotunheim es el dominio de la infraestructura y DevOps. Los gigantes mantienen el árbol en pie.

## Componentes

- **GitHub Actions** — CI/CD pipeline
- **GitHub Pages** — Deploy de documentación
- **Dependabot** — Gestión de dependencias
- **Cloudflare** — DNS y proxy

## Pipeline CI

1. **Lint** — ruff check + ruff format
2. **Test** — pytest por paquete (Python 3.11 + 3.12)
3. **Type Check** — pyright (soft fail)
4. **Deploy** — Docusaurus a GitHub Pages

## Principio

La infraestructura es código. Si no está en git, no existe.
