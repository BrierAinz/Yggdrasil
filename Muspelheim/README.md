# 🔥 Muspelheim — El Reino del Fuego Primordial

> *"Donde las forjas arden sin tregua y las llamas crean lo que aún no existe."*

**Propósito:** Creación ardiente — generación de contenido, gestión de modelos LLM, subtítulos automáticos, pipeline de influencer IA.

**Estado:** ✅ ACTIVO | **Refactoring:** Phase 1 completado 2026-05-21

---

## 📦 Proyectos Activos

| Proyecto | Versión | Estado | Descripción | Tests |
|---|---|---|---|---|
| ForgeMaster | v1.0.0 | ✅ ACTIVO | Gestión de modelos LLM, VRAM, disco — CLI tool | 238 |
| AutoSub | v0.1.0 | ✅ COMPLETO | Generador de subtítulos automático con traducción | — |
| AI-Influencer (Eir) | — | 🌱 FASE 0 | Pipeline de entrenamiento LoRA y generación de contenido | — |

### ForgeMaster
- **CLI:** `forgemaster` — gestión de catálogo, descarga, VRAM/disk monitoring
- **Módulos:** scanner, catalog, metadata, gpu, vram, disk, downloader, logging, config

### AutoSub
- **CLI:** `autosub` — transcripción Whisper + traducción + export SRT/ASS
- **Dependencias:** faster-whisper, deep-translator, pysubs2, typer

### AI-Influencer
- Pipeline de generación de contenido para influencer IA (Eir)
- Scripts de composición, upscaling, postprocesado
- ⚠️ `tools/` — **Directorio vacío** (kohya_ss eliminado en Phase 1)
- Outputs en `outputs/` (imágenes, reels, stories — en `.gitignore`)

---

## ⚠️ Eliminado

### `kohya_ss` — Clone Eliminado (2026-05-21)
- **Antes:** `AI-Influencer/tools/kohya_ss/` — 6.9GB, 10,827 archivos `.py`
- **Razón:** Clon completo del repo de Kohya SS con su propio `.git`. No pertenece al ecosistema Yggdrasil.
- **Acción:** Eliminado completamente en Phase 1
- **Rescatable:** Se puede re-clonar desde GitHub si se necesita
- **Ver:** `Helheim/Graveyard.md` para detalles

---

## 🧹 Limpieza Phase 1 (2026-05-21)

- ✅ `kohya_ss` eliminado (6.9GB, 10,827 archivos .py liberados)
- ✅ `.venv` redundante de ForgeMaster eliminado (~580MB totales entre todos los reinos)
- ✅ `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` limpiados
- ✅ `.gitignore` actualizado con outputs de AI-Influencer

---

## 📂 Árbol

```
Muspelheim/
├── ForgeMaster/           # v1.0.0 — Gestión de modelos LLM
│   ├── forgemaster/       # Código fuente
│   ├── tests/             # 238 tests
│   └── pyproject.toml
├── AutoSub/               # v0.1.0 — Subtítulos automáticos
│   ├── autosub/           # Código fuente
│   ├── tests/
│   └── pyproject.toml
├── AI-Influencer/          # Pipeline Eir (FASE 0)
│   ├── scripts/           # Generación, composición, upscaling
│   ├── workflows/         # API configs
│   ├── outputs/           # Salidas (gitignored)
│   └── tools/             # ⚠️ Vacío (kohya_ss eliminado)
├── AutoMode/              # Plantillas y modos automáticos
└── Docs/                  # Documentación del reino
```

---

## 🔗 Enlaces

- [Asgard](../Asgard/) — Núcleo de Lilith
- [Niflheim](../Niflheim/) — Recursos congelados (modelos, datasets)
- [Helheim](../Helheim/) — Registro de proyectos eliminados (Graveyard.md)

---

*Las forjas de Muspelheim jamás se apagan.*
