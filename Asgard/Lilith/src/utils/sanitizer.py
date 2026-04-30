import os
import re
from typing import Optional

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_for_display(text: str) -> str:
    """
    Limpiar texto antes de enviarlo al frontend:
    - Elimina caracteres de control (excepto saltos de línea y tabs).
    """
    if not isinstance(text, str):
        return text
    return _CONTROL_CHARS_RE.sub("", text)


def sanitize_file_path(path: str) -> Optional[str]:
    """
    Validar y normalizar rutas de archivo para evitar path traversal.
    Devuelve la ruta normalizada o None si es insegura.
    """
    if not path:
        return None

    normalized = os.path.normpath(path)
    # Evitar rutas absolutas y '..' en cualquier segmento
    parts = normalized.split(os.sep)
    if os.path.isabs(normalized) or ".." in parts:
        return None
    return normalized
