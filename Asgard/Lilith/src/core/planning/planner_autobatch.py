"""
Planner Auto-Batch — Agrupa múltiples operaciones PC en un solo batch.

Este módulo detecta cuando un mensaje contiene múltiples operaciones
de filesystem relacionadas y las agrupa para confirmación única.
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.planner.autobatch")


@dataclass
class PCOperation:
    """Representa una operación PC detectada."""

    op_type: str  # mkdir, copy, move, delete, list, exec, write_file
    source: str = ""
    destination: str = ""
    path: str = ""
    content: str = ""
    command: str = ""
    confidence: float = 0.0


# Palabras clave para detectar operaciones PC
_OP_KEYWORDS = {
    "mkdir": ["crea carpeta", "crear carpeta", "nueva carpeta", "mkdir", "directorio"],
    "copy": [
        "copia",
        "copiar",
        "duplicate",
        "duplica",
        "backup",
        "respalda",
        "respaldar",
    ],
    "move": ["mueve", "mover", "traslada", "trasladar", "mv"],
    "delete": [
        "borra",
        "borrar",
        "elimina",
        "eliminar",
        "delete",
        "remove",
        "limpia",
        "limpiar",
    ],
    "list": [
        "lista",
        "listar",
        "qué hay",
        "que hay",
        "muestra",
        "ver",
        "contenido",
        "archivos",
    ],
    "exec": [
        "ejecuta",
        "ejecutar",
        "corre",
        "correr",
        "run",
        "compila",
        "compilar",
        "build",
    ],
    "write_file": ["crea archivo", "nuevo archivo", "escribe", "escribir"],
}

# Separadores que indican múltiples operaciones
_BATCH_SEPARATORS = [
    r",\s*(?:luego|después|despues|then|and)\s+",
    r"\s+y\s+(?:luego|después|despues|then)\s+",
    r";\s*",
    r"\s+→\s+",
    r"\s+->\s+",
    r"\s+=>\s+",
    r"\n",
]

# Rutas conocidas
_PATH_ALIASES = {
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
    """Resuelve aliases de ruta."""
    if not path:
        return path
    p = path.strip().strip('"').strip("'")
    lower = p.lower()

    # Alias exacto
    if lower in _PATH_ALIASES:
        import os

        return os.path.expandvars(_PATH_ALIASES[lower])

    # Alias + subruta
    for alias, real in _PATH_ALIASES.items():
        if (
            lower.startswith(alias + "/")
            or lower.startswith(alias + "\\")
            or lower.startswith(alias + " ")
        ):
            remainder = p[len(alias) :].lstrip("/\\ ")
            import os

            expanded = os.path.expandvars(real)
            return expanded + "\\" + remainder if remainder else expanded

    return p


def _extract_path(text: str) -> Optional[str]:
    """Extrae una ruta de Windows o alias del texto."""
    # Patrón: ruta Windows (D:\...)
    win_path_match = re.search(r'[A-Za-z]:\\[^,"\';\n]*', text)
    if win_path_match:
        return _resolve_path(win_path_match.group(0))

    # Patrón: alias conocido
    words = text.lower().split()
    for word in words:
        if word in _PATH_ALIASES:
            return _resolve_path(word)

    # Patrón: "en X" o "de X"
    en_match = re.search(r'(?:en|de)\s+(["\']?[^"\',;\n]+["\']?)', text, re.IGNORECASE)
    if en_match:
        return _resolve_path(en_match.group(1).strip("\"'"))

    return None


def _detect_operation(text: str) -> Optional[PCOperation]:
    """
    Detecta una operación PC en un fragmento de texto.
    Retorna PCOperation o None si no es operación PC.
    """
    text_lower = text.lower().strip()

    # Detectar tipo de operación
    op_type = None
    confidence = 0.0

    for op, keywords in _OP_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                # Calcular confianza basada en posición y contexto
                conf = 0.8
                if text_lower.startswith(kw):
                    conf = 0.95  # Comienza con la keyword = alta confianza
                op_type = op
                confidence = conf
                break
        if op_type:
            break

    if not op_type:
        return None

    # Extraer rutas y parámetros según el tipo
    op = PCOperation(op_type=op_type, confidence=confidence)

    if op_type == "mkdir":
        # "crea carpeta X en Y" o "mkdir X"
        path = _extract_path(text)
        if path:
            op.path = path

    elif op_type in ("copy", "move"):
        # Buscar "X a Y" o "X → Y" o "X -> Y"
        src_dst_match = re.search(
            r'(["\']?[^"\'→\->]+["\']?)\s+(?:a|→|->|to)\s+(["\']?[^"\',;\n]+["\']?)',
            text,
            re.IGNORECASE,
        )
        if src_dst_match:
            op.source = _resolve_path(src_dst_match.group(1).strip())
            op.destination = _resolve_path(src_dst_match.group(2).strip())
        else:
            # Fallback: extraer dos rutas
            paths = re.findall(r'[A-Za-z]:\\[^,"\';\n]*|\b\w+:\s*[^,"\';\n]*', text)
            if len(paths) >= 2:
                op.source = _resolve_path(paths[0])
                op.destination = _resolve_path(paths[1])
            elif len(paths) == 1:
                op.source = _resolve_path(paths[0])

    elif op_type == "delete":
        path = _extract_path(text)
        if path:
            op.path = path

    elif op_type == "list":
        path = _extract_path(text)
        if path:
            op.path = path
        else:
            # Default: listar directorio actual
            op.path = "."

    elif op_type == "exec":
        # Extraer comando después de keywords
        for prefix in [
            "ejecuta ",
            "ejecutar ",
            "corre ",
            "correr ",
            "run ",
            "compila ",
            "compilar ",
            "build ",
        ]:
            if text_lower.startswith(prefix):
                op.command = text[len(prefix) :].strip()
                break
        if not op.command:
            # Intentar extraer entre comillas o hasta el final
            cmd_match = re.search(r'["\']([^"\']+)["\']', text)
            if cmd_match:
                op.command = cmd_match.group(1)

    elif op_type == "write_file":
        path = _extract_path(text)
        if path:
            op.path = path
        # Intentar extraer contenido después de "con" o "conteniendo"
        content_match = re.search(
            r'(?:con|conteniendo|with)\s+["\']([^"\']+)["\']', text, re.IGNORECASE
        )
        if content_match:
            op.content = content_match.group(1)

    return op


def _split_into_segments(text: str) -> List[str]:
    """
    Divide un mensaje en segmentos que podrían ser operaciones individuales.
    """
    segments = [text]

    for sep in _BATCH_SEPARATORS:
        new_segments = []
        for seg in segments:
            parts = re.split(sep, seg, flags=re.IGNORECASE)
            new_segments.extend(p.strip() for p in parts if p.strip())
        segments = new_segments

    return segments


def detect_pc_batch(text: str) -> Tuple[bool, List[PCOperation]]:
    """
    Detecta si un mensaje contiene múltiples operaciones PC.

    Retorna:
        (es_batch, lista_de_operaciones)
    """
    if not text or not isinstance(text, str):
        return False, []

    # Primero: intentar dividir en segmentos
    segments = _split_into_segments(text)

    operations = []
    for seg in segments:
        op = _detect_operation(seg)
        if op and op.confidence >= 0.7:
            operations.append(op)

    # Si no se detectaron operaciones por segmentos, intentar con el texto completo
    if not operations:
        op = _detect_operation(text)
        if op:
            operations.append(op)

    # Es un batch si hay 2+ operaciones
    is_batch = len(operations) >= 2

    logger.debug(
        f"detect_pc_batch: segments={len(segments)}, ops={len(operations)}, is_batch={is_batch}"
    )

    return is_batch, operations


def operations_to_steps(operations: List[PCOperation]) -> List[Dict[str, Any]]:
    """
    Convierte operaciones PC detectadas a steps del planner.
    """
    steps = []

    for op in operations:
        if op.op_type == "mkdir":
            steps.append({"tool": "pc_mkdir", "params": {"path": op.path}})

        elif op.op_type == "copy":
            steps.append(
                {
                    "tool": "pc_copy",
                    "params": {"source": op.source, "destination": op.destination},
                }
            )

        elif op.op_type == "move":
            steps.append(
                {
                    "tool": "pc_move",
                    "params": {"source": op.source, "destination": op.destination},
                }
            )

        elif op.op_type == "delete":
            steps.append({"tool": "pc_delete", "params": {"path": op.path}})

        elif op.op_type == "list":
            steps.append({"tool": "pc_list", "params": {"path": op.path}})

        elif op.op_type == "exec":
            steps.append(
                {"tool": "pc_exec", "params": {"command": op.command, "path": "."}}
            )

        elif op.op_type == "write_file":
            steps.append(
                {
                    "tool": "pc_write_file",
                    "params": {"path": op.path, "content": op.content},
                }
            )

    return steps


def should_auto_batch(text: str, steps: List[Any]) -> bool:
    """
    Determina si los steps generados deberían agruparse en un batch.

    Criterios:
    - 2+ operaciones PC en el mensaje
    - Las operaciones están relacionadas (mismo contexto/ruta)
    """
    is_batch, operations = detect_pc_batch(text)

    if not is_batch:
        return False

    # Verificar que las operaciones estén relacionadas
    # (mismo directorio base o contexto similar)
    base_paths = set()
    for op in operations:
        for path in [op.path, op.source, op.destination]:
            if path:
                # Extraer directorio base
                if "\\" in path:
                    base_paths.add(path.rsplit("\\", 1)[0])
                else:
                    base_paths.add(path)

    # Si comparten el mismo directorio base, están relacionadas
    if len(base_paths) == 1:
        return True

    # Si hay 2+ operaciones pero rutas diferentes,
    # aún así hacer batch si son pocas operaciones (usuario sabe lo que hace)
    if len(operations) <= 4:
        return True

    return False


def build_batch_step(operations: List[PCOperation]) -> Dict[str, Any]:
    """
    Construye un step pc_operation_batch a partir de operaciones detectadas.
    """
    steps = operations_to_steps(operations)

    return {
        "tool": "pc_operation_batch",
        "params": {
            "operations": steps,
            "description": f"Batch de {len(steps)} operaciones PC",
        },
    }


# ─── Integración con Planner ─────────────────────────────────────────────────


def try_auto_batch(text: str, existing_steps: List[Any]) -> Optional[List[Any]]:
    """
    Intenta convertir steps individuales PC en un batch.

    Args:
        text: Mensaje original del usuario
        existing_steps: Steps generados por el planner

    Retorna:
        Lista de steps modificada con batch, o None si no aplica
    """
    from src.core.planner import Step

    # Verificar si ya hay un batch
    for step in existing_steps:
        if hasattr(step, "tool_name") and step.tool_name in (
            "pc_operation_batch",
            "pc_batch",
        ):
            return None  # Ya es batch

    # Verificar si hay múltiples operaciones PC
    pc_steps = [
        s
        for s in existing_steps
        if hasattr(s, "tool_name") and s.tool_name.startswith("pc_")
    ]

    if len(pc_steps) < 2:
        return None  # No hay suficientes operaciones para batch

    # Verificar si deberían agruparse
    if not should_auto_batch(text, existing_steps):
        return None

    # Crear batch
    is_batch, operations = detect_pc_batch(text)
    if not is_batch:
        # Fallback: crear batch desde steps existentes
        batch_steps = []
        for step in pc_steps:
            batch_steps.append(
                {"tool": step.tool_name, "params": getattr(step, "params", {})}
            )

        operations = []
        for bs in batch_steps:
            op_type = bs["tool"].replace("pc_", "")
            op = PCOperation(op_type=op_type)
            params = bs.get("params", {})
            op.path = params.get("path", "")
            op.source = params.get("source", "")
            op.destination = params.get("destination", "")
            op.command = params.get("command", "")
            operations.append(op)

    # Construir step de batch
    batch_step_data = build_batch_step(operations)

    # Reconstruir lista de steps: mantener no-PC, reemplazar PC con batch
    new_steps = []
    batch_added = False

    for step in existing_steps:
        if hasattr(step, "tool_name") and step.tool_name.startswith("pc_"):
            if not batch_added:
                new_steps.append(
                    Step(
                        tool_name=batch_step_data["tool"],
                        params=batch_step_data["params"],
                    )
                )
                batch_added = True
        else:
            new_steps.append(step)

    logger.info(f"Auto-batch creado: {len(pc_steps)} operaciones -> 1 batch")

    return new_steps
