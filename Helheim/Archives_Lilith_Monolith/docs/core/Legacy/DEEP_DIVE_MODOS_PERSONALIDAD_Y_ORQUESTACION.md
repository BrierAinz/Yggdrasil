# Deep Dive: Modos de personalidad y orquestación 4.0

**Objetivo:** Evaluar cómo interactúan los modos de personalidad con el resto del ecosistema (agentes, auto-aprendizaje, resiliencia, jobs en background, hilos compartidos) y documentar decisiones de diseño.

---

## 1. Aislamiento de agentes especializados (Adán / Eva vs. Lucifer)

**Pregunta:** Si el modo activo es "Albedo", ¿el overlay se inyecta también en los prompts de Adán y Eva cuando el Planner delega refactor o análisis?

**Respuesta:** **No.** Los modos de personalidad afectan **solo al nodo conversacional** que usa `PersonaLoader.get_system_prompt()`.

- **PersonaLoader** se usa únicamente en la API de Discord para construir el system prompt de las rutas de **chat** (owner, trusted, public). Ese prompt se pasa a `generate_reply` → Lucifer (Kimi) como *contexto de usuario* o a la tool GenerateReplyTool, que a su vez llama a Lucifer con ese contexto. El overlay (Albedo, Cortana, etc.) va **solo ahí**.
- **Eva** y **Adán** tienen identidad fija:
  - `EvaAgent.get_system_prompt()` y `AdanAgent.get_system_prompt()` devuelven textos estáticos (Eva: analista, HALLAZGO/EVIDENCIA/RECOMENDACIÓN; Adán: código puro, sin preámbulos).
  - El `context` que reciben en `execute(task, context)` es **contexto de tarea** (salidas de pasos previos, scratchpad, memoria semántica), no el system prompt de Lilith ni el modo de personalidad.
- El **PlanExecutor** al construir `params["context"]` para `delegate_eva` / `delegate_adan` usa `_build_context_from_steps`, scratchpad, etc.; en ningún sitio se llama a `PersonaLoader` ni se lee `persona_mode.json` para esos agentes.

**Conclusión:** Los agentes técnicos (Adán, Eva) mantienen una identidad aséptica y enfocada; la personalidad dinámica (modos) queda confinada al flujo conversacional (Lucifer como voz de Lilith).

---

## 2. Influencia en el cuaderno de auto-aprendizaje

**Pregunta:** En la Fase 2 del clasificador (refino con LLM), ¿el agente evaluador carga el modo de personalidad activo?

**Respuesta:** **No.** El job de auto-aprendizaje usa un prompt **estricto y desconectado** de la personalidad de Discord.

- En `Backend/core/auto_learn/classifier.py`, la fase LLM hace:
  ```python
  lucifer.execute(prompt, context="")
  ```
  con un `prompt` fijo del tipo: *"¿Este contenido es importante para el proyecto o el amo (sí/no)? Responde solo: important: true o important: false."*
- **LuciferAgent** usa siempre su propio `get_system_prompt()` (identidad Lucifer: creativo, rebelde, reglas de formato). No se invoca `PersonaLoader` ni se lee `persona_mode.json` en ese flujo.
- Por tanto, el modo "Arquitecto" o "Albedo" **no** condiciona la clasificación: el criterio es el prompt de clasificación + la identidad fija de Lucifer, no la voz de Lilith en Discord.

**Conclusión:** La clasificación de importancia para el cuaderno es independiente del modo de personalidad; no hay riesgo de que Albedo descarte artículos que Arquitecto consideraría vitales en ese pipeline.

---

## 3. Resiliencia ante fallos de estado (persona_mode.json)

**Pregunta:** Si el JSON se corrompe (sintaxis) o se guarda `"mode": "albed"` (typo), ¿hay fallback seguro o puede romperse la orquestación?

**Comportamiento actual (y refuerzos):**

- **`_load_persona_mode_config`:** Si el archivo no existe o hay excepción al parsear (JSON inválido), devuelve `{"mode": "default", "auto_by_role": False}`. No propaga la excepción.
- **`get_persona_mode_overlay(base_path, mode)`:**  
  - Si `mode` es `None` o vacío → se trata como `"default"` → overlay `""`.  
  - Si `mode` es un typo (ej. `"albed"`) → no está en `persona_modes.json` → `modes.get("albed")` es `None` → se devuelve `""`.  
  - No se lanza excepción; el orchestrator recibe un overlay vacío y el prompt sigue siendo válido.
- **Valores no string en el JSON** (ej. `"mode": 1`): Antes podía provocar `AttributeError` al hacer `.strip()` sobre un entero. Se ha añadido **`_normalize_mode_value(val)`**, que convierte cualquier valor a string y normaliza a `"default"` si queda vacío, de modo que `get_current_persona_mode`, `get_effective_persona_mode` y `get_persona_mode_overlay` sean seguros ante tipos raros o typos.

**Conclusión:** Con el fallback de `_load_persona_mode_config` y la normalización vía `_normalize_mode_value` + búsqueda en `persona_modes`, no se lanzan excepciones que rompan la respuesta en Discord; en el peor caso se usa overlay vacío (equivalente a modo por defecto).

---

## 4. Rol de los procesos de fondo (background jobs)

**Pregunta:** Cuando el job de auto-aprendizaje despierta a Lucifer para clasificar RSS, ¿qué `role` se pasa a `get_effective_persona_mode`? ¿Deberían los jobs del sistema operar siempre en modo aséptico?

**Respuesta:** El job **no** usa `get_effective_persona_mode` ni `PersonaLoader`. No se pasa ningún rol.

- El clasificador invoca directamente `LuciferAgent().execute(prompt, context="")`. Lucifer usa su system prompt fijo; no hay carga de `persona_mode.json` ni de rol de Discord.
- Por tanto, los jobs del sistema **ya operan en modo aséptico** en lo que respecta a la personalidad de Lilith: la decisión de "importante sí/no" no depende del modo Arquitecto/Albedo/Cortana.

**Recomendación:** Mantener este desacoplamiento. Si en el futuro algún job necesitara explícitamente "modo default" (por ejemplo, un job que genere texto hacia el usuario), conviene que ese job invoque con un rol fijo (ej. `role="owner"`) y que en config exista la opción de que los jobs ignoren el modo (p. ej. `jobs_use_persona_mode: false`), o que se documente que los jobs no usan PersonaLoader.

---

## 5. Esquizofrenia de contexto en hilos compartidos

**Pregunta:** En un mismo hilo, un usuario Trusted recibe respuesta en modo Cortana y luego el Owner corrige y recibe respuesta en modo Arquitecto. El historial mezcla estilos. ¿Puede ser un problema?

**Análisis:**

- Cada petición construye un **nuevo** system prompt con el **rol actual** del autor del mensaje → `get_effective_persona_mode(base_path, role)` → overlay del modo correspondiente (Cortana para trusted, Arquitecto para owner).
- La **memoria de hilo** se inyecta como bloque de historial (mensajes anteriores) dentro del prompt. El modelo ve: [system con overlay del modo actual] + [historial con respuestas en distintos estilos].
- Los LLMs suelen dar peso alto a las instrucciones del system y al turno más reciente; aun así, el estilo de mensajes previos puede influir y suavizar el cambio de tono (p. ej. algo de Cortana puede “colar” en la respuesta en modo Arquitecto).

**Conclusión:** En la práctica el overlay suele ser suficiente para marcar el tono del turno actual, pero puede haber **deriva leve** en hilos muy largos o con muchos cambios de interlocutor. Opciones de mitigación si se observan problemas:

- Reforzar en el system prompt una línea del tipo: *"En este turno responde con el estilo del modo activo; el tono de mensajes previos del hilo no debe condicionar tu voz actual."*
- O incluir en el bloque de historial una etiqueta por mensaje indicando el modo con el que se generó (solo para consumo del modelo), de modo que pueda distinguir cambios de voz.

---

## 6. Resumen de vectores

| Vector | Comportamiento actual | Riesgo |
|--------|------------------------|--------|
| **Adán/Eva** | No reciben overlay; usan system prompt propio. | Ninguno. |
| **Cuaderno / clasificador** | Lucifer con prompt fijo de clasificación; sin PersonaLoader. | Ninguno. |
| **persona_mode.json corrupto/typo** | Fallback a config por defecto; overlay vacío si modo desconocido; `_normalize_mode_value` evita errores por tipo. | Bajo. |
| **Jobs en background** | No usan rol ni modo; operan asépticos. | Ninguno. |
| **Hilos compartidos** | Modo por petición según rol; historial mezcla estilos; overlay define el turno actual. | Deriva leve posible; mitigable con refuerzo en system prompt. |

---

## 7. Referencias de código

- **PersonaLoader / modos:** `Backend/core/persona.py` (`get_system_prompt`, `get_effective_persona_mode`, `get_persona_mode_overlay`, `_normalize_mode_value`, `_load_persona_mode_config`).
- **Uso de PersonaLoader:** Solo en `Backend/api/discord_api.py` (rutas de chat).
- **Eva/Adán system prompt:** `Backend/core/agents/eva_agent.py`, `adan_agent.py` (`get_system_prompt()`); contexto de tarea en `Backend/core/plan_executor.py` (`_build_step_params`).
- **Clasificador auto-learn:** `Backend/core/auto_learn/classifier.py` (`lucifer.execute(prompt, context="")`).
- **Lucifer identidad fija:** `Backend/core/agents/lucifer_agent.py` (`get_system_prompt()`).
