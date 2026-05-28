# Roles y permisos — Lilith Discord

Los permisos se resuelven por **ID de Discord** y se configuran en `Config/discord_roles.json`. La API y el bot usan el rol para decidir qué puede hacer cada usuario.

**Importante:** Los comandos de gestión (`/lilith trust`, `/lilith trust_id`, etc.) se usan **en el servidor** por el operador. **Chiste** y **meme** están disponibles para **todos** (público y trusted) en el servidor, porque no afectan a tu persona ni a Lilith. **Status** y solicitar **CLI/Cursor** (confirmación al owner) **solo aplican por DM** para usuarios de confianza.

---

## Roles

| Rol       | Quién es |
|-----------|----------|
| **owner** | Ainz (operador). ID en `Config` del bot. |
| **trusted** | Usuarios en la whitelist: `Core/Memory/discord/trusted_users.json`. Se añaden con `/lilith trust` (mención o ID). |
| **public** | Cualquier otro usuario del servidor. |

---

## Qué puede hacer cada rol

### Owner (Ainz)

- **Todo**: orquestador completo (Eva, Adán, Lucifer, Odín, Kimi, Albedo).
- Comandos de agente: `/eva`, `/adan`, `/lucifer`, `/odin`, `/auto`.
- Lectura/escritura de archivos, memoria semántica, confirmaciones peligrosas.
- Gestión de confianza: `/lilith trust`, `/lilith untrust`, `/lilith set_perfil`, `/lilith users`.
- `/status`, `/notif`, `/memory`, `/patrones`, `/file`, etc.

### Trusted (usuarios de confianza)

- **En el servidor (canal público):** **Charla** (mensaje o `/charla`) con trato más amigable y perfil; **chiste** (`/chiste`) y **meme** (`/meme`) — para todos (no afectan a tu persona ni a Lilith). **No** puede usar `/status` ni pedir acciones que requieran confirmación (CLI, Cursor, etc.) en el servidor; eso **solo en DM**.
- **Por DM con Lilith:** Charla, chiste, meme, **status**; si pide algo peligroso (CLI, Cursor), el owner recibe la confirmación por DM.
- **No** puede: acceder a agentes (Eva, Adán, etc.), archivos, memoria privada de Ainz ni comandos admin.

### Public (resto)

- **Charla** (mensaje o `/charla`), **chiste** (`/chiste`) y **meme** (`/meme`) en el servidor — cosas que no afectan directamente a tu persona ni a Lilith. Sin perfil; límite de respuesta más corto.
- **No** puede: `/status`, ni agentes (Eva, Adán, etc.) ni comandos admin.

---

## Resumen por capacidad

| Capacidad | Owner | Trusted (servidor) | Trusted (DM) | Public |
|-----------|:-----:|:------------------:|:------------:|:------:|
| Charla (mensaje o `/charla`) | ✅ | ✅ (trato amigable) | ✅ | ✅ |
| Chiste (`/chiste`) | ✅ | ✅ | ✅ | ✅ |
| Meme (`/meme`) | ✅ | ✅ | ✅ | ✅ |
| `/status` | ✅ | ❌ (solo DM) | ✅ | ❌ |
| Perfil inyectado | — | ✅ | ✅ | ❌ |
| Pedir CLI/Cursor (confirmación owner) | ✅ | ❌ (solo DM) | ✅ | ❌ |
| Agentes (Eva, Adán, etc.) y /auto | ✅ | ❌ | ❌ | ❌ |
| Comandos /lilith trust, set_perfil, etc. | ✅ (en servidor) | ❌ | ❌ | ❌ |

---

## Configuración

- **Permisos por rol**: `Core/Config/discord_roles.json` (listas `owner`, `trusted`, `public` y opcionalmente `_capabilities` como documentación).
- **Lógica de permisos**: `Backend/core/discord_roles_config.py` (`role_can(role, capability)`).
- **Resolución del rol**: por ID en `Discord/auth.py` (owner por config, trusted por `trusted_users.json`, resto public).

Para refinar permisos, edita `discord_roles.json` y reinicia o invalida la caché (`discord_roles_config.invalidate_cache()`).
