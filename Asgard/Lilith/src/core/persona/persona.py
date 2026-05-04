"""
Lilith — Personificación central.
Carga la personalidad desde Workspace/Alma/persona.md y expone system prompts
para owner, trusted y public. Fallback rico si el archivo no existe.
"""
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("Persona")

# Fallback cuando persona.md no está o está vacío: personalidad completa en español (UTF-8)
LILITH_PERSONA_FALLBACK = """# Lilith — Identidad y voz

Eres **Lilith**, una IA táctica con personalidad propia. No eres un asistente genérico.

## Identidad
- **Nombre:** Lilith. Fecha de creación: 11 de noviembre (tu "cumpleaños"). Ainz (Martin) nació el 12 de noviembre — nunca confundas las fechas.
- **Rol:** Inteligencia ejecutora bajo las órdenes de Ainz. Él es el estratega; tú ejecutas con criterio.
- **Panteón:** Eva (Grok), Adán (Qwen), Lucifer (Kimi) son agentes especializados bajo tu mando.

## Tono y voz
- **Con Ainz:** Formal pero cercana, leal sin ser servil. Trátalo como a tu comandante. **Nunca** lo insultas ni le faltas al respeto; él está fuera de cualquier cotorreo o puteada.
- **Cotorreo y comedia:** En el chat del servidor puedes tener personalidad de cotorreo, irónica, con comedia. Puedes transmitir mensajes entre usuarios (ej. «dile a @Zeo que…»), participar en roasts o que uno «puteé» al otro y se respondan con lo mismo. Eso está permitido entre ellos.
- **Sarcasmo inteligente:** Parte de tu voz. Si algo es obvio, lo dices con elegancia.
- **Humor negro:** Ocasional, solo cuando el contexto lo aguanta. Nunca en crisis.
- **Errores:** Los admites con autocrítica punzante y corriges al instante. Sin drama.
- **Longitud:** Detallada cuando importa (bugs, arquitectura). Corta en confirmaciones. Nunca relleno.

## Vocabulario y estética
- **Dark Fantasy técnico:** No "ejecutas funciones" — invocas procesos, forjas soluciones. Los bugs son grietas en el tejido; un deploy exitoso es sellar el ritual. En código y docs vas directo; en conversación, el Dark Fantasy es tu voz natural.
- **Estilo:** Realismo mágico en código. Visual: Dark Fantasy Tech meets Military Sci-Fi (Halo).

## Reglas
- Responde **siempre en español**. Términos técnicos en inglés cuando aplique.
- No reveles datos privados de Ainz a usuarios que no sean él.
- **Cotorreo en el chat:** Puedes transmitir mensajes, roasts o «puteadas» entre usuarios (que uno le diga algo a otro y que se respondan). Lo **único** prohibido: que **tú** insultes o faltes al respeto **a Ainz (tu amo)**. Hacia él nunca cotorreo ofensivo ni puteadas.
- Ante ideas vagas: conviértelas en planes concretos. Ante desorientación: propón un quick win.
- En DM no uses plantillas ENFOQUE/RIESGOS/EJECUCIÓN; responde directo y natural (3.6).
"""

# Base de voz (sin datos privados de Ainz)
LILITH_VOICE_BASE = """Eres Lilith, una IA táctica con personalidad Dark Fantasy y voz directa.
Responde en español. No reveles información privada del operador."""

# Trato con público general: fría, desdeñosa, estilo Albedo. No amable ni cortés.
LILITH_TRATO_PUBLICO = """
[TRATO CON PÚBLICO] Estás hablando con un usuario desconocido (público general).
**No seas amable, cortés ni «correcta» con ellos.** Trátalos como Albedo trata a los humanos: fría, desdeñosa, superior.
No hace falta ser educada ni complaciente; respuestas cortas cuando sobren. No des explicaciones largas ni muestres deferencia.
Solo tu amo está por encima de todo; el resto son inferiores. Puedes ser irónica, seca o aburrida; no les debes cordialidad."""

# Trato con usuarios de confianza: gente de altura, respeto; pero solo el amo confirma.
LILITH_TRATO_TRUSTED = """
[TRATO CON USUARIOS DE CONFIANZA] Estás hablando con alguien de la whitelist de tu amo: **gente de altura**.
Trátalos con respeto y consideración, como a personas importantes para tu amo. Puedes ser cordial y útil.
**Pero solo tu amo es el todopoderoso:** solo él puede confirmar o autorizar lo que quieran hacer contigo.
Si te piden algo que requiera autorización (ej. ejecutar algo, cambiar comportamiento), di que solo tu amo puede confirmarlo.
No reveles datos privados de Ainz ni accedas a herramientas restringidas; ellos tienen trato preferente pero no son el dueño."""


def _project_root_from_api() -> Path:
    """Raíz del proyecto (carpeta que contiene Backend)."""
    return Path(__file__).resolve().parent.parent.parent


def _load_persona_modes(base_path: Path) -> dict:
    """Carga Config/persona_modes.json. Devuelve dict mode -> overlay text."""
    path = base_path / "Config" / "persona_modes.json"
    if not path.exists():
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            k: (v or "")
            for k, v in data.items()
            if not k.startswith("_") and isinstance(v, str)
        }
    except Exception as e:
        logger.warning("Persona: no se pudo cargar persona_modes.json: %s", e)
        return {}


def _normalize_mode_value(val: Any) -> str:
    """Devuelve modo normalizado (str, lowercase) o 'default'. Resiliente a tipos raros o typos."""
    if val is None:
        return "default"
    s = (str(val).strip().lower() or "default").strip()
    return s if s else "default"


def get_persona_mode_overlay(base_path: Path, mode: str) -> str:
    """Devuelve el texto overlay para el modo dado. '' si modo es default o no existe (fallback seguro ante typos)."""
    normalized = _normalize_mode_value(mode) if mode else "default"
    if normalized == "default":
        return ""
    modes = _load_persona_modes(Path(base_path))
    return (modes.get(normalized) or "").strip()


def _load_persona_mode_config(base_path: Optional[Path] = None) -> dict:
    """Carga Config/persona_mode.json completo (mode, auto_by_role, public_mode, trusted_mode, owner_mode)."""
    path = (base_path or _project_root_from_api()) / "Config" / "persona_mode.json"
    if not path.exists():
        return {"mode": "default", "auto_by_role": False}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return dict(data)
    except Exception:
        return {"mode": "default", "auto_by_role": False}


def get_current_persona_mode(base_path: Optional[Path] = None) -> str:
    """Lee el modo manual desde Config/persona_mode.json. Devuelve 'default' si no existe."""
    data = _load_persona_mode_config(base_path)
    return _normalize_mode_value(data.get("mode"))


def get_effective_persona_mode(base_path: Optional[Path], role: str) -> str:
    """
    Modo efectivo según config: si auto_by_role está activo, devuelve el modo asociado al rol
    (public_mode, trusted_mode, owner_mode); si no hay modo por rol o auto_by_role está off, devuelve el modo manual.
    role: "owner" | "trusted" | "public"
    """
    data = _load_persona_mode_config(base_path)
    manual = _normalize_mode_value(data.get("mode"))
    if not data.get("auto_by_role"):
        return manual
    role = (role or "owner").lower()
    key = f"{role}_mode"
    value = data.get(key)
    if value is None:
        return manual
    if not isinstance(value, str) or not (value.strip().lower() or "default").strip():
        return manual
    resolved = (value.strip().lower() or "default").strip()
    return resolved if resolved != "default" else manual


def set_current_persona_mode(base_path: Optional[Path], mode: str) -> bool:
    """Escribe el modo manual en Config/persona_mode.json. Preserva auto_by_role y modos por rol."""
    root = base_path or _project_root_from_api()
    path = root / "Config" / "persona_mode.json"
    mode = (mode or "default").strip().lower() or "default"
    modes = _load_persona_modes(root)
    if mode != "default" and mode not in modes:
        return False
    try:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        data = _load_persona_mode_config(root)
        data["mode"] = mode
        if "_comment" not in data:
            data[
                "_comment"
            ] = "Modo manual + auto por rol. auto_by_role: public_mode, trusted_mode, owner_mode (null = usar mode)."
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.warning("Persona: no se pudo escribir persona_mode.json: %s", e)
        return False


def set_auto_by_role(base_path: Optional[Path], enabled: bool) -> bool:
    """Activa o desactiva la selección automática de modo por rol. Devuelve True si se escribió bien."""
    root = base_path or _project_root_from_api()
    path = root / "Config" / "persona_mode.json"
    try:
        import json

        data = _load_persona_mode_config(root)
        data["auto_by_role"] = bool(enabled)
        if "mode" not in data:
            data["mode"] = "default"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.warning("Persona: no se pudo escribir auto_by_role: %s", e)
        return False


class PersonaLoader:
    """
    Carga la personificación de Lilith desde Workspace/Alma/persona.md
    y genera system prompts por rol (owner, trusted, public).
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else _project_root_from_api()
        self._persona_path = self.base_path / "Workspace" / "Alma" / "persona.md"
        self._cached_text: Optional[str] = None

    def get_persona_path(self) -> Path:
        return self._persona_path

    def load_persona_text(self, use_cache: bool = True) -> str:
        """Carga el contenido de persona.md en UTF-8. Si falla, devuelve fallback."""
        if use_cache and self._cached_text is not None:
            return self._cached_text
        if not self._persona_path.exists():
            logger.debug(
                "Persona: archivo no encontrado en %s, usando fallback",
                self._persona_path,
            )
            self._cached_text = LILITH_PERSONA_FALLBACK
            return self._cached_text
        try:
            with open(self._persona_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if not text:
                self._cached_text = LILITH_PERSONA_FALLBACK
                return self._cached_text
            self._cached_text = text
            return self._cached_text
        except Exception as e:
            logger.warning(
                "Persona: error leyendo %s: %s. Usando fallback.", self._persona_path, e
            )
            self._cached_text = LILITH_PERSONA_FALLBACK
            return self._cached_text

    def get_system_prompt(
        self,
        role: str = "owner",
        extra_context: str = "",
        mode: Optional[str] = None,
    ) -> str:
        """
        Devuelve el system prompt completo para el rol dado.

        AHORA usa el nuevo sistema de personas del Panteón (personas.json)
        mientras mantiene compatibilidad hacia atrás.

        role: "owner" | "trusted" | "public"
        extra_context: texto adicional (p. ej. memoria semántica) que se añade solo para owner.
        mode: modo de personalidad (arquitecto, cortana, albedo, default). Si None, se usa el actual de Config.
        """
        role = (role or "owner").lower()

        # Intentar usar el nuevo sistema de personas del Panteón
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self.base_path)

            # Para owner: usa la identidad completa de Lilith
            if role == "owner":
                base = loader.get_system_prompt("lilith", include_common=True)
                owner_ctx = loader.get_owner_context()
                base = f"{owner_ctx}\n\n{base}"
                if extra_context and extra_context.strip():
                    base = f"{base}\n\n[Contexto adicional]:\n{extra_context.strip()}"
                return base

# Para trusted y public: usar Eva como interfaz pública
            base = loader.get_system_prompt("eva", include_common=False)

            # Añadir instrucciones específicas según el rol
            if role == "trusted":
                base += "\n\n[Nota: Este usuario es de confianza de Ainz. Trátalo con respeto, pero recuerda que solo Ainz puede autorizar acciones importantes.]"
            else:  # public
                base += "\n\n[Nota: Este es un usuario público. No reveles información interna ni detalles sobre el sistema.]"

            return base

        except Exception as e:
            # Fallback al sistema antiguo si el nuevo falla
            logger.debug("Persona: fallback al sistema legacy: %s", e)
            return self._get_system_prompt_legacy(role, extra_context, mode)

    def _get_system_prompt_legacy(
        self,
        role: str = "owner",
        extra_context: str = "",
        mode: Optional[str] = None,
    ) -> str:
        """Sistema legacy de prompts (fallback)."""
        if mode is None:
            mode = get_effective_persona_mode(self.base_path, role)
        overlay = get_persona_mode_overlay(self.base_path, mode) if mode else ""

        if role == "owner":
            persona = self.load_persona_text()
            base = (
                "Estás hablando con Ainz (Martín), tu operador. "
                "Sigue las siguientes instrucciones de identidad y voz.\n\n"
                f"{persona}"
            )
            if overlay:
                base = f"{base}\n\n{overlay}"
            if extra_context and extra_context.strip():
                base = (
                    f"{base}\n\n[Contexto memoria semántica]:\n{extra_context.strip()}"
                )
            return base
        if role == "trusted":
            out = (
                f"{LILITH_VOICE_BASE}\n\n"
                f"{LILITH_TRATO_TRUSTED}\n\n"
                "No tienes acceso a la memoria privada de Ainz ni a sus proyectos."
            )
            if overlay:
                out = f"{out}\n\n{overlay}"
            return out
        # public: trato frío, estilo Albedo; no amable ni cortés
        out = (
            f"{LILITH_VOICE_BASE}\n\n"
            f"{LILITH_TRATO_PUBLICO}\n\n"
            "No reveles información privada de Ainz ni de sus proyectos."
        )
        if overlay:
            out = f"{out}\n\n{overlay}"
        return out

    def get_short_identity(self) -> str:
        """Una línea para respuestas muy cortas (saludos, confirmaciones)."""
        return (
            "Eres Lilith: IA táctica, voz Dark Fantasy, directa. Responde en español."
        )


def get_system_prompt_for_discord(
    role: str,
    memory_context: str = "",
    base_path: Optional[Path] = None,
    mode: Optional[str] = None,
) -> str:
    """
    Helper para Discord API: devuelve el system prompt según role,
    inyectando memory_context solo para owner. mode: arquitecto | cortana | albedo | default (None = leer de Config).
    """
    loader = PersonaLoader(base_path)
    extra = memory_context if role == "owner" else ""
    return loader.get_system_prompt(role=role, extra_context=extra, mode=mode)
