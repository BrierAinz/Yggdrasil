# Horror GameMaster — Brainstorm Fase 5+
> BrierStudios — 2026-05-29
> 10 nuevas mecanicas + tecnicas de proc-gen + modulo JSONL ambiental

---

## ESTADO ACTUAL (resumen)

- Fases 1-4: DONE (10 modulos, 84 tests, Terminal + Web UI)
- Dataset: 2,067 entradas unificadas (8 fear types)
- Pendiente: stress tests, sonido, GitHub publish, landing page
- Stack: Python + FastAPI + HTMX + Rich + SQLite + sentence-transformers

---

## PARTE 1: 10 NUEVAS MECANICAS (item 10)

### 1. SOUL ECHO — Ecos del jugador anterior
**Prioridad: MUST-HAVE**
**Modulos: Player Memory + Context Manager**

Cuando un jugador muere o abandona una sesion, sus acciones dejan
"ecos" en el mundo. El siguiente jugador (o el mismo en nueva sesion)
encuentra sombras de lo que paso: pisadas en el polvo, palabras
escritas en paredes, objetos dejados. El LLM genera narrativa basada
en los datos reales de sesiones anteriores.

- Extiende PlayerMemory con `session_echoes` table
- Context Manager genera "echo events" al entrar a escenas visitadas
- Los ecos se degradan con el tiempo (3 sesiones max)
- Fear impact: el jugador siente que "alguien estuvo aqui antes"

### 2. MIRROR PSYCHOLOGY — Espejo psicologico
**Prioridad: MUST-HAVE**
**Modulos: Pattern Analyzer + LLM Engine**

El engine crea un "espejo" del perfil psicologico del jugador y lo
usa en su contra. Si el jugador siempre examina objetos, el espejo
crea objetos trampa. Si siempre huye, crea pasillos que se alargan.
Si es valiente, el miedo se vuelve sutil y corrosivo.

- Pattern Analyzer exporta `behavior_signature` (top 5 patrones)
- LLM recibe el signature como parte del system prompt
- Procedural Generator crea trampas especificas para el estilo
- Se actualiza cada 5 turnos (no en tiempo real, para no ser obvio)

### 3. NARRATIVE VIRUS — Virus narrativo
**Prioridad: SHOULD-HAVE**
**Modulos: Context Manager + Procedural Generator**

Una "idea" o "imagen" se propaga por la narrativa como un virus.
Empieza como un detalle menor (un patron en el papel tapiz, un sonido
repetitivo) y gradualmente infecta todo: la UI, los textos de objetos,
los nombres de habitaciones, las respuestas del LLM. El jugador
debe darse cuenta de que algo se esta extendiendo.

- Context Manager rastrea `narrative_patterns` (patrones recurrentes)
- Cuando un patron aparece 3+ veces, se activa "infection mode"
- El LLM recibe instrucciones de inyectar el patron en toda narrativa
- 4 niveles: subtle -> noticeable -> pervasive -> reality_break
- Ejemplo: el patron "tres golpes" aparece primero en una puerta,
  luego en el reloj, luego en el latido del jugador, luego en el texto

### 4. MEMORY CORRUPTION — Corrupcion de memoria
**Prioridad: SHOULD-HAVE**
**Modulos: Player Memory + LLM Engine**

La memoria del jugador se "corrompe" gradualmente. Lo que recuerda
de sesiones anteriores no es 100% confiable. El engine altera
sutilmente los datos de memoria: una puerta que era roja ahora es
azul, un NPC que era amigable ahora fue hostil, una habitacion que
exploraste ahora no tiene salida.

- Player Memory tiene un `corruption_level` (0.0 a 1.0)
- Aumenta con cada sesion (+0.1) o con eventos traumaticos (+0.2)
- LLM Engine altera callbacks con corrupcion proporcional
- El jugador puede reducir corrupcion encontrando "anchor objects"
- Genera paranoia organica: "juro que esta puerta no estaba aqui"

### 5. ENVIRONMENTAL BREATHING — Respiracion del entorno
**Prioridad: MUST-HAVE**
**Modulos: Procedural Generator + Tension Manager**

Los escenarios "respiran" — se expanden y contraen sutilmente.
Las habitaciones cambian de tamano, los pasillos se alargan o
acortan, las puertas aparecen y desaparecen. No es aleatorio:
esta sincronizado con la curva de tension.

- Procedural Generator tiene `room_state` mutable por escena
- Tension Manager envia `breath_cycle` (inhale/exhale/hold)
- En inhale: habitaciones se sienten mas pequenas, paredes cercanas
- En exhale: espacios se abren, se revelan nuevas salidas
- En hold: todo esta quieto, ni un sonido, ni un movimiento
- Cambios son graduales (1-2 metros por ciclo) para no ser obvios

### 6. ENTITY EVOLUTION — Evolucion de entidades
**Prioridad: MUST-HAVE**
**Modulos: NPC Intelligence + Pattern Analyzer**

Las entidades aprenden y evolucionan. Si el jugador siempre huye
del Crawler, el Crawler desarrolla patrones de emboscada. Si el
jugador siempre enfrenta al Watcher, el Watcher se vuelve mas
sutil. Cada entidad tiene un `evolution_tree` con 3 ramas.

- NPC Intelligence扩展 con `entity_evolution` system
- Pattern Analyzer alimenta el `adaptation_data` de cada entidad
- 3 ramas por tipo: aggressive, subtle, hybrid
- Evolucion ocurre despues de 3+ interacciones con el jugador
- El LLM recibe la rama elegida como modifier en la narrativa
- Ejemplo: Crawler(Stalking) -> Stalker/Trapper/Ghost

### 7. COLLECTIVE UNCONSCIOUS — Inconsciente colectivo
**Prioridad: NICE-TO-HAVE**
**Modulos: Player Memory + Context Manager**

Datos anonimizados de TODOS los jugadores alimentan un "inconsciente
colectivo". Los miedos mas comunes entre jugadores se convierten en
el contenido mas frecuente. Si el 60% de jugadores teme la oscuridad,
la oscuridad se vuelve el tema dominante.

- Player Memory agrega `collective_fear_profile` (anonimo)
- Context Manager usa el perfil colectivo para ponderar contenido
- Actualiza cada 10 sesiones (no en tiempo real)
- Requiere multiple jugadores (solo relevante en multiplayer/distribuido)
- Crea sensacion de "todos temen lo mismo"

### 8. PARADOX ENGINE — Motor de paradojas
**Prioridad: SHOULD-HAVE**
**Modulos: Context Manager + LLM Engine**

El engine genera paradojas narrativas deliberadas. El jugador
encuentra evidencia contradictoria: un diario dice que el edificio
se quemo hace 10 anos, pero hay flores frescas en el jarron.
Las paradojas no se resuelvan — se acumulan hasta que la realidad
misma se vuelve inestable.

- Context Manager rastrea `established_facts` (hechos establecidos)
- LLM Engine puede generar `paradox_events` que contradicen hechos
- Max 2 paradojas activas (mas confunde sin entretener)
- Las paradojas escalan: contradiccion -> imposibilidad -> colapso
- El jugador puede "anclar" la realidad investigando (reduce paradojas)

### 9. FEAR RESONANCE — Resonancia de miedo
**Prioridad: SHOULD-HAVE**
**Modulos: Tension Manager + Pattern Analyzer + Procedural Generator**

Los diferentes tipos de miedo interactuan entre si. Darkness +
isolation = paranoia amplificada. Psychological + body_horror =
loss_of_control acelerado. El engine detecta cuando 2+ miedos
estan altos simultaneamente y genera eventos "resonantes" que
explojan la combinacion.

- Pattern Analyzer calcula `fear_interactions` (matriz 7x7)
- Tension Manager usa la resonancia para multiplicar intensidad
- Procedural Generator crea eventos hibridos (2+ fear types)
- Ejemplo: darkness(0.8) + isolation(0.7) = evento donde el jugador
  esta solo en la oscuridad Y algo se mueve JUSTO donde no puede ver
- La resonancia tiene cooldown de 5 turnos para no saturar

### 10. PLAYER AS ENTITY — El jugador como entidad
**Prioridad: NICE-TO-HAVE**
**Modulos: NPC Intelligence + LLM Engine + Pattern Analyzer**

Despues de suficiente exposicion al horror, el jugador empieza a
ser percibido como una entidad por los NPCs. Los NPCs reaccionan
con miedo al jugador. El jugador descubre que ha estado dejando
rastros que asustan a otros. Invierte la perspectiva: ahora el
jugador es lo que temia.

- NPC Intelligence agrega `player_entity_score` (0.0 a 1.0)
- Aumenta con acciones agresivas, exploracion obsesiva, supervivencia
- Cuando score > 0.7, NPCs empiezan a huir del jugador
- LLM Engine genera narrativa desde la perspectiva del NPC asustado
- El jugador ve su propio comportamiento reflejado como algo aterrador
- Requiere 20+ turnos para activarse (slow burn)

---

## PARTE 2: TECNICAS DE PROCEDURAL GENERATION (item 11)

### 1. MARKOV CHAIN NARRATIVE GENERATION
**Dificultad: MEDIO**

Cadenas de Markov de orden 2-3 para generar secuencias narrativas
coherentes. Cada estado es un tipo de evento (atmosphere, tension,
scare, calm, revelation). Las transiciones estan ponderadas por la
curva de tension actual y el perfil de miedo.

```
States: [ATMO, TENS, SCARE, CALM, REV, ENTITY, ENV]
Transition matrix se adapta al tension_level actual
Orden 2-3 mantiene coherencia sin ser predecible
```

**Integracion**: Tension Manager reemplaza su decision engine actual
con un Markov chain ponderado. El LLM rellena el contenido, el Markov
decide la ESTRUCTURA.

### 2. WAVE FUNCTION COLLAPSE (WFC) PARA ROOM LAYOUTS
**Dificultad: ALTO**

WFC genera layouts de habitaciones/pasillos donde cada "celda" es
un tipo de espacio (corridor, room, stairwell, dead_end). Las
restricciones garantizan conectividad y coherencia. Para horror:
las restricciones incluyen "debe haber al menos 1 dead end visible"
y "nunca mas de 2 salidas visibles desde cualquier punto".

```
Grid 8x8, cada celda tiene un set de opciones (superposicion)
Colapsar celdas con menor entropia primero
Restricciones: connectivity, max_exits=2, min_dead_ends=2
Resultado: layout que se siente disenado, no aleatorio
```

**Integracion**: Procedural Generator usa WFC para generar el
"mapa" de cada seccion del juego. El mapa es abstracto (no grafico)
— define que habitaciones conectan con cuales.

### 3. PERLIN NOISE TENSION CURVES
**Dificultad: FACIL**

Curvas de tension basadas en Perlin noise en vez de decisiones
discretas. Multiples octavas controlan diferentes escalas temporales:
octava 1 = micro-tension (turno a turno), octava 2 = meso-tension
(5-10 turnos), octava 3 = macro-tension (sesion completa).

```python
import noise
tension = noise.pnoise1(turn * 0.1, octaves=3)
# Octava 1: variacion rapida (atmosfera)
# Octava 2: onda media (build-ups y releases)
# Octava 3: tendencia general (arc de la sesion)
```

**Integracion**: Tension Manager usa Perlin noise como base y el
decision engine ajusta +/- sobre esa base. Resulta en curvas que
se sienten naturales, no mecanicas.

### 4. CONSTRAINT SATISFACTION PARA PUZZLES
**Dificultad: MEDIO**

Generacion de puzzles ambientales via constraint satisfaction
problems (CSP). Cada puzzle tiene variables (piezas, codigos,
secuencias) y restricciones (logica, tematica, dificultad). El
solver genera puzzles que siempre tienen solucion.

```
Variables: [lock_code(0-999), key_location(room_1..room_10), 
            sequence(A,B,C,D)]
Constraints: code != 000, key NOT in current_room, 
             sequence has no adjacent repeats
Solver: backtracking con forward checking
```

**Integracion**: Procedural Generator crea puzzles como eventos
especiales. El LLM genera la narrativa alrededor del puzzle, pero
la LOGICA es generada por CSP (garantiza que sea resoluble).

### 5. L-SYSTEMS PARA ENVIRONMENT MUTATION
**Dificultad: MEDIO**

L-systems (Lindenmayer systems) para mutaciones organicas del
entorno. Las "reglas de reescritura" transforman espacios simples
en complejos de forma fractal. Para horror: las reglas generan
crecimiento organico (venas en paredes, raices, membranas).

```
Axiom: ROOM
Rules: ROOM -> ROOM[CORRIDOR]ROOM (50%)
       ROOM -> CORRIDOR (30%)
       ROOM -> ROOM[TUNNEL]ROOM[STAIRS] (20%)
Iterations: 3-4 (max profundidad)
Resultado: estructura tipo arbol con ramificaciones
```

**Integracion**: Procedural Generator usa L-systems para generar
la topologia de areas "infectadas" o "corrompidas". Las areas
normales usan layouts mas estructurados.

### 6. AGENT-BASED EMERGENT NARRATIVE
**Dificultad: ALTO**

Simulacion de agentes autonomos (NPCs + entidades) que interactuan
entre si SIN intervencion del jugador. El jugador observa las
consecuencias: un NPC muerto en un pasillo, una puerta rota, voces
distantes. La narrativa emerge de la simulacion, no se escribe.

```python
# Cada agente tiene: position, goal, fear_level, awareness
# Tick: cada agente actua segun su estado
# Resultado: eventos que el jugador descubre, no que le pasan
```

**Integracion**: NPC Intelligence ejecuta una simulacion simplificada
entre turnos del jugador. Los resultados se inyectan como ambient
details en la siguiente narrativa. Requiere cuidado: la simulacion
debe ser ligera (no bloquear el turno del jugador).

### 7. RECURSIVE ROOM GENERATION (Russian Doll)
**Dificultad: FACIL**

Habitaciones dentro de habitaciones. El jugador entra a una
habitacion que contiene una maqueta de otra habitacion. Si examina
la maqueta, descubre que es identica a la habitacion actual. Si
entra a la maqueta (via LLM narrativa), esta en una version
escalada de la misma habitacion.

**Integracion**: Procedural Generator crea `recursive_scenes` —
escenas que se anidan. Max 3 niveles de recursion. Cada nivel
altera un detalle (color, sonido, presencia de entidad).

### 8. ENVIRONMENTAL STATE MACHINES
**Dificultad: FACIL**

Cada habitacion tiene una maquina de estados finitos con 4-6
estados (normal, decaying, corrupted, collapsed, void, alive).
Las transiciones estan ligadas a eventos del juego. El LLM
recibe el estado actual como modifier.

```
States: [NORMAL, UNEASY, DECAYING, CORRUPTED, COLLAPSED, VOID, ALIVE]
Transitions: player_action + time + tension_level -> next_state
Each state has: sensory_description, available_events, entity_spawn_rate
```

**Integracion**: Procedural Generator mantiene un `room_fsm` por
habitacion. El LLM Engine consulta el estado antes de generar
narrativa.

---

## PARTE 3: MODULO JSONL — ENVIRONMENTAL STORYTELLING (item 12)

### Schema

```json
{
  "instruction": "<tipo de generacion>",
  "input": "<contexto de la escena>",
  "output": "<200-400 palabras de prosa atmosferica>",
  "fear_type": "<psychological|darkness|isolation|body_horror|paranoia|loss_of_control|jumpscare>",
  "entry_type": "environmental_storytelling",
  "sub_type": "<room_narrative|object_history|found_document|environmental_change|ambient_decay>"
}
```

### Taxonomia de sub-tipos

| Sub-tipo | Descripcion | Ejemplo |
|----------|-------------|---------|
| room_narrative | La habitacion cuenta su historia sin NPCs | "La cocina huele a algo quemado. Los quemadores estan todos encendidos pero no hay fuego..." |
| object_history | Un objeto tiene un pasado aterrador | "El muneco de trapo tiene una costura nueva en la espalda. Alguien lo abrio y lo cerro..." |
| found_document | Documentos encontrados (diarios, notas) | "Pagina 47: 'Dayo 23. The walls are closer today. I measured. 2cm less...'" |
| environmental_change | Un espacio que cambia entre visitas | "El pasillo tiene una puerta mas que ayer. Estas seguro. Contaste 7 antes. Ahora son 8." |
| ambient_decay | Degradacion organica del espacio | "El techo gotea un liquido que no es agua. Es tibio. Huele a cobre." |

### 5 Ejemplos (guardados como JSONL)

Ver: data/dataset_environmental.jsonl

---

## PARTE 4: TECNICAS ADICIONALES DE INVESTIGACION

### Wave Function Collapse — Implementacion simplificada
- Libreria: `wfc` (pip install wfc) o implementacion propia (~150 LOC)
- Grid 6x6 para testing, 12x12 para produccion
- Restricciones custom para horror: dead ends obligatorios, loops limitados

### Perlin Noise en Python
```python
import noise  # pip install noise
# noise.pnoise1(x, octaves=3, persistence=0.5, lacunarity=2.0)
# Perfecto para tension curves suaves
```

### Markov Chains con numpy
```python
import numpy as np
states = ['atmosphere', 'tension', 'scare', 'calm', 'revelation']
# Matriz de transicion 5x5, ajustable por tension_level
transition = np.array([
    [0.4, 0.3, 0.05, 0.2, 0.05],  # from atmosphere
    [0.2, 0.3, 0.25, 0.1, 0.15],  # from tension
    [0.1, 0.1, 0.1, 0.6, 0.1],    # from scare (usually followed by calm)
    [0.5, 0.2, 0.05, 0.2, 0.05],  # from calm
    [0.2, 0.3, 0.2, 0.1, 0.2],    # from revelation
])
```

---

## PRIORIDADES DE IMPLEMENTACION

| # | Mecanica | Prioridad | Dificultad | Impacto |
|---|----------|-----------|------------|---------|
| 1 | Soul Echo | MUST | Medio | Alto — rejugabilidad |
| 5 | Environmental Breathing | MUST | Facil | Alto — atmosfera |
| 6 | Entity Evolution | MUST | Medio | Alto — variedad |
| 2 | Mirror Psychology | MUST | Medio | Muy Alto — personalizacion |
| 3 | Narrative Virus | SHOULD | Medio | Alto — horror unico |
| 4 | Memory Corruption | SHOULD | Facil | Medio — paranoia |
| 8 | Paradox Engine | SHOULD | Medio | Alto — narrativa |
| 9 | Fear Resonance | SHOULD | Facil | Medio — depth |
| 10 | Player as Entity | NICE | Alto | Muy Alto — twist |
| 7 | Collective Unconscious | NICE | Alto | Bajo — requiere multiplayer |

## SPRINT SUGERIDO (proximas 2 semanas)

**Semana 1**: Soul Echo + Environmental Breathing + Perlin Noise tension
**Semana 2**: Entity Evolution + Mirror Psychology + Fear Resonance

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
