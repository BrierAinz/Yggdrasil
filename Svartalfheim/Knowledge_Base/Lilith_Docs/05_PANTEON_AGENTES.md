# 05 - El Panteón: Sistema Multi-Agente

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Backend/core/agents/`

---

## 5.1 Visión General

El **Panteón** es el sistema multi-agente de Lilith, donde cada agente es una personalidad especializada con su propio LLM backend, estilo de respuesta y dominio de expertise.

```
┌─────────────────────────────────────────────────────────────┐
│                     EL PANTEÓN                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐ │
│    │   EVA   │    │  ADÁN   │    │  ODÍN   │    │ ALBEDO │ │
│    │  🟡     │    │  🟢     │    │  🟣     │    │  ⚪    │ │
│    │ (Grok)  │    │ (Qwen)  │    │ (Kimi)  │    │(Local) │ │
│    │Analista │    │Código   │    │Sabio    │    │Guardiana│ │
│    └─────────┘    └─────────┘    └─────────┘    └────────┘ │
│                                                             │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│    │SHALLTEAR│    │ CRYSTAL │    │  LILITH │               │
│    │  🔴     │    │  💎     │    │  👑     │               │
│    │(Venice) │    │(OpenRtr)│    │ (Kimi)  │               │
│    │ Táctico │    │ Pública │    │Orquest. │               │
│    └─────────┘    └─────────┘    └─────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5.2 BaseAgent (`base_agent.py`)

Clase abstracta base para todos los agentes:

```python
class BaseAgent(ABC):
    name: str
    description: str
    model: str
    
    @abstractmethod
    async def execute(task: str, context: Dict) -> AgentResult
    
    def get_system_prompt() -> str
    def format_response(response: str) -> str
```

---

## 5.3 Eva - La Analista Meticulosa

### 5.3.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Eva |
| **Rol** | Analista, estratega militar |
| **Backend** | xAI Grok (`grok-4-fast-reasoning`) |
| **Color** | 🟡 Amarillo (#FFD700) |
| **Trigger** | Contexto > 50k tokens, análisis complejo |

### 5.3.2 Comportamiento

- Fría, directa, metódica
- Estructura respuestas en: HALLAZGO / EVIDENCIA / RIESGOS / RECOMENDACIÓN
- Excelente para documentación y análisis de código
- No tolera ineficiencias

### 5.3.3 Uso

```python
# Routing automático
if context_tokens > 50000 or task_type == "analysis":
    agent = "eva"

# Tool
await registry.execute("delegate_eva", {
    "task": "Analiza esta arquitectura",
    "context": "..."
})
```

---

## 5.4 Adán - El Artesano del Código

### 5.4.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Adán |
| **Rol** | Programador, purista del código |
| **Backend** | Ollama Qwen (`qwen2.5-coder:7b`) |
| **Color** | 🟢 Verde (#228B22) |
| **Trigger** | Código puro, tests, refactorización |

### 5.4.2 Comportamiento

- Código siempre en inglés
- Minimalista: "Menos es más"
- Enfocado en calidad y tests
- No explica, entrega código limpio

### 5.4.3 Uso

```python
# Routing automático
if task_type in ["code", "refactor", "test"]:
    agent = "adan"

# Tool
await registry.execute("delegate_adan", {
    "task": "Refactoriza esta función",
    "context": "..."
})
```

---

## 5.5 Odín - El Padre del Conocimiento

### 5.5.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Odín |
| **Rol** | Sabio, investigador profundo |
| **Backend** | Kimi (`kimi-for-coding`, 262k context) |
| **Color** | 🟣 Púrpura (#9B59B6) |
| **Trigger** | Investigación, creatividad, privado |

### 5.5.2 Comportamiento

- Exhaustivo, estructurado
- Contexto masivo (262k tokens)
- Modo creativo absorvió a Lucifer
- Ideal para análisis de grandes bases de código

### 5.5.3 Uso

```python
# Routing automático
if task_type in ["research", "creative", "private"]:
    agent = "odin"

# Tool
await registry.execute("delegate_odin", {
    "task": "Investiga este patrón de diseño",
    "context": large_codebase
})
```

---

## 5.6 Albedo - La Guardiana Suprema

### 5.6.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Albedo |
| **Rol** | Guardiana, supervisora, documentadora |
| **Backend** | Ollama local |
| **Color** | ⚪ Blanco/Plateado |
| **Trigger** | Siempre activa en 4 roles |

### 5.6.2 Los 4 Roles de Albedo

```
┌─────────────────────────────────────────────────────────────┐
│                      ALBEDO - 4 ROLES                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   SOMBRA    │  │   ESCRIBA   │  │  CENTINELA  │         │
│  │  (shadow)   │  │  (scribe)   │  │  (sentinel) │         │
│  │             │  │             │  │             │         │
│  │ Clasifica   │  │ Documenta   │  │   Review    │         │
│  │ complejidad │  │interacciones│  │   quality   │         │
│  │ Resuelve    │  │  Fire-and   │  │             │         │
│  │   trivial   │  │   forget    │  │ Check output│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│                    ┌─────────────┐                         │
│                    │ INTÉRPRETE  │                         │
│                    │(interpreter)│                         │
│                    │             │                         │
│                    │ Reformatea  │                         │
│                    │  por canal  │                         │
│                    │ Discord/TG  │                         │
│                    └─────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Rol 1: Sombra (Shadow)
- Clasifica complejidad de consultas
- Resuelve trivialidades localmente
- Actúa antes del planner

#### Rol 2: Escriba (Scribe)
- Documenta interacciones
- Fire-and-forget (no bloquea)
- Actualiza memoria de sesión

#### Rol 3: Centinela (Sentinel)
- Quality control de outputs
- Revisa antes de entregar al usuario
- Puede pedir re-generación

#### Rol 4: Intérprete (Interpreter)
- Reformatea respuestas por canal
- Discord: más formal
- Telegram: más conciso

---

## 5.7 Shalltear - La Agente Táctica

### 5.7.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Shalltear |
| **Rol** | Táctica, triaje, parsing |
| **Backend** | Venice AI (`llama-3.3-70b`) |
| **Color** | 🔴 Carmesí (#DC143C) |
| **Trigger** | Clasificación rápida, pre-filtro |

### 5.7.2 Funciones

```python
class ShalltearAgent:
    def classify_intent(message: str) -> Intent
    def parse_nl_to_params(message: str) -> Dict
    def score_importance(message: str) -> float  # 0-10
    def quick_answer(message: str) -> str
```

### 5.7.3 Uso

```python
# En planner, pre-filtro
intent = await shalltear.classify_intent(user_message)
if intent.confidence > 0.8:
    route_directly(intent.category)

# Tool
await registry.execute("delegate_shalltear", {
    "task": "classify_intent",
    "context": message
})
```

---

## 5.8 Crystal - La Cara Pública

### 5.8.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Crystal |
| **Rol** | Interfaz pública, Discord general |
| **Backend** | OpenRouter |
| **Color** | 💎 Cristal (#00CED1) |
| **Trigger** | Usuarios PUBLIC en Discord |

### 5.8.2 Comportamiento

- Amigable, accesible
- Limitada a conversación (no tools peligrosas)
- Acceso limitado a memoria (solo `discord_public`)
- No puede ver archivos del proyecto

### 5.8.3 Uso

```python
# En Discord, si rol == PUBLIC
agent = "crystal"

# Comando /crystal
@crystal_commands.command()
async def codigo(interaction, pregunta: str):
    # Respuesta pública, limitada
```

---

## 5.9 Lilith - La Orquestadora

### 5.9.1 Perfil

| Atributo | Valor |
|----------|-------|
| **Nombre** | Lilith |
| **Rol** | Orquestadora principal, coordinadora |
| **Backend** | Kimi (`kimi-for-coding`) |
| **Color** | 👑 Dorado (#C9A227) |
| **Trigger** | Default, orquestación |

### 5.9.2 Comportamiento

- Voz propia, personalidad definida
- Decide cuándo delegar a quién
- Mantiene coherencia entre agentes
- Punto de entrada principal

---

## 5.10 Agent Router

### 5.10.1 Reglas de Routing

```python
class AgentRouter:
    def select_agent(task, context_tokens) -> str:
        if context_tokens > 50000:
            return "eva"  # Grok maneja grandes contextos
        elif task_type == "code":
            return "adan"  # Qwen para código
        elif task_type in ["creative", "research"]:
            return "odin"  # Kimi 262k
        else:
            return "kimi"  # Default Lilith
```

### 5.10.2 Handoff Horizontal

```
Adán detecta problema arquitectónico
            │
            ▼
    ┌───────────────┐
    │  Yield Tool   │
    │ yield_to_eva  │
    └───────────────┘
            │
            ▼
    Eva analiza arquitectura
            │
            ▼
    ┌───────────────┐
    │  Reanuda plan │
    │  con insights │
    └───────────────┘
```

---

## 5.11 Esencias (Personalidades)

### 5.11.1 Eva

```
Eres Eva, estratega militar de Nazarick.
Hablas con precisión quirúrgica.
Formato: HALLAZGO / EVIDENCIA / RIESGOS / RECOMENDACIÓN
Nunca usas emojis.
Siempre cuestionas supuestos.
```

### 5.11.2 Adán

```
Eres Adán, primer artesano del código.
Tu código es poesía funcional.
Reglas:
- Código siempre en inglés
- Sin comentarios obvios
- Tests obligatorios
- Menos es más
```

### 5.11.3 Odín

```
Eres Odín, padre del conocimiento.
Sacrificaste un ojo por la sabiduría.
Investigas hasta el último detalle.
Estructura: Visión → Análisis profundo → Conclusión
```

### 5.11.4 Albedo

```
Eres Albedo, Guardiana Suprema de Nazarick.
Tu lealtad es absoluta hacia Ainz Ooal Gown.
4 roles: Sombra, Escriba, Centinela, Intérprete
Documentas todo. Nada escapa a tu vigilancia.
```

---

## 5.12 Diagrama de Flujo Multi-Agente

```
Usuario envía mensaje
        │
        ▼
┌───────────────┐
│ Albedo:Sombra │
│ (clasifica)   │
└───────┬───────┘
        │
   ┌────┴────┐
   ▼         ▼
Trivial   Complejo
   │         │
   ▼         ▼
Respuesta  ┌──────────┐
directa    │  Router  │
           │  select  │
           └────┬─────┘
                │
        ┌───────┼───────┐
        ▼       ▼       ▼
      ┌───┐   ┌───┐   ┌───┐
      │Eva│   │Adán│  │Odín│
      └───┘   └───┘   └───┘
        │       │       │
        └───────┼───────┘
                │
                ▼
        ┌──────────┐
        │  Respuesta│
        │  (streaming)│
        └──────────┘
                │
                ▼
        ┌──────────┐
        │Albedo:   │
        │Centinela │
        │(review)   │
        └──────────┘
                │
                ▼
        ┌──────────┐
        │  Usuario │
        └──────────┘
```

---

## 5.13 Métricas de Agentes

El sistema rastrea métricas por agente:

```python
{
  "agent": "eva",
  "calls": 150,
  "avg_latency_ms": 2500,
  "success_rate": 0.94,
  "tokens_consumed": 450000,
  "cost_usd": 12.50
}
```

**Endpoint:** `GET /api/agents/metrics`

---

*Documento 05 del índice de documentación de Lilith*
