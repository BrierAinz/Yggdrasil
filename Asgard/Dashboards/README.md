# 🏛️ Asgard Command Center

Dashboard de telemetría web para el ecosistema Yggdrasil.

## Características

- 🌳 **Mapa de Yggdrasil**: Estado de los 9 reinos en tiempo real
- 🏛️ **Panteón Control**: Métricas y control de agentes
- 🧠 **Estadísticas de Memoria**: Semantic, Episodic, MuninnDB
- 🔥 **Auto-Mode Tasks**: Tareas autónomas activas
- 📜 **Logs en Vivo**: Streaming de logs via WebSocket

## Inicio Rápido

### Opción 1: Script (Recomendado)

```bash
./Asgard/Dashboards/start_dashboard.bat
```

### Opción 2: Manual

```bash
cd Asgard/Dashboards/web
npm install
npm run dev
```

Abrir http://localhost:3000

## Requisitos

- Node.js 18+
- Lilith corriendo en :8000 (para APIs)

## Estructura

```
Dashboards/
├── web/                    # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── YggdrasilMap.tsx
│   │   │   ├── PantheonControl.tsx
│   │   │   ├── MemoryStats.tsx
│   │   │   ├── AutoModeTasks.tsx
│   │   │   └── LiveLogs.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── start_dashboard.bat     # Script de arranque
└── README.md
```

## APIs

El dashboard consume:

- `GET /api/asgard/ecosystem/status` - Estado de Yggdrasil
- `GET /api/asgard/pantheon/status` - Estado del Panteón
- `GET /api/asgard/memory/stats` - Estadísticas de memoria
- `GET /api/asgard/automode/tasks` - Tareas Auto-Mode
- `WS /api/asgard/ws/logs` - Logs en tiempo real

## Desarrollo

```bash
# Instalar dependencias
npm install

# Servidor de desarrollo
npm run dev

# Build para producción
npm run build
```

---

🏛️ *Centro de Mando - Ojos en todo Yggdrasil*
