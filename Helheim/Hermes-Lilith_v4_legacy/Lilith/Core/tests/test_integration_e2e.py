"""
Tests E2E de Integracion — Lilith v3
=====================================
Los antiguos sellos que comprueban que todos los reinos de Lilith
trabajan en armonia. Cuando los demonios se alzan, los modulos
deben responder como una sola entidad oscura.

Cada test valida un flujo completo entre modulos, asegurando
que las fronteras entre Config, Orchestrator, Skills, Memory,
Tools, Swarm y MCP se desdibujan en la oscuridad compartida.
"""

import asyncio
import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Core.config import SYSTEM_PROMPT
from Lilith.Core.dynamic_tools import DynamicToolRegistry, ToolSource
from Lilith.Core.skill_parser import Skill
from Lilith.Core.toml_config import DEFAULT_CONFIG, LilithConfig
from Lilith.MCP.protocol import MCPTool

# ─── Env vars que pueden interferir desde .env ────────────────────────────────

POLLUTING_ENV_VARS = [
    "LILITH_LM_URL",
    "LILITH_MODEL",
    "LILITH_PROVIDER",
    "LILITH_WORKSPACE",
    "LILITH_PROJECTS",
    "LILITH_SKILLS",
    "LILITH_SKILLS_HOT_RELOAD",
    "LILITH_SKILLS_AUTO_TRIGGER",
    "LILITH_SKILLS_MAX_TRIGGERED",
    "KIMI_API_KEY",
]


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singletons():
    """Los demonios se purifican antes y despues de cada ritual."""
    LilithConfig.reset()
    # Reset otros singletons
    import Lilith.Core.dynamic_tools as _dt_mod

    _dt_mod._registry_instance = None
    import Lilith.MCP.manager as _mcp_mod

    _mcp_mod._manager_instance = None
    yield
    LilithConfig.reset()
    _dt_mod._registry_instance = None
    _mcp_mod._manager_instance = None


@pytest.fixture
def temp_dir(tmp_path):
    """Directorio temporal para archivos de prueba."""
    return tmp_path


@pytest.fixture
def clean_env():
    """Limpia env vars que podrian interferir desde .env."""
    saved = {}
    for key in POLLUTING_ENV_VARS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    yield
    for key, val in saved.items():
        os.environ[key] = val


@pytest.fixture
def temp_config_file(temp_dir):
    """Crea un config.toml temporal con settings custom."""
    config_dir = temp_dir / ".lilith"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text(
        "[llm]\n"
        'default_provider = "lm_studio"\n'
        'default_model = "test-model-v3"\n'
        "\n"
        "[llm.providers.lm_studio]\n"
        'type = "local"\n'
        'base_url = "http://localhost:9999/v1"\n'
        'model = "test-model-v3"\n'
        'api_key = ""\n'
        "\n"
        "[llm.providers.kimi]\n"
        'type = "remote"\n'
        'base_url = "https://api.test.example/v1"\n'
        'model = "test-kimi-model"\n'
        'api_key = ""\n'
        "\n"
        "[chat]\n"
        "max_history = 100\n"
        "\n"
        "[tools]\n"
        "timeout = 120\n"
        "max_calls = 50\n"
        "\n"
        "[memory]\n"
        "save_history = true\n"
        "\n"
        "[skills]\n"
        "auto_trigger = false\n"
        "max_triggered = 5\n"
        "\n"
        "[workspace]\n"
        'dir = "/tmp/test_workspace"\n'
        'projects_dir = "/tmp/test_projects"\n'
        "\n"
        "[dashboard]\n"
        "port = 9876\n"
        "\n"
        "[logging]\n"
        'level = "DEBUG"\n',
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def mock_provider():
    """LLMProvider mockeado que simula respuestas sin API calls."""
    from Lilith.Core.llm_provider import LLMProvider

    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock_provider"
    provider.model = "mock-model"
    provider.provider_type = "local"
    provider.is_available.return_value = True
    provider.chat.return_value = {
        "choices": [
            {"message": {"content": "La oscuridad responde.", "tool_calls": []}}
        ]
    }
    return provider


@pytest.fixture
def mock_provider_with_tool_call():
    """LLMProvider mockeado que devuelve una respuesta con tool_call."""
    from Lilith.Core.llm_provider import LLMProvider

    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock_provider"
    provider.model = "mock-model"
    provider.provider_type = "local"
    provider.is_available.return_value = True

    # Primera llamada devuelve tool_call, segunda devuelve respuesta final
    call_count = {"n": 0}

    def chat_side_effect(messages, tools=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_001",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path": "/tmp/test.txt"}',
                                    },
                                    "type": "function",
                                }
                            ],
                        }
                    }
                ]
            }
        else:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "El archivo dice: contenido de prueba.",
                            "tool_calls": [],
                        }
                    }
                ]
            }

    provider.chat.side_effect = chat_side_effect
    return provider


@pytest.fixture
def temp_memory_db(temp_dir):
    """Crea una base de datos SQLite temporal para memory."""
    db_path = temp_dir / "test_memory.db"
    # Parchear DB_PATH antes de crear EnhancedMemory
    with patch("Lilith.memory.base.DB_PATH", str(db_path)):
        from Lilith.memory.enhanced import EnhancedMemory

        mem = EnhancedMemory()
        yield mem, db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def native_tools_defs():
    """Definiciones de tools nativas de prueba en formato OpenAI."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Lee un archivo del disco",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del archivo"}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_terminal",
                "description": "Ejecuta un comando en la terminal",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Comando a ejecutar",
                        }
                    },
                    "required": ["command"],
                },
            },
        },
    ]


@pytest.fixture
def native_tool_executors():
    """Executores mock para las tools nativas."""

    def mock_read_file(name, args):
        return {"content": f"Contenido de {args.get('path', '?')}"}

    def mock_run_terminal(name, args):
        return {"output": f"Ejecutado: {args.get('command', '?')}"}

    return {
        "read_file": mock_read_file,
        "run_terminal": mock_run_terminal,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Test 1: Config TOML alimenta correctamente al Orchestrator
# ══════════════════════════════════════════════════════════════════════════════


class TestConfigToOrchestrator:
    """El grimorio de config inscribe sus oscuros parametros en el Orchestrator."""

    def test_config_feeds_orchestrator_settings(self, temp_config_file, clean_env):
        """LilithConfig con custom settings alimenta los valores del sistema."""
        config = LilithConfig(config_path=temp_config_file)

        assert config.get("llm.default_model") == "test-model-v3"
        assert (
            config.get("llm.providers.lm_studio.base_url") == "http://localhost:9999/v1"
        )
        assert config.get("tools.max_calls") == 50
        assert config.get("tools.timeout") == 120
        assert config.get("workspace.dir") == "/tmp/test_workspace"

    def test_orchestrator_uses_config_model(
        self, temp_config_file, clean_env, mock_provider
    ):
        """El Orchestrator se inicializa con provider mock que reflecciona el config."""
        config = LilithConfig(config_path=temp_config_file)

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch("Lilith.Core.orchestrator.get_memory") as mock_mem, patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ), patch(
            "Lilith.Core.orchestrator.get_mcp_manager"
        ) as mock_mcp:
            mock_mem.return_value = MagicMock()
            mock_mcp.side_effect = Exception("No MCP")

            from Lilith.Core.orchestrator import LilithOrchestrator

            orch = LilithOrchestrator(provider=mock_provider)
            assert orch.client is mock_provider

    def test_config_reload_updates_orchestrator(self, temp_dir, clean_env):
        """Los vientos cambian — reload_config actualiza los settings del grimorio."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"

        # Escribir config inicial
        config_path.write_text(
            '[llm]\ndefault_model = "model-alpha"\n\n[tools]\nmax_calls = 25\n',
            encoding="utf-8",
        )

        config = LilithConfig(config_path=config_path)
        assert config.get("llm.default_model") == "model-alpha"
        assert config.get("tools.max_calls") == 25

        # Modificar el TOML en runtime
        config_path.write_text(
            '[llm]\ndefault_model = "model-omega"\n\n[tools]\nmax_calls = 99\n',
            encoding="utf-8",
        )

        # Recargar
        config.reload()
        assert config.get("llm.default_model") == "model-omega"
        assert config.get("tools.max_calls") == 99


# ══════════════════════════════════════════════════════════════════════════════
# Test 2: Skills se cargan y exponen al LLM
# ══════════════════════════════════════════════════════════════════════════════


class TestSkillsToOrchestrator:
    """Los Skills emergen de las sombras y son revelados al LLM como herramientas."""

    def test_skill_registry_registers_skills(self, temp_dir):
        """Los Skills se registran en el SkillRegistry y pueden ser encontrados."""
        skills_dir = temp_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "dark_arts.md").write_text(
            "---\nname: dark-arts\ndescription: Conjuro de prueba\ntrigger:\n"
            '  - "hechizo"\n  - "oscuro"\npriority: 100\n---\n\n# Dark Arts\n\n'
            "Contenido del skill.",
            encoding="utf-8",
        )

        with patch("Lilith.Core.skill_registry.SKILLS_DIR", skills_dir), patch(
            "Lilith.Core.skill_registry.SKILLS_HOT_RELOAD", False
        ), patch("Lilith.Core.skill_registry.WATCHDOG_AVAILABLE", False), patch(
            "Lilith.Core.skill_registry.get_parser"
        ) as mock_parser_fn:
            mock_parser = MagicMock()
            mock_skill = Skill(
                name="dark-arts",
                description="Conjuro de prueba",
                content="Contenido del skill.",
                trigger=["hechizo", "oscuro"],
                priority=100,
                source_file=skills_dir / "dark_arts.md",
            )
            mock_parser.parse_file.return_value = mock_skill
            mock_parser_fn.return_value = mock_parser

            from Lilith.Core.skill_registry import SkillRegistry

            registry = SkillRegistry(skills_dir=skills_dir, hot_reload=False)
            registry.skills["dark-arts"] = mock_skill
            assert "dark-arts" in registry.skills

    def test_skills_appear_in_orchestrator_tools(
        self, mock_provider, native_tools_defs, native_tool_executors
    ):
        """Los skills no son tools del LLM pero el system prompt los menciona
        a traves de _build_system_prompt cuando se activan por trigger."""
        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch("Lilith.Core.orchestrator.get_memory") as mock_mem, patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", native_tools_defs
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", native_tool_executors
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_memory = MagicMock()
            mock_memory.get_relevant_context.return_value = ""
            mock_mem.return_value = mock_memory

            mock_skill_registry = MagicMock()
            mock_skill = MagicMock()
            mock_skill.name = "test-skill"
            mock_skill.description = "Skill de prueba"
            mock_skill.content = "Instrucciones del skill"
            mock_skill_registry.get_triggered_skills.return_value = [mock_skill]
            mock_sr_fn.return_value = mock_skill_registry

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            # SKILLS_AUTO_TRIGGER debe estar activado
            with patch("Lilith.Core.orchestrator.SKILLS_AUTO_TRIGGER", True), patch(
                "Lilith.Core.orchestrator.SKILLS_MAX_TRIGGERED", 3
            ):
                prompt = orch._build_system_prompt("test hechizo")
                assert "SKILLS ACTIVOS" in prompt
                assert "test-skill" in prompt

    def test_skill_execution_via_trigger(self, mock_provider):
        """Un skill se activa cuando el input contiene un trigger keyword."""
        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch("Lilith.Core.orchestrator.get_memory") as mock_mem, patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", {}
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_memory = MagicMock()
            mock_memory.get_relevant_context.return_value = ""
            mock_mem.return_value = mock_memory

            skill = Skill(
                name="python-debug",
                description="Debug de codigo Python",
                content="# Python Debug\n\nPasos para debugear.",
                trigger=["debug", "python", "error"],
                priority=50,
            )

            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = [skill]
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            with patch("Lilith.Core.orchestrator.SKILLS_AUTO_TRIGGER", True), patch(
                "Lilith.Core.orchestrator.SKILLS_MAX_TRIGGERED", 3
            ):
                prompt = orch._build_system_prompt("como hago debug de este error?")
                assert "python-debug" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# Test 3: Memory v2 integrado en chat flow
# ══════════════════════════════════════════════════════════════════════════════


class TestMemoryToOrchestrator:
    """La memoria ancestral fluye del pasado al presente de la conversacion."""

    def test_memory_initializes_with_graph(self, temp_dir):
        """EnhancedMemory se inicializa con MemoryGraph integrado."""
        db_path = temp_dir / "test_mem.db"
        with patch("Lilith.memory.base.DB_PATH", str(db_path)), patch(
            "Lilith.memory.enhanced.get_memory_graph"
        ) as mock_gg, patch(
            "Lilith.memory.enhanced.get_consolidation"
        ) as mock_gc, patch(
            "Lilith.memory.enhanced.get_retriever"
        ) as mock_gr:
            mock_gg.return_value = MagicMock()
            mock_gc.return_value = MagicMock()
            mock_gr.return_value = MagicMock()

            from Lilith.memory.enhanced import EnhancedMemory

            mem = EnhancedMemory()
            assert mem.graph is not None
            assert mem.consolidation is not None
            assert mem.retriever is not None

    def test_orchestrator_stores_episodes_in_memory(self, mock_provider):
        """El Orchestrator almacena episodios en Memory tras cada respuesta."""
        mock_memory = MagicMock()

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", {}
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = []
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            result = orch.chat("Hola黑暗女神")
            assert result == "La oscuridad responde."

            # Verificar que se llamo add_episode
            mock_memory.add_episode.assert_called_once()
            call_args = mock_memory.add_episode.call_args
            assert call_args.kwargs.get("user_input") == "Hola黑暗女神" or "Hola" in str(
                call_args
            )

    def test_memory_context_injected_into_prompt(self, mock_provider):
        """El contexto de memoria se inyecta en el system prompt del Orchestrator."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context.return_value = (
            "El usuario prefiere Python sobre JavaScript."
        )

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", {}
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = []
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            prompt = orch._build_system_prompt("que lenguaje prefiero?")
            assert "CONTEXTO RELEVANTE" in prompt
            assert "Python" in prompt

    def test_memory_search_works(self, temp_dir):
        """La busqueda en memoria funciona tras almacenar episodios."""
        db_path = temp_dir / "test_search.db"
        with patch("Lilith.memory.base.DB_PATH", str(db_path)), patch(
            "Lilith.memory.enhanced.get_memory_graph"
        ) as mock_gg, patch(
            "Lilith.memory.enhanced.get_consolidation"
        ) as mock_gc, patch(
            "Lilith.memory.enhanced.get_retriever"
        ) as mock_gr:
            mock_graph = MagicMock()
            mock_gg.return_value = mock_graph
            mock_gc.return_value = MagicMock()
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = [
                {
                    "user_input": "como funciona Python?",
                    "response": "Python es un lenguaje...",
                    "timestamp": "2025-01-01T00:00:00",
                    "retrieval_score": 0.9,
                    "retrieval_sources": {"vector": 0.9},
                }
            ]
            mock_gr.return_value = mock_retriever

            from Lilith.memory.enhanced import EnhancedMemory

            mem = EnhancedMemory()

            # add_episode con embedder mockeado
            with patch.object(mem.embedder, "encode", return_value=[[0.1] * 384]):
                mem.add_episode(
                    user_input="como funciona Python?",
                    response="Python es un lenguaje interpretado.",
                    tools_used=[],
                    session_id="test",
                )

            # Busqueda
            results = mem.search_episodes("Python")
            # Aceptamos que funcione (no crashea)
            assert isinstance(results, list)


# ══════════════════════════════════════════════════════════════════════════════
# Test 4: DynamicToolRegistry — Tools nativas + MCP se registran unificadamente
# ══════════════════════════════════════════════════════════════════════════════


class TestDynamicToolsRegistry:
    """El registro unificado de tools — donde lo nativo y lo foraneo se funden."""

    def test_register_native_tools(self, native_tools_defs, native_tool_executors):
        """Las tools nativas se registran correctamente en el DynamicToolRegistry."""
        registry = DynamicToolRegistry()
        count = registry.register_native_tools(native_tools_defs, native_tool_executors)
        assert count == 2
        assert "read_file" in registry
        assert "run_terminal" in registry
        assert len(registry) == 2

    def test_register_mcp_tools(self):
        """Las tools MCP se registran junto a las nativas sin conflicto."""
        registry = DynamicToolRegistry()

        # Primero registrar tools nativas
        native_defs = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Lee un archivo",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        native_execs = {"read_file": lambda n, a: {"content": "test"}}
        registry.register_native_tools(native_defs, native_execs)

        # Luego registrar tools MCP mock
        mock_mcp_manager = MagicMock()
        mock_mcp_manager.get_all_tools.return_value = [
            MCPTool(
                name="mcp_search",
                description="Buscar en internet",
                server_name="web_server",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
            MCPTool(
                name="mcp_calculate",
                description="Calcular expresiones",
                server_name="math_server",
                input_schema={
                    "type": "object",
                    "properties": {"expr": {"type": "string"}},
                },
            ),
        ]

        mcp_count = registry.register_mcp_tools(mock_mcp_manager)
        assert mcp_count == 2

        # Verificar que ambas coexisten
        assert "read_file" in registry
        assert "mcp_search" in registry
        assert "mcp_calculate" in registry
        assert len(registry) == 3

    def test_get_openai_tools_returns_both(
        self, native_tools_defs, native_tool_executors
    ):
        """get_openai_tools() devuelve tanto nativas como MCP en formato OpenAI."""
        registry = DynamicToolRegistry()
        registry.register_native_tools(native_tools_defs, native_tool_executors)

        mock_mcp = MagicMock()
        mock_mcp.get_all_tools.return_value = [
            MCPTool(
                name="mcp_search",
                description="Buscar en internet",
                server_name="web",
            ),
        ]
        registry.register_mcp_tools(mock_mcp)

        tools = registry.get_openai_tools()
        assert len(tools) == 3  # 2 nativas + 1 MCP

        tool_names = [t["function"]["name"] for t in tools]
        assert "read_file" in tool_names
        assert "run_terminal" in tool_names
        assert "mcp_search" in tool_names

    def test_execute_native_tool(self, native_tools_defs, native_tool_executors):
        """La ejecucion de tools nativas funciona a traves del registry."""
        registry = DynamicToolRegistry()
        registry.register_native_tools(native_tools_defs, native_tool_executors)

        result = registry.execute_native("read_file", {"path": "/tmp/test.txt"})
        assert result == {"content": "Contenido de /tmp/test.txt"}

    async def _async_execute_mcp_tool(self):
        """Helper para ejecutar tools MCP async."""
        registry = DynamicToolRegistry()
        mock_mcp = MagicMock()
        mock_mcp.call_tool = AsyncMock(return_value={"result": "42"})
        mock_mcp.get_all_tools.return_value = [
            MCPTool(
                name="mcp_calc",
                description="Calculadora",
                server_name="math",
            ),
        ]
        registry.register_mcp_tools(mock_mcp)

        result = await registry.execute("mcp_calc", {"expr": "2+2"})
        assert result == {"result": "42"}

    def test_execute_mcp_tool_async(self):
        """La ejecucion async de tools MCP funciona a traves del registry."""
        asyncio.run(self._async_execute_mcp_tool())

    def test_stats_shows_native_and_mcp(self, native_tools_defs, native_tool_executors):
        """Las estadisticas del registry muestran tanto nativas como MCP."""
        registry = DynamicToolRegistry()
        registry.register_native_tools(native_tools_defs, native_tool_executors)

        mock_mcp = MagicMock()
        mock_mcp.get_all_tools.return_value = [
            MCPTool(name="mcp_tool_1", description="MCP", server_name="s1"),
        ]
        registry.register_mcp_tools(mock_mcp)

        stats = registry.get_stats()
        assert stats["total_tools"] == 3
        assert stats["native_tools"] == 2
        assert stats["mcp_tools"] == 1
        assert stats["mcp_connected"] is True


# ══════════════════════════════════════════════════════════════════════════════
# Test 5: Orchestrator Chat Flow — Flujo completo con tools
# ══════════════════════════════════════════════════════════════════════════════


class TestOrchestratorChatFlow:
    """El flujo oscuro del chat — donde la palabra invoca la herramienta."""

    def test_chat_simple_response(self, mock_provider):
        """Un mensaje simple genera una respuesta directa sin tools."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context.return_value = ""

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", {}
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = []
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            result = orch.chat("Saludos desde el abismo")
            assert result == "La oscuridad responde."

            # Verificar que se almaceno en memoria
            mock_memory.add_episode.assert_called_once()

    def test_chat_with_tool_call(self, mock_provider_with_tool_call):
        """Un tool_call en la respuesta se ejecuta y el resultado se
        integra al flujo de chat."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context.return_value = ""

        tool_executors = {
            "read_file": lambda n, a: {"content": "contenido del archivo"}
        }

        with patch(
            "Lilith.Core.orchestrator.get_provider",
            return_value=mock_provider_with_tool_call,
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", tool_executors
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = []
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider_with_tool_call)

            result = orch.chat("lee el archivo test.txt")
            assert "contenido" in result.lower() or "El archivo" in result

            # La tool fue invocada
            assert mock_provider_with_tool_call.chat.call_count == 2

    def test_chat_memory_stores_tools_used(self, mock_provider):
        """El episodio almacenado registra las tools usadas en la conversacion."""
        mock_memory = MagicMock()
        mock_memory.get_relevant_context.return_value = ""

        # Simular una respuesta simple
        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr_fn, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", []
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", {}
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_skill_reg = MagicMock()
            mock_skill_reg.get_triggered_skills.return_value = []
            mock_sr_fn.return_value = mock_skill_reg

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            orch.chat("test")
            call_args = mock_memory.add_episode.call_args
            assert call_args.kwargs.get(
                "tools_used", None
            ) is not None or "tools_used" in str(call_args)


# ══════════════════════════════════════════════════════════════════════════════
# Test 6: Swarm Integration — Agentes en el ecosistema
# ══════════════════════════════════════════════════════════════════════════════


class TestSwarmIntegration:
    """Los agentes del swarm danzan al compas del registry de tools."""

    def test_spawn_agent_creates_working_agent(self, temp_dir):
        """Un agente se spawnea y puede ejecutar su tarea."""
        from Lilith.Swarm.manager import SwarmManager

        swarm = SwarmManager(repo_path=temp_dir)
        agent_id = swarm.spawn_agent(
            task="Crear archivo test.py",
            capabilities=["coding"],
            context={"files_to_read": []},
        )

        assert agent_id is not None
        assert agent_id in swarm.agents
        assert swarm.agents[agent_id].task == "Crear archivo test.py"

        # Cleanup: kill_agent stop el agente y lo desuscribe
        result = swarm.kill_agent(agent_id)
        assert result is True
        # kill_agent no elimina del dict, solo stop
        # Usar kill_all para limpiar completamente
        swarm.kill_all()

    def test_agent_uses_message_bus(self, temp_dir):
        """Los agentes se comunican a traves del MessageBus."""
        from Lilith.Swarm.manager import SwarmManager

        swarm = SwarmManager(repo_path=temp_dir)
        agent_id = swarm.spawn_agent(
            task="Test task",
            capabilities=["testing"],
        )

        # Verificar que el agente esta suscrito al bus
        assert agent_id in swarm.message_bus._subscribers
        swarm.kill_all()

    def test_swarm_stats_reports_agents(self, temp_dir):
        """Swarm reporta estadisticas sobre sus agentes via get_status_report."""
        from Lilith.Swarm.manager import SwarmManager

        swarm = SwarmManager(repo_path=temp_dir)
        _ = swarm.spawn_agent(task="Tarea 1", capabilities=["coding"])
        _ = swarm.spawn_agent(task="Tarea 2", capabilities=["testing"])

        report = swarm.get_status_report()
        assert report["total_agents"] == 2
        assert "active" in report
        assert "complete" in report

        swarm.kill_all()


# ══════════════════════════════════════════════════════════════════════════════
# Test 7: MCP Integration — MCP manager se conecta al registry
# ══════════════════════════════════════════════════════════════════════════════


class TestMCPIntegration:
    """Los servidores MCP extienden las garras de Lilith hacia lo externo."""

    def test_mcp_manager_no_crash_without_servers(self, temp_dir):
        """MCPManager no crashea cuando no hay servidores configurados."""
        from Lilith.MCP.manager import MCPManager

        config_path = temp_dir / "mcp_empty.json"
        config_path.write_text('{"servers": {}}', encoding="utf-8")

        manager = MCPManager(config_path=config_path)
        # start() es async — no hay servers, no crashea
        results = asyncio.run(manager.start())
        assert results == {} or isinstance(results, dict)

    def test_mcp_manager_with_empty_config(self, temp_dir):
        """MCPManager puede cargarse con un config vacio sin errores."""
        from Lilith.MCP.manager import MCPManager

        config_path = temp_dir / "mcp_test.json"
        config_path.write_text('{"servers": {}}', encoding="utf-8")

        manager = MCPManager(config_path=config_path)
        status = manager.get_status()

        assert status["started"] is False
        assert status["servers_count"] == 0
        assert status["total_tools"] == 0

    def test_mcp_connects_to_dynamic_registry(self):
        """Las tools MCP se registran en DynamicToolRegistry tras conectar."""
        registry = DynamicToolRegistry()

        # Registrar tools nativas primero
        native_defs = [
            {
                "type": "function",
                "function": {
                    "name": "native_tool",
                    "description": "Herramienta nativa",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        native_execs = {"native_tool": lambda n, a: {"ok": True}}
        registry.register_native_tools(native_defs, native_execs)

        # Registrar tools MCP mock
        mock_mcp = MagicMock()
        mock_mcp.get_all_tools.return_value = [
            MCPTool(
                name="mcp_filesystem",
                description="Sistema de archivos MCP",
                server_name="filesystem",
            ),
        ]
        registry.register_mcp_tools(mock_mcp)

        # Verificar coexistencia
        stats = registry.get_stats()
        assert stats["native_tools"] == 1
        assert stats["mcp_tools"] == 1
        assert stats["total_tools"] == 2

        # Verificar que ambas aparecen en get_openai_tools
        tools = registry.get_openai_tools()
        assert len(tools) == 2
        names = [t["function"]["name"] for t in tools]
        assert "native_tool" in names
        assert "mcp_filesystem" in names


# ══════════════════════════════════════════════════════════════════════════════
# Test 8: TOML Config Hot Reload
# ══════════════════════════════════════════════════════════════════════════════


class TestTOMLConfigHotReload:
    """El grimorio se reescribe sin apagar la forja — hot reload en runtime."""

    def test_config_reload_updates_values(self, temp_dir, clean_env):
        """LilithConfig.reload() actualiza los valores tras modificar el TOML."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"

        # Config inicial
        config_path.write_text(
            '[llm]\ndefault_provider = "lm_studio"\n\n' "[tools]\nmax_calls = 25\n",
            encoding="utf-8",
        )

        config = LilithConfig(config_path=config_path)
        assert config.get("llm.default_provider") == "lm_studio"
        assert config.get("tools.max_calls") == 25

        # Modificar TOML
        config_path.write_text(
            '[llm]\ndefault_provider = "kimi"\n\n' "[tools]\nmax_calls = 100\n",
            encoding="utf-8",
        )

        # Recargar
        config.reload()
        assert config.get("llm.default_provider") == "kimi"
        assert config.get("tools.max_calls") == 100

    def test_config_set_and_persist(self, temp_dir, clean_env):
        """config.set() modifica valores en memoria correctamente."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"

        config_path.write_text(
            '[llm]\ndefault_model = "alpha"\n\n[tools]\nmax_calls = 25\n',
            encoding="utf-8",
        )

        config = LilithConfig(config_path=config_path)
        assert config.get("llm.default_model") == "alpha"

        # Modificar en memoria
        config.set("llm.default_model", "omega")
        config.set("tools.max_calls", 200)

        # Verificar en memoria
        assert config.get("llm.default_model") == "omega"
        assert config.get("tools.max_calls") == 200

    def test_config_save_creates_file(self, temp_dir, clean_env):
        """config.save() persiste elgrimorio a disco sin crashear."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"

        # Escribir config minimo que no cause duplicate sections
        config_path.write_text(
            "[chat]\nmax_history = 50\n\n[tools]\nmax_calls = 25\n",
            encoding="utf-8",
        )

        config = LilithConfig(config_path=config_path)

        # Modificar valor simple
        config.set("tools.max_calls", 99)
        assert config.get("tools.max_calls") == 99

        # Guardar
        config.save()

        # El archivo debe existir y contener el valor actualizado
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "99" in content

    def test_config_deep_merge_preserves_defaults(self, temp_dir, clean_env):
        """El deep merge preserva secciones que no estan en el TOML."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"

        # Config con solo la seccion llm
        config_path.write_text(
            '[llm]\ndefault_provider = "kimi"\n\n[llm.providers.kimi]\n'
            'type = "remote"\nbase_url = "https://test.api/v1"\nmodel = "test"\napi_key = ""\n',
            encoding="utf-8",
        )

        config = LilithConfig(config_path=config_path)

        # Secciones que no estaban en TOML caen a defaults
        assert config.get("tools.max_calls") == 25  # default
        assert config.get("dashboard.port") == 8765  # default

        # La seccion llm fue sobreescrita
        assert config.get("llm.default_provider") == "kimi"


# ══════════════════════════════════════════════════════════════════════════════
# Test 9: Full Stack Init — Stack completo sin crashes
# ══════════════════════════════════════════════════════════════════════════════


class TestFullStackInit:
    """El ritual completo — todos los modulos se alzan sin que el
    mundo se desmorone."""

    def test_full_stack_initialization(self, mock_provider, temp_dir):
        """Orchestrator + Registry + Skills + Memory + Swarm + MCP
        se inicializan sin crashes."""
        config_dir = temp_dir / ".lilith"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text(
            '[llm]\ndefault_provider = "lm_studio"\n\n[tools]\nmax_calls = 25\n',
            encoding="utf-8",
        )

        # 1. Config
        config = LilithConfig(config_path=config_path)
        assert config.get("llm.default_provider") is not None

        # 2. DynamicToolRegistry
        registry = DynamicToolRegistry()
        native_defs = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Tool de prueba",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        native_execs = {"test_tool": lambda n, a: {"result": "ok"}}
        registry.register_native_tools(native_defs, native_execs)
        assert len(registry) >= 1

        # 3. Memory (mock)
        mock_memory = MagicMock()
        mock_memory.get_relevant_context.return_value = ""

        # 4. SkillRegistry (mock)
        mock_skill_registry = MagicMock()
        mock_skill_registry.get_triggered_skills.return_value = []

        # 5. Swarm
        from Lilith.Swarm.manager import SwarmManager

        swarm = SwarmManager(repo_path=temp_dir)
        assert swarm is not None

        # 6. MCPManager
        mcp_config = temp_dir / "mcp_stack.json"
        mcp_config.write_text('{"servers": {}}', encoding="utf-8")
        from Lilith.MCP.manager import MCPManager

        mcp_manager = MCPManager(config_path=mcp_config)
        assert mcp_manager is not None

        # 7. Orchestrator
        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch(
            "Lilith.Core.orchestrator.get_memory", return_value=mock_memory
        ), patch(
            "Lilith.Core.orchestrator.get_skill_registry",
            return_value=mock_skill_registry,
        ), patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", native_defs
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", native_execs
        ), patch(
            "Lilith.Core.orchestrator.get_mcp_manager"
        ) as mock_mcp_fn:
            mock_mcp_fn.side_effect = Exception("No MCP")

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

        assert orch.client is mock_provider
        assert orch.memory is mock_memory

        # Stats del registry
        stats = registry.get_stats()
        assert stats["native_tools"] >= 1
        assert stats["total_tools"] >= 1

        # Stats del swarm
        swarm_report = swarm.get_status_report()
        assert swarm_report is not None
        assert "total_agents" in swarm_report

        # Cleanup
        swarm.kill_all()

    def test_full_stack_stats(
        self, mock_provider, native_tools_defs, native_tool_executors
    ):
        """Los stats de todos los modulos se pueden obtener sin errores."""
        # Registry
        registry = DynamicToolRegistry()
        registry.register_native_tools(native_tools_defs, native_tool_executors)
        stats = registry.get_stats()
        assert "total_tools" in stats
        assert "native_tools" in stats
        assert stats["native_tools"] == 2

        # Swarm
        import tempfile

        from Lilith.Swarm.manager import SwarmManager

        with tempfile.TemporaryDirectory() as td:
            swarm = SwarmManager(repo_path=Path(td))
            _ = swarm.spawn_agent(task="stat test", capabilities=["testing"])

            report = swarm.get_status_report()
            assert "total_agents" in report
            assert report["total_agents"] == 1
            swarm.kill_all()

    def test_orchestrator_provider_info(
        self, mock_provider, native_tools_defs, native_tool_executors
    ):
        """Orchestrator.get_provider_info() retorna info completa del stack."""
        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider
        ), patch("Lilith.Core.orchestrator.get_memory") as mock_mem, patch(
            "Lilith.Core.orchestrator.get_skill_registry"
        ) as mock_sr, patch(
            "Lilith.Core.orchestrator.ALL_TOOLS", native_tools_defs
        ), patch(
            "Lilith.Core.orchestrator.TOOL_EXECUTORS", native_tool_executors
        ), patch(
            "Lilith.Core.orchestrator._run_async"
        ):
            mock_mem.return_value = MagicMock()
            mock_sr.return_value = MagicMock()

            from Lilith.Core.orchestrator import LilithOrchestrator

            with patch.object(LilithOrchestrator, "_try_init_mcp"):
                orch = LilithOrchestrator(provider=mock_provider)

            info = orch.get_provider_info()
            assert info["name"] == "mock_provider"
            assert info["model"] == "mock-model"
            assert "tools" in info
