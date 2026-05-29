# Reglas de Vanaheim - Vivero de IA

> **Proposito:** Agentes autonomos, bots de plataforma, framework de agentes y gateway Bifrost

---

## Sí Permitido
- Agentes experimentales (Panteón: Odin, Eva, Adán, Crystal, Shalltear)
- Framework de bots empaquetado (vanaheim-framework)
- Bots de Telegram/Discord con bridge a Asgard
- Nuevos agentes que hereden de VanirAgent
- Experimentos con modelos LLM (Ollama local, Kimi, Grok, Venice)

## Prohibido
- Código de producción sin tests
- APIs expuestas sin autenticación JWT
- Modelos sin documentar en agents.json
- Agentes sin health check
- Logs runtime versionados (server.log → .gitignore)

---

## Estructura
```
Vanaheim/
├── Agents/              # Agentes del Panteón (VanirAgent)
│   ├── Base/            # Clase base VanirAgent
│   ├── Adan/            # Codigo (Ollama)
│   ├── Crystal/         # Discord (Kimi)
│   ├── Eva/             # Analisis (Grok)
│   ├── Odin/            # Research (Kimi)
│   └── Shalltear/       # Triage (Venice)
├── Bots_Lilith_v5/     # Bot Telegram (bridge a Asgard)
├── bifrost/             # Gateway: FastAPI + JWT + streaming
├── Config/              # agents.json, vanir_registry.json, bifrost.json
├── Core/                # Framework: API, models, memory, registry, persona
├── vanaheim-framework/  # Paquete pip independiente
├── bots/                # Bots simples (echo, etc.)
└── server.py            # Entry point del Bifrost Gateway
```

### Limpiado (2026-05-03)

Se eliminaron archivos duplicados sueltos en `Agents/` que eran versiones antiguas de los agentes ya organizados en subdirectorios:
- `adan_vanaheim.py` → reemplazado por `Adan/agent.py`
- `eva_vanaheim.py` → reemplazado por `Eva/agent.py`
- `odin_vanaheim.py` → reemplazado por `Odin/agent.py`
- `base_agent.py` → reemplazado por `Base/vanir_agent.py`

---

## Reglas Específicas

1. **Todo agente nuevo hereda de VanirAgent**: Implementar `execute()`, `stream()`, `is_available()`, `health()`
2. **Aislado de producción**: Bifrost Gateway es la unica interfaz con Asgard. Nada de Vanaheim importa directamente desde Lilith Core
3. **Documentar resultados**: Qué funcionó, qué no, por qué
4. **Config centralizada**: Todo agente se registra en `Config/agents.json` con modelo, provider y capacidades
5. **Circuit breaker obligatorio**: Toda llamada a API externa usa el circuit breaker de Core/
6. **Migrar cuando esté listo**: Agentes estables → Midgard/integración

---

*Vivero de IA - Donde crecen los agentes*
