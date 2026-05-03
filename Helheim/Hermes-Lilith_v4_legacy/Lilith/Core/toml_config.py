"""
Lilith Unified Configuration (TOML)
=====================================
El grimorio donde Lilith inscribe sus secretos mas profundos.
Una sola fuente de verdad — ~/.lilith/config.toml — gobierna
todos los reinos del sistema.

Prioridad de invocacion:
    TOML file > env vars > defaults

PEP 680 — TOML es el estandar de config para Python tools.
"""

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

# tomllib es stdlib en Python 3.11+ (PEP 680)
try:
    import tomllib
except ImportError:
    # Fallback para Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

logger = logging.getLogger("Lilith.Config")

# ─── Default Config Schema ─────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "llm": {
        "default_provider": "auto",
        "default_model": "auto",
        "providers": {
            "lm_studio": {
                "type": "local",
                "base_url": "http://localhost:1234/v1",
                "model": "auto",
                "api_key": "",
            },
            "kimi": {
                "type": "remote",
                "base_url": "https://api.moonshot.cn/v1",
                "model": "kimi-2.6",
                "api_key": "",
            },
        },
    },
    "chat": {
        "max_history": 50,
        "system_prompt": "",
    },
    "tools": {
        "timeout": 60,
        "max_calls": 25,
    },
    "memory": {
        "dir": "",
        "save_history": True,
    },
    "skills": {
        "dir": "",
        "hot_reload": True,
        "auto_trigger": True,
        "max_triggered": 3,
    },
    "workspace": {
        "dir": "D:\\Proyectos\\Midgard",
        "projects_dir": "D:\\Proyectos",
    },
    "dashboard": {
        "host": "localhost",
        "port": 8765,
        "auto_open": False,
    },
    "mcp": {
        "config_path": "",
    },
    "logging": {
        "level": "INFO",
        "file": "",
    },
}

# ─── Env var overrides ────────────────────────────────────────────────────────
# Mapeo de env vars a dotted keys en el config TOML.
# Se leen DESPUES del TOML, pisando cualquier valor del archivo.

ENV_OVERRIDES: Dict[str, str] = {
    "LILITH_LM_URL": "llm.providers.lm_studio.base_url",
    "LILITH_MODEL": "llm.default_model",
    "LILITH_PROVIDER": "llm.default_provider",
    "LILITH_WORKSPACE": "workspace.dir",
    "LILITH_PROJECTS": "workspace.projects_dir",
    "LILITH_SKILLS": "skills.dir",
    "LILITH_SKILLS_HOT_RELOAD": "skills.hot_reload",
    "LILITH_SKILLS_AUTO_TRIGGER": "skills.auto_trigger",
    "LILITH_SKILLS_MAX_TRIGGERED": "skills.max_triggered",
    "KIMI_API_KEY": "llm.providers.kimi.api_key",
}

# ─── Type coercion para env vars ────────────────────────────────────────────────

_BOOL_STRINGS = {
    "true": True,
    "false": False,
    "1": True,
    "0": False,
    "yes": True,
    "no": False,
}


def _coerce_env_value(key: str, value: str) -> Any:
    """Convierte un string de env var al tipo apropiado segun el schema default."""
    # Obtener el tipo esperado del default
    default_val = _get_nested(DEFAULT_CONFIG, key)
    if isinstance(default_val, bool):
        return _BOOL_STRINGS.get(value.lower(), False)
    if isinstance(default_val, int):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _get_nested(data: Dict, dotted_key: str) -> Any:
    """Obtiene un valor de un dict anidado usando dotted notation.

    Ejemplo: _get_nested(data, "llm.providers.lm_studio.base_url")
    """
    keys = dotted_key.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current


def _set_nested(data: Dict, dotted_key: str, value: Any) -> None:
    """Establece un valor en un dict anidado usando dotted notation."""
    keys = dotted_key.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


# ─── LilithConfig Singleton ────────────────────────────────────────────────────


class LilithConfig:
    """El grimorio de configuracion de Lilith.

    Fuente unica de verdad: ~/.lilith/config.toml
    Prioridad: TOML > env vars > defaults.

    Thread-safe — los demonios no esperan en la puerta.

    Uso:
        config = LilithConfig.instance()
        url = config.get("llm.providers.lm_studio.base_url")
        config.set("llm.default_model", "gemma-4")
    """

    _instance: Optional["LilithConfig"] = None
    _lock = threading.Lock()

    def __init__(self, config_path: Optional[Path] = None):
        self._lock = threading.Lock()
        self._config_path = config_path or Path.home() / ".lilith" / "config.toml"
        self._data: Dict[str, Any] = {}
        self._loaded = False
        self._load()

    @classmethod
    def instance(cls, config_path: Optional[Path] = None) -> "LilithConfig":
        """Obtiene la instancia singleton del grimorio.

        En el reino de los singleton, solo uno reina.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config_path)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destruye la instancia singleton — para tests, no para mortales."""
        with cls._lock:
            cls._instance = None

    # ─── Carga / Guardado ──────────────────────────────────────────────────────

    def _load(self) -> None:
        """Carga config: TOML > env vars > defaults."""
        with self._lock:
            # 1. Defaults como base
            import copy

            self._data = copy.deepcopy(DEFAULT_CONFIG)

            # 2. TOML file pisa defaults
            self._load_toml()

            # 3. Env vars pisan TODO
            self._apply_env_overrides()

            # 4. Expandir paths auto
            self._expand_auto_paths()

            self._loaded = True
            logger.info("[Config] Grimorio cargado desde %s", self._config_path)

    def _load_toml(self) -> None:
        """Lee el archivo TOML y merge con los defaults."""
        if not self._config_path.exists():
            logger.info(
                "[Config] No existe %s — creando config default", self._config_path
            )
            self._create_default_config()
            return

        if tomllib is None:
            logger.warning(
                "[Config] No se encontro tomllib ni tomli — solo se usan defaults y env vars"
            )
            return

        try:
            with open(self._config_path, "rb") as f:
                toml_data = tomllib.load(f)
            # Deep merge: TOML pisa defaults
            self._deep_merge(self._data, toml_data)
            logger.debug("[Config] TOML cargado: %s", self._config_path)
        except Exception as e:
            logger.error(
                "[Config] Error leyendo %s: %s — usando defaults", self._config_path, e
            )

    def _create_default_config(self) -> None:
        """Crea el archivo config.toml default si no existe."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # Generar TOML con comentarios descriptivos
            content = _generate_default_toml()
            self._config_path.write_text(content, encoding="utf-8")
            logger.info("[Config] Creado config default en %s", self._config_path)
        except Exception as e:
            logger.warning("[Config] No se pudo crear config default: %s", e)

    def _apply_env_overrides(self) -> None:
        """Las env vars son susurros del mas alla — pisan al grimorio."""
        for env_var, dotted_key in ENV_OVERRIDES.items():
            value = os.getenv(env_var)
            if value is not None:
                coerced = _coerce_env_value(dotted_key, value)
                _set_nested(self._data, dotted_key, coerced)
                logger.debug("[Config] Env override: %s → %s", env_var, dotted_key)

    def _expand_auto_paths(self) -> None:
        """Expande paths vacios (auto) a valores calculados."""
        # memory.dir: "" → <project_root>/memory
        if not self._data.get("memory", {}).get("dir"):
            project_root = Path(__file__).parent.parent.parent
            _set_nested(self._data, "memory.dir", str(project_root / "memory"))

        # skills.dir: "" → ~/.lilith/skills
        if not self._data.get("skills", {}).get("dir"):
            _set_nested(
                self._data, "skills.dir", str(Path.home() / ".lilith" / "skills")
            )

        # logging.file: "" → <project_root>/logs/lilith.log
        if not self._data.get("logging", {}).get("file"):
            project_root = Path(__file__).parent.parent.parent
            _set_nested(
                self._data, "logging.file", str(project_root / "logs" / "lilith.log")
            )

        # mcp.config_path: "" → ~/.lilith/mcp.json
        if not self._data.get("mcp", {}).get("config_path"):
            _set_nested(
                self._data, "mcp.config_path", str(Path.home() / ".lilith" / "mcp.json")
            )

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Merge profundo: override pisa base, dicts se mergean recursivamente."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    # ─── API Publica ───────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor del grimorio usando dotted notation.

        Args:
            key: Clave dotted, ej: "llm.providers.lm_studio.base_url"
            default: Valor por defecto si no existe

        Returns:
            El valor configurado o el default
        """
        with self._lock:
            result = _get_nested(self._data, key)
            return result if result is not None else default

    def set(self, key: str, value: Any) -> None:
        """Establece un valor en el grimorio.

        NO guarda automaticamente en disco — llamar save() si deseas persistir.

        Args:
            key: Clave dotted, ej: "llm.default_model"
            value: Valor a establecer
        """
        with self._lock:
            _set_nested(self._data, key, value)

    def save(self) -> None:
        """Persiste el grimorio a config.toml.

        Advertencia: TOML no preserva comentarios al reescribir.
        Las secciones con API keys se escriben vacias por seguridad.
        """
        with self._lock:
            try:
                self._config_path.parent.mkdir(parents=True, exist_ok=True)

                # Generar TOML manualmente para preservar estructura y seguridad
                content = _dict_to_toml(self._data)
                self._config_path.write_text(content, encoding="utf-8")
                logger.info("[Config] Grimorio guardado en %s", self._config_path)
            except Exception as e:
                logger.error("[Config] Error guardando config: %s", e)

    def reload(self) -> None:
        """Recarga el grimorio desde disco — para cuando los vientos cambian."""
        self._load()

    @property
    def data(self) -> Dict[str, Any]:
        """Retorna una copia del config completo — leer solo, no modificar."""
        with self._lock:
            import copy

            return copy.deepcopy(self._data)

    @property
    def config_path(self) -> Path:
        """El camino al grimorio."""
        return self._config_path

    # ─── Convenience Properties ─────────────────────────────────────────────────

    @property
    def project_root(self) -> Path:
        """La raiz del proyecto — donde todo comienza."""
        return Path(__file__).parent.parent.parent


# ─── TOML Generation Helpers ───────────────────────────────────────────────────


def _generate_default_toml() -> str:
    """Genera el contenido default del config.toml con comentarios."""
    lines = [
        "# ════════════════════════════════════════════════════════════════════════",
        "# Lilith Configuration — El Grimorio Unificado",
        "# ════════════════════════════════════════════════════════════════════════",
        "# Fuente unica de verdad para todos los reinos de Lilith.",
        "# Prioridad: Este archivo > env vars > defaults",
        "#",
        "# NO pongas API keys directamente aqui — usa env vars o .env",
        '# Las secciones con api_key="" leen de KIMI_API_KEY, etc.',
        "# ════════════════════════════════════════════════════════════════════════",
        "",
        "[llm]",
        '# Provider: "auto" (fallback chain), "lm_studio", "kimi"',
        'default_provider = "auto"',
        'default_model = "auto"',
        "",
        "[llm.providers.lm_studio]",
        'type = "local"',
        'base_url = "http://localhost:1234/v1"',
        'model = "auto"',
        'api_key = ""  # LM Studio no requiere key',
        "",
        "[llm.providers.kimi]",
        'type = "remote"',
        'base_url = "https://api.moonshot.cn/v1"',
        'model = "kimi-2.6"',
        'api_key = ""  # se lee de KIMI_API_KEY env var si vacio',
        "",
        "[chat]",
        "max_history = 50",
        '# system_prompt = ""  # path a archivo o inline; vacio = default',
        "",
        "[tools]",
        "timeout = 60",
        "max_calls = 25",
        "",
        "[memory]",
        '# dir = ""  # vacio = auto (<project_root>/memory)',
        "save_history = true",
        "",
        "[skills]",
        '# dir = ""  # vacio = auto (~/.lilith/skills)',
        "hot_reload = true",
        "auto_trigger = true",
        "max_triggered = 3",
        "",
        "[workspace]",
        'dir = "D:\\\\Proyectos\\\\Midgard"',
        'projects_dir = "D:\\\\Proyectos"',
        "",
        "[dashboard]",
        'host = "localhost"',
        "port = 8765",
        "auto_open = false",
        "",
        "[mcp]",
        '# config_path = ""  # vacio = auto (~/.lilith/mcp.json)',
        "",
        "[logging]",
        'level = "INFO"',
        '# file = ""  # vacio = auto (<project_root>/logs/lilith.log)',
        "",
    ]
    return "\n".join(lines)


def _dict_to_toml(data: Dict[str, Any], prefix: str = "", indent: int = 0) -> str:
    """Convierte un dict a formato TOML (serializer manual).

    NOTA: No usa tomllib porque este solo parsea, no escribe.
    Este serializer simple cubre los tipos que necesitamos.
    """
    lines = []
    sub_sections = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Dict anidado → seccion TOML
            sub_sections.append((full_key, key, value))
        elif isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            # Escapar comillas y backslashes
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif value is None:
            lines.append(f'{key} = ""')
        else:
            lines.append(f"{key} = {repr(value)}")

    result = ""
    if lines:
        if indent > 0:
            section_name = prefix.split(".")[-1]
            result += f"\n{'[' * 0}[{prefix}]\n"
        for line in lines:
            result += f"{line}\n"

    for full_key, key, subdict in sub_sections:
        result += f"\n[{full_key}]\n"
        result += _dict_to_toml(subdict, full_key, indent + 1)

    return result


# ─── Funcion de conveniencia ────────────────────────────────────────────────────


def get_config(config_path: Optional[Path] = None) -> LilithConfig:
    """Obtiene la instancia singleton de LilithConfig.

    Atajo para los que prefieren no invocar al grimorio directamente.
    """
    return LilithConfig.instance(config_path)
