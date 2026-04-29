# 07 - Frontend SPA (React + Vite)

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Frontend/spa/`

---

## 7.1 Tecnologías

| Tecnología | Versión | Uso |
|------------|---------|-----|
| React | 18.2.0 | UI Library |
| Vite | 5.0.8 | Build tool |
| Zustand | 4.4.7 | Estado global |
| Tailwind CSS | 3.3.6 | Estilos |
| Framer Motion | 10.16.16 | Animaciones |
| Monaco Editor | 4.6.0 | Editor código |
| xterm.js | 5.3.0 | Terminal |
| Recharts | 2.15.4 | Gráficos |
| Axios | 1.6.2 | HTTP client |

---

## 7.2 Estructura del Proyecto

```
spa/
├── index.html              # Entry HTML
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx           # Entry React
│   ├── App.jsx            # Componente raíz
│   ├── store/
│   │   └── index.js       # Zustand stores
│   ├── hooks/
│   │   └── useWebSocket.js
│   ├── styles/
│   │   ├── index.css      # Tailwind + estilos
│   │   └── theme.css      # Variables tema
│   └── components/
│       ├── Layout/
│       │   ├── Header.jsx
│       │   ├── RightPanel.jsx
│       │   └── StatusBar.jsx
│       ├── Sidebar/
│       │   ├── Sidebar.jsx
│       │   ├── FileTree.jsx
│       │   ├── SessionList.jsx
│       │   ├── PantheonPanel.jsx
│       │   └── MemoryPanel.jsx
│       ├── Chat/
│       │   ├── ChatPanel.jsx
│       │   ├── MessageContent.jsx
│       │   └── AutoModePanel.jsx
│       ├── IDE/
│       │   └── EditorPanel.jsx
│       ├── Terminal/
│       │   └── TerminalPanel.jsx
│       ├── Dashboard/
│       │   └── DashboardPanel.jsx
│       └── Notifications/
│           ├── NotificationDrawer.jsx
│           └── NotificationToast.jsx
```

---

## 7.3 Sistema de Diseño: Dark Fantasy Tech

### Paleta de Colores

```css
/* Fondos */
--bg-void: #0a0a0f;
--bg-deep: #0f0f1a;
--bg-surface: #13131f;
--bg-elevated: #1a1a2e;
--bg-overlay: #1f1f35;

/* Dorado - Acento */
--gold-bright: #f5c542;
--gold-main: #c9a227;
--gold-dim: #8a6f1a;

/* Carmesí */
--crimson: #8b1a1a;
--crimson-bright: #c0392b;

/* Texto */
--text-primary: #e8e0d0;
--text-secondary: #9a8f7e;
--text-muted: #5a5248;
```

### Tipografía

| Variable | Fuente | Uso |
|----------|--------|-----|
| `--font-display` | Cinzel | Títulos |
| `--font-body` | Crimson Pro | Párrafos |
| `--font-ui` | Rajdhani | UI, botones |
| `--font-mono` | JetBrains Mono | Código |

---

## 7.4 Layout Principal

```
┌─────────────────────────────────────────────────────────────┐
│                        HEADER                               │
├──────────┬──────────────────────────────┬──────────────────┤
│          │                              │                  │
│ SIDEBAR  │      MAIN CONTENT            │  RIGHT PANEL     │
│          │   (Chat / Editor)            │  (Dashboard/     │
│ FileTree │                              │   Tabs)          │
│ Sessions │                              │                  │
│ Pantheon │                              │                  │
│ Memory   │                              │                  │
│          │                              │                  │
├──────────┴──────────────────────────────┴──────────────────┤
│                      TERMINAL PANEL                         │
├─────────────────────────────────────────────────────────────┤
│                      STATUS BAR                             │
└─────────────────────────────────────────────────────────────┘
```

### Sistema de Paneles

Usa `react-resizable-panels`:
- **Left Panel**: 15-35%
- **Center Panel**: Flex
- **Right Panel**: 20-40%
- **Terminal Panel**: 10-60% altura

---

## 7.5 Estado Global (Zustand)

### Stores

```javascript
// 1. useChatStore
- sessions[]
- currentSessionId
- messages[]
- isStreaming
- streamingContent

// 2. useIDEStore
- files[]
- openFiles[]
- activeFileId
- fileContents{}
- selectedProject

// 3. useUIStore
- sidebarVisible
- sidebarView: 'files' | 'sessions'
- terminalVisible
- rightPanelVisible
- rightPanelView: 'tabs' | 'dashboard'
- theme: 'dark'

// 4. useConnectionStore
- isConnected
- sendMessage
- eventListeners

// 5. useNotificationStore
- notifications[]
- unreadCount
- toasts[]
- drawerOpen
```

### Persistencia

```javascript
// Stores con persistencia
useChatStore.persist = localStorage // sessions
useUIStore.persist = localStorage   // layout config
```

---

## 7.6 WebSocket

### Hook useWebSocket

```javascript
const { 
  isConnected, 
  sendMessage, 
  onEvent 
} = useWebSocket('ws://localhost:8000/ws/conversational');
```

### Tipos de Mensajes

| Tipo | Descripción |
|------|-------------|
| `chat_delta` | Chunk de streaming |
| `chat_final` | Fin de respuesta |
| `agent_thinking` | Agente procesando |
| `error` | Error del servidor |
| `session_loaded` | Sesión cargada |
| `token_stats` | Estadísticas de tokens |
| `pantheon_status` | Estado de agentes |
| `memory_stored` | Memoria guardada |
| `notification_new` | Nueva notificación |
| `auto_plan_created` | Plan automático creado |
| `auto_progress` | Progreso tarea automática |
| `auto_complete` | Tarea completada |

---

## 7.7 Componentes Principales

### 7.7.1 ChatPanel

**Features:**
- Input con comandos `/`
- Streaming de respuestas
- Badges de agente delegado
- Scroll automático
- Markdown rendering

**Comandos `/`:**
- `/eva` - Forzar Eva
- `/adan` - Forzar Adán
- `/odin` - Forzar Odín
- `/lilith` - Default
- `/auto` - Modo automático

### 7.7.2 EditorPanel (Monaco)

**Features:**
- Syntax highlighting
- Autocompletado
- Tabs de archivos
- Guardar (Ctrl+S)
- Toolbar: guardar, ejecutar, debug

### 7.7.3 TerminalPanel (xterm.js)

**Features:**
- Tema Dark Fantasy
- Comandos integrados:
  - `help` - Ayuda
  - `clear` - Limpiar
  - `status` - Estado sistema
  - `scan` - Escanear proyecto
- Múltiples tabs

### 7.7.4 DashboardPanel

**Métricas:**
- Tokens consumidos (total + por agente)
- Sesiones totales
- Agentes operativos (X/4)
- Sesiones por día (gráfico barras)
- Memoria: errores, decisiones, sesiones

### 7.7.5 Sidebar Panels

**FileTree:**
- Árbol de archivos
- Navegación
- Abrir en editor

**SessionList:**
- Lista de sesiones
- Cambiar sesión
- Nueva sesión
- Renombrar

**PantheonPanel:**
- Estado de agentes (online/offline)
- Métricas por agente

**MemoryPanel:**
- Memoria semántica
- Memoria episódica
- Memoria procedimental

---

## 7.8 Panteón de Agentes (UI)

### Colores en UI

| Agente | Color | Badge |
|--------|-------|-------|
| Lilith | #C9A227 | 👑 Dorado |
| Eva | #FFD700 | 🟡 Amarillo |
| Adán | #228B22 | 🟢 Verde |
| Lucifer | #DC143C | 🔴 Rojo |

### Indicadores

- **Pulsing dot**: Agente respondiendo
- **Static badge**: Agente que respondió
- **Offline**: Agente no disponible

---

## 7.9 Modo Automático

### AutoModePanel

**Features:**
- Planificación automática
- Subtareas asignadas a agentes
- Progreso en tiempo real
- Pausar/Reanudar

**Estados:**
```
planning → running → paused → done/failed
```

---

## 7.10 Sistema de Notificaciones

### NotificationToast

- Duración: 4 segundos
- Posición: Bottom-right
- Tipos: success, error, warning, info

### NotificationDrawer

- Historial completo
- Badge de no leídas
- Marcar como leída
- Limpiar todas

**Tipos de notificación:**
- `error_recurrente`
- `token_usage`
- `inactivity`
- `memory_insight`

---

## 7.11 Features Avanzados

### Shortcuts de Teclado

| Shortcut | Acción |
|----------|--------|
| `Ctrl+S` | Guardar archivo |
| `Ctrl+W` | Cerrar archivo |
| `Enter` | Enviar mensaje |
| `Shift+Enter` | Nueva línea |

### Animaciones (Framer Motion)

- Transiciones de paneles
- Indicador "pensando"
- Entrada/salida de mensajes
- Hover effects

### Glassmorphism

```css
.glass {
  background: rgba(19, 19, 31, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(197, 162, 39, 0.15);
}
```

---

## 7.12 Integración API

### Endpoints REST

| Endpoint | Uso |
|----------|-----|
| `GET /api/files/tree` | Árbol de archivos |
| `GET /api/files/content` | Contenido archivo |
| `POST /api/files/save` | Guardar archivo |
| `GET /api/memory/*` | Memoria |
| `GET /api/dashboard/stats` | Estadísticas |
| `GET /api/notifications` | Notificaciones |

---

*Documento 07 del índice de documentación de Lilith*
