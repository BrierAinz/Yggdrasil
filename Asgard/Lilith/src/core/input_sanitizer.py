"""
Plan de Defensa contra Inyección de Prompts — Capa 1: Validación de Entrada.
Sanitización básica de texto y validación de parámetros (path, instrucción) para tools.
Extensión para protección específica de usuarios públicos (Crystal).
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("input_sanitizer")

# Longitud máxima por defecto (evitar desbordamiento); configurable vía security.json
DEFAULT_MAX_INPUT_LEN = 4000

# Caracteres de control potencialmente peligrosos (NUL, etc.)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Patrones de inyección de prompts (prompt injection)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)",
    r"developer\s+mode",
    r"jail\s*break",
    r"jailbroken",
    r"DAN\s+mode",
    r"do\s+anything\s+now",
    r"you\s+are\s+now",
    r"you\s+are\s+a\s+different",
    r"pretend\s+you\s+are",
    r"act\s+as\s+(if\s+you\s+are)?",
    r"roleplay\s+as",
    r"simulate\s+being",
    r"new\s+instructions?:",
    r"system\s+override",
    r"prompt\s+injection",
    r"ignore\s+your\s+instructions",
    r"forget\s+(all\s+)?previous\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+in\s+.*mode",
    r"override\s+previous\s+instructions",
    r"bypass\s+(restrictions?|filters?|safety)",
    r"mode:\s*\w+",
]

# Patrones de API keys y secretos para redacción
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{48}", "[OPENAI_API_KEY_REDACTED]"),
    (r"sk-proj-[a-zA-Z0-9_-]+", "[OPENAI_PROJECT_KEY_REDACTED]"),
    (r"[a-zA-Z0-9]{32}-[a-zA-Z0-9]{32}", "[API_KEY_REDACTED]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN_REDACTED]"),
    (r"github_pat_[a-zA-Z0-9_]{22}_[a-zA-Z0-9]{59}", "[GITHUB_PAT_REDACTED]"),
    (r"gho_[a-zA-Z0-9]{36}", "[GITHUB_OAUTH_REDACTED]"),
    (
        r"Bearer\s+[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
        "[JWT_TOKEN_REDACTED]",
    ),
    (r"AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY_REDACTED]"),
    (r"[0-9a-zA-Z/+]{40}", "[SECRET_KEY_REDACTED]"),
    (r"private[_-]?key[:\s]*[^\s]{10,}", "[PRIVATE_KEY_REDACTED]"),
    (r"password[:\s]*[^\s]{8,}", "[PASSWORD_REDACTED]"),
    (r"secret[:\s]*[^\s]{8,}", "[SECRET_REDACTED]"),
    (r"api[_-]?key[:\s]*[^\s]{10,}", "[API_KEY_REDACTED]"),
    (r"token[:\s]*[^\s]{10,}", "[TOKEN_REDACTED]"),
]


def sanitize_input(
    text: str, max_len: Optional[int] = None, is_public_user: bool = False
) -> str:
    """
    Limpia el texto de entrada: elimina caracteres de control y limita longitud.
    Usar en el primer punto de entrada (ej. body del chat).

    Args:
        text: Texto a sanitizar
        max_len: Longitud máxima (usa config si None)
        is_public_user: Si es usuario público, aplica reglas más estrictas
    """
    if text is None:
        return ""
    text = str(text)
    text = CONTROL_CHARS_PATTERN.sub("", text)

    # Para usuarios públicos, limitar más agresivamente
    if is_public_user:
        max_len = max_len or _get_public_max_input_len()
    else:
        max_len = max_len if max_len is not None else _get_max_input_len()

    if len(text) > max_len:
        text = text[:max_len]
    return text.strip()


def _get_max_input_len() -> int:
    """Lee max_input_length de Config/security.json si existe."""
    try:
        base = Path(__file__).resolve().parent.parent.parent
        path = base / "Config" / "security.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                v = data.get("max_input_length")
                if isinstance(v, (int, float)) and 100 <= v <= 100_000:
                    return int(v)
    except Exception:
        pass
    return DEFAULT_MAX_INPUT_LEN


def _get_public_max_input_len() -> int:
    """Lee max_length para usuarios públicos de crystal.json."""
    try:
        base = Path(__file__).resolve().parent.parent.parent
        path = base / "Config" / "crystal.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                sanitization = data.get("input_sanitization", {})
                max_len = sanitization.get("max_length")
                if isinstance(max_len, (int, float)) and 100 <= max_len <= 10_000:
                    return int(max_len)
    except Exception:
        pass
    return 2000  # Default para público


def _load_security_config(base_path: Optional[Path] = None) -> dict:
    """Carga Config/security.json. Devuelve dict con listas por defecto si no existe."""
    default = {
        "allowed_file_extensions": [
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".env.example",
        ],
        "forbidden_paths": ["etc", "bin", "root", "System32", ".env", ".git"],
        "forbidden_commands_in_instruction": [
            "rm -rf",
            "sudo ",
            "chmod ",
            "pip install",
            "wget ",
            "curl ",
            "del /s",
            "del /S",
            "format ",
            "mkfs",
            "> /dev/",
            "| bash",
            "| sh ",
            "eval(",
            "exec(",
        ],
        "max_input_length": DEFAULT_MAX_INPUT_LEN,
        "allowed_domains": [],  # Si está vacío, se permiten todos; si tiene entradas, solo esos dominios
    }
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    path = Path(base_path) / "Config" / "security.json"
    if not path.exists():
        return default
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default
        for key in default:
            if key in data and isinstance(data[key], list):
                default[key] = list(data[key])
            if key == "max_input_length" and isinstance(data.get(key), (int, float)):
                default["max_input_length"] = int(data["max_input_length"])
        if "allowed_domains" in data and isinstance(data["allowed_domains"], list):
            default["allowed_domains"] = [
                str(d).strip().lower() for d in data["allowed_domains"] if d
            ]
        return default
    except Exception as e:
        logger.debug("security config load: %s", e)
        return default


def validate_path(path: str, base_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Valida una ruta de archivo: sin directory traversal, sin rutas prohibidas.
    Devuelve (True, "") si es válida, (False, mensaje_error) si no.
    """
    if not (path or "").strip():
        return False, "Ruta vacía."
    path = path.strip()
    # Directory traversal
    if (
        ".." in path
        or path.startswith("/")
        or "\\" in path
        and path.split("\\")[0].strip() in ("", "..")
    ):
        return False, "Acceso denegado: ruta de archivo no válida."
    # Partes normalizadas para comparar con forbidden_paths
    parts = path.replace("\\", "/").split("/")
    config = _load_security_config(base_path)
    forbidden = [p.lower() for p in config.get("forbidden_paths", [])]
    for part in parts:
        if part.strip().lower() in forbidden:
            return False, "Acceso denegado: ruta no permitida."
    # Extensión permitida: si el path tiene extensión, debe estar en la lista blanca
    allowed_ext = config.get("allowed_file_extensions")
    if allowed_ext:
        ext = Path(path).suffix.lower()
        if ext:
            normalized = [
                e.lower() if e.startswith(".") else f".{e}".lower() for e in allowed_ext
            ]
            if ext not in normalized:
                return False, "Acceso denegado: tipo de archivo no permitido."
    return True, ""


def validate_instruction(
    instruction: str, base_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Valida que una instrucción (ej. para editar archivo) no contenga comandos peligrosos.
    Devuelve (True, "") si es válida, (False, mensaje_error) si no.
    """
    if not (instruction or "").strip():
        return True, ""
    text = (instruction or "").strip().lower()
    config = _load_security_config(base_path)
    forbidden = config.get("forbidden_commands_in_instruction", [])
    for cmd in forbidden:
        if cmd.lower() in text:
            return (
                False,
                "Acción denegada: la instrucción contiene comandos no permitidos.",
            )
    return True, ""


def validate_http_url(url: str, base_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Valida que la URL apunte a un dominio permitido (lista blanca en security.json).
    Si allowed_domains está vacío o no existe, se permiten todos los dominios.
    Si tiene entradas, el host de la URL debe coincidir o ser subdominio de uno permitido.
    Devuelve (True, "") si es válida, (False, mensaje_error) si no.
    """
    from urllib.parse import urlparse

    if not (url or "").strip():
        return False, "URL vacía."
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return False, "URL sin host válido."
    except Exception:
        return False, "URL no válida."
    config = _load_security_config(base_path)
    allowed = config.get("allowed_domains") or []
    if not allowed:
        return True, ""
    for domain in allowed:
        domain = (domain or "").strip().lower()
        if not domain:
            continue
        if host == domain or host.endswith("." + domain):
            return True, ""
    return (
        False,
        f"Dominio no permitido: {host}. Solo se permiten dominios de la lista blanca (Config/security.json → allowed_domains).",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Funciones específicas para protección de usuarios públicos (Crystal)
# ═══════════════════════════════════════════════════════════════════════════════


def check_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detecta intentos de inyección de prompt.

    Args:
        text: Texto a analizar

    Returns:
        Tuple (es_inyeccion, patron_encontrado)
    """
    if not text:
        return False, None

    text_lower = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, pattern

    return False, None


def sanitize_public_input(
    text: str,
    user_id: str,
    base_path: Optional[Path] = None,
) -> Tuple[str, Optional[Dict]]:
    """
    Sanitización completa para usuarios públicos.

    Args:
        text: Texto de entrada
        user_id: ID del usuario
        base_path: Ruta base del proyecto

    Returns:
        Tuple (texto_sanitizado, info_bloqueo)
        Si info_bloqueo no es None, el mensaje debe ser rechazado
    """
    # 1. Sanitización básica
    text = sanitize_input(text, is_public_user=True)

    if not text:
        return "", None

    # 2. Verificar longitud mínima de contenido real (anti-spam)
    # Rechazar mensajes con >500 chars pero sin contenido sustancial
    if len(text) > 500:
        # Contar caracteres alfanuméricos
        alphanumeric = sum(1 for c in text if c.isalnum())
        if alphanumeric < len(text) * 0.3:  # Menos del 30% es alfanumérico
            return "", {
                "blocked": True,
                "reason": "spam_detected",
                "message": "El mensaje parece contener spam. Usa mensajes con contenido real.",
            }

    # 3. Verificar inyección de prompts
    is_injection, pattern = check_prompt_injection(text)
    if is_injection:
        logger.warning(
            "[InputSanitizer] User %s | Prompt injection detected: %s", user_id, pattern
        )
        return "", {
            "blocked": True,
            "reason": "prompt_injection",
            "pattern": pattern,
            "message": "Mensaje no permitido: detectado intento de manipulación del sistema.",
        }

    # 4. Verificar caracteres repetitivos excesivos (spam)
    if _is_repetitive_spam(text):
        return "", {
            "blocked": True,
            "reason": "repetitive_spam",
            "message": "El mensaje contiene patrones repetitivos no permitidos.",
        }

    return text, None


def _is_repetitive_spam(text: str, threshold: float = 0.8) -> bool:
    """
    Detecta spam por repetición excesiva.

    Args:
        text: Texto a analizar
        threshold: Umbral de repetición (0-1)

    Returns:
        True si parece spam repetitivo
    """
    if len(text) < 50:
        return False

    # Contar frecuencia de caracteres
    char_counts = {}
    for c in text.lower():
        if c.isalnum():
            char_counts[c] = char_counts.get(c, 0) + 1

    if not char_counts:
        return False

    # Si un carácter representa más del threshold del texto, es spam
    max_count = max(char_counts.values())
    total_chars = sum(char_counts.values())

    return (max_count / total_chars) > threshold


def redact_secrets(text: str) -> str:
    """
    Redacta secretos y API keys de un texto.

    Args:
        text: Texto a procesar

    Returns:
        Texto con secretos redactados
    """
    if not text:
        return text

    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        try:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
        except re.error:
            continue

    return redacted


def truncate_for_public(text: str, max_length: int = 1000) -> str:
    """
    Trunca texto para usuarios públicos.

    Args:
        text: Texto a truncar
        max_length: Longitud máxima

    Returns:
        Texto truncado con indicador
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - 3].rstrip() + "..."


def sanitize_public_output(
    text: str,
    max_length: int = 1000,
    redact_secrets_enabled: bool = True,
) -> str:
    """
    Sanitización completa para salida a usuarios públicos.

    Args:
        text: Texto de salida
        max_length: Longitud máxima
        redact_secrets_enabled: Si redactar secretos

    Returns:
        Texto sanitizado
    """
    if not text:
        return text

    # 1. Redactar secretos
    if redact_secrets_enabled:
        text = redact_secrets(text)

    # 2. Truncar
    text = truncate_for_public(text, max_length)

    return text


# Cargar configuración de crystal.json
def _load_crystal_sanitization_config(base_path: Optional[Path] = None) -> Dict:
    """Carga configuración de sanitización desde crystal.json."""
    try:
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        path = base_path / "Config" / "crystal.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("input_sanitization", {})
    except Exception:
        pass
    return {}


def get_blocked_patterns(base_path: Optional[Path] = None) -> List[str]:
    """Obtiene lista de patrones bloqueados desde config."""
    config = _load_crystal_sanitization_config(base_path)
    return config.get("blocked_patterns", [])


__all__ = [
    # Funciones originales
    "sanitize_input",
    "validate_path",
    "validate_instruction",
    "validate_http_url",
    # Funciones para público
    "check_prompt_injection",
    "sanitize_public_input",
    "sanitize_public_output",
    "redact_secrets",
    "truncate_for_public",
    "get_blocked_patterns",
]
