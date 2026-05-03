# MISIÓN LILITH 3.9 — FIXES Y REFINAMIENTO

**Estado:** PLANIFICADA.

**Visión:** Fase **exclusivamente** de correcciones y refinamiento. Sin nuevas funcionalidades: solo bugs, pulido, documentación y pequeños ajustes de configuración o UX. Con la base de configuración de la 3.8, la 3.9 deja el sistema estable y listo para el salto a la 4.0.

**Principio:** Si es un *fix* o un *refinamiento* de lo existente → 3.9. Si es una *nueva capacidad* o un cambio de arquitectura → backlog 4.0 o fuera de 3.9.

---

## OBJETIVO

- Corregir fallos detectados en uso (Discord, API, Planner, memoria, confirmaciones, etc.).
- Refinar mensajes, límites, timeouts y valores por defecto en config.
- Alinear documentación con el comportamiento real (README, FIXES_Y_MEJORAS, roles, config).
- Aumentar cobertura o estabilidad de tests donde sea bajo coste.
- Pequeños ajustes de UX (textos, embeds, mensajes de error o de espera) sin añadir flujos nuevos.

---

## ALCANCE 3.9 (sí)

| Área | Ejemplos |
|------|----------|
| **Bugs** | Errores 500, timeouts incorrectos, comandos que no responden, rutas que fallan, edge cases del Planner o de la API. |
| **Config** | Ajustar defaults en `memory.json`, `learning.json`, `planner.json`, `tools.json`; corregir comentarios en JSON. |
| **Documentación** | Actualizar README, FIXES_Y_MEJORAS, ROLES_Y_PERMISOS, Config/README.md para que reflejen el estado actual. |
| **Tests** | Añadir o corregir tests que fallen; cubrir casos límite ya implementados (sin exigir tests para código no tocado). |
| **UX menor** | Mejorar textos de “esperando aprobación”, mensajes de error, etiquetas de prioridad o límites de caracteres mostrados. |
| **Limpieza** | Código muerto, imports no usados, logs demasiado verbosos o incoherentes. |

---

## FUERA DE ALCANCE 3.9 (no)

| Área | Motivo |
|------|--------|
| **Nuevas features** | Nuevas tools, nuevos endpoints, nuevos flujos (ej. “aplicar sugerencia” de intents). → 4.0 o backlog. |
| **Cambios de arquitectura** | DAG, memoria en grafo, nuevo dashboard, nuevos agentes de dominio. → 4.0. |
| **Nuevos JSON o nuevas claves de contrato** | Salvo corrección de valores o documentación de claves ya existentes. |

---

## CRITERIOS DE CIERRE 3.9

- [ ] Lista de fixes aplicados documentada (en FIXES_Y_MEJORAS o en este doc).
- [ ] Documentación de config y roles alineada con el comportamiento actual.
- [ ] Tests existentes en verde; opcionalmente 1–2 tests añadidos para casos críticos corregidos.
- [ ] Sin regresiones conocidas en flujos principales (chat, trust, confirmación, relay, modelo local).

---

## SECUENCIA HACIA 4.0

```
3.8 (config, memoria, aprendizaje, planner, tools)
    → 3.9 (solo fixes y refinamiento)
        → [Opcional] MuninnDB (memoria cognitiva) — ver PRE_4.0_MUNINNDB.md
            → 4.0 (horizonte: DAG, memoria en grafo, dashboard, agentes autónomos)
```

---

## DOCUMENTOS RELACIONADOS

- **[HORIZONTE_LILITH_4.0.md](HORIZONTE_LILITH_4.0.md)** — Visión 4.0 (DAGs, memoria en grafo, dashboard, ecosistema de agentes).
- **[PRE_4.0_MUNINNDB.md](PRE_4.0_MUNINNDB.md)** — Integración opcional de MuninnDB (memoria cognitiva) antes de 4.0.
- **[ROADMAP_HACIA_4.0.md](ROADMAP_HACIA_4.0.md)** — Propuestas por área; 3.8 implementa el corto plazo; 3.9 no añade features.
- **[MISION_LILITH_3.8.md](MISION_LILITH_3.8.md)** — Base de configuración (learning.json, planner.json, tools.json, memory.json ampliado).
- **[FIXES_Y_MEJORAS.md](FIXES_Y_MEJORAS.md)** — Donde registrar los fixes aplicados en 3.9.
