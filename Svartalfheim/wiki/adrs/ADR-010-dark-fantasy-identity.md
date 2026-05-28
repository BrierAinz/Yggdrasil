---
adr_id: ADR-010
title: Dark Fantasy Aesthetic como Identity
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🌑 ADR-010: Dark Fantasy Aesthetic como Identity

## Context

El ecosistema Yggdrasil no es solo código — es un sistema con personalidad. Los nombres de reinos, variables, comentarios y documentación forman parte de la identidad del proyecto. Sin una directiva estética consistente, el resultado es un sandbox de nombres sin coherencia.

## Decision

Adoptar **Dark Fantasy Norse Mythology** como estética unificada del ecosistema:

1. **Nomenclatura de reinos**: Los 9 reinos nórdicos como namespaces
2. **Nombres de código**: Referencias mitológicas en variables y docstrings
   - Circuit Breaker states: CLOSED/MIDGARD, OPEN/MUSPELHEIM, HALF_OPEN/NIFLHEIM
   - Norns como hilo de consolidación de memoria
   - Runas como metáforas (Raido = camino restaurado, Isa = hielo/fallo)
3. **Docstrings poéticos**: Comentarios con sabor dark fantasy
4. **Markdown con estética**: Emojis rúnicos, headers con símbolos, colores
5. **Svartalfheim como archivo vivo**: Toda doc sigue esta estética

Ejemplos en código:
```python
# resistance.py docstring:
"""Las Norns tejen los hilos del destino — cuando un provider cae,
el circuito se abre como las puertas de Asgard ante el caos."""
```

```python
# session_store.py docstring:
"""En las profundidades del Well of Souls, cada sesión es un eco
que persiste más allá de su conclusión."""
```

## Consequences

### Positivas
- **Identidad**: El proyecto tiene personalidad y es memorable
- **Consistencia**: Nombres y metáforas siguen un patrón coherente
- **Onboarding**: La mitología es un framework conceptual para entender el sistema
- **Motivación**: Es más divertido trabajar en "Asgard" que en "core"

### Negativas
- **Curva de aprendizaje**: Los recién llegados deben aprender la nomenclatura
- **Overhead**: Pensar en metáforas Norse consume tiempo de desarrollo
- **Riesgo de afectación**: Si se exagera, puede parecer pretencioso
- **Documentación dual**: Se necesita glosario para mapear términos mitológicos a técnicos
