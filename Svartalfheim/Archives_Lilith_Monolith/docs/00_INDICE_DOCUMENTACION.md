# Índice de Documentación - Lilith

**Proyecto:** Lilith - Sistema Multi-Agente Inteligente
**Última actualización:** 2026-03-26
**Versión actual:** v5.0

---

## 📚 Documentación por Categoría

### 🔧 Misiones Completadas (Recientes)

| Documento | Descripción | Fecha | Estado |
|-----------|-------------|-------|--------|
| [MISION_DISCORD_REDIRECT_MESSAGE.md](MISION_DISCORD_REDIRECT_MESSAGE.md) | Mejora UX para PC operations bloqueadas en Discord | 2026-03-26 | ✅ Completada |
| [MISION_PLANNER_AUTOBATCH.md](MISION_PLANNER_AUTOBATCH.md) | Auto-batching de operaciones PC en planner | 2026-03-24 | ✅ Completada |
| [MISION_PC_AGENT_TELEGRAM_E2E.md](MISION_PC_AGENT_TELEGRAM_E2E.md) | PC Agent End-to-End para Telegram | 2026-03-24 | ✅ 97% Completada |

### 📖 Documentación Técnica Core

| Documento | Descripción | Versión |
|-----------|-------------|---------|
| [01_ARQUITECTURA_SISTEMA.md](01_ARQUITECTURA_SISTEMA.md) | Arquitectura general del sistema | v5.0 |
| [02_MOTIVOS_DELEGACION.md](02_MOTIVOS_DELEGACION.md) | Sistema de motivos de delegación | v4.2 |
| [03_SISTEMA_METACOGNICION.md](03_SISTEMA_METACOGNICION.md) | Metacognición y confirmaciones | v4.2 |
| [04_SISTEMA_TOOLS_V3.md](04_SISTEMA_TOOLS_V3.md) | Sistema de Tools V3 | v4.2 |
| [05_ORQUESTACION_DAG.md](05_ORQUESTACION_DAG.md) | Orquestación basada en DAG | v4.2 |
| [06_INTEGRACION_MEMORIA.md](06_INTEGRACION_MEMORIA.md) | Integración con sistema de memoria | v4.2 |
| [07_FRONTEND_SPA.md](07_FRONTEND_SPA.md) | Frontend SPA con React | v4.2 |
| [08_SISTEMA_PLUGINS.md](08_SISTEMA_PLUGINS.md) | Sistema de plugins | v4.2 |
| [09_VAULTS_SEGURIDAD.md](09_VAULTS_SEGURIDAD.md) | Sistema de vaults y seguridad | v4.2 |

### 🚀 Roadmap y Planificación

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [ROADMAP_v5.0.md](ROADMAP_v5.0.md) | Roadmap hacia versión 5.0 | 🔄 En progreso |
| [ESTADO_ACTUAL_LILITH.md](ESTADO_ACTUAL_LILITH.md) | Estado actual del proyecto | 🔄 Actualizado |
| [CHANGELOG.md](../CHANGELOG.md) | Historial de cambios | 🔄 Actualizado |

### 🔐 Seguridad y Auditoría

| Documento | Descripción | Versión |
|-----------|-------------|---------|
| [SECURITY_AUDIT.md](SECURITY_AUDIT.md) | Auditoría de seguridad | v4.2 |
| [DEFENSA_INYECCION_PROMPTS.md](Legacy/DEFENSA_INYECCION_PROMPTS.md) | Defensa contra inyección de prompts | v4.0 |
| [AUDITORIA_DECISIONES.md](AUDITORIA_DECISIONES.md) | Sistema de auditoría de decisiones | v4.2 |

### 🤖 Agentes Especializados

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [AGENT_EVA.md](AGENT_EVA.md) | Agente Eva - Minería web | ✅ Documentado |
| [AGENT_ADAN.md](AGENT_ADAN.md) | Agente Adán - Análisis de código | ✅ Documentado |
| [AGENT_ALBEDO.md](AGENT_ALBEDO.md) | Agente Albedo - Generación código | ✅ Documentado |
| [AGENT_CRYSTAL.md](AGENT_CRYSTAL.md) | Agente Crystal - Discord público | ✅ Documentado |
| [AGENT_ODIN.md](AGENT_ODIN.md) | Agente Odín - Búsqueda local | ✅ Documentado |

### 📱 Integraciones

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [INTEGRACION_TELEGRAM.md](INTEGRACION_TELEGRAM.md) | Integración con Telegram | ✅ Completada |
| [INTEGRACION_DISCORD.md](INTEGRACION_DISCORD.md) | Integración con Discord | ✅ Completada |
| [INTEGRACION_KIMI.md](INTEGRACION_KIMI.md) | Integración con Kimi API | ✅ Completada |

### 🧪 Testing

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [TEST_SUITE_PC_AGENT_E2E.md](TEST_SUITE_PC_AGENT_E2E.md) | Suite de tests E2E para PC Agent | 📝 Creada |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Guía de testing | ✅ Documentada |

### 📁 Legacy / Histórico

La carpeta `Legacy/` contiene documentación de versiones anteriores:

- Misiones v2.x, v3.x, v4.0, v4.1
- Diseños arquitectónicos previos
- Decisiones técnicas históricas

---

## 🗂️ Estructura de Documentación

```
docs/
├── 00_INDICE_DOCUMENTACION.md      ← Este archivo
├── ESTADO_ACTUAL_LILITH.md         ← Estado del proyecto
├── MISION_*.md                      ← Documentación de misiones
├── 01_*.md - 09_*.md               ← Documentación técnica core
├── AGENT_*.md                       ← Documentación de agentes
├── INTEGRACION_*.md                ← Documentación de integraciones
├── ROADMAP_v5.0.md                 ← Roadmap actual
├── SECURITY_AUDIT.md               ← Auditoría de seguridad
├── TEST_SUITE_*.md                 │
├── CHANGELOG.md                     ← Historial de cambios (raíz)
└── Legacy/                          ← Documentación histórica
    ├── MISION_LILITH_V2.3.md
    ├── MISION_LILITH_3.0_COMPLETO.md
    ├── MISION_LILITH_4.0.md
    └── ...
```

---

## 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Versión actual | v5.0 |
| Completitud PC Agent Telegram E2E | 97% |
| Tests unitarios | ~140 |
| Líneas de código backend | ~12,000 |
| Líneas de código frontend | ~4,700 |
| APIs REST | 65+ |
| Componentes React | 15 |
| Agentes especializados | 6 |

---

## 🔄 Convenciones

### Nomenclatura de Archivos

- `MISION_<nombre>.md` - Documentación de una misión específica
- `AGENT_<nombre>.md` - Documentación de un agente
- `INTEGRACION_<nombre>.md` - Documentación de integración externa
- `0X_<nombre>.md` - Documentación técnica core numerada
- `ROADMAP_vX.Y.md` - Roadmap por versión

### Estados

- ✅ Completada / Documentada
- 🔄 En progreso / Actualizado
- ⏳ Pendiente
- 📝 Creada / Borrador
- ❌ Obsoleto (en Legacy/)

---

**Mantenido por:** Ainz & Claude
**Última actualización:** 2026-03-26
