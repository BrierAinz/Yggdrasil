# Misión 35: Council Vanaheim - Multi-Agente Colaborativo v5.3

> **Versión objetivo**: Lilith v5.3
> **Feature**: Council Vanaheim (Multi-Agent Deliberation)
> **Prioridad**: Alta (architectural evolution)
> **Esfuerzo estimado**: 20-24 horas
> **Dependencias**: v5.0-alpha, agentes activos

---

## 🎯 Objetivo

Implementar un sistema de **deliberacion multi-agente** donde multiples agentes del Panteon pueden **colaborar, debatir y llegar a consenso** en tareas complejas que requieren perspectivas multiples.

**Estado actual**: Agentes operan en silos, delegacion 1-a-1
**Estado deseado**: Council que permite debate estructurado y consenso entre agentes

---

## 💡 Motivacion

### Problema Actual

```
Usuario: "Analiza si deberia invertir en X startup"

Lilith delega a Eva (analisis) → Respuesta unidimensional

Mejor approach:
→ Eva (analisis financiero)
→ Odin (investigacion de mercado)
→ Albedo (devil's advocate)
→ Council debate → Consenso ponderado
```

**Issues**:
- Decisiones complejas se delegan a 1 solo agente
- No hay contraste de perspectivas
- Falta devil's advocate
- Sesgo de agente unico

### Solucion: Council Vanaheim

```
Usuario: "Analiza si deberia invertir en X"

Lilith → Detecta "decision compleja"
      → Convoca Council Vanaheim
      → Asigna roles:
          • Eva: Analista financiero
          • Odin: Investigador de mercado
          • Albedo: Devil's advocate
          • Shalltear: Mediador

→ Ronda 1: Posiciones iniciales (paralelo)
→ Ronda 2: Debate (secuencial, responden a otros)
→ Ronda 3: Sintesis y consenso
→ Lilith: Presenta conclusion multi-perspectiva
```

---

## 🏗️ Arquitectura

### Conceptos Core

#### Council Session
```python
@dataclass
class CouncilSession:
    """Sesion de deliberacion multi-agente"""
    session_id: str
    topic: str
    members: List[CouncilMember]
    rounds: List[Round]
    consensus: Optional[Consensus]
    created_at: datetime
    status: str  # 'active', 'deliberating', 'concluded'
```

#### Council Member
```python
@dataclass
class CouncilMember:
    """Agente participante con rol asignado"""
    agent_name: str  # Eva, Odin, Albedo, etc.
    role: str        # 'analyst', 'researcher', 'advocate', 'mediator'
    stance: Optional[str]  # 'support', 'oppose', 'neutral'
    weight: float    # Peso del voto (0-1)
```

#### Round
```python
@dataclass
class Round:
    """Ronda de deliberacion"""
    round_number: int
    type: str  # 'initial', 'debate', 'synthesis'
    contributions: List[Contribution]
    summary: str
```

---

### Componentes Nuevos

#### 1. `CouncilOrchestrator`

**Ubicacion**: `Core/Backend/core/council_orchestrator.py`

```python
class CouncilOrchestrator:
    """
    Orquesta sesiones de Council Vanaheim.

    Responsabilidades:
    - Detectar cuando convocar Council
    - Seleccionar agentes apropiados
    - Asignar roles
    - Gestionar rounds de deliberacion
    - Sintetizar consenso
    """

    async def should_convoke_council(
        self,
        query: str,
        context: Dict
    ) -> bool:
        """Determina si query requiere Council"""

        indicators = [
            any(word in query.lower() for word in
                ['deberia', 'should', 'recomiendas', 'opinion']),
            any(word in query.lower() for word in
                ['analiza', 'evalua', 'compara', 'pros y contras']),
            self._is_controversial_topic(query),
            'council' in query.lower() or 'debate' in query.lower()
        ]

        return any(indicators)

    async def convoke_council(
        self,
        topic: str,
        query: str,
        user_id: str,
        member_count: int = 3
    ) -> CouncilSession:
        """Convoca Council y ejecuta deliberacion"""

        # 1. Seleccionar agentes
        members = await self._select_members(topic, member_count)

        # 2. Asignar roles
        for member in members:
            member.role = await self._assign_role(member, topic)

        # 3. Crear sesion
        session = CouncilSession(
            session_id=generate_id(),
            topic=topic,
            members=members,
            rounds=[],
            created_at=datetime.now(),
            status='active'
        )

        # 4. Ejecutar rounds
        await self._execute_rounds(session, query)

        # 5. Sintetizar consenso
        consensus = await self._synthesize_consensus(session)
        session.consensus = consensus
        session.status = 'concluded'

        return session
```

#### 2. Rounds de Deliberacion

```python
async def _execute_rounds(self, session: CouncilSession, query: str):
    """Ejecuta 3 rounds de deliberacion"""

    # Round 1: Initial Positions (paralelo)
    round1 = await self._round_initial_positions(session, query)
    session.rounds.append(round1)

    # Round 2: Debate (secuencial, responden a otros)
    round2 = await self._round_debate(session, round1)
    session.rounds.append(round2)

    # Round 3: Synthesis (convergencia)
    round3 = await self._round_synthesis(session, [round1, round2])
    session.rounds.append(round3)

async def _round_initial_positions(
    self,
    session: CouncilSession,
    query: str
) -> Round:
    """Round 1: Posiciones iniciales en paralelo"""

    contributions = []

    # Ejecutar en paralelo
    tasks = [
        self._get_agent_position(member, query, session.topic)
        for member in session.members
    ]
    results = await asyncio.gather(*tasks)

    for member, result in zip(session.members, results):
        contribution = Contribution(
            member=member,
            content=result.content,
            references=result.references,
            confidence=result.confidence,
            timestamp=datetime.now()
        )
        contributions.append(contribution)

    return Round(
        round_number=1,
        type='initial',
        contributions=contributions,
        summary=self._summarize_round(contributions)
    )
```

#### 3. API Endpoints

**Ubicacion**: `Core/Backend/api/council_api.py` (nuevo)

```python
@router.post("/council/convoke")
async def convoke_council(request: ConvokeRequest):
    """Convoca Council para deliberar sobre tema"""

@router.get("/council/session/{session_id}")
async def get_session(session_id: str):
    """Obtiene detalles de sesion"""

@router.get("/council/sessions/recent")
async def get_recent_sessions(limit: int = 10):
    """Lista sesiones recientes"""
```

---

## 📋 Alcance (Scope)

### ✅ Fase 1: Core Council (v5.3.0)

1. **Deteccion Automatica**
   - Heuristicas para convocar Council
   - Config de triggers
   - Override manual (`/council` command)

2. **Orchestration**
   - Seleccion de agentes apropiados
   - Asignacion de roles dinamicos
   - Gestion de 3 rounds

3. **Deliberation**
   - Round 1: Posiciones iniciales (paralelo)
   - Round 2: Debate (secuencial con referencias)
   - Round 3: Sintesis (convergencia)

4. **Consensus**
   - Deteccion de acuerdos/desacuerdos
   - Ponderacion de votos
   - Recomendacion final

### ❌ NO Incluido (v5.4+)

- Votacion formal con quorum
- Roles dinamicos por agente
- Council asincrono (dias de deliberacion)
- Participacion de usuario en debate
- Council publico (multi-usuario)

---

## 🎯 Criterios de Éxito

### Tests Unitarios (12 nuevos)

```python
# Core/Tests/test_council_orchestrator.py
def test_should_convoke_council()
def test_select_members()
def test_assign_roles()
def test_round_initial_positions()
def test_round_debate()
def test_synthesize_consensus()
```

### Smoke Tests (3 criticos)

1. **Council simple (3 agentes)**
   ```
   Topic: "Deberia aprender Rust?"
   Members: Eva, Odin, Albedo

   → 3 rounds ejecutados
   → Consenso alcanzado
   → Recomendacion clara
   ```

2. **Debate con desacuerdo**
   ```
   Topic: "Invertir en crypto?"
   Members: Eva (oppose), Odin (support), Albedo (neutral)

   → Perspectivas contrastantes
   → Debate documentado
   → Split decision clara
   ```

3. **Convocacion automatica**
   ```
   User: "Analiza si deberia cambiar de trabajo"

   → Detecta "decision compleja"
   → Convoca Council automaticamente
   → Deliberacion multi-perspectiva
   ```

---

## 📦 Archivos a Crear/Modificar

### Nuevos (7 archivos)
```
Core/Backend/
├── core/
│   ├── council_orchestrator.py       # Orchestration
│   ├── council_session_store.py      # Persistence
│   └── consensus_calculator.py       # Consensus logic
├── api/
│   └── council_api.py                # REST API
└── Tests/
    └── test_council_orchestrator.py  # 12 tests

Core/Data/
├── council_sessions.jsonl            # Session storage
└── council_config.json               # Config (nuevo)
```

### Modificados (2 archivos)
```
Core/Backend/
├── core/
│   └── orchestrator.py               # +Council detection
└── api/
    └── discord_api.py                # +/council command
```

---

## ⚙️ Configuracion

```json
{
  "auto_convoke": {
    "enabled": true,
    "triggers": [
      "deberia",
      "should",
      "recomiendas",
      "analiza",
      "evalua"
    ],
    "min_confidence": 0.7
  },
  "members": {
    "default_count": 3,
    "max_count": 5,
    "roles": [
      "analyst",
      "researcher",
      "advocate",
      "mediator",
      "skeptic"
    ]
  },
  "rounds": {
    "count": 3,
    "timeout_seconds": 120,
    "allow_early_consensus": true
  }
}
```

---

## 🚀 Plan de Implementacion

| Fase | Tiempo | Tareas |
|------|--------|--------|
| Fase 1 | 8-10h | Council Orchestrator, rounds, roles, tests (8) |
| Fase 2 | 4-6h | Consensus Calculator, CouncilSessionStore, tests (4) |
| Fase 3 | 6-8h | API endpoints, Discord integration, smoke tests (3) |
| Fase 4 | 2h | Dashboard, docs, polish |

**Total**: 20-24 horas

---

## 📊 Impacto

### Positivo
- ✅ Decisiones multi-perspectiva
- ✅ Contraste de opiniones
- ✅ Devil's advocate built-in
- ✅ Trazabilidad de deliberacion

### Riesgos
- ⚠️ Latencia (3 rounds, multiples agentes)
- ⚠️ Costo de LLM calls (mitigado: parallelizacion)
- ⚠️ Consenso imposible (mitigado: split decisions OK)

---

## 🎯 Metricas de Éxito

| Metrica | Objetivo |
|---------|----------|
| Tests pasando | 12/12 (100%) |
| Smoke tests | 3/3 pasando |
| Council sessions | >20 en primer mes |
| User satisfaction | >85% "mejor que agente unico" |
| Consensus rate | >70% alcanza consenso |

---

*Mision creada: 2026-03-26*
*Estado: 📋 Disenada, pendiente de implementacion*
*Prioridad: Alta (architectural evolution)*
