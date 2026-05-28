---
title: Debug de Problemas Comunes
category: runbook
severity: operational
last_updated: 2026-05-02
---

# 🔍 Runbook: Debug de Problemas Comunes

> *Las Norns desenredan los hilos del destino — diagnóstica el caos paso a paso.*

## 🏗️ Diagnóstico General

### Health Check Rápido

```bash
# Verificar que el CLI arranca
python Asgard/Hermes-Lilith/main.py --health

# Verificar providers
python -c "
from Lilith.Core.llm_provider import test_all_providers
import json
result = test_all_providers()
for name, info in result.items():
    status = '✅' if info['available'] else '❌'
    print(f'{status} {name}: {info}')
"

# Verificar estado del circuit breaker
python -c "
from Lilith.Core.llm_provider import list_providers
import json
for p in list_providers():
    cb = p.get('circuit_breaker', {})
    state = cb.get('state', 'UNKNOWN')
    emoji = {'CLOSED': '✅', 'OPEN': '🚫', 'HALF_OPEN': '⚠️'}.get(state, '❓')
    print(f'{emoji} {p[\"name\"]}: circuit={state}, model={p[\"model\"]}')
"
```

---

## 🐛 Problema: "ConnectionError: Ningun provider disponible"

### Causas
1. LM Studio no está corriendo
2. API key incorrecta o faltante
3. URL del provider incorrecta
4. Circuit breaker OPEN en todos los providers

### Diagnóstico

```bash
# 1. Verificar LM Studio
curl http://localhost:1234/v1/models

# 2. Verificar config
cat ~/.lilith/config.toml

# 3. Verificar circuit breakers
python -c "
from Lilith.Core.llm_provider import list_providers
for p in list_providers():
    print(f'{p[\"name\"]}: available={p[\"available\"]}, error={p.get(\"last_error\")}')
"

# 4. Test de conexión directo
python -c "
import httpx
try:
    r = httpx.get('http://localhost:1234/v1/models', timeout=5)
    print(f'LM Studio: {r.status_code}')
except Exception as e:
    print(f'LM Studio: ERROR - {e}')
"
```

### Solución
1. Iniciar LM Studio y cargar un modelo
2. Verificar API keys en `~/.lilith/config.toml`
3. Resetear circuit breakers reiniciando Lilith

---

## 🐛 Problema: "CircuitBreakerError: Circuit breaker OPEN"

### Causas
1. 3+ fallos consecutivos en el provider
2. Provider temporalmente caído (error 5xx, timeout)
3. Rate limiting (429)

### Diagnóstico

```python
from Lilith.Core.llm_provider import list_providers
for p in list_providers():
    cb = p.get('circuit_breaker', {})
    print(f"Provider: {p['name']}")
    print(f"  State: {cb.get('state')}")
    print(f"  Failures: {cb.get('failure_count')}")
    print(f"  Last failure: {cb.get('last_failure_time')}")
    print(f"  Recovery in: {cb.get('recovery_timeout')}s")
```

### Solución
1. **Esperar**: Recovery timeout default es 60s
2. **Reset manual**:
```python
from Lilith.Core.llm_provider import get_provider
p = get_provider()
p.circuit_breaker.reset()
```
3. **Ajustar thresholds** en config.toml si ocurre frecuentemente

---

## 🐛 Problema: "ModuleNotFoundError: No module named 'Lilith'"

### Causas
1. Path de import incorrecto
2. Ejecutando desde directorio equivocado
3. Dependencias no instaladas

### Solución
```bash
# Asegurarse de estar en el directorio correcto
cd Asgard/Hermes-Lilith/

# Instalar dependencias
pip install -r requirements.txt

# O instalar en modo desarrollo
pip install -e .
```

---

## 🐛 Problema: Memoria no funciona / SQLite errors

### Causas
1. Base de datos corrompida
2. Permisos de escritura
3. Lock de SQLite (WAL mode issue)

### Diagnóstico

```bash
# Verificar integridad de la BD
python -c "
import sqlite3
conn = sqlite3.connect('memory/lilith_memory.db')
result = conn.execute('PRAGMA integrity_check').fetchone()
print(f'Integrity: {result[0]}')
print(f'Tables: {[r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type=table\").fetchall()]}')
conn.close()
"
```

### Solución
```bash
# Backup y recrear
cp memory/lilith_memory.db memory/lilith_memory.db.bak
rm memory/lilith_memory.db

# Reinicializar (se recrea automáticamente al iniciar)
python main.py
```

---

## 🐛 Problema: Skills no se activan

### Causas
1. Archivo de skill con formato incorrecto
2. `trigger_regex` con regex inválido
3. Skill con `enabled: false`

### Diagnóstico
```python
from Lilith.Core.skill_registry import get_skill_registry
from Lilith.Core.skill_parser import SkillParser

# Parsear skills y ver errores
parser = SkillParser()
for skill_file in Path("Lilith/skills").glob("*.md"):
    try:
        skill = parser.parse_file(skill_file)
        print(f"✅ {skill.name}: triggers={skill.trigger + skill.trigger_regex}")
    except Exception as e:
        print(f"❌ {skill_file}: {e}")

# Verificar registry
registry = get_skill_registry()
print(f"Skills loaded: {registry.list_skills()}")
```

### Solución
1. Verificar YAML frontmatter en cada skill
2. Validar regex con `python -c "import re; re.compile('TU_REGEX')"`
3. Verificar `enabled: true` en cada skill

---

## 🐛 Problema: Swarm agents no coordinan

### Causas
1. SwarmDatabase con lock
2. MessageBus sin subscribers
3. File locks en conflicto

### Diagnóstico
```python
from Lilith.Swarm.database import SwarmDatabase
db = SwarmDatabase()
# Verificar sesiones activas
sessions = db.get_active_sessions()
print(f"Active sessions: {len(sessions)}")
for s in sessions:
    print(f"  {s['id']}: status={s['status']}")
```

### Solución
1. Limpiar sesiones stale: `DELETE FROM swarm_sessions WHERE status='active' AND ...`
2. Verificar que MessageBus está inicializado
3. Revisar logs de conflict detection

---

## 📊 Tabla de Severidad

| Nivel | emoji | Significado | Acción |
|-------|-------|-------------|--------|
| P0 | 🔴 | Sistema caído | Investigar inmediatamente, rollback si necesario |
| P1 | 🟠 | Funcionalidad degradada | Investigar en <1h, workaround temporal |
| P2 | 🟡 | Bug no crítico | Agregar a backlog, investigar en <24h |
| P3 | 🔵 | Mejora/Feature request | Backlog normal |
