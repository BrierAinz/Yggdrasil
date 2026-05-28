---
title: Batch Mode — Ejecución No-Interactiva
last_updated: 2026-05-02
version: v4.0.0+
category: feature
---

# 🏭 Batch Mode — Ejecución No-Interactiva

> *Cuando la forja no necesita al herrero presente, los motores trabajan solos.*

## Resumen

Batch Mode permite ejecutar Lilith de forma no-interactiva mediante CLI, ideal para pipelines CI/CD, scripts de automatización, y procesamiento masivo de tareas sin intervención humana.

## Uso

```bash
# Ejecución básica
lilith --batch "Resume los cambios del último commit"

# Con system prompt personalizado
lilith --batch "Genera el CHANGELOG" --batch-sys "Eres un generador de changelogs técnico"

# Stream de salida (para pipes)
lilith --batch "Analiza el código" --batch-stream

# Salida en JSON estructurado
lilith --batch "Clasifica estos archivos" --batch-json

# Sin herramientas (solo texto)
lilith --batch "Traduce al inglés" --batch-no-tools

# También via módulo Python
python -m Lilith.batch "Analiza el_performance del sistema"
```

## Flags Disponibles

| Flag | Descripción |
|------|-------------|
| `--batch "prompt"` | Ejecuta en modo batch con el prompt dado |
| `--batch-sys "system"` | System prompt personalizado |
| `--batch-stream` | Stream de output en tiempo real (para pipes) |
| `--batch-json` | Salida estructurada en JSON |
| `--batch-no-tools` | Deshabilita invocación de herramientas |

## Modos de Salida

### Texto Plano (default)
```
$ lilith --batch "Lista los archivos Python"
Los archivos Python encontrados son:
- main.py
- orchestrator.py
- ...
```

### JSON (`--batch-json`)
```json
{
  "response": "Los archivos Python encontrados son...",
  "model": "kimi-for-coding",
  "provider": "kimi",
  "tokens": {"input": 42, "output": 156},
  "tools_used": [],
  "duration_ms": 2340
}
```

### Stream (`--batch-stream`)
Output en tiempo real, carácter por carácter. Ideal para integración con pipes Unix:
```bash
lilith --batch "Genera SQL para la tabla users" --batch-stream | tee migra.sql
```

## Integración con Swarm

Batch Mode es la base de ejecución de los Swarm Agents. Cada worker:

1. Se inicializa con `--batch-sys` definiendo su rol
2. Ejecuta con `--batch-no-tools` si es razonamiento puro
3. Reporta resultados via MessageBus
4. El SwarmManager coordinada via `--batch-json` para parsear resultados

## Casos de Uso

### 1. CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
- name: Análisis de código
  run: lilith --batch "Analiza la quality de este PR" --batch-json > analysis.json
```

### 2. Procesamiento Masivo
```bash
for dir in projects/*/; do
  lilith --batch "Resume el README de $dir" --batch-no-tools >> summaries.txt
done
```

### 3. Generación de Docs
```bash
lilith --batch "Genera documentación API para Lilith/Swarm/" \
  --batch-sys "Eres un documentador técnico experto"
```

## Implementación

El módulo batch está en `Lilith/batch/`:

```
Lilith/batch/
├── __init__.py       # Entry point, registra modo batch
├── runner.py         # Ejecución principal
├── formatter.py      # Formateo de salida (text/json/stream)
└── config.py         # Configuración del modo batch
```

Flujo interno:

1. `main.py` detecta `--batch` flag
2. Inicializa `BatchRunner` con prompt y flags
3. Crea sesión temporal (no persiste en historial interactivo)
4. Ejecuta a través del orquestador existente
5. Formatea salida según flags seleccionadas
6. Sale con código 0 (éxito) o 1 (error)

## Notas

- Batch Mode no persiste sesión interactiva
- Los tokens se contabilizan igual que modo interactivo
- Si el provider falla, el fallback automático se activa
- `--batch-no-tools` reduce consumo de tokens significativamente
