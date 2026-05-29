"""
Lilith — Carga y parseo seguro de JSON.
Nunca lanza: devuelve un valor por defecto y registra el fallo.
Uso: safe_load(path), safe_loads(text), safe_load_lines(path, default_item=None).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

logger = logging.getLogger("json_safe")

_DEFAULT_DICT: dict = {}
_DEFAULT_LIST: list = []


def safe_load(
    path: Union[Path, str],
    default: Optional[Any] = None,
) -> Any:
    """
    Carga un archivo JSON desde disco. Nunca lanza.
    - Si el archivo no existe: devuelve default (o {} si default es None).
    - Si hay error de codificación o JSON: registra y devuelve default (o {}).
    """
    if default is None:
        default = _DEFAULT_DICT
    path = Path(path) if isinstance(path, str) else path
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning("json_safe: JSON inválido en %s: %s", path, e)
        return default
    except Exception as e:
        logger.warning("json_safe: error leyendo %s: %s", path, e)
        return default


def safe_loads(
    text: str,
    default: Optional[Any] = None,
) -> Any:
    """
    Parsea una cadena JSON. Nunca lanza.
    - Si text está vacío o no es JSON válido: devuelve default (o {} si default es None).
    """
    if default is None:
        default = _DEFAULT_DICT
    if not (text or text.strip()):
        return default
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        logger.debug("json_safe: JSON inválido en string: %s", e)
        return default
    except Exception as e:
        logger.warning("json_safe: error en loads: %s", e)
        return default


def safe_load_lines(
    path: Union[Path, str],
    default: Optional[List[Any]] = None,
    skip_invalid: bool = True,
) -> List[Any]:
    """
    Carga un archivo donde cada línea es un JSON (ej. JSONL). Nunca lanza.
    Líneas vacías o inválidas se omiten (no se añaden a la lista).
    """
    if default is None:
        default = _DEFAULT_LIST
    path = Path(path) if isinstance(path, str) else path
    if not path.exists():
        return default
    result: List[Any] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    if not skip_invalid:
                        result.append(None)
    except Exception as e:
        logger.warning("json_safe: error leyendo líneas de %s: %s", path, e)
        return default
    return result
