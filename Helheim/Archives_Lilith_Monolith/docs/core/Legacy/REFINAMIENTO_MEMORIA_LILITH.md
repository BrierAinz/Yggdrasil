# Refinamiento y mejora de la memoria de Lilith

Documento de referencia: arquitectura actual de memoria y vías para mejorarla o refinarla.

---

## 1. Arquitectura actual (Lilith 3.0)

### Tri-capa en `Backend/core/memory/`

| Capa | Ubicación | Rol |
|------|-----------|-----|
| **Semántica** | `core/memory/semantic/` + delegación a `Backend/memory/semantic_memory.py` | Contexto largo plazo: perfil de Ainz, proyectos, preferencias. El Planner la consulta para enriquecer el contexto. |
| **Episódica** | `core/memory/episodic/` | Logs de interacciones (mensaje, plan ejecutado, respuesta, outcome). Base para el LearningEngine y `self_improve`. |
| **Procedimental** | `core/memory/procedural/` | Patrones aprendidos (planes reutilizables). El Planner prioriza planes aprendidos cuando el LearningEngine devuelve uno. |

### Flujo actual

- **Planner**: llama a `memory_manager.search_semantic(message)` y opcionalmente `learning_engine.get_plan_for_message(message)` (que usa episódica + procedimental).
- **Orchestrator**: tras ejecutar el plan, llama a `memory_manager.store_episodic(...)`.
- **SemanticStore (core)**: hoy delega en `SemanticMemory.get_context_for_prompt()` (un bloque de texto); no hay búsqueda vectorial por similitud.

---

## 2. ¿Se puede mejorar o refinar? Sí

### 2.1 Memoria semántica

**Estado**: Un único bloque de contexto (perfil/proyectos) inyectado en el prompt. No hay búsqueda por similitud ni por tiempo.

**Mejoras posibles**:

1. **Búsqueda vectorial (embeddings)**  
   - Guardar fragmentos de perfil, decisiones y resúmenes con embeddings.  
   - Ante cada mensaje, recuperar los K fragmentos más similares en lugar de todo el contexto.  
   - Reduce ruido y permite escalar a mucho más texto sin llenar el contexto del LLM.

2. **Actualización automática**  
   - Tras interacciones relevantes (p. ej. “guarda que prefiero X”), extraer hechos y escribirlos en la memoria semántica (o en un JSON/JSONL de “hechos”) para que `get_context_for_prompt()` los incluya.

3. **Separar “perfil fijo” y “hechos recientes”**  
   - Perfil: datos estables (nombre, proyectos, rol).  
   - Hechos: preferencias, decisiones, recordatorios. Así se puede limitar o rotar lo reciente sin tocar el perfil.

### 2.2 Memoria episódica

**Estado**: Se guarda cada interacción (mensaje, plan, respuesta, outcome). El LearningEngine la usa para sugerir patrones.

**Mejoras posibles**:

1. **Resúmenes por sesión o por tema**  
   - Periódicamente (o al cerrar “sesión”) generar un resumen y guardarlo en semántica o en un store de “resúmenes”, para no depender solo de logs crudos.

2. **Filtrado por outcome**  
   - Solo usar episodios con `outcome == "success"` (o con alta valoración) para aprender patrones, y opcionalmente marcar episodios “importantes” a mano o con heurísticas.

3. **Límite de retención**  
   - Política de retención (p. ej. últimos N episodios o por fecha) para no crecer sin límite y para que el LearningEngine trabaje sobre ventanas recientes.

### 2.3 Memoria procedimental

**Estado**: Almacena patrones (plan sugerido para un tipo de mensaje). El Planner los usa antes de reglas fijas.

**Mejoras posibles**:

1. **Refuerzo/actualización**  
   - Cuando un plan aprendido lleva a éxito, reforzar ese patrón (prioridad, peso o última vez usado). Cuando falla, no reforzar o bajar prioridad.

2. **Vencimiento o validez**  
   - Asociar “válido hasta” o “usado hace X días” para deprecar patrones que ya no aplican.

3. **Agrupación por intención**  
   - Etiquetar patrones por intención (p. ej. “editar_archivo”, “analizar_codigo”) para que el Planner elija por intención + similitud de mensaje.

### 2.4 Integración Planner + memoria

- **Clasificador de intención local**: Ya existe; se puede entrenar con más datos y usar su salida para elegir entre patrones procedimentales y reglas.
- **Ponderar fuentes**: Combinar “plan aprendido” + “reglas” + “clasificador” con pesos o prioridades configurables para refinar cuándo confiar en cada uno.

---

## 3. Resumen: qué tocar para refinar

| Objetivo | Dónde | Esfuerzo |
|----------|--------|----------|
| Búsqueda semántica por similitud | `SemanticStore` + embeddings (nuevo o integrado) | Alto |
| Hechos/recordatorios automáticos | Módulo de extracción + escritura en semántica o JSON | Medio |
| Resúmenes de sesión | Pipeline post-episódico + store de resúmenes | Medio |
| Reforzar/deprecar patrones procedimentales | `ProceduralStore` + lógica en LearningEngine | Bajo–medio |
| Política de retención episódica | `EpisodicStore` (límite por cantidad o fecha) | Bajo |

La base actual (tri-capa, MemoryManager, Planner, LearningEngine) permite ir aplicando estas mejoras de forma incremental sin reescribir todo el sistema.
