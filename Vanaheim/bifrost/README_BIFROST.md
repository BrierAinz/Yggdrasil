# Bifrost Gateway

> **Estado:** EN DESARROLLO
> **Reino:** Vanaheim
> **Versión:** 2.0.0

## Descripción

Bifrost es el gateway API que conecta los servicios de Asgard con autenticación JWT, streaming y bridge hacia Hermes Agent.

## Componentes

- **auth.py** — Middleware de autenticación (JWT, API key, Basic Auth)
- **gateway.py** — Servidor FastAPI con proxy streaming y WebSocket fan-out
- **bifrost/** — Paquete Python con punto de entrada

## Instalación

```bash
uv pip install -e .
```

## Uso

```bash
uvicorn bifrost.gateway:app --host 0.0.0.0 --port 8001
```

## Testing

```bash
pytest
```

## Dependencias

- lilith-core, lilith-memory, lilith-orchestrator, lilith-bridge (workspace)
- FastAPI, uvicorn, pydantic, httpx
- python-jose (JWT), passlib (bcrypt)