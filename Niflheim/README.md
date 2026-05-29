<<<<<<< HEAD
# Niflheim

**Assets — Modelos, Datasets y Recursos Estaticos**

Niflheim es el reino de la niebla y los recursos ocultos. Aqui se almacenan los modelos de IA, datasets y archivos grandes que no van en git.

## Contenido

| Tipo | Ejemplos | Excluido de git |
|------|----------|-----------------|
| Modelos | .safetensors, .pth, .pt, .bin, .onnx, .ckpt | Si |
| Datasets | .jsonl, .csv, .parquet | Si |
| Assets | Imagenes, videos, audio | Si |

## Nota

Todo el contenido de Niflheim esta excluido del control de versiones via `.gitignore`. Los archivos se almacenan localmente o en almacenamiento externo.

---

*Parte del ecosistema Yggdrasil — BrierStudios*
=======
# ❄️ Niflheim

El reino de la niebla y el hielo. Donde los datos se congelan en silencio y los modelos esperan su despertar.

Niflheim almacena los recursos de inteligencia artificial: datasets, modelos preentrenados y los artefactos de niebla que alimentan las venas del árbol. Aquí nada se ejecuta — todo descansa. Es el almacén glacial donde las criaturas de silicona aguardan ser invocadas. **Nada de código vive en Niflheim.** El código es fuego y pertenece a Muspelheim.

> ✅ **MIGRACIÓN COMPLETADA:** `ForgeMaster/` fue trasladado a `Muspelheim/ForgeMaster/`. Niflheim ahora cumple su regla de solo-recursos. `scripts/model_manager.py` permanece como utilidad de infraestructura del propio realm.

## 📂 Estructura del Reino

```
Niflheim/
├── Datasets/
│   └── cifar-10-batches-py/          # Dataset CIFAR-10. Los ojos congelados de la criatura.
├── Models/
│   └── Lilith_v5_models/              # Modelos preentrenados de Lilith v5.
└── scripts/
    └── model_manager.py               # Utilidad de infraestructura local (gestiona modelos del realm).
```

## ⚔️ Estado

**Limpio.** Niflheim ahora es un reino puro de recursos. Solo datos, modelos y utilidades de gestión del propio realm.

## 🔗 Vínculos

- [Models — Lilith v5](./Models/Lilith_v5_models/) — La manifestación congelada de Lilith.
- [Datasets — CIFAR-10](./Datasets/cifar-10-batches-py/) — Datos de entrenamiento, preservados en el hielo.
- [ForgeMaster → Muspelheim](../Muspelheim/ForgeMaster/) — Herramienta de gestión de modelos (migrada a Muspelheim).

---

*Última actualización: 2026-05-02*
>>>>>>> origin/main
