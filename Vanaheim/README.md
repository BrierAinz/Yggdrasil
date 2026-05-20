# Vanaheim — Reino de los Vanir (Vivero de Agentes de IA)

> *"Donde los Vanir cultivan la inteligencia que fluye como rios."*

**Proposito:** Agentes autonomos, bots de plataforma (Telegram/Discord), framework de agentes y gateway Bifrost de comunicacion con Asgard.

**Estado:** ACTIVO | **Tamano:** ~442 KB | **Ultima auditoria:** 2026-05-02

---

## Estructura Actual

```
Vanaheim/
├── Agents/                          # Agentes del Panteon
│   ├── Base/                        # Clase base VanirAgent
│   │   ├── vanir_agent.py           # ABC con execute/stream/is_available/health
│   │   └── __init__.py
│   ├── Adan/                        # Codigo y refactoring (Ollama/qwen2.5-coder)
│   │   ├── agent.py
│   │   └── __init__.py
│   ├── Eva/                         # Analisis y documentacion (Grok/xAI)
│   │   ├── agent.py
│   │   └── __init__.py
│   ├── Odin/                        # Investigacion profunda (Kimi, 262k ctx)
│   │   ├── agent.py
│   │   └── __init__.py
│   ├── Shalltear/                   # Clasificacion, triaje, parsing NL (Venice)
│   │   ├── agent.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── base_agent.py                # [LEGACY] Base agent v1 (pre-remaster)
│   ├── adan_vanaheim.py             # [LEGACY] Agente plano pre-Agents/
│   ├── eva_vanaheim.py              # [LEGACY] Agente plano pre-Agents/
│   └── odin_vanaheim.py             # [LEGACY] Agente plano pre-Agents/
├── Bots_Lilith_v5/                  # Bot Telegram (heritage monolito)
│   ├── bridge/
│   │   └── lilith_bridge.py         # Bridge a LilithEngine via Gateway REST
│   └── telegram/
│       ├── bot.py                   # Bot Telegram principal
│       ├── bot_wrapper.py
│       ├── retry_manager.py
│       ├── telegram_signal_handlers.py
│       ├── telegram_structured_logging.py
│       └── telegram_heartbeat.py
├── bifrost/                         # Bifrost Gateway (conexion con Asgard)
│   ├── gateway.py                   # FastAPI con LilithEngine, JWT y streaming
│   ├── auth.py                      # Validacion de tokens JWT
│   └── __init__.py
├── bots/                            # Bots simples
│   ├── echo_bot.py
│   └── __init__.py
├── Config/                          # Configuracion
│   ├── agents.json                  # Config de agentes (modelos, providers, timeouts)
│   ├── vanir_registry.json          # Registry con estado y capacidades
│   └── bifrost.json                 # Config del gateway Bifrost
├── Core/                            # Framework core
│   ├── api/
│   │   └── server.py                # FastAPI server para agentes
│   ├── circuit_breaker.py           # Circuit breaker pattern
│   ├── memory/
│   │   └── muninn_client.py         # Cliente del servicio de memoria (Muninn)
│   ├── models/
│   │   ├── agent.py                 # AgentState, AgentConfig, AgentCapabilities, etc.
│   │   ├── requests.py              # Modelos de request
│   │   ├── responses.py             # Modelos de response
│   │   └── __init__.py
│   ├── persona/
│   │   └── loader.py                # Carga de system prompts por agente
│   ├── registry/
│   │   └── vanir_registry.py         # Registry de agentes en runtime
│   └── __init__.py
├── vanaheim-framework/              # Framework empaquetado (pip)
│   ├── vanaheim/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   └── config.py
│   ├── tests/
│   │   └── test_framework.py
│   ├── pyproject.toml
│   └── vanaheim_framework.egg-info/
├── Council/
│   └── templates/
│       └── architecture_decision_record.md
├── server.py                        # Entry point: Bifrost Gateway Server (uvicorn)
├── launcher.py                      # Launcher de bots (legacy)
├── launch.py                        # Launcher alternativo
├── requirements.txt                 # Dependencias Python
├── bot_registry.json                # Registro de bots disponibles
├── REGLAS.md                        # Reglas del reino
├── README_BIFROST.md                # Documentacion del protocolo Bifrost
└── server.log                       # [RUNTIME] Log de servidor (no versionar)
```

---

## Agentes del Panteon

| Agente | Modelo | Provider | Especialidad | Contexto |
|--------|--------|----------|-------------|----------|
| **Shalltear** | llama-3.3-70b | Venice | Clasificacion, parsing NL, triaje | 32k |
| **Adan** | qwen2.5-coder:7b | Ollama (local) | Codigo, tests, refactoring | 32k |
| **Eva** | grok-4-fast-reasoning | xAI/Grok | Analisis, documentacion, research | 128k |
| **Odin** | kimi-for-coding | Kimi | Investigacion profunda, analisis masivo | 262k |

---

## Componentes Clave

### Bifrost Gateway
- **Proposito:** Comunicacion bidireccional entre Asgard (Lilith) y Vanaheim
- **Puerto:** `http://localhost:9000`
- **Endpoints:** `/api/bifrost/health`, `/api/bifrost/agents`, `/api/bifrost/execute`
- **Seguridad:** JWT tokens + circuit breaker + fallback automatico
- **Ver detalles:** `README_BIFROST.md`

### Framework Core
- **VanirAgent** (ABC): Clase base con `execute()`, `stream()`, `is_available()`, `health()`
- **AgentConfig/AgentCapabilities**: Modelos Pydantic para configuracion y capacidades
- **VanirRegistry**: Registro en runtime con heartbeats y estado persistente
- **CircuitBreaker**: Patron de resiliencia para llamadas a APIs externas
- **MuninnClient**: Cliente de memoria contextual (conecta con servicio Muninn)

### Bot Telegram (Bots_Lilith_v5)
- Bot Telegram con LilithBridge como interfaz con el engine de Asgard
- Incluye: retry manager, signal handlers, heartbeat, structured logging

---

## Como Iniciar

### Bifrost Gateway Server
```bash
cd Yggdrasil/Vanaheim
pip install -r requirements.txt
python server.py                        # Default: 0.0.0.0:9000
python server.py --port 9000 --reload   # Con auto-reload (dev)
```

### Bot Telegram
```bash
cd Yggdrasil/Vanaheim
python -m Bots_Lilith_v5.telegram.bot
```

---

## Notas de Auditoria (2026-05-02)

### Problemas Identificados
1. **Agentes duplicados**: Existen archivos planos legacy (`adan_vanaheim.py`, `eva_vanaheim.py`, `odin_vanaheim.py`) junto con las versiones estructuradas (`Agents/Adan/agent.py`, etc.). Los archivos planos deberian archivarse o eliminarse.
2. **`base_agent.py` vs `Agents/Base/vanir_agent.py`**: Dos clases base de agente. `vanir_agent.py` es la version actual (Pydantic, state management); `base_agent.py` es legacy.
3. **`Bots_Lilith_v5`**: El nombre referencia al monolito Lilith v5. El bridge (`lilith_bridge.py`) apunta a `localhost:8000` (Asgard gateway).
4. **`launcher.py`**: Referencia modulos que ya no existen (`Bots.vanaheim-bot`, `Bots.bot_telegram`, etc.).
5. **`server.log`**: Archivo de log en raiz — deberia estar en `.gitignore`.
6. **`README_BIFROST.md`**: Referencia `Backend.core.bifrost_client` como import de Asgard, que puede estar desactualizado tras la descomposicion en paquetes.

### Dependencias con Otros Reinos
- **Asgard** (Lilith Engine): Motor de procesamiento de lenguaje, Bifrost client
- **Niflheim**: Modelos LLM para inferencia local (Ollama)
- **Svartalfheim**: Documentacion generada por agentes

---

## Reglas (REGLAS.md)

1. **Experimentacion controlada**: Prueba primero, escala despues
2. **Aislado de produccion**: Nada de Vanaheim corre en Lilith Core sin validacion
3. **Documentar resultados**: Que funciono, que no, por que
4. **Migrar cuando este listo**: Agentes estables → integracion con Asgard

---

*Bifrost arde con la luz de los Nueve Mundos.*

*Última actualización: 2026-05-19*
