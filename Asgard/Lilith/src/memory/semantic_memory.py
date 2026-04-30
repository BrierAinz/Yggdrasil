"""
Lilith v2.2 — Memoria Semántica (Fase A)
Carga/guarda user_profile, projects, code_style, architecture_decisions.
Carga JSON vía json_safe para no fallar nunca por JSON inválido.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SemanticMemory")

# Nombres de archivos en memory/semantic/
USER_PROFILE_FILE = "user_profile.json"
PROJECTS_FILE = "projects.json"
CODE_STYLE_FILE = "code_style.json"
ARCH_DECISIONS_FILE = "architecture_decisions.json"
FACTS_FILE = "facts.jsonl"  # Misión 3.2 (D.1): hechos recientes (perfil vs hechos)


class SemanticMemory:
    """
    Memoria semántica: perfil de usuario, proyectos, estilo de código y decisiones de arquitectura.
    Los JSON se guardan en memory/semantic/.
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        self.semantic_dir = self.base_path / "memory" / "semantic"
        self.semantic_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        return self.semantic_dir / filename

    # ── Load / Save por archivo ─────────────────────────────────────────────

    def load_user_profile(self) -> Dict[str, Any]:
        from src.core.json_safe import safe_load

        out = safe_load(self._path(USER_PROFILE_FILE), default={})
        return out if isinstance(out, dict) else {}

    def save_user_profile(self, data: Dict[str, Any]) -> None:
        p = self._path(USER_PROFILE_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_projects(self) -> Dict[str, Any]:
        from src.core.json_safe import safe_load

        out = safe_load(self._path(PROJECTS_FILE), default={})
        return out if isinstance(out, dict) else {}

    def save_projects(self, data: Dict[str, Any]) -> None:
        p = self._path(PROJECTS_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_code_style(self) -> Dict[str, Any]:
        from src.core.json_safe import safe_load

        out = safe_load(self._path(CODE_STYLE_FILE), default={})
        return out if isinstance(out, dict) else {}

    def save_code_style(self, data: Dict[str, Any]) -> None:
        p = self._path(CODE_STYLE_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_architecture_decisions(self) -> List[Dict[str, Any]]:
        from src.core.json_safe import safe_load

        out = safe_load(self._path(ARCH_DECISIONS_FILE), default=[])
        return out if isinstance(out, list) else []

    def save_architecture_decisions(self, data: List[Dict[str, Any]]) -> None:
        p = self._path(ARCH_DECISIONS_FILE)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ── Hechos recientes (Misión 3.2 D.1: perfil vs hechos) ──────────────────

    def _memory_config(self) -> Dict[str, Any]:
        """Carga Config/memory.json. Nunca falla por JSON."""
        from src.core.json_safe import safe_load

        out = safe_load(self.base_path / "Config" / "memory.json", default={})
        return out if isinstance(out, dict) else {}

    def add_fact(
        self, text: str, source_id: Optional[str] = None, topic: Optional[str] = None
    ) -> None:
        """
        Añade un hecho reciente (D.1/D.2). JSONL + vector store (D.3a).
        4.0: source_id y topic opcionales; chunking con overlap; topic permite filtrar búsqueda por dominio.
        Atomicidad: se escribe primero en ChromaDB; si falla, no se escribe JSONL (evita split-brain).
        """
        raw = (text or "").strip()
        if not raw:
            return
        import hashlib
        from datetime import datetime, timezone

        cfg = self._memory_config()
        chunk_threshold = max(400, int(cfg.get("vector_chunk_threshold") or 500))
        path = self._path(FACTS_FILE)
        ts = datetime.now(timezone.utc).isoformat()
        topic_str = (topic or "").strip() or None
        try:
            from src.core.memory.semantic.vector_store import add_fact as vs_add_fact
            from src.core.memory.semantic.vector_store import is_available

            if len(raw) <= chunk_threshold:
                entry = {
                    "ts": ts,
                    "text": raw[:2000],
                    "source_id": source_id,
                    "topic": topic_str,
                }
                if is_available(self.base_path):
                    vs_add_fact(
                        self.base_path,
                        fact_id=ts,
                        fact_text=entry["text"],
                        source_id=source_id,
                        topic=topic_str,
                    )
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                logger.debug("SemanticMemory: added fact")
                return
            sid = source_id or hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            from src.core.memory.semantic.vector_store import chunk_text

            chunk_size = max(300, int(cfg.get("vector_chunk_size") or 450))
            overlap = min(100, int(cfg.get("vector_chunk_overlap") or 50))
            chunks = chunk_text(raw, chunk_size=chunk_size, overlap=overlap)
            entries_to_append = []
            if is_available(self.base_path):
                for i, ch in enumerate(chunks):
                    fact_id_i = f"{sid}_chunk_{i}"
                    vs_add_fact(
                        self.base_path,
                        fact_id=fact_id_i,
                        fact_text=ch,
                        source_id=sid,
                        topic=topic_str,
                    )
                    entries_to_append.append(
                        {
                            "ts": ts,
                            "text": ch[:2000],
                            "source_id": sid,
                            "topic": topic_str,
                        }
                    )
            else:
                for i, ch in enumerate(chunks):
                    entries_to_append.append(
                        {
                            "ts": ts,
                            "text": ch[:2000],
                            "source_id": sid,
                            "topic": topic_str,
                        }
                    )
            with open(path, "a", encoding="utf-8") as f:
                for entry in entries_to_append:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.debug(
                "SemanticMemory: added %d chunks (source_id=%s)", len(chunks), sid
            )
        except Exception as e:
            logger.warning("SemanticMemory: add_fact failed: %s", e)

    def get_recent_facts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Devuelve los últimos N hechos (para no saturar el prompt). Nunca falla por JSON."""
        from src.core.json_safe import safe_load_lines

        path = self._path(FACTS_FILE)
        cfg = self._memory_config()
        limit = int(cfg.get("max_facts") or 0) or limit
        all_entries = safe_load_lines(path, default=[])
        valid = [e for e in all_entries if isinstance(e, dict)]
        return list(reversed(valid[-limit:]))[:limit]

    # ── Contexto para el prompt ──────────────────────────────────────────────

    def _expand_query_with_synonyms(self, query: str) -> str:
        """3.6: expande la query con sinónimos de Config/memory.json query_synonyms para mejorar búsqueda."""
        cfg = self._memory_config()
        syn_map = cfg.get("query_synonyms")
        if not isinstance(syn_map, dict) or not query or not query.strip():
            return query.strip()
        expanded = [query.strip()]
        words = query.strip().lower().split()
        for w in words:
            if w in syn_map and isinstance(syn_map[w], list):
                expanded.extend(str(s).strip() for s in syn_map[w] if s)
        return " ".join(expanded)[:2000]

    def _get_facts_for_query(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """D.3a: si hay query y vector store, hechos por similitud (3.6: query expandida con sinónimos); si no, últimos N por recencia."""
        if query and query.strip():
            try:
                from src.core.memory.semantic.vector_store import (
                    is_available,
                    search_facts,
                )

                if is_available(self.base_path):
                    cfg = self._memory_config()
                    k = int(cfg.get("vector_facts_k") or 0) or 5
                    search_query = self._expand_query_with_synonyms(query)
                    topic_filter = (
                        cfg.get("vector_topic_filter") or ""
                    ).strip() or None
                    results = search_facts(
                        self.base_path,
                        search_query,
                        k=k,
                        k_candidates_multiplier=max(
                            1, int(cfg.get("vector_candidates_multiplier") or 3)
                        ),
                        diversity_strategy=(
                            cfg.get("vector_diversity_strategy") or "one_per_source"
                        ).strip()
                        or "one_per_source",
                        topic=topic_filter,
                    )
                    # Zero-hit fallback: si el filtro por topic devuelve 0 resultados, reintentar sin filtro (preguntas híbridas)
                    if topic_filter and not results:
                        results = search_facts(
                            self.base_path,
                            search_query,
                            k=k,
                            k_candidates_multiplier=max(
                                1, int(cfg.get("vector_candidates_multiplier") or 3)
                            ),
                            diversity_strategy=(
                                cfg.get("vector_diversity_strategy") or "one_per_source"
                            ).strip()
                            or "one_per_source",
                            topic=None,
                        )
                    if results:
                        max_dist = cfg.get("vector_max_distance")
                        if max_dist is not None and max_dist != "":
                            try:
                                threshold = float(max_dist)
                                if threshold > 0:
                                    results = [
                                        r
                                        for r in results
                                        if r.get("distance") is None
                                        or r.get("distance") <= threshold
                                    ]
                            except (TypeError, ValueError):
                                pass
                        return [{"text": r.get("text") or ""} for r in results]
            except Exception:
                pass
        return self.get_recent_facts()

    def get_context_for_prompt(self, query: Optional[str] = None) -> str:
        """
        Devuelve un resumen en texto del perfil (estable) y hechos (D.1/D.3a: por query o recientes).
        query: si se pasa, y hay vector store, los hechos se eligen por similitud a query.
        """
        profile = self.load_user_profile()
        lines = []
        if profile:
            nombre = profile.get("nombre", "Usuario")
            edad = profile.get("edad")
            if edad is not None:
                lines.append(f"- Nombre: {nombre}, edad: {edad}.")
            proyectos = profile.get("proyectos", {})
            activos = [
                (k, v)
                for k, v in proyectos.items()
                if isinstance(v, dict) and v.get("estado") == "activo"
            ]
            if activos:
                lines.append("- Proyectos activos:")
                for name, info in activos:
                    tipo = info.get("tipo", "proyecto")
                    lines.append(f"  · {name}: {tipo}.")
            preferencias = profile.get("preferencias", {})
            if preferencias:
                pref_str = ", ".join(f"{k}={v}" for k, v in preferencias.items())
                lines.append(f"- Preferencias: {pref_str}.")
            code_style = self.load_code_style()
            if code_style:
                lines.append("- Tiene preferencias de estilo de código registradas.")
        else:
            lines.append("No hay perfil de usuario cargado.")

        facts = self._get_facts_for_query(query)
        if facts:
            lines.append("- [Hechos recientes]:")
            for f in reversed(facts):
                text = (f.get("text") or "").strip()
                if text:
                    lines.append(f"  · {text}")

        return "\n".join(lines) if lines else "Sin contexto adicional."

    # ── Registrar decisión de arquitectura ──────────────────────────────────

    def record_architecture_decision(
        self,
        decision: str,
        context: str,
        project: str,
    ) -> None:
        """Añade una decisión de arquitectura a la lista y persiste."""
        decisions = self.load_architecture_decisions()
        from datetime import datetime

        decisions.append(
            {
                "decision": decision,
                "context": context,
                "project": project,
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        self.save_architecture_decisions(decisions)
        logger.info("Recorded architecture decision for project %s", project)

    # ── Actualizar desde resumen de sesión (Fase B) ────────────────────────────

    def update_from_session(self, summary: Dict[str, Any]) -> None:
        """
        Actualiza memoria semántica a partir del resumen de sesión generado por SessionSummarizer.
        - decisiones_arquitectura → append a architecture_decisions.json
        - archivos_modificados → actualiza projects.json con ultima_actividad
        """
        if not summary:
            return
        from datetime import datetime

        now = datetime.utcnow().isoformat() + "Z"
        context = summary.get("resumen", "") or "Resumen de sesión"

        decisiones = summary.get("decisiones_arquitectura") or []
        if decisiones:
            current = self.load_architecture_decisions()
            for d in decisiones:
                if isinstance(d, str) and d.strip():
                    current.append(
                        {
                            "decision": d.strip(),
                            "context": context,
                            "project": "Lilith",
                            "recorded_at": now,
                            "source": "session_summary",
                        }
                    )
            self.save_architecture_decisions(current)
            logger.info(
                "Updated architecture_decisions from session (%d new)", len(decisiones)
            )

        archivos = summary.get("archivos_modificados") or []
        if archivos:
            projects = self.load_projects()
            # Actualizar proyecto Lilith (o clave por defecto) con ultima_actividad
            if "Lilith" not in projects or not isinstance(projects["Lilith"], dict):
                projects["Lilith"] = {}
            pl = projects["Lilith"]
            if not isinstance(pl, dict):
                pl = {}
            pl["ultima_actividad"] = now
            pl["archivos_recientes"] = list(archivos)[:50]
            projects["Lilith"] = pl
            self.save_projects(projects)
            logger.info(
                "Updated projects.json ultima_actividad (%d archivos)", len(archivos)
            )

    # ── Preferencias y patrones aprendidos ─────────────────────────────────────

    async def update_preference(self, key: str, value: str) -> None:
        """
        Guarda una preferencia aprendida del usuario en user_profile.json
        bajo la clave \"preferencias_aprendidas\".
        """
        if not key:
            return
        profile = self.load_user_profile()
        prefs = profile.get("preferencias_aprendidas") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        prefs[key] = value
        profile["preferencias_aprendidas"] = prefs
        self.save_user_profile(profile)
        logger.info("SemanticMemory: updated learned preference %s=%s", key, value)

    async def update_code_style_pattern(self, pattern: str, ejemplo: str = "") -> None:
        """
        Guarda un nuevo patrón de estilo de código aprendido en code_style.json
        bajo la clave \"patrones_aprendidos\".
        """
        pattern = (pattern or "").strip()
        ejemplo = (ejemplo or "").strip()
        if not pattern:
            return
        data = self.load_code_style()
        patrones = data.get("patrones_aprendidos") or []
        if not isinstance(patrones, list):
            patrones = []
        from datetime import datetime

        patrones.append(
            {
                "pattern": pattern,
                "ejemplo": ejemplo,
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        # Mantener últimos 50 patrones
        data["patrones_aprendidos"] = patrones[-50:]
        self.save_code_style(data)
        logger.info("SemanticMemory: added code style pattern")

    # ── Actualizar estilo de código (con Eva) ──────────────────────────────────

    def update_code_style(self, samples: List[str]) -> Dict[str, Any]:
        """
        Analiza los fragmentos de código con Eva y actualiza code_style.json.
        Si Eva no está disponible, devuelve el code_style actual sin modificar.
        """
        if not samples:
            return self.load_code_style()

        try:
            from src.core.agents.panteon.eva import EvaAgent

            eva = EvaAgent()
            if not eva.is_available():
                logger.warning(
                    "Eva no disponible para análisis de estilo; code_style sin cambios."
                )
                return self.load_code_style()

            context = "\n\n---\n\n".join(samples[:10])  # límite razonable
            task = """Analiza los fragmentos de código anteriores y extrae reglas de estilo en formato JSON.
Incluye solo claves que puedas inferir, por ejemplo: naming (variables, funciones, clases),
indentación, comillas, longitud de líneas, documentación (docstrings sí/no), etc.
Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después."""

            response = eva.execute(task=task, context=context)
            current = self.load_code_style()

            # Intentar extraer JSON de la respuesta
            response = (response or "").strip()
            for start in ("{", "```json", "```"):
                idx = response.find(start)
                if idx != -1:
                    if start == "```json":
                        idx = response.find("{", idx)
                    if idx != -1:
                        end = response.rfind("}") + 1
                        if end > idx:
                            try:
                                new_rules = json.loads(response[idx:end])
                                if isinstance(new_rules, dict):
                                    current.update(new_rules)
                                    self.save_code_style(current)
                                    logger.info("Code style updated from Eva analysis.")
                                    return current
                            except json.JSONDecodeError:
                                pass
            logger.warning("Eva no devolvió JSON válido; code_style sin cambios.")
        except Exception as e:
            logger.warning("update_code_style failed: %s", e)

        return self.load_code_style()
