"""
Episode Tagger - D.12: Auto-tagging de episodios con detección de proyecto/outcome.
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.episode_tagger")


class EpisodeTagger:
    """
    Tagger automático para episodios.
    Detecta tags, proyecto y outcome basado en contenido.
    """

    # Tags automáticos y sus patrones
    AUTO_TAGS = {
        "refactor": [
            "refactor",
            "refactoriza",
            "reestructura",
            "limpiar código",
            "clean code",
        ],
        "bug_fix": ["bug", "error", "fix", "arregla", "corregir", "soluciona", "debug"],
        "deployment": [
            "deploy",
            "despliegue",
            "publicar",
            "release",
            "prod",
            "producción",
        ],
        "documentation": ["docs", "documentación", "README", "guía", "manual", "wiki"],
        "testing": ["test", "testing", "prueba", "spec", "cobertura", "coverage"],
        "optimization": [
            "optimiza",
            "performance",
            "mejora",
            "rápido",
            "lento",
            "cache",
        ],
        "security": [
            "seguridad",
            "security",
            "vulnerabilidad",
            "auth",
            "encrypt",
            "hash",
        ],
        "api_change": ["api", "endpoint", "endpoint", "route", "controller", "schema"],
        "database": [
            "database",
            "db",
            "sql",
            "migration",
            "migración",
            "tabla",
            "modelo",
        ],
        "ui_ux": ["ui", "ux", "interfaz", "diseño", "css", "frontend", "componente"],
    }

    # Indicadores de outcome
    SUCCESS_INDICATORS = [
        "completado",
        "exitoso",
        "success",
        "funciona",
        "working",
        "done",
        "terminado",
        "finalizado",
        "resuelto",
        "solucionado",
        "ok",
        "bien",
    ]

    FAILURE_INDICATORS = [
        "falló",
        "error",
        "failed",
        "failure",
        "crash",
        "excepción",
        "exception",
        "timeout",
        "no funciona",
        "broken",
        "issue",
        "problema",
        "bug",
    ]

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()
        self.projects = self.config.get("projects", {})

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde episodic.json"""
        config_path = self.base_path / "Config" / "episodic.json"
        try:
            if config_path.exists():
                return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[EpisodeTagger] Error loading config: {e}")

        # Config por defecto
        return {
            "enrichment": {
                "auto_tag_enabled": True,
                "auto_detect_project": True,
                "auto_detect_outcome": True,
            },
            "projects": {
                "lilith": {
                    "patterns": [
                        "Core/",
                        "Discord/",
                        "Telegram/",
                        "Backend/",
                        "Frontend/",
                    ],
                    "keywords": ["lilith", "bot", "agente"],
                },
                "nazarick": {
                    "patterns": ["nazarick/", "bases/"],
                    "keywords": ["nazarick", "base de datos"],
                },
                "personal": {
                    "patterns": [],
                    "keywords": ["personal", "configuración", "setup"],
                },
            },
        }

    def auto_tag(
        self, episode_content: str, tool_result: Optional[Dict] = None
    ) -> List[str]:
        """
        Detecta tags automáticamente basado en contenido.

        Args:
            episode_content: Contenido del episodio
            tool_result: Resultado de tool (opcional, para extraer más contexto)

        Returns:
            Lista de tags detectados
        """
        content_lower = episode_content.lower()
        tags = []

        # Heurísticas basadas en patrones
        for tag, patterns in self.AUTO_TAGS.items():
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    tags.append(tag)
                    break

        # Extraer de tool_result si existe
        if tool_result:
            tool_tags = self._extract_tags_from_tool(tool_result)
            tags.extend(tool_tags)

        # Deduplicar
        tags = list(set(tags))

        if tags:
            logger.info(f"[EpisodeTagger] Tags detected: {tags}")

        return tags

    def _extract_tags_from_tool(self, tool_result: Dict) -> List[str]:
        """Extrae tags del resultado de una tool."""
        tags = []

        # Detectar errores
        if tool_result.get("error") or tool_result.get("stderr"):
            tags.append("bug_fix")

        # Detectar tipo de tool
        tool_name = tool_result.get("tool", "")
        if "test" in tool_name.lower():
            tags.append("testing")
        if "deploy" in tool_name.lower():
            tags.append("deployment")
        if "doc" in tool_name.lower():
            tags.append("documentation")

        return tags

    def detect_project(self, episode_content: str) -> Optional[str]:
        """
        Detecta proyecto basado en contenido.

        Args:
            episode_content: Contenido del episodio

        Returns:
            ID del proyecto o None
        """
        content_lower = episode_content.lower()

        for project_id, config in self.projects.items():
            # Buscar patterns
            for pattern in config.get("patterns", []):
                if pattern.lower() in content_lower:
                    logger.info(
                        f"[EpisodeTagger] Project detected: {project_id} (pattern: {pattern})"
                    )
                    return project_id

            # Buscar keywords
            for keyword in config.get("keywords", []):
                if keyword.lower() in content_lower:
                    logger.info(
                        f"[EpisodeTagger] Project detected: {project_id} (keyword: {keyword})"
                    )
                    return project_id

        return None

    def detect_outcome(
        self, episode_content: str, tool_result: Optional[Dict] = None
    ) -> str:
        """
        Detecta outcome basado en contenido y resultado de tool.

        Args:
            episode_content: Contenido del episodio
            tool_result: Resultado de tool (opcional)

        Returns:
            "success" | "failure" | "partial"
        """
        content_lower = episode_content.lower()

        # Si hay tool_result, usarlo primero
        if tool_result:
            if tool_result.get("error") or tool_result.get("stderr"):
                logger.info("[EpisodeTagger] Outcome: failure (tool error)")
                return "failure"
            if tool_result.get("success") or tool_result.get("returncode") == 0:
                logger.info("[EpisodeTagger] Outcome: success (tool success)")
                return "success"

        # Buscar indicadores en contenido
        failure_count = sum(
            1 for ind in self.FAILURE_INDICATORS if ind in content_lower
        )
        success_count = sum(
            1 for ind in self.SUCCESS_INDICATORS if ind in content_lower
        )

        # Determinar outcome
        if failure_count > success_count:
            logger.info("[EpisodeTagger] Outcome: failure (content indicators)")
            return "failure"
        elif success_count > failure_count:
            logger.info("[EpisodeTagger] Outcome: success (content indicators)")
            return "success"
        else:
            # Default: partial si hay actividad pero no claro
            logger.info("[EpisodeTagger] Outcome: partial (unclear)")
            return "partial"

    def suggest_emotional_tag(
        self, episode_content: str, outcome: str
    ) -> Optional[str]:
        """
        Sugiere tag emocional basado en contenido y outcome.

        Args:
            episode_content: Contenido del episodio
            outcome: Outcome detectado

        Returns:
            Tag emocional sugerido o None
        """
        content_lower = episode_content.lower()

        # Frustrante: errores, bugs, fallos
        frustrating_patterns = [
            "frustrante",
            "loco",
            "maldito",
            "odio",
            "imposible",
            "horas",
            "días",
            "no entiendo",
            "por qué",
        ]
        if any(p in content_lower for p in frustrating_patterns):
            return "frustrating"

        # Exitoso: outcome success + celebración
        exciting_patterns = [
            "increíble",
            "amazing",
            "fantástico",
            "perfecto",
            "logré",
            "funcionó",
            "yes",
            "¡sí!",
            "finalmente",
        ]
        if outcome == "success" and any(p in content_lower for p in exciting_patterns):
            return "exciting"

        # Exitoso rutinario
        if outcome == "success":
            return "successful"

        # Rutinario: nada especial
        return "routine"

    def enrich_episode(
        self,
        content: str,
        tool_result: Optional[Dict] = None,
        existing_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Enriquece un episodio con todos los metadatos automáticos.

        Args:
            content: Contenido del episodio
            tool_result: Resultado de tool (opcional)
            existing_tags: Tags ya existentes (opcional)

        Returns:
            Dict con project_id, outcome, tags, emotional_tag
        """
        # Detectar automáticos
        auto_tags = (
            self.auto_tag(content, tool_result)
            if self.config["enrichment"]["auto_tag_enabled"]
            else []
        )

        # Combinar con tags existentes
        all_tags = list(set((existing_tags or []) + auto_tags))

        # Detectar proyecto
        project_id = None
        if self.config["enrichment"]["auto_detect_project"]:
            project_id = self.detect_project(content)

        # Detectar outcome
        outcome = "partial"
        if self.config["enrichment"]["auto_detect_outcome"]:
            outcome = self.detect_outcome(content, tool_result)

        # Sugerir tag emocional
        emotional_tag = self.suggest_emotional_tag(content, outcome)

        return {
            "project_id": project_id or "unknown",
            "outcome": outcome,
            "tags": all_tags,
            "emotional_tag": emotional_tag,
        }


# Singleton
tagger_instance: Optional[EpisodeTagger] = None


def get_episode_tagger(base_path: Optional[Path] = None) -> EpisodeTagger:
    """Obtiene instancia singleton del EpisodeTagger"""
    global tagger_instance
    if tagger_instance is None:
        tagger_instance = EpisodeTagger(base_path)
    return tagger_instance


def auto_tag_episode(
    content: str, tool_result: Optional[Dict] = None, base_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Función conveniencia para enriquecer episodio"""
    tagger = get_episode_tagger(base_path)
    return tagger.enrich_episode(content, tool_result)
