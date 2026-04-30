"""
NLParamExtractor — Extrae parámetros de operaciones de filesystem desde lenguaje natural.
Usado por el Planner para PC Agent operations cuando se detecta un intent pc_*.
Si el LLM falla, aplica heurísticas de regex como fallback.
Parte 3: Shalltear como LLM default.
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

# Import Shalltear para uso como LLM default
from src.core.agents.panteon.shalltear import ShalltearAgent

logger = logging.getLogger("lilith.nl_param_extractor")

# ─── Path aliases ─────────────────────────────────────────────────────────────

PATH_ALIASES: Dict[str, str] = {
    "proyectos": r"D:\Proyectos",
    "projects": r"D:\Proyectos",
    "lilith": r"D:\Proyectos\Yggdrasil\Asgard\Lilith",
    "core": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core",
    "backend": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Backend",
    "config": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Config",
    "docs": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Docs",
    "yggdrasil": r"D:\Proyectos\Yggdrasil",
    "ragnarok": r"D:\Proyectos\Ragnarok",
    "desktop": r"%USERPROFILE%\Desktop",
    "escritorio": r"%USERPROFILE%\Desktop",
    "downloads": r"%USERPROFILE%\Downloads",
    "descargas": r"%USERPROFILE%\Downloads",
    "documents": r"%USERPROFILE%\Documents",
    "documentos": r"%USERPROFILE%\Documents",
}


def _resolve_path(path: str) -> str:
    """Resuelve aliases, expande variables de entorno y normaliza rutas."""
    import os

    if not path:
        return path
    p = path.strip().strip('"').strip("'")
    lower = p.lower()
    for alias, real in PATH_ALIASES.items():
        if lower == alias:
            # Expandir variables de entorno como %USERPROFILE%
            return os.path.expandvars(real)
        if (
            lower.startswith(alias + "/")
            or lower.startswith(alias + "\\")
            or lower.startswith(alias + " ")
        ):
            remainder = p[len(alias) :].lstrip("/\\").lstrip()
            expanded = os.path.expandvars(real)
            return expanded + "\\" + remainder if remainder else expanded
    # También expandir variables si el path no es un alias
    return os.path.expandvars(p)


# ─── LLM extraction prompt ────────────────────────────────────────────────────

_EXTRACT_PROMPT = """Eres un extractor de parámetros de operaciones de filesystem.
Dada la instrucción del usuario, extrae los parámetros como JSON.
Responde SOLO con el JSON, sin explicaciones ni markdown.

Operaciones y parámetros:
- pc_list:       {{"path": "ruta"}}
- pc_mkdir:      {{"path": "ruta_completa_nueva_carpeta"}}
- pc_move:       {{"source": "ruta_origen", "destination": "ruta_destino"}}
- pc_copy:       {{"source": "ruta_origen", "destination": "ruta_destino"}}
- pc_delete:     {{"path": "ruta"}}
- pc_write_file: {{"path": "ruta_archivo", "content": "contenido"}}
- pc_exec:       {{"command": "comando", "cwd": "directorio_trabajo_o_null"}}

Rutas conocidas:
- "proyectos" o "projects" = D:\\Proyectos
- "lilith" = D:\\Proyectos\\Lilith
- "yggdrasil" = D:\\Proyectos\\Yggdrasil
- "core" = D:\\Proyectos\\Lilith\\Core
- "desktop"/"escritorio" = %USERPROFILE%\\Desktop
- "downloads"/"descargas" = %USERPROFILE%\\Downloads

Si no puedes determinar un parámetro con certeza, ponlo como null.

Instrucción: {message}
Operación: {operation}

JSON:"""


# ─── Heurísticas regex (fallback sin LLM) ────────────────────────────────────


def _heuristic_extract(operation: str, message: str) -> Dict[str, Any]:
    """Extracción heurística básica sin LLM."""
    msg_lower = message.lower()

    if operation == "pc_mkdir":
        # "crea una carpeta llamada X en Y"
        m = re.search(r'llamad[ao]\s+["""]?([^"""]+?)["""]?\s+en\s+(.+)', message, re.I)
        if m:
            name, parent = m.group(1).strip(), _resolve_path(m.group(2).strip())
            return {"path": parent.rstrip("\\") + "\\" + name}
        # "crea la carpeta X"
        m = re.search(
            r'(?:crea|crear|haz|nueva)\s+(?:una\s+|la\s+|el\s+)?(?:carpeta|directorio)\s+["""]?([^\s"""]+)',
            message,
            re.I,
        )
        if m:
            return {"path": _resolve_path(m.group(1).strip())}

    elif operation == "pc_list":
        # "qué hay en X" / "lista X"
        m = re.search(
            r'(?:en|de|la|el|carpeta|directorio)\s+["""]?([^\s"""]+)', message, re.I
        )
        if m:
            return {"path": _resolve_path(m.group(1).strip())}

    elif operation in ("pc_move", "pc_copy"):
        # "mueve X a Y" / "copia X a Y"
        m = re.search(
            r'(?:mueve?|copia?|traslada?)\s+["""]?(.+?)["""]?\s+(?:a|en|hacia)\s+["""]?(.+)["""]?',
            message,
            re.I,
        )
        if m:
            return {
                "source": _resolve_path(m.group(1).strip()),
                "destination": _resolve_path(m.group(2).strip()),
            }

    elif operation == "pc_delete":
        # "elimina/borra X"
        m = re.search(
            r'(?:elimina?|borra?|delete|remove)\s+["""]?(.+)["""]?', message, re.I
        )
        if m:
            return {"path": _resolve_path(m.group(1).strip())}

    elif operation == "pc_exec":
        # "ejecuta X" / "corre X"
        m = re.search(
            r'(?:ejecuta?|corre?|run|exec(?:uta)?)\s+["""]?(.+)["""]?', message, re.I
        )
        if m:
            return {"command": m.group(1).strip()}

    elif operation == "pc_write_file":
        # "escribe/crea el archivo X con contenido Y"
        m = re.search(
            r'(?:archivo|fichero)\s+["""]?([^\s"""]+)["""]?(?:\s+con\s+contenido\s+(.+))?',
            message,
            re.I,
        )
        if m:
            return {
                "path": _resolve_path(m.group(1).strip()),
                "content": (m.group(2) or "").strip(),
            }

    return {}


# ─── NLParamExtractor ─────────────────────────────────────────────────────────


class NLParamExtractor:
    """
    Extrae parámetros de operaciones de PC Agent desde lenguaje natural.
    Intenta primero con LLM (via Shalltear u otro); fallback a heurísticas.
    """

    def __init__(self, llm_generate_fn=None):
        """
        llm_generate_fn: callable(system, prompt) → str
        Si None, usa Shalltear como LLM default.
        """
        if llm_generate_fn is None:
            # Parte 3: Shalltear como LLM default para parsing
            self._shalltear = ShalltearAgent()
            self._llm = self._shalltear_extract
        else:
            self._llm = llm_generate_fn
            self._shalltear = None

    def _shalltear_extract(self, system: str, prompt: str) -> str:
        """Wrapper para usar Shalltear en el extractor."""
        try:
            # Shalltear espera task y operation
            # Extraemos la operación del prompt
            operation = "filesystem_batch"
            if "pc_move" in prompt.lower():
                operation = "pc_move"
            elif "pc_copy" in prompt.lower():
                operation = "pc_copy"
            elif "pc_delete" in prompt.lower():
                operation = "pc_delete"
            elif "pc_mkdir" in prompt.lower():
                operation = "pc_mkdir"
            elif "pc_list" in prompt.lower():
                operation = "pc_list"
            elif "pc_exec" in prompt.lower():
                operation = "pc_exec"
            elif "pc_write_file" in prompt.lower():
                operation = "pc_write_file"

            result = self._shalltear.parse_nl_to_params(prompt, operation=operation)
            if result and "operations" in result and result["operations"]:
                # Devolver el primer operation como JSON
                import json

                return json.dumps(result["operations"][0].get("params", {}))
            return "{}"
        except Exception as e:
            logger.debug("Shalltear extract error: %s", e)
            return "{}"

    def extract(self, message: str, operation: str) -> Dict[str, Any]:
        """Extrae parámetros de `message` para `operation` (sync)."""
        if self._llm:
            try:
                return self._extract_with_llm(message, operation)
            except Exception as e:
                logger.debug("NLParamExtractor LLM fallback: %s", e)
        return _heuristic_extract(operation, message)

    def _extract_with_llm(self, message: str, operation: str) -> Dict[str, Any]:
        prompt = _EXTRACT_PROMPT.format(message=message, operation=operation)
        raw = self._llm(
            system="Extrae parámetros como JSON puro. Responde SOLO con el objeto JSON.",
            prompt=prompt,
        )
        clean = (raw or "").strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
        parsed = json.loads(clean)
        # Resolver aliases en valores de ruta
        result: Dict[str, Any] = {}
        for k, v in parsed.items():
            if v is None:
                continue
            if k in ("path", "source", "destination", "cwd") and isinstance(v, str):
                result[k] = _resolve_path(v)
            else:
                result[k] = v
        return result


# ─── Singleton ────────────────────────────────────────────────────────────────

_extractor: Optional[NLParamExtractor] = None


def get_nl_param_extractor(llm_fn=None) -> NLParamExtractor:
    global _extractor
    if _extractor is None:
        _extractor = NLParamExtractor(llm_fn)
    return _extractor
