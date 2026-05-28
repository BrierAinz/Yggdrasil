# 06 - Bots: Discord y Telegram

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Discord/`, `Lilith/Telegram/`

---

## 6.1 Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                    BOTS DE LILITH                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐        ┌─────────────────┐           │
│   │   DISCORD BOT   │        │  TELEGRAM BOT   │           │
│   │   (bot.py)      │        │ (telegram_bot)  │           │
│   │                 │        │                 │           │
│   │ • Multi-rol     │        │ • Solo OWNER    │           │
│   │ • Slash cmds    │        │ • Polling HTTP  │           │
│   │ • WebSocket     │        │ • Inline keys   │           │
│   │ • DMs + Canales │        │ • PC Agent full │           │
│   └────────┬────────┘        └────────┬────────┘           │
│            │                          │                    │
│            └──────────┬───────────────┘                    │
│                       │                                    │
│                       ▼                                    │
│            ┌─────────────────┐                            │
│            │   LILITH API    │                            │
│            │  (FastAPI)      │                            │
│            │                 │                            │
│            │ /api/discord/*  │                            │
│            │ /api/telegram/* │                            │
│            └─────────────────┘                            │
│                       │                                    │
│                       ▼                                    │
│            ┌─────────────────┐                            │
│            │  ORQUESTADOR    │                            │
│            └─────────────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6.2 Discord Bot

### 6.2.1 Estructura

```
Discord/
├── bot.py                 # Punto de entrada
├── auth.py                # Sistema de roles
├── config.py              # Configuración
├── handlers/
│   ├── chat_handler.py    # Procesamiento de mensajes
│   ├── command_handler.py # Comandos slash
│   ├── notification_handler.py
│   └── investiga_handler.py
└── groups/
    ├── admin_commands.py      # /admin
    ├── trusted_commands.py    # /trusted
    └── crystal_commands.py    # /crystal
```

### 6.2.2 Jerarquía de Roles

```python
class UserRole(Enum):
    OWNER = "owner"      # Ainz - control total
    TRUSTED = "trusted"  # Usuarios de confianza
    PUBLIC = "public"    # Usuarios generales
```

**Determinación de rol:**
```python
def get_user_role(user_id):
    if user_id == AINZ_DISCORD_ID:
        return UserRole.OWNER
    elif user_id in trusted_users_list:
        return UserRole.TRUSTED
    else:
        return UserRole.PUBLIC
```

### 6.2.3 Flujo de Mensajes

#### DM (Mensaje Directo)
```
OWNER/TRUSTED: Respuesta completa con acceso a herramientas
PUBLIC: Mensaje fijo redirigiendo al canal #lilith
```

#### Canales de Servidor
```
1. Verificar canal en whitelist
2. Requiere mención @Lilith
3. Procesar según rol del usuario
```

### 6.2.4 Handlers

#### Chat Handler (`chat_handler.py`)

**Funciones:**
- `_call_chat_api()`: POST a `/api/discord/chat`
- `_listen_progress_ws()`: WebSocket para progreso
- `handle_message()`: Procesamiento principal

**Características:**
- Historial: últimos 20 mensajes
- Detección de planes "pesados" → crea hilos
- Sistema de confirmación con botones (✅/❌)
- Embeds con color por agente
- Reacciones aleatorias (💜, ✨, 👍, 💬)

**Colores por agente:**
| Agente | Color |
|--------|-------|
| Lilith/Kimi | #C9A227 (Dorado) |
| Albedo/Odin | #9B59B6 (Púrpura) |
| Eva/Grok | #3498DB (Azul) |
| Adán/Qwen | #2ECC71 (Verde) |
| Lucifer | #C0392B (Rojo) |

#### Command Handler (`command_handler.py`)

**Comandos disponibles:**

| Comando | Nivel | Descripción |
|---------|-------|-------------|
| `/status` | Todos | Dashboard |
| `/notif` | Owner | Notificaciones |
| `/memory` | Owner | Perfil memoria |
| `/charla` | Trusted+ | Chat |
| `/chiste` | Trusted+ | Chiste |
| `/meme` | Trusted+ | Meme |
| `/ayuda` | Todos | Guía |
| `/feedback` | Todos | Valoración 1-5 |
| `/modo` | Owner | Cambiar personalidad |
| `/modo_actual` | Trusted+ | Ver modo |
| `/pendientes` | Owner | Lista pendientes |
| `/pendiente_add` | Trusted+ | Añadir pendiente |
| `/auto_learn` | Owner | Auto-aprendizaje |
| `/cuaderno` | Owner | Cuaderno Lilith |
| `/recado` | Trusted+ | Dejar recado |
| `/recados` | Owner | Ver recados |
| `/responder_recado` | Owner | Responder recado |
| `/audit` | Owner | Auditoría |
| `/patrones` | Owner | Patrones aprendidos |

### 6.2.5 Groups (Comandos Slash Organizados)

#### `/admin` - Admin Commands

**25 subcomandos** (límite Discord). Solo OWNER.

**Agentes:**
| Comando | Agente | Función |
|---------|--------|---------|
| `/admin eva` | Eva | Análisis largo |
| `/admin adan` | Adán | Código |
| `/admin lucifer` | Odín | Creatividad |
| `/admin odin` | Odín | Análisis masivo |
| `/admin auto` | Multi | Modo automático |

**Gestión:**
- `/admin trust @user` - Añadir trusted
- `/admin untrust @user` - Quitar trusted
- `/admin users` - Listar trusted
- `/admin set_perfil` - Configurar perfil

**Sistema:**
- `/admin status` - Estado
- `/admin audit` - Auditoría
- `/admin modo` - Personalidad
- `/admin autolearn` - Auto-aprendizaje
- `/admin investiga` - Investigación web
- `/admin avatar` - Cambiar foto
- `/admin allow_*` - Whitelist canales
- `/admin file_*` - Operaciones archivos

#### `/trusted` - Trusted Commands

Para OWNER y TRUSTED.

| Comando | Descripción |
|---------|-------------|
| `/trusted ayuda` | Lista comandos |
| `/trusted investiga` | Investigación (3/hora) |
| `/trusted codigo` | Análisis código |
| `/trusted modo_actual` | Ver modo |
| `/trusted permisos` | Capacidades |

#### `/crystal` - Crystal Commands

**Comandos públicos** - todos los usuarios.

| Comando | Descripción |
|---------|-------------|
| `/crystal ayuda` | Qué puede hacer |
| `/crystal codigo` | Ayuda programación |
| `/crystal chiste` | Chiste |
| `/crystal meme` | Tono meme |
| `/crystal info` | Info servidor |

### 6.2.6 Auth (`auth.py`)

**Archivos de persistencia:**
```
Core/Memory/discord/
├── trusted_users.json          # IDs de usuarios trusted
├── trusted_audit.json          # Auditoría de cambios
├── trusted_profiles.json       # Perfiles (nombre, relación, notas)
└── profile_reminder_sent.json  # Throttle recordatorios
```

**Funciones:**
- `add_trusted_user()` - Añadir a whitelist
- `remove_trusted_user()` - Quitar
- `set_trusted_profile()` - Configurar perfil
- `try_parse_and_save_profile()` - Auto-parseo

### 6.2.7 Config (`config.py`)

**Variables de entorno:**
```python
DISCORD_TOKEN              # Token bot
AINZ_DISCORD_ID           # ID owner
DISCORD_GUILD_ID          # Servidor
LILITH_HOME_CHANNEL_NAME  # Canal propio
LILITH_HOME_CATEGORY_ID   # Categoría
LILITH_API_URL            # Backend
LILITH_INTERNAL_TOKEN     # Seguridad
ALLOWED_CHANNEL_IDS       # Whitelist canales
LILITH_BOT_ID             # ID bot
LILITH_MAIN_CHANNEL_ID    # Canal principal
```

### 6.2.8 Discord Roles Config (`discord_roles_config.py`)

**Permisos por defecto:**
```python
_DEFAULT = {
    "owner": ["*"],           # Todo permitido
    "trusted": ["limited_chat", "charla", "chiste", "meme", "status"],
    "public": ["charla", "chiste", "meme"]
}
```

**Overrides por usuario:** `Config/trusted_scopes.json`

### 6.2.9 Discord Thread Memory (`discord_thread_memory.py`)

**Almacenamiento:**
```
Data/discord_threads/
├── {channel_id}.json
└── {channel_id}_{thread_id}.json
```

**Formato:**
```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "summary": "Resumen histórico...",
  "summary_updated_at": "2026-03-21T10:30:00Z"
}
```

**Configuración:**
```json
{
  "thread_memory_max_exchanges": 15,
  "thread_memory_max_chars": 2500,
  "thread_memory_rolling_trigger": 30,
  "thread_memory_rolling_keep": 10
}
```

---

## 6.3 Telegram Bot

### 6.3.1 Características

- **Solo OWNER** (verifica `TELEGRAM_OWNER_CHAT_ID`)
- **Sin SDK**: Usa `requests` directo a API HTTP
- **Polling** cada 30 segundos
- **Keyboards inline** para confirmaciones

### 6.3.2 Variables de Entorno

```python
TELEGRAM_BOT_TOKEN        # Token bot
TELEGRAM_OWNER_CHAT_ID    # Chat ID owner
LILITH_API_URL            # Backend
LILITH_INTERNAL_TOKEN     # Token interno
```

### 6.3.3 Comandos

| Comando | Descripción |
|---------|-------------|
| `/start`, `/help`, `/ayuda` | Status y ayuda |
| `/status` | Estado del sistema |
| `/ls <path>` | Listar archivos |
| `/cat <archivo>` | Ver contenido |
| `/exec <comando>` | Ejecutar comando |
| `/eva <tarea>` | Delegar a Eva |
| `/adan <tarea>` | Delegar a Adán |
| `/odin <tarea>` | Delegar a Odín |
| `/investiga <query>` | Investigación web |
| `/auto <objetivo>` | Modo automático |
| `/lock` / `/unlock` | Bloquear/desbloquear PC |
| `/modo <modo>` | Cambiar modo |
| `/memoria` | Qué recuerda |

### 6.3.4 PC Agent en Telegram

**Diferencia clave:** Telegram tiene acceso completo a PC Agent (Discord está deshabilitado por seguridad).

```python
# Ejemplo de uso
/ls proyectos
/cat proyectos/README.md
/exec git status
/pc_exec code .
```

---

## 6.4 Discord API (Backend)

### 6.4.1 Endpoints Principales

#### Chat y Confirmación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/discord/chat` | Chat principal |
| POST | `/api/discord/confirm` | Confirmar acción |
| GET | `/api/discord/pending-for-dm` | Polling confirmaciones |

#### Gestión de Notas (Recados)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/discord/notes/leave` | Dejar recado |
| GET | `/api/discord/notes/pending` | Recados pendientes |
| POST | `/api/discord/notes/mark-delivered` | Marcar entregado |

#### Modos y Personalidad
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/discord/mode` | Obtener modo |
| POST | `/api/discord/mode` | Establecer modo |

#### Stack de Atención
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/discord/attention` | Listar pendientes |
| POST | `/api/discord/attention/add` | Añadir pendiente |
| POST | `/api/discord/attention/complete` | Completar |

### 6.4.2 Sistema de Confirmación

```python
_PENDING_CONFIRMATIONS = {}

class _PendingConfirmation:
    token: str
    owner_user_id: str
    created_at: float
    message: str
    system_prompt: str
    steps: List[Dict]
    summary: str
    requested_by_user_id: str
    requested_by_display_name: str
    dm_sent: bool
```

**TTL:** 5 minutos (`_CONFIRM_TTL_SECONDS = 300`)

---

## 6.5 Niveles de Acceso Detallados

### Configuración

- **Permisos por rol:** `Core/Config/discord_roles.json`
- **Lógica de permisos:** `Backend/core/discord_roles_config.py`
- **Resolución del rol:** `Discord/auth.py`

### Capacidades por Rol

| Capacidad | Owner | Trusted (servidor) | Trusted (DM) | Public |
|-----------|:-----:|:------------------:|:------------:|:------:|
| **Charla** (mensaje o `/charla`) | ✅ | ✅ (trato amigable) | ✅ | ✅ |
| **Chiste** (`/chiste`) | ✅ | ✅ | ✅ | ✅ |
| **Meme** (`/meme`) | ✅ | ✅ | ✅ | ✅ |
| **Status** (`/status`) | ✅ | ❌ | ✅ | ❌ |
| **Perfil inyectado** | — | ✅ | ✅ | ❌ |
| **CLI/Cursor** (con confirmación owner) | ✅ | ❌ | ✅ | ❌ |
| **Agentes** (Eva, Adán, etc.) | ✅ | ❌ | ❌ | ❌ |
| **Comandos /admin** | ✅ | ❌ | ❌ | ❌ |
| **Gestión de usuarios** | ✅ | ❌ | ❌ | ❌ |

### Qué Puede Hacer Cada Rol

#### Owner (Ainz)
- **Todo**: orquestador completo (Eva, Adán, Lucifer, Odín, Kimi, Albedo)
- Comandos de agente: `/eva`, `/adan`, `/lucifer`, `/odin`, `/auto`
- Lectura/escritura de archivos, memoria semántica, confirmaciones peligrosas
- Gestión de confianza: `/lilith trust`, `/lilith untrust`, `/lilith set_perfil`, `/lilith users`
- `/status`, `/notif`, `/memory`, `/patrones`, `/file`, etc.

#### Trusted (usuarios de confianza)
- **En servidor:** Charla, chiste, meme (no afectan a tu persona ni a Lilith)
- **Por DM:** Charla, chiste, meme, status
- Si pide algo peligroso (CLI, Cursor), el owner recibe confirmación por DM
- **No puede:** acceder a agentes (Eva, Adán, etc.), archivos, memoria privada de Ainz ni comandos admin

#### Public (resto)
- Charla (`/charla`), chiste (`/chiste`), meme (`/meme`) en el servidor
- Sin perfil; límite de respuesta más corto
- **No puede:** `/status`, agentes (Eva, Adán, etc.) ni comandos admin

---

## 6.6 Niveles de Acceso Rápidos

| Función | OWNER | TRUSTED | PUBLIC |
|---------|-------|---------|--------|
| Chat completo | ✅ | ⚠️ | ❌ |
| /admin | ✅ | ❌ | ❌ |
| /trusted | ✅ | ✅ | ❌ |
| /crystal | ✅ | ✅ | ✅ |
| Archivos proyecto | ✅ | ❌ | ❌ |
| PC Agent (Discord) | ⚠️ | ❌ | ❌ |
| PC Agent (Telegram) | ✅ | ❌ | ❌ |
| Investigación web | ✅ | ⚠️ | ❌ |
| Cambiar modo | ✅ | ❌ | ❌ |
| Gestionar trusted | ✅ | ❌ | ❌ |

---

*Documento 06 del índice de documentación de Lilith*
