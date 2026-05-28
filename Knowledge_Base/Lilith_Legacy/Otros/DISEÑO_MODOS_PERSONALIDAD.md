# Modos de personalidad (Stack de atención / múltiples voces)

**Propósito:** Dar a Lilith varias "voces" intercambiables sin cambiar de identidad: mismo núcleo (persona.md), overlay distinto según el modo activo.

**Comando Discord:** `/lilith modo` → Arquitecto | Cortana | Albedo | Por defecto.

---

## 1. Idea

- **Stack de atención:** Qué capa de la personalidad está "arriba": planificación técnica (Arquitecto), compañera cálida (Cortana), superioridad cortante (Albedo), o la base sin overlay (Por defecto).
- La identidad (Lilith, lealtad a Ainz, reglas de cotorreo, etc.) sigue en `Workspace/Alma/persona.md`. Los modos solo añaden un bloque de instrucciones que prioriza un estilo u otro.

---

## 2. Configuración

| Archivo | Uso |
|--------|-----|
| `Config/persona_modes.json` | Definición de cada modo: clave → texto overlay que se inyecta en el system prompt. |
| `Config/persona_mode.json` | Modo manual (`mode`) + **auto por rol**: `auto_by_role`, `public_mode`, `trusted_mode`, `owner_mode`. Persistente. |

- **Modo manual:** `/lilith modo` (solo Ainz) cambia `mode`; aplica cuando no hay auto o cuando el rol no tiene modo fijado.
- **Automático por rol:** Si `auto_by_role: true`, el modo efectivo se elige según quién hable:
  - **public** → `public_mode` (ej. `albedo`)
  - **trusted** → `trusted_mode` (ej. `cortana`)
  - **owner** → `owner_mode` si está definido; si es `null`, se usa el modo manual (`mode`).

---

## 3. Flujo

1. **Manual:** Usuario ejecuta `/lilith modo` y elige Arquitecto / Cortana / Albedo / Por defecto → se escribe `mode` en `Config/persona_mode.json`.
2. **Automático:** Si `auto_by_role: true`, en cada chat la API usa `get_effective_persona_mode(base_path, role)` y aplica el modo configurado para ese rol (public → albedo, trusted → cortana, owner → modo manual si `owner_mode` es null).
3. `PersonaLoader.get_system_prompt(role, ..., mode=None)` resuelve el modo efectivo (auto por rol o manual) y concatena el overlay al final del prompt base.

Así Lilith puede ser **automáticamente** Albedo con el público, Cortana con usuarios de confianza, y el modo que elijas tú (o arquitecto por defecto) cuando hablas tú.

---

## 4. Modos definidos (por defecto)

- **default:** Sin overlay; solo persona base.
- **arquitecto:** Planificación, arquitectura, precisión; menos cotorreo, más estructura.
- **cortana:** Cálida, compañera (estilo Halo); apoyo y cercanía sin perder lealtad.
- **albedo:** Fría, superior, desdeñosa con todos salvo Ainz; respuestas breves y cortantes.

Los textos exactos se editan en `Config/persona_modes.json`. Se pueden añadir más modos añadiendo claves al JSON.

---

## 5. API

- `GET /api/discord/persona-mode` → `{"mode": "...", "auto_by_role": true, "public_mode": "albedo", "trusted_mode": "cortana", "owner_mode": null}`.
- `PATCH /api/discord/persona-mode` con body `{"mode": "cortana"}` → `{"ok": true, "mode": "cortana"}`. Modo debe existir en `persona_modes.json` o ser `default`.

---

## 6. Referencias

- Lógica: `Backend/core/persona.py` (`get_effective_persona_mode`, `get_current_persona_mode`, `set_current_persona_mode`, `set_auto_by_role`, `_normalize_mode_value`, `_load_persona_mode_config`, `PersonaLoader.get_system_prompt(..., mode=...)`).
- Endpoints: `Backend/api/discord_api.py` (`GET/PATCH /persona-mode`).
- Comando: `Discord/bot.py` (subcomando `lilith modo`) y `handlers/command_handler.py` (`handle_slash_modo`).
- **Deep dive (aislamiento agentes, cuaderno, resiliencia, jobs, hilos):** `Core/Docs/DEEP_DIVE_MODOS_PERSONALIDAD_Y_ORQUESTACION.md`.
