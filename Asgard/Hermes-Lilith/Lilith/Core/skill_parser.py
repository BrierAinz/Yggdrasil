"""
Skill Parser v2
===============
Parsea archivos de skills con formato YAML frontmatter + Markdown body,
asi como archivos YAML puros (.yaml/.yml).

Formato MD:
---
name: skill-name
description: Cuando usar este skill
trigger:
  - "keyword1"
  - "keyword2"
trigger_regex:
  - "\\bpython\\b"
trigger_intent:
  - "coding"
priority: 100
enabled: true
tools_required:
  - "read_file"
prompt_template: "Eres un experto en {{context}}. Ayuda con: {{user_input}}"
---

# Titulo del Skill

Contenido en markdown...

Formato YAML puro (.yaml/.yml):
name: skill-name
description: Descripcion
trigger:
  - "keyword"
content: |
  Contenido del skill...
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("Lilith.SkillParser")

# Intent labels predefinidos
KNOWN_INTENTS = {
    "coding", "research", "writing", "analysis", "creative",
    "planning", "conversation", "debugging", "learning", "math",
    "translation", "summarization", "extraction", "review",
}


@dataclass
class Skill:
    """Representa un skill cargado."""

    name: str
    description: str
    content: str  # Markdown body
    version: str = "1.0.0"
    trigger: List[str] = field(default_factory=list)  # keywords (backward compat)
    trigger_regex: List[str] = field(default_factory=list)  # regex patterns
    trigger_intent: List[str] = field(default_factory=list)  # intent labels
    priority: int = 100
    enabled: bool = True
    tools_required: List[str] = field(default_factory=list)
    prompt_template: Optional[str] = None  # overrides content when set
    source_file: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Usage stats (non-serialized)
    _times_triggered: int = field(default=0, repr=False)
    _last_triggered: Optional[float] = field(default=None, repr=False)

    def should_trigger(self, text: str, threshold: float = 0.1) -> bool:
        """Determina si este skill debe activarse para el texto dado.

        Args:
            text: Texto del usuario
            threshold: Score minimo para considerar activacion (default 0.1)
        """
        return self.trigger_score(text) >= threshold

    def trigger_score(self, text: str) -> float:
        """Calcula un score ponderado de relevancia (0.0 - 1.0).

        Score = keyword_match * 0.4 + regex_match * 0.4 + intent_match * 0.2

        Args:
            text: Texto del usuario
        """
        keyword_score = self._keyword_score(text)
        regex_score = self._regex_score(text)
        intent_score = self._intent_score(text)

        # Si no hay ningun tipo de trigger, score = 0
        has_triggers = self.trigger or self.trigger_regex or self.trigger_intent
        if not has_triggers:
            return 0.0

        # Calcular pesos activos
        weights = []
        scores = []

        if self.trigger:
            weights.append(0.4)
            scores.append(keyword_score)
        if self.trigger_regex:
            weights.append(0.4)
            scores.append(regex_score)
        if self.trigger_intent:
            weights.append(0.2)
            scores.append(intent_score)

        # Normalizar pesos
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(w * s for w, s in zip(weights, scores))
        return weighted_sum / total_weight

    def _keyword_score(self, text: str) -> float:
        """Score basado en keywords (inclusion)."""
        if not self.trigger:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for k in self.trigger if k.lower() in text_lower)
        return matches / len(self.trigger)

    def _regex_score(self, text: str) -> float:
        """Score basado en regex patterns (cualquier match = score proporcional)."""
        if not self.trigger_regex:
            return 0.0
        matches = 0
        for pattern in self.trigger_regex:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
            except re.error:
                logger.warning(f"[Skill] Regex invalido en skill '{self.name}': {pattern}")
        return matches / len(self.trigger_regex)

    def _intent_score(self, text: str) -> float:
        """Score basado en intent labels (match por inclusion de etiqueta)."""
        if not self.trigger_intent:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for intent in self.trigger_intent if intent.lower() in text_lower)
        return matches / len(self.trigger_intent)

    def render(self, **kwargs) -> str:
        """Renderiza el prompt_template con variables.

        Variables soportadas: {{user_input}}, {{context}}, {{memory}}, {{skills}},
        y cualquier otra variable pasada como keyword argument.
        Si no hay prompt_template, usa content como fallback.
        """
        template = self.prompt_template or self.content
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "trigger": self.trigger,
            "trigger_regex": self.trigger_regex,
            "trigger_intent": self.trigger_intent,
            "priority": self.priority,
            "enabled": self.enabled,
            "tools_required": self.tools_required,
            "prompt_template": self.prompt_template,
            "source_file": str(self.source_file) if self.source_file else None,
            "metadata": self.metadata,
        }


class SkillParseError(Exception):
    """Error al parsear un archivo de skill."""

    pass


class SkillParser:
    """Parser para archivos de skills en formato YAML frontmatter + Markdown,
    y YAML puro (.yaml/.yml)."""

    # Regex para separar frontmatter YAML del body markdown
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

    # Campos requeridos en el frontmatter
    REQUIRED_FIELDS = {"name", "description"}

    def __init__(self):
        pass

    def parse(self, content: str, source_file: Optional[Path] = None) -> Skill:
        """
        Parsea el contenido de un archivo de skill.

        Soporta dos formatos:
        - MD con YAML frontmatter: ---\\nYAML\\n---\\nBODY
        - YAML puro: todo el contenido es YAML (para .yaml/.yml)

        Args:
            content: Contenido completo del archivo
            source_file: Ruta del archivo (opcional, para debugging)

        Returns:
            Skill parseado

        Raises:
            SkillParseError: Si el formato es invalido
        """
        match = self.FRONTMATTER_PATTERN.match(content.strip())

        if match:
            # Formato MD con frontmatter
            frontmatter_text = match.group(1)
            body = match.group(2).strip()
            return self._parse_frontmatter(frontmatter_text, body, source_file)
        else:
            # Intentar como YAML puro
            return self._parse_yaml_pure(content, source_file)

    def _parse_frontmatter(
        self, frontmatter_text: str, body: str, source_file: Optional[Path] = None
    ) -> Skill:
        """Parsea frontmatter YAML + body markdown."""
        try:
            metadata = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            raise SkillParseError(f"YAML invalido en frontmatter: {e}")

        if not isinstance(metadata, dict):
            raise SkillParseError(
                f"Frontmatter debe ser un diccionario YAML, no {type(metadata).__name__}"
            )

        missing = self.REQUIRED_FIELDS - set(metadata.keys())
        if missing:
            raise SkillParseError(f"Campos requeridos faltantes: {', '.join(missing)}")

        return self._build_skill(metadata, body, source_file)

    def _parse_yaml_pure(self, content: str, source_file: Optional[Path] = None) -> Skill:
        """Parsea un archivo YAML puro (sin frontmatter)."""
        try:
            metadata = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise SkillParseError(f"YAML invalido: {e}")

        if not isinstance(metadata, dict):
            raise SkillParseError(
                f"YAML puro debe ser un diccionario, no {type(metadata).__name__}"
            )

        missing = self.REQUIRED_FIELDS - set(metadata.keys())
        if missing:
            raise SkillParseError(f"Campos requeridos faltantes: {', '.join(missing)}")

        body = metadata.pop("content", "")
        return self._build_skill(metadata, body, source_file)

    def _build_skill(
        self, metadata: Dict[str, Any], body: str, source_file: Optional[Path] = None
    ) -> Skill:
        """Construye un Skill desde los metadatos y el body parseados."""
        name = metadata.pop("name", "").strip()
        description = metadata.pop("description", "").strip()
        version = str(metadata.pop("version", "1.0.0"))
        trigger = metadata.pop("trigger", [])
        trigger_regex = metadata.pop("trigger_regex", [])
        trigger_intent = metadata.pop("trigger_intent", [])
        priority = int(metadata.pop("priority", 100))
        enabled = metadata.pop("enabled", True)
        tools_required = metadata.pop("tools_required", [])
        prompt_template = metadata.pop("prompt_template", None)

        # Normalizar trigger (keywords)
        if isinstance(trigger, str):
            trigger = [trigger]
        elif not isinstance(trigger, list):
            trigger = []
        trigger = [str(t).strip().lower() for t in trigger if t]

        # Normalizar trigger_regex
        if isinstance(trigger_regex, str):
            trigger_regex = [trigger_regex]
        elif not isinstance(trigger_regex, list):
            trigger_regex = []
        trigger_regex = [str(t).strip() for t in trigger_regex if t]

        # Normalizar trigger_intent
        if isinstance(trigger_intent, str):
            trigger_intent = [trigger_intent]
        elif not isinstance(trigger_intent, list):
            trigger_intent = []
        trigger_intent = [str(t).strip().lower() for t in trigger_intent if t]

        # Normalizar tools_required
        if isinstance(tools_required, str):
            tools_required = [tools_required]
        elif not isinstance(tools_required, list):
            tools_required = []
        tools_required = [str(t).strip() for t in tools_required if t]

        # Normalizar prompt_template
        if prompt_template is not None:
            prompt_template = str(prompt_template).strip() or None

        # Normalizar enabled
        if not isinstance(enabled, bool):
            enabled = bool(enabled)

        return Skill(
            name=name,
            description=description,
            content=body,
            version=version,
            trigger=trigger,
            trigger_regex=trigger_regex,
            trigger_intent=trigger_intent,
            priority=priority,
            enabled=enabled,
            tools_required=tools_required,
            prompt_template=prompt_template,
            source_file=source_file,
            metadata=metadata,  # Resto de campos custom
        )

    def parse_file(self, file_path: Path) -> Skill:
        """Parsea un archivo de skill desde disco."""
        if not file_path.exists():
            raise SkillParseError(f"Archivo no encontrado: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self.parse(content, source_file=file_path)

    def is_valid_skill_file(self, file_path: Path) -> bool:
        """Verifica si un archivo parece ser un skill valido."""
        if not file_path.suffix.lower() in (".md", ".skill", ".yaml", ".yml"):
            return False

        try:
            content = file_path.read_text(encoding="utf-8")
            if file_path.suffix.lower() in (".yaml", ".yml"):
                # YAML puro: todo es frontmatter
                metadata = yaml.safe_load(content)
                return isinstance(metadata, dict) and "name" in metadata
            else:
                return self.FRONTMATTER_PATTERN.match(content.strip()) is not None
        except Exception:
            return False


# Singleton
_parser: Optional[SkillParser] = None


def get_parser() -> SkillParser:
    """Devuelve el parser singleton."""
    global _parser
    if _parser is None:
        _parser = SkillParser()
    return _parser