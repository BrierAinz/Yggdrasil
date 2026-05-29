---
sidebar_position: 2
title: Creando un Agente Personalizado
---

# Creando un Agente Personalizado

Construye un agente con herramientas, memoria y personalidad propias.

## Paso 1: Definir Configuración

```python
from lilith_core import YggdrasilConfig

config = YggdrasilConfig(
    root_path="./mi-agente",
    model="gpt-4",
    temperature=0.8,
)
```

## Paso 2: Configurar Memoria

```python
from lilith_memory.store import MemoryStore

memory = Store(config.root / "memoria_agente.db")
```

## Paso 3: Registrar Herramientas Personalizadas

```python
from lilith_tools.registry import ToolRegistry

@ToolRegistry.tool(description="Obtener datos del clima")
def obtener_clima(ciudad: str) -> dict:
    return {"ciudad": ciudad, "temp": 22, "condicion": "soleado"}

@ToolRegistry.tool(description="Enviar un email")
def enviar_email(para: str, asunto: str, cuerpo: str) -> bool:
    return True
```

## Paso 4: Crear el Motor

```python
from lilith_orchestrator.engine import LilithEngine

engine = LilithEngine(config, memory)
```

## Paso 5: Ejecutar

```python
resultado = engine.process("¿Qué clima hace en Tokio?")
print(resultado["response"])
# "El clima en Tokio actualmente es soleado con 22°C."
```
