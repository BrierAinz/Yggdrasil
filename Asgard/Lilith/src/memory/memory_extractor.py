"""
Lilith v2.2 — Fase C: Memory Extractor
Detecta errores+solución, decisiones de arquitectura y archivos en cada par (user, assistant)
y actualiza procedural_memory y semantic_memory.
"""
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("MemoryExtractor")

# Usuario: indica que hay un error (fallback basado en regex)
USER_ERROR_PAT = re.compile(
    r"\b(error|exception|traceback|falla|no funciona|failed|NameError|TypeError|AttributeError|KeyError|ImportError)\b",
    re.I,
)
# Asistente: indica que dio una solución (fallback)
ASSISTANT_SOLUTION_PAT = re.compile(
    r"\b(solución|fix|cambiar|agregar|el problema era|debes|tienes que|usa |añade|declare|global |import )\b",
    re.I,
)
# Asistente: indica decisión de arquitectura (fallback)
ASSISTANT_DECISION_PAT = re.compile(
    r"\b(decidimos|usaremos|la arquitectura|mejor opción|recomiendo usar|conviene usar|establecemos)\b",
    re.I,
)
# Archivos mencionados: algo.py o path/to/file.ext
FILE_PAT = re.compile(
    r"(?:^|[\s\[\(])([A-Za-z_][A-Za-z0-9_]*\.(?:py|js|ts|tsx|json|md|txt|bat|yml|yaml))(?:[\s\]\)]|$)",
    re.I,
)
# Archivo en texto tipo "en main.py" / "in main.py"
FILE_EN_PAT = re.compile(
    r"\b(?:en|in|file|archivo)\s+([A-Za-z_][A-Za-z0-9_]*\.(?:py|js|ts|json|md))\b",
    re.I,
)


class MemoryExtractor:
    """
    Extrae de cada par (user_msg, assistant_msg): errores+solución, decisiones,
    archivos; y actualiza procedural_memory y semantic_memory.
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)

    async def extract_and_store(
        self,
        user_msg: str,
        assistant_msg: str,
        on_stored: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """
        Detecta y persiste: (a) error+solución, (b) decisión de arquitectura,
        (c) archivos mencionados. Si on_stored se proporciona, se llama con
        (type, summary) cada vez que se guarda algo ("error"|"decision"|"file").
        """
        if not user_msg and not assistant_msg:
            return
        user_msg = (user_msg or "").strip()
        assistant_msg = (assistant_msg or "").strip()

        used_semantic = False

        # ── Nuevo flujo: clasificación semántica con Eva ──────────────────────
        classification = await self._classify_with_eva(user_msg, assistant_msg)
        if classification:
            try:
                tipo = (classification.get("tipo") or "ninguno").strip()
                datos: Dict[str, Any] = classification.get("datos") or {}
                confianza = float(classification.get("confianza") or 0.0)
            except Exception:
                tipo, datos, confianza = "ninguno", {}, 0.0

            if confianza >= 0.7 and tipo != "ninguno":
                logger.info(
                    "MemoryExtractor: clasificación Eva tipo=%s confianza=%.2f",
                    tipo,
                    confianza,
                )
                try:
                    if tipo == "error_solucion":
                        from src.core.memory.procedural_memory import ProceduralMemory

                        proc = ProceduralMemory(self.base_path)
                        error_text = datos.get("error") or user_msg[:400]
                        archivo = datos.get("archivo") or datos.get("file") or ""
                        solucion = (
                            datos.get("solucion")
                            or datos.get("solución")
                            or assistant_msg[:1500]
                        )
                        await proc.record_error(error_text, archivo, solucion)
                        used_semantic = True
                        if on_stored:
                            summary = (
                                f"Error en {archivo or 'código'} registrado"
                                if archivo
                                else "Error registrado"
                            )
                            try:
                                on_stored("error", summary)
                            except Exception:
                                pass

                    elif tipo == "decision_arquitectura":
                        from src.core.memory.semantic_memory import SemanticMemory

                        sem = SemanticMemory(self.base_path)
                        decision = datos.get("decision") or assistant_msg[:500]
                        contexto = (
                            datos.get("contexto") or user_msg[:300] or "Conversación"
                        )
                        proyecto = datos.get("proyecto") or "Lilith"
                        sem.record_architecture_decision(
                            decision=decision,
                            context=contexto,
                            project=proyecto,
                        )
                        used_semantic = True
                        if on_stored:
                            try:
                                resumen = (
                                    (decision[:80] + "…")
                                    if len(decision) > 80
                                    else decision
                                )
                                on_stored("decision", resumen)
                            except Exception:
                                pass

                    elif tipo == "preferencia_usuario":
                        from src.core.memory.semantic_memory import SemanticMemory

                        sem = SemanticMemory(self.base_path)
                        key = datos.get("preferencia")
                        value = datos.get("valor")
                        if key and value:
                            await sem.update_preference(str(key), str(value))
                            used_semantic = True
                            if on_stored:
                                try:
                                    on_stored("preference", f"{key}={value}")
                                except Exception:
                                    pass

                    elif tipo == "aprendizaje_codigo":
                        from src.core.memory.semantic_memory import SemanticMemory

                        sem = SemanticMemory(self.base_path)
                        pattern = datos.get("patron") or datos.get("patrón") or ""
                        ejemplo = datos.get("ejemplo") or ""
                        if pattern:
                            await sem.update_code_style_pattern(
                                str(pattern), str(ejemplo)
                            )
                            used_semantic = True
                            if on_stored:
                                try:
                                    on_stored("code_style", pattern[:80])
                                except Exception:
                                    pass

                except Exception as e:
                    logger.warning(
                        "MemoryExtractor semantic classification handling failed: %s", e
                    )

        # ── Fallback regex para errores/decisiones si no se usó clasificación ─
        if not used_semantic:
            # (a) Error + solución (regex clásico)
            if USER_ERROR_PAT.search(user_msg) and ASSISTANT_SOLUTION_PAT.search(
                assistant_msg
            ):
                try:
                    from src.core.memory.procedural_memory import ProceduralMemory

                    proc = ProceduralMemory(self.base_path)
                    error_snippet = user_msg[:400]
                    file_match = FILE_EN_PAT.search(user_msg) or FILE_PAT.search(
                        user_msg
                    )
                    file_name = file_match.group(1) if file_match else ""
                    solution_snippet = assistant_msg[:1500]
                    await proc.record_error(error_snippet, file_name, solution_snippet)
                    if on_stored:
                        summary = (
                            f"Error en {file_name or 'código'} registrado"
                            if file_name
                            else "Error registrado"
                        )
                        try:
                            on_stored("error", summary)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(
                        "MemoryExtractor record_error (regex fallback): %s", e
                    )

            # (b) Decisión de arquitectura (regex clásico)
            if ASSISTANT_DECISION_PAT.search(assistant_msg):
                try:
                    from src.core.memory.semantic_memory import SemanticMemory

                    sem = SemanticMemory(self.base_path)
                    decision_snippet = assistant_msg[:500]
                    sem.record_architecture_decision(
                        decision=decision_snippet,
                        context=user_msg[:300] or "Conversación",
                        project="Lilith",
                    )
                    if on_stored:
                        try:
                            resumen = (
                                (decision_snippet[:80] + "…")
                                if len(decision_snippet) > 80
                                else decision_snippet
                            )
                            on_stored("decision", resumen)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(
                        "MemoryExtractor record_architecture_decision (regex fallback): %s",
                        e,
                    )

        # (c) Archivos mencionados → projects.json ultima_actividad (se mantiene)
        files = set()
        for m in FILE_PAT.finditer(user_msg + " " + assistant_msg):
            files.add(m.group(1))
        for m in FILE_EN_PAT.finditer(user_msg + " " + assistant_msg):
            files.add(m.group(1))
        if files:
            try:
                from src.core.memory.semantic_memory import SemanticMemory

                sem = SemanticMemory(self.base_path)
                from datetime import datetime

                projects = sem.load_projects()
                if "Lilith" not in projects or not isinstance(projects["Lilith"], dict):
                    projects["Lilith"] = {}
                projects["Lilith"]["ultima_actividad"] = (
                    datetime.utcnow().isoformat() + "Z"
                )
                projects["Lilith"]["archivos_recientes"] = list(files)[:30]
                sem.save_projects(projects)
                if on_stored:
                    try:
                        on_stored(
                            "file", f"{len(files)} archivo(s) en ultima_actividad"
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("MemoryExtractor update projects: %s", e)

    # ── Clasificador semántico con Eva ─────────────────────────────────────────

    async def _classify_with_eva(
        self, user_msg: str, assistant_msg: str
    ) -> Optional[Dict[str, Any]]:
        """
        Usa Eva (Grok) para clasificar el intercambio en tipos de memoria.
        Devuelve dict con claves: tipo, datos, confianza; o None si falla.
        """
        text_user = (user_msg or "")[:500]
        text_assistant = (assistant_msg or "")[:800]
        if not (text_user or text_assistant):
            return None

        prompt = f"""Analiza este intercambio y responde SOLO con JSON:

Usuario: {text_user}
Asistente: {text_assistant}

{{{chr(10)}  "tipo": "error_solucion" | "decision_arquitectura" | "preferencia_usuario" | "aprendizaje_codigo" | "ninguno",
  "datos": {{
    // error_solucion: "error", "archivo", "solucion"
    // decision_arquitectura: "decision", "contexto", "proyecto"
    // preferencia_usuario: "preferencia", "valor"
    // aprendizaje_codigo: "patron", "ejemplo"
  }},
  "confianza": 0.0
}}"""

        try:
            from src.core.agents.panteon.eva import EvaAgent

            eva = EvaAgent()
            if not eva.is_available():
                logger.debug(
                    "Eva no disponible para MemoryExtractor; usando regex fallback."
                )
                return None

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: eva.execute(task="Clasifica el intercambio.", context=prompt),
            )

            if not response:
                return None

            data = self._parse_json_from_response(response)
            if not isinstance(data, dict):
                return None
            return data
        except Exception as e:
            logger.warning("MemoryExtractor _classify_with_eva failed: %s", e)
            return None

    @staticmethod
    def _parse_json_from_response(response: str) -> Optional[Dict[str, Any]]:
        """Extrae un objeto JSON de una respuesta potencialmente envuelta en markdown."""
        if not response:
            return None
        text = response.strip()
        # Si viene en bloque ```json ... ```
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        # Buscar primer { y último }
        start = text.find("{")
        if start == -1:
            return None
        end = text.rfind("}")
        if end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
