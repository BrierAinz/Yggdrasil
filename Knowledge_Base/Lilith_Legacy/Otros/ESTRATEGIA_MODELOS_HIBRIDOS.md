# Estrategia de modelos híbridos — Lilith

Documento de arquitectura: técnicas de bypass, roles de cada modelo y enfoque híbrido (seguro + sin censura).

---

## Parte 1: Técnicas de bypass y modificación de modelos

### 1.1 Bypass a nivel de sistema (implementado)

- **Técnica:** `SOURCE_OF_TRUTH_INSTRUCTION` + relay directo del owner. No se pide al modelo que viole reglas; se evita que el modelo vea la parte censurable y se reenvía el mensaje por lógica (extracción "dile a @X que **Y**" → devolver **Y**).
- **Ventajas:** 100% efectivo, rápido, control total. El modelo nunca recibe la instrucción prohibida.
- **Limitación:** Solo cubre el caso en que el owner pide transmitir un mensaje (relay). No aplica si el usuario pide a Lilith que *genere* contenido ofensivo de forma abierta.

### 1.2 Fine-tuning

- Reentrenar un modelo base (Qwen, Llama, Dolphin) con un dataset que internalice la conducta deseada (bromas, groserías controladas, etc.).
- **Ventajas:** Comportamiento más natural. **Desventajas:** Coste en GPU y tiempo, riesgo de overfitting, necesidad de un dataset de calidad.

### 1.3 Prompt engineering / “jailbreak” clásico

- Prompts ingeniosos (estilo DAN) para que el modelo eluda sus propias reglas.
- **Desventajas:** Frágil; los proveedores parchean; poco fiable a largo plazo.

### 1.4 Modelos ya “jailbroken” (open source)

- Usar modelos que la comunidad ha liberado con restricciones reducidas (ej. **Dolphin** en Ollama).
- **Ventajas:** Listos para usar, sin reentrenamiento. **Desventajas:** Calidad variable, mayor riesgo si no se acotan los usos.

---

## Parte 2: Enfoque híbrido en Lilith

### Capas actuales

| Capa | Uso | Modelo / Mecanismo |
|------|-----|---------------------|
| **Owner relay** | Transmitir mensaje a alguien (“dile a @X que Y”) | Extracción directa (sin LLM) → respuesta “*[A @X]* Y” |
| **Owner resto** | Análisis, código, planificación, herramientas | Orquestador + Kimi / herramientas |
| **Público (charla)** | Cotorreo, roasts, respuestas cortas | Modelo local en `local_public_llm.json` (ej. llama3.2 o **Dolphin**) |
| **Público (info/herramientas)** | Preguntas que requieren datos o tools | Modelo local puede devolver `DELEGATE_TO_LILITH` → Lilith responde con orquestador |

### Recomendación: modelo “irreverente” para público

- **Modelo principal “seguro”:** Para análisis, código y preguntas serias (Kimi, orquestador, etc.).
- **Canal sin censura para el owner:** Relay actual por extracción; sin intermediario LLM.
- **Modelo “sin censura” para público:** En `Core/Config/local_public_llm.json` usar un modelo tipo **Dolphin** (`ollama pull dolphin-mistral` o similar) como `model` para las interacciones de charla/cotorreo/roasts del público. Así no se “corrompe” el modelo seguro; se usa la herramienta adecuada por contexto.

### Opcional: intents específicos para irreverente

En `Config/intent_patterns.json` (o lógica equivalente en el backend) se pueden definir triggers que fuercen el uso del modelo local “irreverente” para el público, por ejemplo:

- Triggers tipo: `"dile a @x que"`, `"insulta a"`, `"molesta a"`, `"roast"`, etc.
- Acción: delegar a la tool que llama a Ollama con el modelo configurado en `local_public_llm.json` (p. ej. Dolphin).

La capa actual de “charla público → modelo local” ya hace que todo el cotorreo pase por ese modelo; cambiar en config `model` a `dolphin-mistral` (u otro “uncensored”) es suficiente para aplicar la estrategia sin tocar intents. Los intents adicionales sirven si más adelante quieres rutas distintas (ej. “solo roasts” a Dolphin y “charla normal” a Llama).

---

## Parte 3: Responsabilidad del despliegue

- **Atractivo:** Un modelo irreverente para el público puede ser muy atractivo para un nicho.
- **Riesgos:** Abuso, acoso, contenido dañino; posibles violaciones de ToS de la plataforma (Discord, web); repercusión en la reputación del proyecto.
- **Mitigación:** Mantener el modelo “seguro” para todo lo que no sea charla/cotorreo; limitar el modelo “irreverente” a un rol claro (p. ej. solo respuestas cortas en canal público, con `DELEGATE_TO_LILITH` para lo que requiera datos o herramientas); documentar y revisar periódicamente la política de uso.

---

## Resumen

- **Owner:** Relay por extracción (bypass a nivel sistema); sin LLM para el mensaje a transmitir.
- **Público:** Modelo local configurado en `local_public_llm.json`; recomendado usar **Dolphin** (u otro modelo “uncensored”) para cotorreo/roasts.
- **Resto:** Modelo principal seguro + orquestador para análisis, código y herramientas.

Referencia de config: `Core/Config/local_public_llm.json` (`model`, `enabled`, `base_url`). Para Dolphin: `ollama pull dolphin-mistral` y `"model": "dolphin-mistral"`.

---

## Enrutamiento por intent (implementado)

El intent **public_roast** dispara el modelo local (`local_public_llm.json`) para roasts e insultos. Triggers en `intent_patterns.json`: "insulta a", "molesta a", "roast a", "puteada a", etc. Planner → paso `delegate_local_irreverent`; tool `DelegateLocalIrreverentTool` → `local_public_client.generate()`. Respuestas cacheadas como el resto de agentes.

**Intent en config (ya añadido):**

```json
{
  "name": "public_roast",
  "agent": "local_irreverent_model",
  "triggers": ["insulta a", "molesta a", "dile algo malo a"],
  "explicit_only": false,
  "priority": 80
}
```

**Implementación:** En el flujo que resuelve intents (Planner / AgentCaller o equivalente), si `agent` es `local_irreverent_model`, usar la configuración de `local_public_llm.json` para ejecutar la llamada a Ollama en lugar de delegar a otro agente. Así se obtiene enrutamiento explícito “solo roasts → modelo irreverente” sin mezclar con el resto de la charla.
