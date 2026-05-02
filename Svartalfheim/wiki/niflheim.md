---
name: Niflheim
realm: Niflheim
status: Activo
stack:
  - GGUF/GGML (modelos LLM)
  - SQLite (datasets)
  - Assets varios
dependencies:
  - Asgard (consume modelos)
  - Vanaheim (consume modelos)
  - Alfheim (sirve assets visuales)
---

# ❄️ Niflheim — Reino de los Recursos y Assets

> *Donde las nieblas eternas guardan los modelos que dan vida a la inteligencia.*

## 📜 Propósito

Niflheim es la bóveda de recursos del ecosistema — aquí residen los modelos LLM, datasets, assets visuales y cualquier recurso pesado que los demás reinos necesitan consumir. Es la fuente primaria de "materia prima" para la inteligencia.

## 🏗️ Arquitectura

```
Niflheim/
└── Models/
    ├── [model-name].gguf     # Modelos LLM locales
    ├── [model-name].ggml     # Modelos LLM (formato legacy)
    └── datasets/             # Datasets de entrenamiento/fine-tuning
```

## 🔧 Componentes Clave

| Componente | Función |
|-----------|---------|
| Models/ | Modelos LLM para LM Studio |
| Datasets/ | Datos para fine-tuning y evaluación |
| Assets/ | Recursos visuales y multimedia |

## 🔗 Dependencias

- **Asgard**: Consume modelos via LM Studio (local inference)
- **Vanaheim**: Consume modelos para bots
- **Alfheim**: Sirve assets visuales para dashboards

## 📊 Estado

- **Tamaño**: ~4.3 GB, 12 archivos
- **Modelos**: Modelos GGUF para inference local
- **Uso principal**: LM Studio apunta aquí para servir modelos

## ❄️ Reglas de la Niebla

1. No se commitean binarios grandes a git (LNK files en su lugar)
2. Los modelos se descargan y organizan manualmente
3. Documentar fuente y versión de cada modelo
4. Niflheim sirve a todos los reinos pero no depende de ninguno
