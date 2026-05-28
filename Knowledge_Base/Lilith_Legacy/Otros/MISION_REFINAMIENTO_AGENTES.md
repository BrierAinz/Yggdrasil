# Misión: Refinamiento del Ecosistema de Agentes

**Fecha**: 2026-03-19
**Estado**: ✅ COMPLETADO (las 6 mejoras implementadas)

---

## Mejora 1 — AgentMetrics ✅

**Objetivo**: Visibilidad en tiempo real del rendimiento de cada tool/agente.

**Implementado**:
- `Core/Backend/core/agent_metrics.py`:
  - `ToolStats` — dataclass: total_calls, success_rate, avg_latency_ms, p95_latency_ms, etc.
  - `AgentMetrics` — singleton en RAM; thread-safe (GIL CPython)
  - `record_call(tool, latency_ms, success, error_msg, cache_hit)`
  - `get_stats(tool=None)` — un tool o todos
  - `health_summary()` — herramientas con success_rate < 70% o p95 > 10s
- `agent_caller.py` instrumentado en todos los paths de ejecución (cache hit, AgentRegistry, registry, exceptions)
- `Core/Backend/api/agents_api.py`:
  - `GET /api/agents/health` — resumen de salud
  - `GET /api/agents/stats` — todas las stats
  - `GET /api/agents/stats/{tool_name}` — stats de un tool específico

---

## Mejora 2 — PromptTemplate ✅

**Objetivo**: Estandarizar la composición de prompts de sistema.

**Implementado**:
- `Core/Backend/core/agents/prompt_template.py`:
  - `AgentPromptConfig` — dict de secciones nombradas + separador
  - Secciones: `identity`, `rules`, `capabilities`, `format`, `memory`, `extra`
  - `build(memory_block, extra_context)` — construye el string final, inyectando memoria y contexto
  - `add_section / override_section / remove_section`
  - `make_prompt(agent_name)` — fábrica vacía
  - `from_string(agent_name, prompt)` — compatibilidad con prompts monolíticos

*Los agentes existentes aún usan strings monolíticos; la migración gradual es tarea futura.*

---

## Mejora 3 — FallbackChain ✅

**Objetivo**: Cambio automático de agente cuando el primario falla.

**Implementado**:
- `Core/Config/agents.json`:
  - `fallback_chains`: `{delegate_odin: [eva, lucifer], delegate_eva: [lucifer], ...}`
  - `fallback_strategy`: `"ordered"`
  - `max_fallback_attempts`: `3`
  - `fallback_error_patterns`: `["offline", "timeout", "rate limit", "503", ...]`
- `Core/Backend/core/agents/fallback_chain.py`:
  - `should_fallback(tool, error_msg)` — decide si activar cadena
  - `next_after(original_tool, error_msg, tried)` — siguiente candidato
  - `get_chain(tool)` — lista completa de alternativas
  - `reset(tool=None)` — limpia contadores
- `agent_caller.py` — tras error en `registry.execute()`, itera cadena hasta encontrar respuesta válida

---

## Mejora 4 — ComplexityRouter para Adán ✅

**Objetivo**: Adán solo recibe tareas acordes a sus capacidades; las complejas van a Eva.

**Implementado**:
- `Core/Backend/core/agents/complexity_router.py`:
  - `classify_complexity(task, context)` → `"simple" | "medium" | "complex"`
  - Heurística: regex de complejidad (arquitectura, migración, full-stack...) + simpleza (función, snippet...) + longitud de tokens
  - `route_code_task(task, context)` → `"delegate_adan"` o `"delegate_eva"`
- `agent_caller.py` — si `tool_name == "delegate_adan"` y tarea compleja → `"delegate_eva"`
- Thresholds: `_LONG_TASK_TOKENS = 300`, escalado a `complex` con 2+ señales de complejidad

---

## Mejora 5 — OutputValidator ✅

**Objetivo**: Detectar respuestas de baja calidad antes de retornarlas.

**Implementado**:
- `Core/Backend/core/agents/output_validator.py`:
  - `ValidationResult(valid, issues, score, suggestion)` — dataclass
  - `OutputValidator.validate(text, tool_name, task)` — heurística pura (sin LLM)
  - Detecta: empty, too_short, failure_pattern, unresolved_placeholder, truncated, no_code_in_code_task
  - `score`: 0.0 (inútil) → 1.0 (perfecta); `suggestion`: "retry" / "escalate" / "accept"
- `agent_caller.py` — valida tras ejecución exitosa; loggea warning si score < 0.5; registra en metrics como `tool:quality_warn`

---

## Mejora 6 — ReviewChain (inter-agente) ✅

**Objetivo**: Albedo revisa respuestas de otros agentes y añade notas de calidad si son bajas.

**Implementado**:
- `Core/Backend/core/agents/review_chain.py`:
  - `ReviewChain(base_path, min_score=6, enabled=True)`
  - `review_sync(tool, task, response)` → llama `AlbedoAgent.sentinel_review_sync()`
  - `annotate_if_low_quality(tool, task, response)` → añade nota al final si score < min_score
  - Solo activa para `delegate_adan`, `delegate_eva`, `delegate_odin`
  - Longitud mínima para activar: 300 chars (evita overhead en snippets cortos)
- `agent_caller.py` — llama `annotate_if_low_quality()` para tools revisables antes de devolver resultado
