# Muspelheim

**Dev/WIP — Proyectos en Desarrollo Activo**

Muspelheim es el reino del fuego y la creacion. Aqui nacen los proyectos nuevos y se experimenta sin restricciones. Maximo 4 proyectos activos.

## Proyectos

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| **Horror-GameMaster** | Fases 1-4 DONE | Motor de terror procedural con IA |

### Horror-GameMaster

El proyecto principal de Muspelheim. Motor de juego de terror procedural:

- **Dataset:** 2,200+ entradas JSONL (v3 generacion activa, 19 modelos)
- **Tests:** 84 tests
- **Modulos:** 8 modulos (generacion procedural, integracion LLM, frontend)
- **Scripts:** `generate_v2.py`, `generate_v3.py` (rotacion BytePlus + MiMo)
- **Fases completadas:**
  - Fase 1: Dataset base
  - Fase 2: Motor de Terror
  - Fase 3: Integracion LLM
  - Fase 4: Frontend

## Estructura

```
Muspelheim/
├── Horror-GameMaster/
│   ├── data/          # Datasets JSONL (v1, v2, v3, unified, environmental)
│   ├── deploy/        # Configuracion de despliegue
│   ├── docs/          # Documentacion y brainstorm
│   ├── scripts/       # Scripts de generacion
│   ├── src/           # Cigo fuente (8 modulos)
│   ├── tests/         # Suite de tests (84 tests)
│   ├── Dockerfile     # Contenedor
│   ├── README.md      # Documentacion del proyecto
│   └── ROADMAP.md     # Hoja de ruta
└── README.md
```

## Reglas

1. Maximo 4 proyectos activos simultaneamente.
2. Los proyectos estables se migran a su realm correspondiente.
3. Los experimentos fallidos van a Helheim.

---

*Parte del ecosistema Yggdrasil — BrierStudios*
