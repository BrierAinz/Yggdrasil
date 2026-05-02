---
title: Cross-Realm Dependency Map
last_updated: 2026-05-02
---

# 🕸️ Cross-Realm — Mapa de Dependencias entre Reinos

> *Las raíces del Yggdrasil conectan los nueve mundos — este mapa revela sus lazos.*

## 🗺️ Mapa Visual

```
                        ┌─────────────┐
                        │   ASGARD    │
                        │ (Lilith Core)│
                        └──────┬──────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
               ┌────▼───┐ ┌───▼────┐ ┌───▼──────┐
               │NIFLHEIM│ │SVART-  │ │VANAHEIM  │
               │(Models)│ │ALFHEIM │ │(Bots)    │
               └────┬───┘ │(Docs)  │ └───┬──────┘
                    │     └────┬───┘     │
                    │          │         │
               ┌────▼──────────▼─────────▼──┐
               │                             │
          ┌────▼───┐                  ┌──────▼──┐
          │ALFHEIM │                  │MUSPEL-  │
          │  (UI)  │                  │HEIM(WIP)│
          └────┬───┘                  └────┬────┘
               │                          │
          ┌────▼─────────────┐    ┌────────▼───────┐
          │    MIDGARD       │    │   HELHEIM      │
          │  (Personal Apps) │    │   (Archive)    │
          └────────────────┘    └────────────────┘
               ┌──────────────┐
               │  JOTUNHEIM   │
               │  (Giants)     │
               └──────────────┘
```

## 📊 Matriz de Dependencias

| Desde ↓ / Hacia → | Asgard | Vanaheim | Alfheim | Svartalfheim | Muspelheim | Niflheim | Helheim | Jotunheim | Midgard |
|---------------------|--------|----------|---------|-------------|------------|----------|---------|-----------|---------|
| **Asgard** | — | usa | — | usa | — | usa | — | — | — |
| **Vanaheim** | usa | — | — | contribuye | — | usa | — | — | — |
| **Alfheim** | usa | usa | — | — | — | — | — | — | — |
| **Svartalfheim** | documenta | documenta | documenta | — | documenta | documenta | documenta | documenta | documenta |
| **Muspelheim** | usa | — | — | genera docs | — | — | archiva | — | — |
| **Niflheim** | sirve | sirve | — | — | — | — | — | — | — |
| **Helheim** | — | — | — | — | — | — | — | — | — |
| **Jotunheim** | usa | — | — | genera docs | — | usa | — | — | — |
| **Midgard** | usa | — | usa | — | — | — | — | — | — |

## 🔗 Dependencias Detalladas

### Asgard → Niflheim
- **Tipo**: Runtime dependency
- **Qué**: Modelos LLM para inference local
- **Cómo**: LM Studio carga modelos desde Niflheim/Models/
- **Riesgo**: Si Niflheim no tiene modelos, Asgard no puede funcionar en modo local

### Asgard → Svartalfheim
- **Tipo**: Documentación
- **Qué**: Guías de uso, runbooks, ADRs
- **Cómo**: Asgard consulta docs para操作 procedures
- **Riesgo**: Bajo — docs complementarias, no esenciales para runtime

### Asgard → Vanaheim
- **Tipo**: Herramientas
- **Qué**: Bots externos como tools
- **Cómo**: Orchestrator puede invocar tools de Vanaheim
- **Riesgo**: Medio — algunos features dependen de bots

### Vanaheim → Niflheim
- **Tipo**: Runtime dependency
- **Qué**: Modelos de IA para bots
- **Cómo**: Bots consumen modelos para generar respuestas
- **Riesgo**: Alto — sin modelos, bots son inoperativos

### Alfheim → Asgard
- **Tipo**: API dependency
- **Qué**: Dashboard consume datos del orquestador
- **Cómo**: FastAPI server en Asgard sirve datos al frontend de Alfheim
- **Riesgo**: Alto — sin Asgard, no hay datos que mostrar

### Svartalfheim → Todos
- **Tipo**: Documentación (unidireccional)
- **Qué**: Documenta las APIs, arquitectura y decisiones de todos los reinos
- **Riesgo**: Nulo — solo lectura, no afecta runtime

### Muspelheim → Helheim
- **Tipo**: Flujo de proyecto
- **Qué**: Proyectos que fallan se archivan en Helheim
- **Cómo**: Movimiento manual de directorios
- **Riesgo**: Nulo — es un flujo de decisión, no técnico

## ⚠️ Restricciones

1. **Sin dependencias circulares**: Si A depende de B, B no puede depender de A
2. **Sin binarios en git**: Los modelos LLM se referencian, no se commitean
3. **Sin cross-realm imports Python**: Los reinos se comunican via API, no via imports directos
4. **Svartalfheim es pasivo**: Solo documenta, nunca afecta el runtime de otros reinos
