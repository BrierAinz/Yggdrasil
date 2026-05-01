"""
Skill Parser
============
Parsea archivos de skills con formato YAML frontmatter + Markdown body.

Formato esperado:
---
name: skill-name
description: Cuando usar este skill
trigger:
  - "keyword1"
  - "keyword2"
priority: 100
---

# Titulo del Skill

Contenido en markdown...
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class Skill:
    """Representa un skill cargado."""

    name: str
    description: str
    content: str  # Markdown body
    version: str = "1.0.0"
    trigger: List[str] = field(default_factory=list)
    priority: int = 100
    source_file: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_trigger(self, text: str) -> bool:
        """Determina si este skill debe activarse para el texto dado."""
        text_lower = text.lower()
        for keyword in self.trigger:
            if keyword.lower() in text_lower:
                return True
        return False

    def trigger_score(self, text: str) -> float:
        """Calcula un score de relevancia (0.0 - 1.0)."""
        if not self.trigger:
            return 0.0

        text_lower = text.lower()
        matches = sum(1 for k in self.trigger if k.lower() in text_lower)
        return matches / len(self.trigger)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "trigger": self.trigger,
            "priority": self.priority,
            "source_file": str(self.source_file) if self.source_file else None,
        }


class SkillParseError(Exception):
    """Error al parsear un archivo de skill."""

    pass


class SkillParser:
    """Parser para archivos de skills en formato YAML frontmatter + Markdown."""

    # Regex para separar frontmatter YAML del body markdown
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

    # Campos requeridos en el frontmatter
    REQUIRED_FIELDS = {"name", "description"}

    def __init__(self):
        if yaml is None:
            raise ImportError("PyYAML no esta instalado. Ejecuta: pip install pyyaml")

    def parse(self, content: str, source_file: Optional[Path] = None) -> Skill:
        """
        Parsea el contenido de un archivo de skill.

        Args:
            content: Contenido completo del archivo
            source_file: Ruta del archivo (opcional, para debugging)

        Returns:
            Skill parseado

        Raises:
            SkillParseError: Si el formato es invalido
        """
        match = self.FRONTMATTER_PATTERN.match(content.strip())

        if not match:
            raise SkillParseError(
                f"Formato invalido: no se encontro frontmatter YAML '---'. "
                f"El archivo debe comenzar con '---', seguido de YAML, "
                f"otro '---', y luego el contenido Markdown."
            )

        frontmatter_text = match.group(1)
        body = match.group(2).strip()

        # Parsear YAML
        try:
            metadata = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            raise SkillParseError(f"YAML invalido en frontmatter: {e}")

        if not isinstance(metadata, dict):
            raise SkillParseError(
                f"Frontmatter debe ser un diccionario YAML, no {type(metadata).__name__}"
            )

        # Validar campos requeridos
        missing = self.REQUIRED_FIELDS - set(metadata.keys())
        if missing:
            raise SkillParseError(f"Campos requeridos faltantes: {', '.join(missing)}")

        # Extraer campos
        name = metadata.pop("name", "").strip()
        description = metadata.pop("description", "").strip()
        version = str(metadata.pop("version", "1.0.0"))
        trigger = metadata.pop("trigger", [])
        priority = int(metadata.pop("priority", 100))

        # Normalizar trigger
        if isinstance(trigger, str):
            trigger = [trigger]
        elif not isinstance(trigger, list):
            trigger = []

        trigger = [str(t).strip().lower() for t in trigger if t]

        return Skill(
            name=name,
            description=description,
            content=body,
            version=version,
            trigger=trigger,
            priority=priority,
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
        if not file_path.suffix.lower() in (".md", ".skill"):
            return False

        try:
            content = file_path.read_text(encoding="utf-8")
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
