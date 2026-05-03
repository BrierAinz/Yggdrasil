# Guía de Web UI - Lilith Dashboard

**Versión:** 4.1  
**Fecha:** 2026-03-21

---

## Introducción

El Dashboard Web de Lilith proporciona una interfaz visual completa para gestionar todos los aspectos del sistema sin necesidad de usar comandos de texto.

## Stack Tecnológico

- **Framework:** React 18 + Vite
- **Estilos:** Tailwind CSS
- **Estado:** Zustand
- **Routing:** React Router DOM
- **HTTP:** Axios
- **Fechas:** date-fns

---

## Páginas

### 1. Dashboard Principal

**Ruta:** `/`

Muestra un resumen del sistema con:
- Cards de estadísticas (hechos, tasks, confirmaciones, uptime)
- Actividad reciente
- Accesos rápidos

### 2. Chat

**Ruta:** `/chat`

Interface de chat conversacional con Lilith:
- Historial de mensajes
- Envío de mensajes
- Indicadores de typing
- Soporte markdown

### 3. Memoria

**Ruta:** `/memory`

Gestión de la memoria de Lilith:

#### Hechos Semánticos
- Tabla con todos los hechos almacenados
- Búsqueda semántica
- Filtros por categoría
- Ordenamiento
- Eliminación de hechos

#### Timeline Episódica
- Visualización cronológica
- Filtros por agente/herramienta
- Indicadores de éxito/fallo
- Detalles expandibles

### 4. Tasks

**Ruta:** `/tasks`

Gestión de tareas programadas:

#### Scheduled Tasks
- Lista de tasks con estado
- Pause/Resume
- Ejecución manual
- Editor de tasks (cron)

#### Source Monitors
- Lista de URLs monitoreadas
- Estado de cada monitor
- Intervalos de chequeo
- Añadir/eliminar monitores

### 5. Confirmaciones

**Ruta:** `/confirmations`

Gestión de acciones pendientes:

#### Pendientes
- Lista de planes esperando aprobación
- Nivel de riesgo (color-coded)
- Preview de steps
- Botones Approve/Deny

#### Historial
- Decisiones pasadas
- Filtros por fecha/decisión

### 6. Configuración

**Ruta:** `/settings`

Configuración del sistema:

#### Memoria
- Peso de hechos recientes (slider)
- Prioridad de thread memory
- Toggles de memoria semántica/episódica

#### Planner
- Umbral de confianza
- Usar planes aprendidos
- Usar clasificador local

#### Notificaciones
- Webhook de Discord
- Notificaciones de Telegram
- Email

---

## Autenticación

El dashboard requiere autenticación con token de owner:

1. Al iniciar, se muestra pantalla de login
2. Ingresar `LILITH_INTERNAL_TOKEN`
3. El token se valida contra la API
4. Se genera JWT para sesión (24h)

---

## Desarrollo

### Instalación

```bash
cd Lilith/Core/Frontend/spa
npm install
```

### Development server

```bash
npm run dev
```

Accede a `http://localhost:3000`

### Build para producción

```bash
npm run build
```

### Variables de entorno

```bash
# .env
VITE_API_URL=http://localhost:8000
```

---

## Componentes

### Layout

```jsx
<Sidebar />     // Navegación lateral
<Header />      // Barra superior
<StatusBar />   // Barra de estado inferior
```

### Páginas

```jsx
<MemoryPage />         // Gestión de memoria
<TasksPage />          // Tasks y monitores
<ConfirmationsPage />  // Confirmaciones pendientes
<SettingsPage />       // Configuración
```

### UI Components

- `SemanticFactsTable` - Tabla de hechos
- `EpisodicTimeline` - Timeline visual
- `TaskEditor` - Modal de edición
- `ConfirmationCard` - Card de confirmación

---

## API Endpoints Usados

| Endpoint | Uso |
|----------|-----|
| `GET /api/memory/semantic` | Listar hechos |
| `GET /api/memory/episodic` | Listar episodios |
| `GET /api/memory/search` | Búsqueda semántica |
| `GET /api/tasks` | Listar tasks |
| `GET /api/monitors` | Listar monitores |
| `GET /api/confirmations/pending` | Confirmaciones pendientes |
| `POST /api/config` | Guardar configuración |

---

## Tests

```bash
# Tests unitarios
npm test

# Tests e2e (Playwright)
npm run test:e2e
```

---

## Screenshots

### Dashboard
```
+------------------------------------------+
|  Dashboard          [Stats Cards]        |
|                                        |
|  [Memory: 156]  [Tasks: 8]  [Pending: 2] |
|                                        |
|  Recent Activity                       |
|  - Backup completed                    |
|  - Task executed                       |
+------------------------------------------+
```

### Memory Page
```
+------------------------------------------+
|  Memory > Semantic Facts                 |
|                                        |
|  [Search...] [Category ▼] [Sort ▼]     |
|                                        |
|  Timestamp | Category | Content | ...  |
|  21/03 10:30 | Pref | Python... | [🗑️] |
+------------------------------------------+
```

---

## Troubleshooting

### "Cannot connect to API"
Verificar que `VITE_API_URL` apunte al servidor correcto.

### "Authentication failed"
Verificar que `LILITH_INTERNAL_TOKEN` sea válido.

### "Blank page after build"
Revisar errores en consola del navegador.
