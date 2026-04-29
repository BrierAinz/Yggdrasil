# Yggdrasil v2.0

> *"Del caos del vacio, Yggdrasil crece con raices profundas y ramas que tocan todos los cielos."*

Ecosistema personal de proyectos organizado bajo la metafora de los 9 reinos nordicos.

## Quick Start

```bash
# Instalar dependencias
pip install -e Asgard/lilith-core -e Asgard/lilith-tools -e Asgard/lilith-memory \
    -e Asgard/lilith-orchestrator -e Asgard/lilith-api -e Asgard/lilith-cli \
    -e Vanaheim/vanaheim-framework

# Correr tests
pytest

# Iniciar API
uvicorn lilith_api.main:app --reload --port 8000

# Iniciar CLI
python -m lilith_cli.main

# Lanzar bot de Vanaheim
python Vanaheim/launcher.py vanaheim
```

## Estructura

```
Yggdrasil/
  Asgard/        — Core tech (Lilith, Hermes)
  Vanaheim/      — AI agents y bots
  Alfheim/       — UI prototypes y dashboards
  Svartalfheim/  — Documentacion y knowledge base
  Muspelheim/    — Active development / WIP
  Niflheim/      — Recursos, assets, modelos LLM
  Midgard/       — Apps personales
  Jotunheim/     — Proyectos masivos
  Helheim/       — Archivo y legacy
```

## Estado del Ecosistema

- **Tests:** 17/17 pasando
- **Pre-commit:** Activo (black, isort, trailing-whitespace)
- **API:** FastAPI en `lilith-api`
- **CLI:** `lilith-cli` con entry point `lilith`
- **Framework Bots:** `vanaheim-framework` con launcher unificado

## Reglas

Ver `REGLAS_YGGDRASIL.md` para las reglas completas del ecosistema.
