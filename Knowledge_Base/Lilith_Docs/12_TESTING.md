# 12 - Sistema de Testing

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/12_TESTING.md`

---

## 12.1 Visión General

La suite de tests de Lilith garantiza la robustez del sistema a través de múltiples niveles de verificación, desde tests unitarios hasta tests E2E con orquestador real.

### Estadísticas Actuales

| Métrica | Valor |
|---------|-------|
| **Tests Pasados** | 143 |
| **Tests Fallidos** | 0 |
| **Tests Skipped** | 14 (documentados) |
| **Cobertura** | Core systems, tools, integración |

### Comandos de Ejecución

```bash
# Ejecutar suite completa (resumen)
python -m pytest Core/Tests/ --tb=no -q

# Con detalle y traceback corto
python -m pytest Core/Tests/ -v --tb=short

# Tests específicos
python -m pytest Core/Tests/test_planning_engine.py -v
python -m pytest Core/Tests/test_health_checks.py -v

# Tests con marca específica
python -m pytest Core/Tests/ -m "not slow" -v
```

---

## 12.2 Estructura de Tests

### Organización de Carpetas

```
Core/Tests/
├── conftest.py                    # Fixtures compartidos
├── harness.py                     # Utilidades de test
├── test_*.py                      # Tests por módulo
├── fases/
│   ├── test_fase_e.py            # Tests manuales de endpoints
│   ├── test_auto_workflow.py     # Tests de workflow automático
│   └── ...
└── integration/
    └── test_integration.py       # Tests E2E
```

### Categorías de Tests

| Categoría | Archivos | Descripción |
|-----------|----------|-------------|
| **Unitarios** | `test_model_selector.py`, `test_rate_limiting_v2.py` | Componentes aislados |
| **Integración** | `test_integration.py`, `test_plugin_system.py` | Flujos completos |
| **Planning** | `test_planning_engine.py`, `test_enhanced_planning.py` | Orquestador y planner |
| **Memoria** | `test_attention_stack.py`, `test_personality_modes.py` | Sistemas de memoria |
| **Agentes** | `test_crystal_openrouter.py`, `test_public_sandbox.py` | Agentes del Panteón |
| **E2E** | `test_pc_agent_macros.py` | Flujos end-to-end |

---

## 12.3 Fixtures y Configuración

### conftest.py - Configuración Global

```python
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """
    Event loop compartido para tests async.
    Compatible con pytest-asyncio >= 0.21 (modo strict).
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_memory_dir(tmp_path):
    """Directorio temporal para memoria de tests."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    return str(memory_dir)

@pytest.fixture
def mock_orchestrator():
    """Mock del orquestador para tests unitarios."""
    from unittest.mock import MagicMock
    orch = MagicMock()
    orch.execute_plan.return_value = {
        "status": "success",
        "result": "mocked result"
    }
    return orch
```

### Decoradores Comunes

```python
# Tests asíncronos
@pytest.mark.asyncio
async def test_async_function():
    result = await async_tool.execute()
    assert result is not None

# Tests lentos (excluibles)
@pytest.mark.slow
async def test_heavy_integration():
    ...

# Skip con razón documentada
@pytest.mark.skip(
    reason="Gemini reemplazado por Kimi en v2.0",
    allow_module_level=True
)
```

---

## 12.4 Patrones de Testing

### 1. Tests de Planning Engine

```python
# test_planning_engine.py
class TestPlanningEngine:
    """Tests del motor de planificación."""
    
    def setup_method(self):
        """Setup antes de cada test."""
        from Backend.core.planner import Planner
        self.planner = Planner()
    
    def test_intent_detection_read_file(self):
        """Detecta correctamente intención de lectura."""
        message = "lee el archivo Backend/core/planner.py"
        
        intent_result = self.planner.detect_intent(message)
        
        assert intent_result.intent == "read_file"
        assert "path" in intent_result.params
    
    def test_learned_plan_recognition(self):
        """Reconoce planes aprendidos previos."""
        message = "investiga sobre FastAPI"
        
        # Asumiendo que existe un plan aprendido para "investiga"
        plan = self.planner.plan(message, context={})
        
        assert plan.decision_source == "learned_plan"
        assert len(plan.steps) > 0
```

### 2. Tests de Memoria

```python
# test_attention_stack.py
class TestAttentionStack:
    """Tests del stack de atención."""
    
    def test_push_and_get_active(self, temp_memory_dir):
        """Añade tareas y recupera activas."""
        from Backend.core.attention_stack import AttentionStack
        
        stack = AttentionStack(session_id="test_123", base_path=temp_memory_dir)
        
        # Añadir tareas
        item1 = stack.push("Refactorizar módulo X", priority=5)
        item2 = stack.push("Crear tests", priority=3, dependencies=[item1.id])
        
        # Verificar activas
        active = stack.get_active()
        assert len(active) == 2
        assert active[0].priority == 5  # Ordenadas por prioridad
    
    def test_complete_task(self, temp_memory_dir):
        """Marca tarea como completada."""
        stack = AttentionStack(session_id="test_123", base_path=temp_memory_dir)
        
        item = stack.push("Tarea de prueba")
        stack.complete(item.id)
        
        active = stack.get_active()
        assert len(active) == 0
        
        completed = stack.get_completed()
        assert len(completed) == 1
```

### 3. Tests de Agentes

```python
# test_crystal_openrouter.py
@pytest.mark.asyncio
class TestCrystalOpenRouter:
    """Tests del agente Crystal (OpenRouter proxy)."""
    
    async def test_public_mode_sandboxing(self):
        """Verifica sandboxing en modo público."""
        from Backend.agents.crystal_agent import CrystalAgent
        
        agent = CrystalAgent(mode="public")
        
        # En modo público, ciertas tools deben estar bloqueadas
        result = await agent.execute(
            task="lee archivo .env",
            context={}
        )
        
        assert result["status"] == "blocked"
        assert "permisos" in result["message"].lower()
    
    async def test_routing_by_complexity(self):
        """Enruta según complejidad estimada."""
        agent = CrystalAgent(mode="trusted")
        
        # Tarea simple → modelo rápido
        simple_result = await agent.execute("confirma que recibiste esto")
        assert simple_result["model_used"] == "haiku"
        
        # Tarea compleja → modelo potente
        complex_result = await agent.execute("diseña arquitectura microservicios")
        assert complex_result["model_used"] == "opus"
```

### 4. Tests de Health Checks

```python
# test_health_checks.py
class TestHealthChecks:
    """Tests del endpoint de salud."""
    
    @pytest.fixture
    def client(self):
        """Cliente de test para FastAPI."""
        from Backend.api.main_api import app
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Endpoint /health responde correctamente."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "subsystems" in data
    
    def test_subsystem_health_muninn(self, client):
        """Verifica salud específica de Muninn."""
        response = client.get("/health/subsystem/muninn")
        
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["subsystem"] == "muninn"
        assert "latency_ms" in data
```

---

## 12.5 Tests de Integración

### Flujo Completo Discord

```python
# test_integration.py
@pytest.mark.asyncio
class TestDiscordFlow:
    """Tests E2E del flujo de Discord."""
    
    async def test_owner_full_orchestrator(self):
        """Owner puede usar orquestador completo."""
        from Backend.api.discord_api import process_message
        
        result = await process_message(
            message="lee Core/Config/settings.json",
            user_id="12345",
            role="OWNER"
        )
        
        assert result["status"] == "success"
        assert "content" in result
        assert result["tool_used"] == "read_file"
    
    async def test_trusted_limited_registry(self):
        """Trusted usa registro limitado."""
        result = await process_message(
            message="lee archivo secreto",
            user_id="67890",
            role="TRUSTED"
        )
        
        # Trusted no puede usar read_file directamente
        assert result["action"] == "generate_reply"
        assert "no tienes permisos" in result["response"].lower()
```

---

## 12.6 Troubleshooting Común

### Issues Resueltos (Histórico)

| Issue | Causa | Solución |
|-------|-------|----------|
| `async def` no soportado | Tests async sin decorator | Añadir `@pytest.mark.asyncio` |
| UnicodeDecodeError en Windows | Encoding por defecto cp1252 | Usar `encoding='utf-8'` explícito |
| PermissionError en Windows | `os.unlink` en archivo abierto | Usar `tmp_path` de pytest |
| Paths hardcodeados | `__file__` apuntaba a Tests/ | Usar `Path(__file__).resolve().parent.parent.parent` |
| KeyError document_count | Esquema variable en stats | Usar `.get()` con default |

### Mock del Orchestrator

```python
# Para tests que necesiten orquestador sin dependencias pesadas
@pytest.fixture
def mock_orchestrator_full():
    """Mock completo del orquestador."""
    from unittest.mock import MagicMock, patch
    
    mock = MagicMock()
    mock.execute_plan.return_value = {
        "status": "success",
        "steps_executed": 2,
        "final_result": "Success",
        "plan": {
            "steps": [
                {"tool": "read_file", "status": "success"},
                {"tool": "generate_reply", "status": "success"}
            ]
        }
    }
    
    with patch('Backend.api.discord_api._get_orchestrator', return_value=mock):
        yield mock
```

---

## 12.7 Cobertura de Código

### Generar Reporte

```bash
# Instalar coverage
pip install pytest-cov

# Ejecutar con cobertura
python -m pytest Core/Tests/ --cov=Backend --cov-report=html --cov-report=term

# Ver reporte HTML
start htmlcov/index.html
```

### Áreas Prioritarias

| Módulo | Prioridad | Estado |
|--------|-----------|--------|
| `Backend/core/planner.py` | Alta | ✅ Cubierto |
| `Backend/core/plan_executor.py` | Alta | ✅ Cubierto |
| `Backend/tools/` | Alta | ✅ Cubierto |
| `Backend/api/discord_api.py` | Media | ⚠️ Parcial |
| `Backend/agents/` | Media | ⚠️ Parcial |
| `Backend/memory/` | Media | ✅ Cubierto |

---

## 12.8 Referencias

| Recurso | Ubicación |
|---------|-----------|
| Tests Unitarios | `Core/Tests/test_*.py` |
| Tests de Fases | `Core/Tests/fases/` |
| Fixtures | `Core/Tests/conftest.py` |
| Legacy Tests | `Core/Docs/Legacy/TESTS_SUMMARY.md` |

---

*Documento 12 del índice - Sistema de Testing*
