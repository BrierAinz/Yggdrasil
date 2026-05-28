# 20 - Story Engine V2

> **Versión:** 1.0  
> **Fecha:** 2026-03-21  
> **Clasificación:** Proyecto Histórico - Motor de Juego  
> **Origen:** Ultralegacy/03_Archives_Proyectos_Historicos/StoryEngine_Fase1/

---

## 20.1 Visión del Juego

### ¿Qué es Story Engine?

**Story Engine V2** es un **simulador de supervivencia post-apocalíptica no lineal** con capacidad de diferentes temáticas de apocalipsis y flexibilidad NSFW.

> **Estado del Proyecto:** 🔄 En definición (Diseño completo, implementación pendiente)

### Características Clave

| Feature | Descripción |
|---------|-------------|
| **No lineal** | Cada partida es diferente |
| **Multi-temática** | El apocalipsis se define al inicio |
| **Contenido adulto configurable** | Flexibilidad NSFW según preferencia |
| **Sistema de NPCs complejo** | Reclutamiento, captura, relaciones |
| **Economía de recursos** | Energía, alimento, tiempo |

---

## 20.2 Temáticas de Apocalipsis

### Motor Agnóstico a Temática

El motor es **agnóstico a la temática**. Se define al crear partida mediante:
- **Seed** (reproducibilidad opcional)
- **Configuración** (parámetros de mundo)
- **Prompts** (contexto para el LLM)

### Tipos de Apocalipsis Soportados

| Código | Temática | Estética |
|--------|----------|----------|
| `NUCLEAR` | Radiación / Fallout | Desiertos, mutantes, bunkers |
| `ZOMBIE` | Infectados | Ciudades muertas, hordas |
| `PLAGUE` | Pandemia | Cuarentenas, supervivientes escasos |
| `AI_REBEL` | Máquinas rebeldes | Drones, ciudades automatizadas |
| `FROZEN` | Era de hielo | Nieve, escasez de calor |
| `FLOOD` | Inundación | Islas, botes, ciudades sumergidas |
| `CYBER` | Cyberpunk colapsado | Neón roto, corpos caídas |

---

## 20.3 Identidad del Jugador

### El Sobreviviente

**Quién es:** Sobreviviente solitario que puede reclutar o capturar NPCs.

### Sistema de NPCs

#### Reclutamiento

| Tipo | Descripción |
|------|-------------|
| **Reclutamiento voluntario** | NPCs que se unen por amistad/utilidad |
| **Captura forzada** | Sistema de esclavos (NSFW) |
| **Relaciones complejas** | Múltiples ejes de relación |

#### Ejes de Relación NPC

| Eje | Descripción | Rango |
|-----|-------------|-------|
| `agrado` | Qué tan bien le caes | -100 a +100 |
| `sumisión` | Qué tan obediente es | 0 a 100 |
| `amistad` | Vínculo emocional | 0 a 100 |
| `lealtad` | ¿Te traicionaría? | 0 a 100 |

#### Roles de NPCs en la Base

- **Trabajo** — Farmeo de recursos, crafting, defensa
- **Compañía** — Diálogos, historias, relaciones
- **Erótico** — Contenido adulto (configurable)

---

## 20.4 Loop de Gameplay

### Economía de Recursos

| Recurso | Rol | Mecánica |
|---------|-----|----------|
| **Energía** | Moneda principal | Gastas para hacer acciones |
| **Alimento** | Tiempo de juego | Sin comida → no puedes seguir |
| **Tiempo** | Limitante diario | Cada día tiene un límite |

### Acciones del Día

```
┌─────────────────────────────────────────────┐
│ NUEVO DÍA                                   │
├─────────────────────────────────────────────┤
│ Opción A: ENTRENAR                          │
│   └── Sube habilidad │ Cuesta energía       │
│                                             │
│ Opción B: EXPLORAR                          │
│   └── Encuentra recursos/NPCs/eventos       │
│   └── Cuesta energía + riesgo               │
│                                             │
│ Opción C: GESTIONAR BASE                    │
│   └── Asignar NPCs, craftear, etc.          │
│                                             │
│ Opción D: DESCANSAR                         │
│   └── Recupera energía │ Consume alimento   │
├─────────────────────────────────────────────┤
│ FIN DEL DÍA → Consume alimento → Siguiente  │
└─────────────────────────────────────────────┘
```

### Principio de Diseño

> **⚠️ EXPLORAR = RECOMPENSA + RIESGO**
> 
> Cada exploración da frutos: recursos, NPCs, eventos, progreso.  
> Pero también tiene costos: daño, efectos (sangrando, infectado), pérdida de recursos.  
> El jugador debe calcular si vale la pena.

---

## 20.5 Sistemas del Motor

### 1. Sistema de Eventos

Los eventos son **generados proceduralmente** basados en:
- Temática del apocalipsis
- Estado actual del mundo
- Historial del jugador
- RNG con seed

### 2. Sistema de Exploración

```
Explorar → Zona aleatoria → Encuentro:
├── Recursos (materiales, comida, medicina)
├── NPCs (amistosos, hostiles, neutrales)
├── Eventos (historias, misiones, peligros)
└── Estructuras (bunkers, tiendas, bases)
```

### 3. Sistema de Crafting

Recursos → Crafting → Equipo/Mejoras/Base

### 4. Sistema de Combate

Por turnos o tiempo real (configurable según temática).

### 5. Sistema de Historia

Generada por LLM con:
- Contexto de la partida
- Historial de decisiones
- Personalidad de NPCs
- Estado del mundo

---

## 20.6 Arquitectura Técnica

### Stack Propuesto

| Capa | Tecnología |
|------|------------|
| **Engine** | Python / Godot / Unity |
| **LLM Integration** | OpenAI / Anthropic / Local |
| **State Management** | JSON / SQLite |
| **Procedural Gen** | Python + Templates |
| **Frontend** | TBD (Web/Desktop/Mobile) |

### Estructura de Datos

```python
@dataclass
class GameState:
    """Estado completo de una partida."""
    seed: str
    apocalypse_type: str  # NUCLEAR, ZOMBIE, etc.
    day: int
    player: Player
    base: Base
    npcs: List[NPC]
    world: WorldMap
    history: List[Event]

@dataclass
class Player:
    """Estado del jugador."""
    name: str
    stats: Stats  # Fuerza, Inteligencia, etc.
    inventory: List[Item]
    energy: int
    health: int

@dataclass
class NPC:
    """Personaje no jugador."""
    id: str
    name: str
    personality: str  # Prompt para LLM
    relationship: Relationship  # Ejes de relación
    skills: List[Skill]
    backstory: str  # Generado por LLM
```

---

## 20.7 Diseño del Mundo

### Generación Procedural

El mundo se genera usando:
1. **Seed** para reproducibilidad
2. **Biomas** según temática
3. **Puntos de interés** (POIs)
4. **Rutas** entre zonas
5. **Dificultad escalante** desde el spawn

### Zonas

```
Mundo:
├── Zona Segura (Spawn)
│   └── Recursos básicos, baja dificultad
├── Zona de Riesgo Medio
│   └── Mejores recursos, NPCs hostiles
├── Zona Peligrosa
│   └── Alto riesgo, alta recompensa
└── Zona Extrema
    └── Legendario, casi imposible
```

---

## 20.8 Integración con Lilith

### ¿Cómo se Relaciona?

Story Engine es parte del **ecosistema Yggdrasil**:

| Realm | Proyecto | Relación con Story Engine |
|-------|----------|---------------------------|
| Svartalfheim | Lilith | Lilith puede ejecutar tests, generar código |
| Asgard | Story Engine | **Este proyecto** |
| Valhalla | Council | NPCs del juego pueden usar Council para decisiones |

### Uso de Lilith en Desarrollo

```
Lilith puede ayudar a desarrollar Story Engine:
├── Generar código Python/Godot
├── Crear prompts para LLM
├── Balancear economía (simulaciones)
├── Generar contenido (historias, NPCs)
└── Testing automático
```

---

## 20.9 Estado del Proyecto

### Fases Completadas

| Fase | Estado | Descripción |
|------|--------|-------------|
| **Fase 1: Diseño** | ✅ Completo | Visión, mecánicas, arquitectura |
| **Fase 2: Prototipo** | 📝 Pendiente | Implementación básica |
| **Fase 3: Contenido** | 📝 Pendiente | Temáticas, eventos, NPCs |
| **Fase 4: Polish** | 📝 Pendiente | Balance, UI/UX, testing |

### Documentación Existente

En `Ultralegacy/03_Archives_Proyectos_Historicos/StoryEngine_Fase1/Design/`:

| Documento | Contenido |
|-----------|-----------|
| `00_VISION.md` | Visión general del juego |
| `04_THEME_SYSTEM.md` | Sistema de temáticas |
| `06_EXPLORATION_SYSTEM.md` | Sistema de exploración |
| `07_EVENT_SYSTEM.md` | Sistema de eventos |
| `08_NPC_SYSTEM.md` | Sistema de NPCs |
| `12_TECH_STACK.md` | Stack tecnológico |

---

## 20.10 Próximos Pasos

### Para Continuar el Desarrollo

1. **Elegir engine**: Python puro, Godot, Unity, o web-based
2. **Prototipo básico**: Loop de gameplay mínimo viable
3. **Integración LLM**: Prompts engineering para narrativa
4. **Sistema de guardado**: Persistencia de partidas
5. **UI/UX**: Interfaz de usuario

### Integración con Lilith

```python
# Ejemplo: Lilith genera contenido para Story Engine

async def generate_npc(lilith, theme, zone):
    """Usa Lilith para generar un NPC coherente."""
    prompt = f"""
    Genera un NPC para un juego post-apocalíptico.
    Temática: {theme}
    Zona: {zone}
    
    Incluye:
    - Nombre
    - Personalidad (prompt para LLM)
    - Backstory (2-3 párrafos)
    - Skills
    - Apariencia
    """
    
    response = await lilith.generate(prompt)
    return parse_npc(response)
```

---

## 20.11 Conclusión

Story Engine V2 representa la **ambición creativa** del ecosistema Yggdrasil: no solo herramientas de productividad, sino **experiencias narrativas inmersivas**.

> *"El fin del mundo es solo el comienzo de la historia."*

### Recursos para Continuar

- **Diseño completo**: `Ultralegacy/StoryEngine_Fase1/Design/`
- **Integración Lilith**: Usar el Panteón de Agentes para generación de contenido
- **Inspiración**: Fallout, Dark Souls, RimWorld, Dwarf Fortress

---

**🎮 Story Engine V2 — Documentado para el Futuro**  
*Proyecto histórico preservado en el Archivo Fundacional.*
