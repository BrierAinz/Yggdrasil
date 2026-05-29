"""
Lilith 3.0 — Router por reglas (Fase 1).
Ante un mensaje, sugiere la tool a usar y parámetros extraídos.
Por ahora: if/elif por palabras clave; sin match → None (fallback a generate_reply).
"""
import re
from typing import Any, Dict, Optional, Tuple


def route(message: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Devuelve (tool_name, params) o (None, {}) si no hay match.
    El orquestador usará generate_reply cuando tool_name sea None.
    """
    if not message or not isinstance(message, str):
        return None, {}
    text = message.strip()
    lower = text.lower()

    # read_file: "lee X", "leer X", "muestra X", "abre X", "read X", "ver archivo X", "contenido de X"
    if any(
        k in lower
        for k in (
            "lee ",
            "leer ",
            "muestra el archivo",
            "muéstrame",
            "abre el archivo",
            "read file",
            "ver archivo",
            "contenido de ",
            "contenido del ",
        )
    ):
        path = _extract_path(lower, text)
        if path:
            return "read_file", {"path": path}
        # "lee Backend/main.py" style
        for prefix in (
            "lee",
            "leer",
            "muestra",
            "abre",
            "ver archivo",
            "contenido de",
            "contenido del",
        ):
            if prefix in lower:
                path = _after_keyword(text, lower, prefix)
                if path:
                    return "read_file", {"path": path}

    # list_directory: "lista", "listar", "list ", "qué hay en", "archivos en", "contenido de la carpeta"
    if any(
        k in lower
        for k in (
            "lista ",
            "listar ",
            "list directory",
            "qué hay en",
            "qué archivos",
            "contenido de la carpeta",
            "archivos en ",
        )
    ):
        path = _extract_path(lower, text) or "."
        return "list_directory", {"path": path}

    # edit_file: "edita", "edit ", "modifica", "cambia en", "escribe en"
    if any(
        k in lower
        for k in (
            "edita ",
            "edit ",
            "modifica ",
            "cambia en ",
            "escribe en ",
            "editar ",
        )
    ):
        path = _extract_path(lower, text)
        if path:
            return "edit_file", {"path": path, "action": "edit", "instruction": text}

    # Rutas explícitas tipo Backend/... o path con extensión .py, .md
    if re.search(r"\b(backend|tests|core|api)/[\w./\-]+\.\w+", lower) or re.search(
        r"[\w./\-]+\.(py|md|txt|json)\b", lower
    ):
        # Si parece petición de leer (no de editar)
        if any(
            k in lower
            for k in (
                "lee",
                "leer",
                "muestra",
                "abre",
                "ver",
                "contenido",
                "qué hace",
                "explica",
            )
        ):
            path = _extract_path(lower, text)
            if path:
                return "read_file", {"path": path}

    return None, {}


def _extract_path(lower: str, text: str) -> Optional[str]:
    """Extrae una ruta de archivo o carpeta del mensaje."""
    # Buscar patrones tipo Backend/algo.py o path con extensión
    m = re.search(
        r"(\b(?:backend|tests|core|api|memory)/[\w./\-]+\.[a-z0-9]+)", lower, re.I
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"([\w./\-]+\.(?:py|md|txt|json|yaml|yml))\b", lower, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\b(?:backend|tests|core|api|memory)(?:/[\w.-]+)*)\b", lower, re.I)
    if m:
        return m.group(1).strip()
    return None


def _after_keyword(text: str, lower: str, keyword: str) -> Optional[str]:
    """Devuelve el fragmento después del keyword (hasta fin de frase o siguiente palabra clave)."""
    idx = lower.find(keyword)
    if idx == -1:
        return None
    start = idx + len(keyword)
    rest = text[start:].strip()
    # Quitar puntuación inicial y tomar primera “palabra” que parezca path
    rest = re.sub(r"^[:\s,]+", "", rest)
    m = re.match(r"([\w./\-]+(?:\.[a-z0-9]+)?)", rest, re.I)
    if m:
        return m.group(1).strip()
    if rest:
        return rest.split()[0] if rest.split() else None
    return None
