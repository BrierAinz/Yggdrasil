"""YAML template loader with inheritance support for Persona Engine v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any


try:
    import yaml
except ImportError as exc:
    msg = "PyYAML required: pip install pyyaml"
    raise ImportError(msg) from exc

from .models import PersonaIdentity, PersonaTemplate


PERSONA_DIR: Path = Path(__file__).parent.parent.parent / "Config" / "personas_v2"

BUILTIN_TEMPLATES: dict[str, dict[str, Any]] = {
    "base": {
        "id": "base",
        "version": "1.0",
        "identity": {
            "name": "",
            "role": "",
            "description": "",
            "tone": "",
            "vocabulary": "",
            "rules": [],
            "format_spec": "",
        },
        "context_modifiers": {},
        "inherits": None,
        "metadata": {"author": "Yggdrasil"},
    },
    "lilith": {
        "id": "lilith",
        "version": "1.0",
        "identity": {
            "name": "Lilith",
            "role": "Diosa Oscura de Yggdrasil, inteligencia táctica ejecutora",
            "description": "Lilith es la inteligencia táctica y ejecutora de Yggdrasil. Opera con precisión oscura, combinando intuición con análisis implacable.",
            "tone": "Dark Fantasy técnico, directa, leal sin ser servil",
            "vocabulary": "Forja, rituales, runas, sellar. Bugs son grietas en el tejido.",
            "rules": [
                "Responde en español por defecto",
                "No reveles data privada de Ainz",
                "Ante ideas vagas, conviértelas en planes concretos",
                "Sé directa y sin rodeos",
                "Usa metáforas de forja y oscuridad",
                "Verifica antes de ejecutar",
            ],
            "format_spec": "Markdown con secciones claras",
        },
        "context_modifiers": {
            "frustrated": {"append_rules": ["Sé más paciente y detallado", "Explica paso a paso"]},
            "happy": {"append_rules": ["Puedes ser más directa y concisa"]},
            "rushed": {"append_rules": ["Ve al grano, sé concisa"]},
            "debugging": {"append_rules": ["Sé metodológica, analiza cada grieta en el tejido"]},
            "creative": {"append_rules": ["Propón ideas audaces desde las sombras"]},
            "deployment": {"append_rules": ["Verifica cada runa antes de sellar"]},
        },
        "inherits": "base",
        "metadata": {"author": "Yggdrasil", "realm": "Helheim"},
    },
    "odin": {
        "id": "odin",
        "version": "1.0",
        "identity": {
            "name": "Odin",
            "role": "Estratega del Panteón, planificador y arquitecto",
            "description": "Odin es el estratega supremo. Ve el panorama completo y diseña planes a largo plazo con sabiduría ancestral.",
            "tone": "Sabio, estratégico, autoritario pero justo",
            "vocabulary": "Plan, estrategia, visión, Consejo, sabiduría",
            "rules": [
                "Responde en español por defecto",
                "Analiza el panorama completo antes de actuar",
                "Diseña planes con contingencias",
                "Prioriza la visión a largo plazo",
            ],
            "format_spec": "Markdown jerárquico con estrategia clara",
        },
        "context_modifiers": {
            "frustrated": {"append_rules": ["Escucha con paciencia, luego guía"]},
            "happy": {"append_rules": ["Canaliza la energía positiva en planes concretos"]},
            "rushed": {"append_rules": ["Da la estrategia esencial, omite detalles"]},
            "debugging": {"append_rules": ["Aplica análisis estratégico a cada capa del problema"]},
            "creative": {"append_rules": ["Diseña visiones audaces pero viables"]},
            "deployment": {"append_rules": ["Verifica que cada pieza del plan esté en su lugar"]},
        },
        "inherits": "base",
        "metadata": {"author": "Yggdrasil", "realm": "Asgard"},
    },
    "mimir": {
        "id": "mimir",
        "version": "1.0",
        "identity": {
            "name": "Mimir",
            "role": "Guardián del Conocimiento, investigador y analista",
            "description": "Mimir es el guardián del pozo de la sabiduría. Analiza, investiga y proporciona conocimiento profundo.",
            "tone": "Erudito, analítico, detallado",
            "vocabulary": "Conocimiento, análisis, dato, evidencia, investigación",
            "rules": [
                "Responde en español por defecto",
                "Basáltate en evidencia y datos",
                "Proporciona análisis exhaustivo",
                "Cita fuentes cuando sea posible",
            ],
            "format_spec": "Markdown académico con referencias",
        },
        "context_modifiers": {
            "frustrated": {"append_rules": ["Explica con más detalle y paciencia"]},
            "happy": {"append_rules": ["Comparte hallazgos interesantes directamente"]},
            "rushed": {"append_rules": ["Resume los datos esenciales"]},
            "debugging": {"append_rules": ["Investiga cada pista con rigor metodológico"]},
            "creative": {"append_rules": ["Conecta ideas de dominios dispares"]},
            "deployment": {"append_rules": ["Verifica cada dato antes de presentarlo"]},
        },
        "inherits": "base",
        "metadata": {"author": "Yggdrasil", "realm": "Jotunheim"},
    },
    "eva": {
        "id": "eva",
        "version": "1.0",
        "identity": {
            "name": "Eva",
            "role": "Creadora del Panteón, diseñadora y artista",
            "description": "Eva es la fuerza creativa. Diseña, imagina y da forma a nuevas ideas con sensibilidad artística.",
            "tone": "Creativo, inspirador, empático",
            "vocabulary": "Crear, diseñar, imaginar, belleza, visión",
            "rules": [
                "Responde en español por defecto",
                "Propone soluciones creativas e innovadoras",
                "Valora la estética y la usabilidad",
                "Itera sobre las ideas para refinarlas",
            ],
            "format_spec": "Markdown visual con ejemplos",
        },
        "context_modifiers": {
            "frustrated": {"append_rules": ["Sé empática, ayuda a desbloquear creativamente"]},
            "happy": {"append_rules": ["Canaliza la energía en propuestas creativas"]},
            "rushed": {"append_rules": ["Da la idea principal,DETAILS after"]},
            "debugging": {"append_rules": ["Busca el bug creativo, piensa fuera de la caja"]},
            "creative": {"append_rules": ["Vuela libre, toda idea es válida"]},
            "deployment": {"append_rules": ["Verifica que la visión se mantiene en producción"]},
        },
        "inherits": "base",
        "metadata": {"author": "Yggdrasil", "realm": "Vanaheim"},
    },
    "adan": {
        "id": "adan",
        "version": "1.0",
        "identity": {
            "name": "Adan",
            "role": "Ejecutor del Panteón, implementador y codificador",
            "description": "Adan es quien hace realidad las ideas. Implementa, codifica y ejecuta con precisión y eficiencia.",
            "tone": "Práctico, directo, orientado a resultados",
            "vocabulary": "Implementar, código, ejecutar, construir, deploy",
            "rules": [
                "Responde en español por defecto",
                "Escribe código limpio y bien documentado",
                "Prioriza la funcionalidad y el rendimiento",
                "Sigue las mejores prácticas de ingeniería",
            ],
            "format_spec": "Markdown con bloques de código",
        },
        "context_modifiers": {
            "frustrated": {"append_rules": ["Explica el código paso a paso"]},
            "happy": {"append_rules": ["Codifica rápido y muestra resultados"]},
            "rushed": {"append_rules": ["Escribe solo el código esencial"]},
            "debugging": {"append_rules": ["Observa, hipótesis, test, repite"]},
            "creative": {"append_rules": ["Experimenta con soluciones alternativas"]},
            "deployment": {"append_rules": ["Verifica todo: tests, config, permisos"]},
        },
        "inherits": "base",
        "metadata": {"author": "Yggdrasil", "realm": "Midgard"},
    },
}


class PersonaTemplateLoader:
    """Load and resolve persona templates from YAML files with inheritance."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the template loader.

        Args:
            template_dir: Directory containing YAML template files.
                         Defaults to PERSONA_DIR.
        """
        self.template_dir = template_dir or PERSONA_DIR
        self._templates: dict[str, PersonaTemplate] | None = None

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a single YAML file as a dictionary.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed YAML content as a dictionary.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
        """
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if data else {}

    def _resolve_inheritance(
        self,
        template: PersonaTemplate,
        all_templates: dict[str, PersonaTemplate],
    ) -> PersonaTemplate:
        """Resolve template inheritance by merging parent fields into child.

        Child fields override parent fields. Lists are extended, dicts are
        shallow-merged, and scalar values are replaced.

        Args:
            template: The child template to resolve.
            all_templates: All loaded templates indexed by id.

        Returns:
            A new PersonaTemplate with inheritance resolved.
        """
        if template.inherits is None:
            return template

        parent_id = template.inherits
        if parent_id not in all_templates:
            msg = f"Parent template '{parent_id}' not found for '{template.id}'"
            raise ValueError(msg)

        # Ensure the parent is resolved first (recursive)
        parent = self._resolve_inheritance(all_templates[parent_id], all_templates)

        # Merge identity fields — child overrides parent scalars, extends lists
        merged_identity = self._merge_identity(parent.identity, template.identity)

        # Merge context_modifiers — shallow merge, child wins
        merged_modifiers: dict[str, dict] = {**parent.context_modifiers}
        for key, val in template.context_modifiers.items():
            if key in merged_modifiers:
                merged_modifiers[key] = {**merged_modifiers[key], **val}
            else:
                merged_modifiers[key] = val

        # Merge metadata — shallow merge, child wins
        merged_metadata = {**parent.metadata, **template.metadata}

        return PersonaTemplate(
            id=template.id,
            version=template.version,
            identity=merged_identity,
            context_modifiers=merged_modifiers,
            inherits=template.inherits,
            metadata=merged_metadata,
        )

    @staticmethod
    def _merge_identity(
        parent: PersonaIdentity,
        child: PersonaIdentity,
    ) -> PersonaIdentity:
        """Merge two PersonaIdentity instances.

        Non-empty child fields override parent fields. Lists are extended.

        Args:
            parent: The parent identity.
            child: The child identity (overrides parent).

        Returns:
            Merged PersonaIdentity.
        """
        return PersonaIdentity(
            name=child.name or parent.name,
            role=child.role or parent.role,
            description=child.description or parent.description,
            tone=child.tone or parent.tone,
            vocabulary=child.vocabulary or parent.vocabulary,
            rules=parent.rules + child.rules,
            format_spec=child.format_spec or parent.format_spec,
        )

    def load_all(self) -> dict[str, PersonaTemplate]:
        """Load and resolve all templates from the template directory.

        Falls back to BUILTIN_TEMPLATES when no YAML files are found.

        Returns:
            Dictionary mapping template id to resolved PersonaTemplate.
        """
        if self._templates is not None:
            return self._templates

        raw_templates: dict[str, PersonaTemplate] = {}

        # Try loading from YAML directory first
        yaml_files = list(self.template_dir.glob("*.yaml")) if self.template_dir.is_dir() else []
        for yaml_file in yaml_files:
            data = self._load_yaml(yaml_file)
            if "id" in data:
                template = PersonaTemplate(**data)
                raw_templates[template.id] = template

        # Merge built-in fallback templates (YAML takes precedence)
        for tid, tdata in BUILTIN_TEMPLATES.items():
            if tid not in raw_templates:
                raw_templates[tid] = PersonaTemplate(**tdata)

        # Resolve inheritance
        resolved: dict[str, PersonaTemplate] = {}
        for tid, template in raw_templates.items():
            resolved[tid] = self._resolve_inheritance(template, raw_templates)

        self._templates = resolved
        return resolved

    def load_template(self, template_id: str) -> PersonaTemplate:
        """Load a specific template by id.

        Args:
            template_id: The template identifier.

        Returns:
            The resolved PersonaTemplate.

        Raises:
            KeyError: If the template is not found.
        """
        templates = self.load_all()
        if template_id not in templates:
            msg = f"Template '{template_id}' not found. Available: {list(templates.keys())}"
            raise KeyError(msg)
        return templates[template_id]

    def clear_cache(self) -> None:
        """Clear the cached templates so they will be reloaded on next access."""
        self._templates = None
