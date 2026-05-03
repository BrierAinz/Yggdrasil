# 09 - Yggdrasil: Los 9 Reinos

> **Versión:** 4.2.2  
> **Fecha:** 2026-03-21  
> **Ubicación:** `D:\Proyectos\Yggdrasil`

---

## 9.1 Visión General

**Yggdrasil** (el Árbol del Mundo) es el ecosistema de proyectos organizado en **nueve reinos**. Cada reino tiene un **propósito específico y concreto** basado en el flujo de trabajo real.

**Nota importante:** Lilith reside en `D:\Proyectos\Yggdrasil\Asgard\Lilith` — orquestador central del ecosistema, dentro de su reino correspondiente.

```
                    ┌─────────┐
                    │  ASGARD │  ← Centro de Mando
                    │   (1)   │    Dashboards, Control
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
   │ ALFHEIM │     │ MIDGARD │     │SVARTALF-│
   │   (2)   │     │   (3)   │     │ HEIM (4)│
   │  Labora-│     │Productos│     │Bibliote-│
   │ torio   │     │Personales      │ ca     │
   │ Visual  │     │         │     │Técnica  │
   └─────────┘     └─────────┘     └────┬────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
               ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
               │JOTUNHEIM│        │VANAHEIM │        │MUSPEL-  │
               │   (6)   │        │   (5)   │        │ HEIM (7)│
               │Gigantes │        │ Vivero  │        │ Fuego   │
               │Proyectos│        │    de   │        │Desarrollo
               │Masivos  │        │    IA   │        │Activo   │
               └─────────┘        └─────────┘        └─────────┘

                    ┌─────────┐
                    │NIFLHEIM │  ← Niebla
                    │   (8)   │    Banco de Recursos
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │ HELHEIM │  ← Más Allá
                    │   (9)   │    Cripta de Proyectos
                    └─────────┘
```

---

## 9.2 Los 9 Reinos - Propósitos Definidos

### 9.2.1 🏛️ Asgard - Centro de Mando

**Propósito:** Orquestador central del ecosistema (Lilith Core)
**Estado:** ✅ ACTIVO - Lilith migrada
**README:** ✅ Creado

```
Asgard/
├── README.md
├── Lilith/             # ← MIGRADO desde D:/Proyectos/Lilith
│   ├── Core/           #   Backend API, Panteón, Memoria, Tools
│   ├── Discord/        #   Bot de Discord
│   ├── Telegram/       #   Bot de Telegram
│   └── VSCode/         #   Extensión VS Code
├── Dashboards/         # Paneles de control del ecosistema
├── Scripts/            # Scripts de gestión cross-reino
└── Config/             # Configuración central de Asgard
```

**Reglas:**
- Lilith como orquestador central del ecosistema
- Dashboards de monitoreo y control
- Scripts de gestión transversal

---

### 9.2.2 🎨 Alfheim - Laboratorio Visual

**Propósito:** Prototipos de UI, experimentos frontend, diseño visual  
**Estado:** Vacío (estructura preparada)  
**README:** ✅ Creado

```
Alfheim/
├── README.md
├── Prototypes/         # Prototipos de UI
├── Themes/             # Esquemas de color
└── Experiments/        # Pruebas visuales
```

**Reglas:**
- Todo es experimental
- Iteración rápida: probar, fallar, iterar
- Documentar decisiones de diseño

---

### 9.2.3 🌍 Midgard - Productos Personales

**Propósito:** Aplicaciones y herramientas para uso personal  
**Estado:** Vacío (proyectos migrarán aquí)  
**README:** ✅ Creado

```
Midgard/
├── README.md
├── Piano/              # Auto-player de piano
├── Portafolio/         # Gestión de arte
├── Productivity/       # Herramientas personales
└── Automation/         # Automatizaciones
```

**Reglas:**
- Solo proyectos personales (no para terceros)
- Debe funcionar para mí, no necesita ser perfecto
- Sin presión comercial

**Proyectos previstos:**
- Piano Autoplayer (Python + AutoHotkey)
- Portafolio de Arte (gestión de ilustraciones)

---

### 9.2.4 📚 Svartalfheim - Biblioteca Técnica

**Propósito:** Documentación, playbooks, grimorios de conocimiento  
**Estado:** Vacío (conocimiento migrará aquí)  
**README:** ✅ Creado

```
Svartalfheim/
├── README.md
├── Playbooks/          # Procedimientos paso a paso
├── Grimorios/          # Conocimiento profundo
├── Archivos_Historicos/# Documentación histórica
└── Knowledge_Base/     # Base searchable
```

**Reglas:**
- Conocimiento persistente: lo que aprendes, se documenta
- Estructurado y searchable
- Lilith puede indexar esto para RAG

---

### 9.2.5 🌿 Vanaheim - Vivero de IA

**Propósito:** Agentes auxiliares, experimentos LLM, fine-tuning  
**Estado:** Vacío (Albedo y experimentos migrarán aquí)  
**README:** ✅ Creado

```
Vanaheim/
├── README.md
├── Albedo/             # Agente auxiliar personal
├── LLM_Experiments/    # Experimentos con modelos
├── Agents/             # Agentes especializados
└── Training/           # Datasets y training
```

**Reglas:**
- Experimentación controlada: prueba primero, escala después
- Aislado de producción
- Memoria de experimentos (qué funcionó y qué no)

---

### 9.2.6 🏔️ Jotunheim - Proyectos Masivos

**Propósito:** Sistemas grandes, monolitos complejos, largo alcance  
**Estado:** Vacío (Story Engine y otros gigantes)  
**README:** ✅ Creado

```
Jotunheim/
├── README.md
├── StoryEngine/        # Motor de juego post-apocalíptico
├── LargeSystems/       # Otros sistemas grandes
└── Archives/           # Versiones anteriores
```

**Reglas:**
- Solo proyectos de escala (>1 mes, múltiples componentes)
- Documentación obligatoria
- Versionado estricto

**Proyecto previsto:**
- Story Engine (motor de juego post-apocalíptico, doc 20)

---

### 9.2.7 🔥 Muspelheim - Desarrollo Activo

**Propósito:** Proyectos en desarrollo intenso, código candente, WIP  
**Estado:** Vacío (listo para sprints)  
**README:** ✅ Creado

```
Muspelheim/
├── README.md
├── Active/             # Proyectos actualmente en desarrollo
├── Hotfixes/           # Parches urgentes
└── Burnout/            # Código descartado del calor
```

**Reglas:**
- Todo es temporal: se mueve o se muere
- Sprint mode: cambios rápidos, commits frecuentes
- Migración obligatoria al terminar sprint

**Ciclo de Vida:**
```
Idea → Muspelheim (desarrollo) → [Midgard|Jotunheim|...] (destino)
                            ↓
                        Helheim (si falla)
```

---

### 9.2.8 🌫️ Niflheim - Banco de Recursos

**Propósito:** Assets, datasets, templates, dotfiles, configuraciones  
**Estado:** Vacío (recursos migrarán aquí)  
**README:** ✅ Creado

```
Niflheim/
├── README.md
├── Assets/             # Recursos visuales
├── Datasets/           # Datos para ML
├── Templates/          # Plantillas reutilizables
├── Configs/            # Configuraciones de herramientas
└── Dotfiles/           # Configuraciones personales
```

**Reglas:**
- Recursos compartidos entre reinos
- Organizado por tipo
- Sin código ejecutable (solo datos/configs/assets)

---

### 9.2.9 ⚰️ Helheim - Cripta de Proyectos

**Propósito:** Proyectos abandonados, versiones antiguas, código muerto  
**Estado:** Vacío (listo para archivar)  
**README:** ✅ Creado

```
Helheim/
├── README.md
├── Abandoned/          # Proyectos abandonados
├── Deprecated/         # Versiones viejas
├── Obsolete/           # Código que ya no funciona
└── Graveyard.md        # Índice de lo que murió y por qué
```

**Reglas:**
- Read-only: no se desarrolla, solo se archiva
- Documentar el porqué (epitafio para cada proyecto)
- Resucitación posible como fork nuevo

**Ritual de Entrada:**
1. Último commit: "[ARCHIVADO] Razón: X"
2. Mover a Helheim/
3. Actualizar Graveyard.md

---

## 9.3 Mapa de Decisiones

```
¿Qué estoy haciendo?
│
├─→ Monitorear o controlar el ecosistema → ASGARD
│
├─→ Prototipar UI o experimentar diseño → ALFHEIM
│
├─→ Desarrollar algo para mi uso personal → MIDGARD
│
├─→ Documentar conocimiento o procedimientos → SVARTALFHEIM
│
├─→ Experimentar con IA/agentes/LLMs → VANAHEIM
│
├─→ Proyecto grande (>1 mes, complejo) → JOTUNHEIM
│
├─→ Sprint intenso, código cambiando rápido → MUSPELHEIM
│
├─→ Almacenar assets, configs, templates → NIFLHEIM
│
└─→ Archivar proyecto muerto o versión vieja → HELHEIM
```

---

## 9.4 Relación con Lilith

```
┌─────────────────────────────────────────┐
│              YGGDRASIL                  │
│          D:\Proyectos\Yggdrasil         │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  ASGARD - Centro de Mando        │  │
│  │                                   │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  LILITH                     │  │  │
│  │  │  D:\...\Asgard\Lilith       │  │  │
│  │  │  - Orquestador central      │  │  │
│  │  │  - Core del sistema         │  │  │
│  │  │  - Documentación            │  │  │
│  │  └─────────────────────────────┘  │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ← Lilith orquesta todos los reinos →  │
│                                         │
│  ┌─────────┐ ← Lilith gestiona estado  │
│  │ ASGARD  │    Dashboards/Monitoreo   │
│  └────┬────┘                           │
│       │                                 │
│       └→ Conoce y gestiona otros reinos │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ALFHEIM  │ │MIDGARD  │ │SVARTALF-│   │
│  │Labora-  │ │Productos│ │  HEIM   │   │
│  │torio    │ │Personales│ │Bibliote-│   │
│  │Visual   │ │         │ │   ca    │   │
│  └─────────┘ └─────────┘ └─────────┘   │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │VANAHEIM │ │JOTUNHEIM│ │MUSPEL-  │   │
│  │ Vivero  │ │Gigantes │ │  HEIM   │   │
│  │   de    │ │Proyectos│ │  Fuego  │   │
│  │   IA    │ │Masivos  │ │ Activo  │   │
│  └─────────┘ └─────────┘ └─────────┘   │
│                                         │
│  ┌─────────┐ ┌─────────┐               │
│  │NIFLHEIM │ │ HELHEIM │               │
│  │  Niebla │ │ Más Allá│               │
│  │ Recursos│ │ Cripta  │               │
│  └─────────┘ └─────────┘               │
└─────────────────────────────────────────┘
```

---

## 9.5 Checklist de Activación

Para cada reino, antes de usarlo:

- [x] **Asgard**: Lilith migrada ✅ — pendiente: crear primer dashboard básico
- [ ] **Alfheim**: Configurar entorno de prototipado
- [ ] **Midgard**: Migrar Piano y Portafolio
- [ ] **Svartalfheim**: Migrar grimorios de conocimiento
- [ ] **Vanaheim**: Migrar/montar Albedo
- [ ] **Jotunheim**: Iniciar Story Engine
- [ ] **Muspelheim**: Definir workflow de sprint
- [ ] **Niflheim**: Migrar assets y templates
- [ ] **Helheim**: Crear Graveyard.md

---

## 9.6 Convenciones de Nomenclatura

### Proyectos en reinos:
- `NombreProyecto/` - Directorio del proyecto
- `README.md` - Descripción y propósito
- `docs/` - Documentación específica
- `archive/` - Versiones viejas del mismo proyecto

### Documentación:
- `README.md` - Obligatorio en cada reino
- `DECISIONS.md` - Decisiones arquitectónicas importantes
- `TODO.md` - Tareas pendientes del reino

---

*Documento 09 del índice de documentación de Lilith*  
*Yggdrasil: Los 9 Reinos definidos y listos para activación*
