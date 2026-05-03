# Muninn: `vault_tokens`, configuración y arranque de la API

Guía rápida para usar **varias claves `mk_`** (una por vault físico en Muninn) y para **levantar la API** de Lilith.

---

## ¿Puedo abrir la API ya?

**Sí.** La API no depende de que Muninn esté encendido para arrancar:

- Si **`muninn.json` → `enabled`: `false`**, el código no llama a Muninn (memoria cognitiva desactivada; el resto funciona).
- Si **`enabled`: `true`**, necesitas:
  1. **Servidor Muninn** accesible en la URL de `muninn.json` (por defecto `http://127.0.0.1:8475`).
  2. **Tokens correctos**: cada petición a un vault físico usa el token que corresponde a ese vault (ver abajo). Si Muninn no responde o el token no coincide con el vault, verás 401/403 en logs; la API puede seguir en marcha.

---

## Arranque de la API

Desde el director **`Lilith/Core/`** (donde están `Backend/` y `Config/`):

```bash
python -m Backend.api.server
```

- **Puerto**: por defecto **8000**. Se puede cambiar con variables de entorno `LILITH_API_PORT` o `PORT`.
- **Host**: en `start_server` por defecto escucha en `0.0.0.0` (accesible en la red local según firewall).

Al iniciar, el *lifespan* llama a `MuninnMemory(...).ensure_vaults()`. Si Muninn no expone `POST /vaults` (p. ej. HTTP 405), es normal: los vaults se crean desde la UI/consola de Muninn.

Variables `.env` opcionales (también se cargan rutas como `Core/Config/secrets.env` desde `server.py`): ver `Backend/README.md`.

---

## ¿Por qué `vault_tokens`?

En Muninn, una API key `mk_` queda ligada a **un** vault. Si todas las rutas lógicas apuntan a un vault pero envías el token de otro, obtienes **401** al activar/escribir en un vault no autorizado para esa clave.

**Solución en Lilith:** mapeo **nombre de vault físico** → **token** en `Config/muninn.json`:

```json
"vault_tokens": {
  "default": "mk_xxxxxxxx",
  "lilith": "mk_yyyyyyyy"
}
```

El código (`Backend/core/muninn_memory.py`) resuelve el vault físico con `vault_map` + `muninn_vaults`, elige el token y usa un cliente HTTP con la cabecera `Authorization` adecuada **por token** (caché por clave).

---

## Claves en `muninn.json` (resumen)

| Clave | Rol |
|--------|-----|
| `enabled` | Activa/desactiva llamadas a Muninn. |
| `url` | Base del servidor Muninn (REST bajo `.../api`). |
| `muninn_token` / `token` / `api_key` | **Token por defecto**: se usa cuando el vault físico **no** tiene entrada en `vault_tokens`. |
| `vault_tokens` | Objeto: **vault físico** → **mk_** de ese vault. |
| `vault_map` | Vaults lógicos legacy (`facts`, `episodes`, `projects`) → nombre físico en Muninn. |
| `muninn_vaults` | Agente o clave lógica (`lilith`, `odin`, …) → vault físico. |
| `proactive_multi_vault` | Si `true`, la proactividad consulta varios vaults (cada uno con su token si está en `vault_tokens`). |

Los nombres en `vault_tokens` deben coincidir con los **nombres de vault en Muninn** tras el mapeo (p. ej. `default`, `lilith`). La búsqueda de clave es **case-insensitive**.

---

## Seguridad

- No subas `muninn.json` con claves reales a repositorios públicos.
- Preferible: `vault_tokens` vacío en el repo y valores solo en **variables de entorno** o `secrets.env` (si en el futuro se añade lectura desde env por vault).
- Si una clave se filtró (chat, issue, log), **rótala** en Muninn.

---

## Referencias

- `Core/Backend/README.md` — `python -m Backend.api.server`.
- `Core/Config/README.md` — Lista de archivos de configuración.
- `Core/Docs/MISION_MUNINNDB_POTENCIAL_COMPLETO.md` — Funciones Muninn (vaults por agente, Why, proactividad, etc.).
