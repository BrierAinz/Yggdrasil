"""
Tests para LilithConfig (TOML Unified Configuration)
=====================================================
Verifica que el grimorio carga, guarda, y respeta prioridades.

Prioridad: defaults < TOML file < env vars
"""

import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys_path = str(Path(__file__).parent.parent.parent)
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

from Lilith.Core.toml_config import (
    DEFAULT_CONFIG,
    LilithConfig,
    _coerce_env_value,
    _get_nested,
    _set_nested,
    get_config,
)

# ─── Env vars que pueden interferir desde .env ────────────────────────────────
# Estas env vars se cargan desde .env y pueden interferir con los tests.
# Las listeamos aqui para limpiarlas en los tests que necesitan aislamiento.

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


# ─── Helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singleton():
    """Resetea el singleton antes y despues de cada test."""
    LilithConfig.reset()
    yield
    LilithConfig.reset()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Directorio temporal para archivos de config."""
    config_dir = tmp_path / ".lilith"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def config_path(temp_config_dir):
    """Path a un config.toml temporal."""
    return temp_config_dir / "config.toml"


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
def config(config_path, clean_env):
    """Instancia LilithConfig con path temporal y env limpio."""
    return LilithConfig(config_path=config_path)


# ─── Test: Carga desde TOML ──────────────────────────────────────────────────


class TestTOMLLoading:
    """El grimorio se lee desde el disco correctamente."""

    def test_load_default_config_creates_file(self, config_path, clean_env):
        """Si no existe config.toml, se crea el default."""
        assert not config_path.exists()
        cfg = LilithConfig(config_path=config_path)
        assert config_path.exists()
        # El archivo debe contener secciones clave
        content = config_path.read_text()
        assert "[llm]" in content
        assert "[chat]" in content

    def test_load_existing_toml(self, config_path, clean_env):
        """Se carga un config.toml existente correctamente."""
        config_path.write_text(
            '[llm]\ndefault_model = "test-model-v2"\ndefault_provider = "kimi"\n',
            encoding="utf-8",
        )
        cfg = LilithConfig(config_path=config_path)
        assert cfg.get("llm.default_model") == "test-model-v2"
        assert cfg.get("llm.default_provider") == "kimi"

    def test_deep_merge_with_defaults(self, config_path, clean_env):
        """TOML merge profundamente con defaults — valores parciales."""
        config_path.write_text(
            '[llm]\ndefault_model = "custom-model"\n[chat]\nmax_history = 100\n',
            encoding="utf-8",
        )
        cfg = LilithConfig(config_path=config_path)
        # Valores custom del TOML
        assert cfg.get("llm.default_model") == "custom-model"
        assert cfg.get("chat.max_history") == 100
        # Defaults se preservan donde no hay override
        assert cfg.get("llm.default_provider") == "auto"
        assert cfg.get("tools.timeout") == 60

    def test_providers_from_toml(self, config_path, clean_env):
        """Providers se cargan desde TOML."""
        config_path.write_text(
            "[llm.providers.lm_studio]\n"
            'type = "local"\n'
            'base_url = "http://192.168.1.100:1234/v1"\n'
            'model = "custom-model"\n'
            'api_key = ""\n',
            encoding="utf-8",
        )
        cfg = LilithConfig(config_path=config_path)
        assert (
            cfg.get("llm.providers.lm_studio.base_url")
            == "http://192.168.1.100:1234/v1"
        )
        assert cfg.get("llm.providers.lm_studio.model") == "custom-model"


# ─── Test: Env vars override ──────────────────────────────────────────────────


class TestEnvOverride:
    """Los susurros del mas alla (env vars) pisan al grimorio."""

    def test_env_var_overrides_toml(self, config_path, clean_env):
        """LILITH_MODEL pisa el valor del TOML."""
        config_path.write_text(
            '[llm]\ndefault_model = "toml-model"\n',
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"LILITH_MODEL": "env-model"}):
            cfg = LilithConfig(config_path=config_path)
            assert cfg.get("llm.default_model") == "env-model"

    def test_env_var_overrides_default(self, config_path, clean_env):
        """LILITH_LM_URL pisa el default cuando no hay TOML override."""
        with patch.dict(os.environ, {"LILITH_LM_URL": "http://custom:9999/v1"}):
            cfg = LilithConfig(config_path=config_path)
            assert (
                cfg.get("llm.providers.lm_studio.base_url") == "http://custom:9999/v1"
            )

    def test_env_var_bool_coercion(self, config_path, clean_env):
        """Env vars booleanas se convierten correctamente."""
        with patch.dict(os.environ, {"LILITH_SKILLS_HOT_RELOAD": "false"}):
            LilithConfig.reset()
            cfg = LilithConfig(config_path=config_path)
            assert cfg.get("skills.hot_reload") is False

        LilithConfig.reset()
        with patch.dict(os.environ, {"LILITH_SKILLS_HOT_RELOAD": "true"}, clear=False):
            cfg = LilithConfig(config_path=config_path)
            assert cfg.get("skills.hot_reload") is True

    def test_env_var_int_coercion(self, config_path, clean_env):
        """Env vars enteras se convierten correctamente."""
        with patch.dict(os.environ, {"LILITH_SKILLS_MAX_TRIGGERED": "5"}):
            cfg = LilithConfig(config_path=config_path)
            assert cfg.get("skills.max_triggered") == 5

    def test_kimi_api_key_env(self, config_path, clean_env):
        """KIMI_API_KEY env var se propaga al config."""
        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-test-secret-key"}):
            cfg = LilithConfig(config_path=config_path)
            assert cfg.get("llm.providers.kimi.api_key") == "sk-test-secret-key"


# ─── Test: Defaults ────────────────────────────────────────────────────────────


class TestDefaults:
    """Los valores del abismo, cuando ni TOML ni env vars existen."""

    def test_default_provider(self, config):
        assert config.get("llm.default_provider") == "auto"

    def test_default_model(self, config):
        assert config.get("llm.default_model") == "auto"

    def test_default_lm_studio_url(self, config):
        assert (
            config.get("llm.providers.lm_studio.base_url") == "http://localhost:1234/v1"
        )

    def test_default_kimi_url(self, config):
        assert config.get("llm.providers.kimi.base_url") == "https://api.moonshot.cn/v1"

    def test_default_chat_history(self, config):
        assert config.get("chat.max_history") == 50

    def test_default_tools_timeout(self, config):
        assert config.get("tools.timeout") == 60

    def test_default_tools_max_calls(self, config):
        assert config.get("tools.max_calls") == 25

    def test_default_memory_save_history(self, config):
        assert config.get("memory.save_history") is True

    def test_default_skills_settings(self, config):
        assert config.get("skills.hot_reload") is True
        assert config.get("skills.auto_trigger") is True
        assert config.get("skills.max_triggered") == 3

    def test_default_dashboard(self, config):
        assert config.get("dashboard.host") == "localhost"
        assert config.get("dashboard.port") == 8765
        assert config.get("dashboard.auto_open") is False

    def test_default_logging(self, config):
        assert config.get("logging.level") == "INFO"

    def test_get_nonexistent_key(self, config):
        """Claves inexistentes retornan None o el default provisto."""
        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "fallback") == "fallback"


# ─── Test: Auto paths ──────────────────────────────────────────────────────────


class TestAutoPaths:
    """Paths vacios se expanden automaticamente."""

    def test_memory_dir_auto(self, config):
        """memory.dir vacio se expande a <project_root>/memory."""
        mem_dir = config.get("memory.dir")
        assert mem_dir is not None
        assert "memory" in str(mem_dir)

    def test_skills_dir_auto(self, config):
        """skills.dir vacio se expande a ~/.lilith/skills."""
        skills_dir = config.get("skills.dir")
        assert skills_dir is not None
        assert ".lilith" in str(skills_dir)

    def test_logging_file_auto(self, config):
        """logging.file vacio se expande a <project_root>/logs/lilith.log."""
        log_file = config.get("logging.file")
        assert log_file is not None
        assert "lilith.log" in str(log_file)

    def test_mcp_config_path_auto(self, config):
        """mcp.config_path vacio se expande a ~/.lilith/mcp.json."""
        mcp_path = config.get("mcp.config_path")
        assert mcp_path is not None
        assert "mcp.json" in str(mcp_path)

    def test_explicit_path_not_overridden(self, config_path, clean_env):
        """Paths explicitos en TOML no se sobreescriben con auto."""
        config_path.write_text(
            '[memory]\ndir = "/custom/memory"\n[logging]\nfile = "/custom/log.log"\n',
            encoding="utf-8",
        )
        cfg = LilithConfig(config_path=config_path)
        assert cfg.get("memory.dir") == "/custom/memory"
        assert cfg.get("logging.file") == "/custom/log.log"


# ─── Test: Save / Reload ───────────────────────────────────────────────────────


class TestSaveReload:
    """El grimorio puede ser escrito y releido."""

    def test_save_creates_file(self, config):
        """save() crea el archivo config.toml."""
        config.set("llm.default_model", "saved-model")
        config.save()
        assert config.config_path.exists()

    def test_set_and_get(self, config):
        """set() modifica valores en memoria, get() los recupera."""
        config.set("llm.default_model", "test-model-xyz")
        assert config.get("llm.default_model") == "test-model-xyz"

    def test_set_nested_key(self, config):
        """set() con dotted key crea estructura anidada si no existe."""
        config.set("custom.new_section.value", 42)
        assert config.get("custom.new_section.value") == 42

    def test_reload_picks_up_changes(self, config_path, clean_env):
        """reload() lee cambios del archivo modificado externamente."""
        cfg = LilithConfig(config_path=config_path)
        # Default model deberia ser "auto"
        assert cfg.get("llm.default_model") == "auto"

        # Escribir nuevo config TOML directamente
        config_path.write_text(
            '[llm]\ndefault_model = "reloaded-model"\ndefault_provider = "kimi"\n',
            encoding="utf-8",
        )
        cfg.reload()
        assert cfg.get("llm.default_model") == "reloaded-model"
        assert cfg.get("llm.default_provider") == "kimi"


# ─── Test: Dotted key access ───────────────────────────────────────────────────


class TestDottedKeyAccess:
    """Las claves del grimorio se navegan con notacion de puntos."""

    def test_get_top_level(self, config):
        """Acceso a seccion completa."""
        llm_section = config.get("llm")
        assert isinstance(llm_section, dict)
        assert "default_provider" in llm_section

    def test_get_nested_key(self, config):
        """Claves anidadas con dotted notation."""
        assert (
            config.get("llm.providers.lm_studio.base_url") == "http://localhost:1234/v1"
        )

    def test_get_deep_nested(self, config):
        """Navegacion profunda en el arbol."""
        assert config.get("llm.providers.kimi.type") == "remote"

    def test_set_and_get_nested(self, config):
        """set() con dotted key y get() con dotted key."""
        config.set("llm.providers.lm_studio.model", "gemma-4")
        assert config.get("llm.providers.lm_studio.model") == "gemma-4"


# ─── Test: Retro-compatibilidad con config.py ──────────────────────────────────


class TestRetroCompatibility:
    """Las constantes de config.py siguen funcionando como siempre."""

    def test_lm_studio_url(self):
        """LM_STUDIO_URL es accesible desde config.py."""
        from Lilith.Core.config import LM_STUDIO_URL

        assert isinstance(LM_STUDIO_URL, str)
        assert "localhost" in LM_STUDIO_URL or "1234" in LM_STUDIO_URL

    def test_default_model(self):
        """DEFAULT_MODEL es accesible desde config.py."""
        from Lilith.Core.config import DEFAULT_MODEL

        assert isinstance(DEFAULT_MODEL, str)

    def test_llm_providers(self):
        """LLM_PROVIDERS es una lista de dicts con la estructura esperada."""
        from Lilith.Core.config import LLM_PROVIDERS

        assert isinstance(LLM_PROVIDERS, list)
        assert len(LLM_PROVIDERS) >= 2
        names = [p["name"] for p in LLM_PROVIDERS]
        assert "lm_studio" in names
        assert "kimi" in names
        # Verificar estructura de cada provider
        for p in LLM_PROVIDERS:
            assert "name" in p
            assert "type" in p
            assert "base_url" in p
            assert "model" in p

    def test_llm_provider_setting(self):
        """LLM_PROVIDER es 'auto' o un nombre valido."""
        from Lilith.Core.config import LLM_PROVIDER

        assert LLM_PROVIDER in ("auto", "lm_studio", "kimi")

    def test_skills_dir(self):
        """SKILLS_DIR es un Path apuntando a ~/.lilith/skills."""
        from Lilith.Core.config import SKILLS_DIR

        assert isinstance(SKILLS_DIR, Path)

    def test_skills_hot_reload(self):
        """SKILLS_HOT_RELOAD es bool."""
        from Lilith.Core.config import SKILLS_HOT_RELOAD

        assert isinstance(SKILLS_HOT_RELOAD, bool)

    def test_max_history(self):
        """MAX_HISTORY_MESSAGES es int."""
        from Lilith.Core.config import MAX_HISTORY_MESSAGES

        assert isinstance(MAX_HISTORY_MESSAGES, int)

    def test_memory_dir(self):
        """MEMORY_DIR es un string con path."""
        from Lilith.Core.config import MEMORY_DIR

        assert isinstance(MEMORY_DIR, str)
        assert "memory" in MEMORY_DIR

    def test_tool_timeout(self):
        """TOOL_TIMEOUT es un entero."""
        from Lilith.Core.config import TOOL_TIMEOUT

        assert isinstance(TOOL_TIMEOUT, int)

    def test_max_tool_calls(self):
        """MAX_TOOL_CALLS es un entero."""
        from Lilith.Core.config import MAX_TOOL_CALLS

        assert isinstance(MAX_TOOL_CALLS, int)

    def test_workspace(self):
        """WORKSPACE es un string."""
        from Lilith.Core.config import WORKSPACE

        assert isinstance(WORKSPACE, str)

    def test_log_level(self):
        """LOG_LEVEL es un string."""
        from Lilith.Core.config import LOG_LEVEL

        assert isinstance(LOG_LEVEL, str)

    def test_reload_config(self):
        """reload_config() actualiza las constantes del modulo."""
        from Lilith.Core import config as config_module

        config_module.reload_config()
        # El valor debe seguir siendo un string valido
        assert isinstance(config_module.DEFAULT_MODEL, str)


# ─── Test: Thread safety ───────────────────────────────────────────────────────


class TestThreadSafety:
    """El grimorio es seguro ante demonios concurrentes."""

    def test_concurrent_gets(self, config_path, clean_env):
        """Multiples threads pueden leer config simultaneamente."""
        cfg = LilithConfig(config_path=config_path)
        errors = []

        def reader():
            try:
                for _ in range(100):
                    val = cfg.get("llm.providers.lm_studio.base_url")
                    assert val is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errores en threads: {errors}"

    def test_concurrent_gets_and_sets(self, config_path, clean_env):
        """Multiples threads pueden leer y escribir config simultaneamente."""
        cfg = LilithConfig(config_path=config_path)
        errors = []

        def reader():
            try:
                for _ in range(50):
                    cfg.get("llm.default_model")
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(50):
                    cfg.set("llm.default_model", f"model-{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errores en threads: {errors}"


# ─── Test: Config creation default ─────────────────────────────────────────────


class TestConfigCreationDefault:
    """Si el grimorio no existe, se crea uno nuevo con defaults."""

    def test_creates_config_dir(self, tmp_path, clean_env):
        """Se crea el directorio si no existe."""
        nonexistent = tmp_path / "deep" / "nested" / "config.toml"
        cfg = LilithConfig(config_path=nonexistent)
        assert nonexistent.parent.exists()
        assert nonexistent.exists()

    def test_default_config_has_all_sections(self, config):
        """El config default tiene todas las secciones esperadas."""
        data = config.data
        assert "llm" in data
        assert "chat" in data
        assert "tools" in data
        assert "memory" in data
        assert "skills" in data
        assert "workspace" in data
        assert "dashboard" in data
        assert "mcp" in data
        assert "logging" in data

    def test_default_config_file_content(self, config_path, clean_env):
        """El archivo config.toml generado es TOML valido."""
        LilithConfig(config_path=config_path)
        content = config_path.read_text()
        assert "[llm]" in content
        assert "[chat]" in content
        assert "default_provider" in content


# ─── Test: Helper functions ──────────────────────────────────────────────────────


class TestHelperFunctions:
    """Funciones auxiliares del grimorio."""

    def test_get_nested(self):
        """_get_nested navega dicts con dotted keys."""
        data = {"llm": {"providers": {"lm_studio": {"base_url": "http://test"}}}}
        assert _get_nested(data, "llm.providers.lm_studio.base_url") == "http://test"

    def test_get_nested_missing_key(self):
        """_get_nested retorna None para claves inexistentes."""
        data = {"llm": {"providers": {}}}
        assert _get_nested(data, "llm.providers.nonexistent") is None

    def test_set_nested(self):
        """_set_nested establece valores en dicts anidados."""
        data = {"llm": {"providers": {}}}
        _set_nested(data, "llm.providers.kimi.base_url", "https://test.api")
        assert data["llm"]["providers"]["kimi"]["base_url"] == "https://test.api"

    def test_set_nested_creates_structure(self):
        """_set_nested crea estructura intermedia si no existe."""
        data = {}
        _set_nested(data, "custom.deep.key", 42)
        assert data["custom"]["deep"]["key"] == 42

    def test_coerce_env_bool_true(self):
        """_coerce_env_value convierte 'true' a True."""
        assert _coerce_env_value("skills.hot_reload", "true") is True

    def test_coerce_env_bool_false(self):
        """_coerce_env_value convierte 'false' a False."""
        assert _coerce_env_value("skills.hot_reload", "false") is False

    def test_coerce_env_int(self):
        """_coerce_env_value convierte strings a int."""
        assert _coerce_env_value("skills.max_triggered", "10") == 10

    def test_coerce_env_string(self):
        """_coerce_env_value deja strings como strings."""
        assert _coerce_env_value("llm.default_model", "gemma-4") == "gemma-4"


# ─── Test: Singleton ────────────────────────────────────────────────────────────


class TestSingleton:
    """El grimorio es uno, y su nombre es singleton."""

    def test_instance_returns_same(self, config_path, clean_env):
        """instance() retorna siempre la misma instancia."""
        cfg1 = LilithConfig.instance(config_path=config_path)
        cfg2 = LilithConfig.instance()
        assert cfg1 is cfg2

    def test_reset_creates_new(self, config_path, clean_env):
        """reset() permite obtener una nueva instancia."""
        cfg1 = LilithConfig.instance(config_path=config_path)
        LilithConfig.reset()
        cfg2 = LilithConfig.instance(config_path=config_path)
        assert cfg1 is not cfg2

    def test_data_is_copy(self, config):
        """data retorna una copia, no la referencia interna."""
        data1 = config.data
        data2 = config.data
        # Modificar la copia no afecta al original
        data1["llm"]["default_model"] = "modified"
        assert config.get("llm.default_model") == "auto"

    def test_get_config_convenience(self, config_path, clean_env):
        """get_config() es atajo al singleton."""
        cfg = get_config(config_path=config_path)
        assert isinstance(cfg, LilithConfig)
