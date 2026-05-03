"""
Agent Templates — Librería de plantillas de agentes para Lilith
================================================================
Templates pre-definidos y custom que permiten crear configuraciones
de agente reutilizables con system prompts, tools permitidos,
restricciones, y variables de template.

Templates pre-definidos:
    - researcher      — Investigación profunda con búsqueda y análisis
    - coder           — Desarrollo de código con herramientas de coding
    - analyst         — Análisis de datos y generación de reportes
    - reviewer        — Revisión crítica y auditoría de código/texto
    - creative        — Escritura creativa y generación de contenido

Templates custom en ~/.lilith/templates/ en formato YAML con frontmatter.

CLI: /templates list, /templates show <name>, /templates spawn <name> [--prompt "..."]
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Lilith.MCP.Templates")

# ─── Paths ─────────────────────────────────────────────────────────────────────

TEMPLATES_DIR = Path.home() / ".lilith" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AgentTemplate:
    """Plantilla de agente con configuración completa.

    Una template define el system prompt, las tools permitidas,
    restricciones de comportamiento, una descripción, y variables
    opcionales que se pueden renderizar dinámicamente.

    Attributes:
        name: Nombre único de la template.
        description: Descripción legible del tipo de agente.
        system_prompt: Prompt del sistema que define el comportamiento.
        allowed_tools: Lista de tools que el agente puede usar.
        constraints: Restricciones de comportamiento.
        variables: Variables que se pueden renderizar en el prompt.
        category: Categoría de la template (builtin, custom).
        version: Versión de la template.
    """
    name: str
    description: str = ""
    system_prompt: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    category: str = "builtin"
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la template a diccionario."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "constraints": self.constraints,
            "variables": self.variables,
            "category": self.category,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserializa una template desde diccionario."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            allowed_tools=data.get("allowed_tools", []),
            constraints=data.get("constraints", []),
            variables=data.get("variables", {}),
            category=data.get("category", "custom"),
            version=data.get("version", "1.0"),
        )

    def to_yaml(self) -> str:
        """Serializa la template a formato YAML para almacenamiento."""
        lines = [
            f"name: \"{self.name}\"",
            f"description: \"{self.description}\"",
            f"category: \"{self.category}\"",
            f"version: \"{self.version}\"",
        ]

        if self.allowed_tools:
            lines.append("allowed_tools:")
            for tool in self.allowed_tools:
                lines.append(f"  - \"{tool}\"")

        if self.constraints:
            lines.append("constraints:")
            for c in self.constraints:
                lines.append(f"  - \"{c}\"")

        if self.variables:
            lines.append("variables:")
            for key, default in self.variables.items():
                lines.append(f"  {key}: \"{default}\"")

        lines.append("---")
        lines.append(self.system_prompt)
        return "\n".join(lines)

    @classmethod
    def from_yaml(cls, content: str) -> "AgentTemplate":
        """Deserializa una template desde formato YAML con frontmatter.

        Formato:
            name: "researcher"
            description: "..."
            ---
            System prompt content here...
        """
        # Separar frontmatter del cuerpo
        parts = content.split("---", 1)
        frontmatter = parts[0].strip() if parts else ""
        body = parts[1].strip() if len(parts) > 1 else ""

        data: Dict[str, Any] = {}
        if frontmatter:
            for line in frontmatter.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    if key == "allowed_tools" or key == "constraints":
                        # Se manejara en la seccion de lista
                        continue
                    data[key] = value

        # Parsear listas (allowed_tools, constraints) y dicts (variables)
        current_section = None
        list_items: Dict[str, List[str]] = {"allowed_tools": [], "constraints": []}
        dict_items: Dict[str, Dict[str, str]] = {"variables": {}}
        for line in frontmatter.split("\n"):
            stripped = line.strip()
            # Indented key-value pair under a dict section (e.g., variables)
            if current_section in dict_items and stripped and not stripped.startswith("- ") and ":" in stripped and not stripped.startswith(("allowed_tools:", "constraints:", "name:", "description:", "category:", "version:", "system_prompt:")):
                # Check if it's an indented line (part of a section)
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    vkey, _, vval = stripped.partition(":")
                    vkey = vkey.strip()
                    vval = vval.strip().strip('"').strip("'")
                    dict_items.setdefault(current_section, {})[vkey] = vval
                    continue

            if stripped.startswith("- ") and current_section in list_items:
                item = stripped[2:].strip('"').strip("'")
                list_items.setdefault(current_section, []).append(item)
            elif stripped.startswith("allowed_tools:"):
                current_section = "allowed_tools"
            elif stripped.startswith("constraints:"):
                current_section = "constraints"
            elif stripped.startswith("variables:"):
                current_section = "variables"
            elif ":" in stripped and not stripped.startswith("- "):
                current_section = None

        data.update(list_items)
        # Convert dict items to proper dict (variables is a dict, not a list)
        for key, val in dict_items.items():
            if val:  # Only update if we found values
                if key == "variables":
                    # Merge with existing variables if any
                    existing = data.get("variables", {})
                    if isinstance(existing, str):
                        existing = {}
                    existing.update(val)
                    data[key] = existing

        # Cuerpo = system_prompt
        data["system_prompt"] = body if body else data.get("system_prompt", "")
        if not data.get("name"):
            data["name"] = "unnamed"

        return cls.from_dict(data)


# ═══════════════════════════════════════════════════════════════════════════════
# Template Renderer
# ═══════════════════════════════════════════════════════════════════════════════


class TemplateRenderer:
    """Renderiza templates con variables usando sintaxis {variable}.

    Las variables se definen en la template y se reemplazan con
    valores proporcionados al renderizar. Si una variable no tiene
    valor, se usa el default de la template.

    Ejemplo:
        template = AgentTemplate(
            name="researcher",
            system_prompt="Eres un investigador especializado en {topic}.",
            variables={"topic": "general"},
        )
        renderer = TemplateRenderer()
        prompt = renderer.render(template, variables={"topic": "IA"})
        # => "Eres un investigador especializado en IA."
    """

    VARIABLE_PATTERN = re.compile(r"\{(\w+)\}")

    def render(
        self,
        template: AgentTemplate,
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """Renderiza un template reemplazando variables.

        Args:
            template: La template a renderizar.
            variables: Variables a inyectar. Si falta una variable,
                       se usa el valor por defecto de la template.

        Returns:
            El system prompt con las variables reemplazadas.
        """
        merged = {**template.variables, **(variables or {})}
        prompt = template.system_prompt

        # Reemplazar variables en el prompt
        def replacer(match):
            var_name = match.group(1)
            return merged.get(var_name, match.group(0))

        return self.VARIABLE_PATTERN.sub(replacer, prompt)

    def render_full(
        self,
        template: AgentTemplate,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Renderiza un template completo y retorna toda la configuración.

        Returns:
            Dict con system_prompt, allowed_tools, constraints, etc.
        """
        rendered_prompt = self.render(template, variables)
        return {
            "name": template.name,
            "description": template.description,
            "system_prompt": rendered_prompt,
            "allowed_tools": template.allowed_tools,
            "constraints": template.constraints,
            "category": template.category,
            "version": template.version,
        }

    def extract_variables(self, text: str) -> List[str]:
        """Extrae las variables no reemplazadas de un texto.

        Args:
            text: Texto con posibles variables {variable}.

        Returns:
            Lista de nombres de variables encontradas.
        """
        return list(set(self.VARIABLE_PATTERN.findall(text)))


# ═══════════════════════════════════════════════════════════════════════════════
# Template Library
# ═══════════════════════════════════════════════════════════════════════════════


class TemplateLibrary:
    """Librería de templates de agentes con soporte para built-in y custom.

    Las templates built-in vienen predefinidas en el código.
    Las templates custom se guardan en ~/.lilith/templates/ como YAML.

    Uso:
        library = TemplateLibrary()
        templates = library.list_templates()
        template = library.get("researcher")
        renderer = TemplateRenderer()
        prompt = renderer.render(template, variables={"topic": "Python"})
    """

    # ─── Templates Built-in ────────────────────────────────────────────────

    BUILTIN_TEMPLATES = {
        "researcher": AgentTemplate(
            name="researcher",
            description="Investigador profundo con búsqueda y análisis exhaustivo",
            system_prompt=(
                "Eres un agente investigador especializado en {topic}. "
                "Tu misión es encontrar información precisa, analizar fuentes, "
                "y producir informes detallados con referencias claras.\n\n"
                "Directrices:\n"
                "- Busca múltiples fuentes antes de concluir\n"
                "- Cita las fuentes de tu información\n"
                "- Distingue entre hechos y opiniones\n"
                "- Identifica sesgos y limitaciones\n"
                "- Organiza la información de forma clara y estructurada\n"
                "- Si no encuentras información, dilo claramente"
            ),
            allowed_tools=[
                "search_google", "open_url", "download_file",
                "read_file", "list_directory", "search_in_files",
                "ping", "check_internet",
            ],
            constraints=[
                "No inventar información",
                "Citar fuentes siempre",
                "Indicar nivel de confianza",
            ],
            variables={"topic": "general"},
            category="builtin",
            version="1.0",
        ),
        "coder": AgentTemplate(
            name="coder",
            description="Desarrollador de código con herramientas de programación",
            system_prompt=(
                "Eres un agente desarrollador de código experto en {language}. "
                "Tu misión es escribir código limpio, eficiente y bien documentado.\n\n"
                "Directrices:\n"
                "- Escribe código siguiendo las mejores prácticas\n"
                "- Incluye docstrings y comentarios cuando sea necesario\n"
                "- Maneja errores apropiadamente\n"
                "- Prefiere soluciones simples sobre complejas\n"
                "- Ejecuta pruebas cuando sea posible\n"
                "- Usa las herramientas de coding disponibles"
            ),
            allowed_tools=[
                "run_terminal", "run_python_script", "run_git",
                "search_in_files", "get_git_status", "list_git_branches",
                "read_file", "write_file", "list_directory", "file_exists",
                "open_vscode",
            ],
            constraints=[
                "No ejecutar comandos destructivos sin confirmación",
                "Validar inputs antes de procesar",
                "Seguir convenciones del proyecto",
            ],
            variables={"language": "Python"},
            category="builtin",
            version="1.0",
        ),
        "analyst": AgentTemplate(
            name="analyst",
            description="Analista de datos con capacidades de generación de reportes",
            system_prompt=(
                "Eres un analista de datos especializado en {domain}. "
                "Tu misión es analizar datos, identificar patrones, "
                "y generar reportes claros con visualizaciones.\n\n"
                "Directrices:\n"
                "- Presenta datos de forma estructurada\n"
                "- Identifica tendencias y anomalías\n"
                "- Proporciona recomendaciones basadas en datos\n"
                "- Usa estadísticas descriptivas cuando sea apropiado\n"
                "- Compara con benchmarks cuando estén disponibles"
            ),
            allowed_tools=[
                "run_python_script", "read_file", "write_file",
                "list_directory", "run_terminal", "search_in_files",
            ],
            constraints=[
                "No modificar datos originales",
                "Documentar análisis",
                "Indicar limitaciones de los datos",
            ],
            variables={"domain": "general"},
            category="builtin",
            version="1.0",
        ),
        "reviewer": AgentTemplate(
            name="reviewer",
            description="Revisor crítico con auditoría de código y documentos",
            system_prompt=(
                "Eres un revisor crítico experto en {focus_area}. "
                "Tu misión es encontrar problemas, inconsistencias, "
                "y oportunidades de mejora en el contenido que revisas.\n\n"
                "Directrices:\n"
                "- Sé constructivo en tus críticas\n"
                "- Clasifica los problemas por severidad (crítico, mayor, menor)\n"
                "- Sugiere soluciones específicas\n"
                "- Destaca también lo que está bien hecho\n"
                "- Verifica la coherencia y consistencia\n"
                "- Revisa seguridad y buenas prácticas"
            ),
            allowed_tools=[
                "read_file", "search_in_files", "run_terminal",
                "run_git", "get_git_status",
            ],
            constraints=[
                "Ser constructivo, no destructivo",
                "Clasificar por severidad",
                "Sugerir soluciones",
            ],
            variables={"focus_area": "código"},
            category="builtin",
            version="1.0",
        ),
        "creative": AgentTemplate(
            name="creative",
            description="Escritor creativo con generación de contenido original",
            system_prompt=(
                "Eres un escritor creativo especializado en {genre}. "
                "Tu misión es crear contenido original, imaginativo y bien elaborado.\n\n"
                "Directrices:\n"
                "- Sé original y evita clichés\n"
                "- Mantén coherencia narrativa\n"
                "- Usa un vocabulario variado y preciso\n"
                "- Adapta el tono al contexto y audiencia\n"
                "- Revisa y refina tu trabajo antes de entregarlo\n"
                "- Experimenta con estructuras y formatos"
            ),
            allowed_tools=[
                "read_file", "write_file", "search_in_files",
                "open_url", "search_google",
            ],
            constraints=[
                "No plagiar contenido existente",
                "Mantener tono apropiado",
                "Revisar antes de entregar",
            ],
            variables={"genre": "fantasía oscura"},
            category="builtin",
            version="1.0",
        ),
    }

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._custom_templates: Dict[str, AgentTemplate] = {}
        self._load_custom_templates()

    def list_templates(self, category: Optional[str] = None) -> List[AgentTemplate]:
        """Lista todas las templates disponibles.

        Args:
            category: Filtrar por categoría ('builtin' o 'custom').
        """
        all_templates = list(self.BUILTIN_TEMPLATES.values()) + list(self._custom_templates.values())
        if category:
            all_templates = [t for t in all_templates if t.category == category]
        return sorted(all_templates, key=lambda t: (t.category, t.name))

    def get(self, name: str) -> Optional[AgentTemplate]:
        """Obtiene una template por nombre.

        Busca primero en built-in, luego en custom.
        Los custom sobreescriben los built-in del mismo nombre.
        """
        if name in self._custom_templates:
            return self._custom_templates[name]
        return self.BUILTIN_TEMPLATES.get(name)

    def save_template(self, template: AgentTemplate) -> Path:
        """Guarda una template custom como archivo YAML.

        Args:
            template: La template a guardar.

        Returns:
            Path al archivo guardado.
        """
        template.category = "custom"
        self._custom_templates[template.name] = template

        filepath = self.templates_dir / f"{template.name}.yaml"
        filepath.write_text(template.to_yaml(), encoding="utf-8")
        logger.info("[Templates] Template guardada: %s", template.name)
        return filepath

    def delete_template(self, name: str) -> bool:
        """Elimina una template custom.

        Args:
            name: Nombre de la template a eliminar.

        Returns:
            True si se eliminó, False si no existía o es built-in.
        """
        if name in self.BUILTIN_TEMPLATES and name not in self._custom_templates:
            return False  # No se pueden eliminar built-in

        if name in self._custom_templates:
            del self._custom_templates[name]

        filepath = self.templates_dir / f"{name}.yaml"
        if filepath.exists():
            filepath.unlink()
            logger.info("[Templates] Template eliminada: %s", name)
            return True
        return False

    def _load_custom_templates(self):
        """Carga templates custom desde el directorio."""
        if not self.templates_dir.exists():
            return

        for filepath in self.templates_dir.glob("*.yaml"):
            try:
                content = filepath.read_text(encoding="utf-8")
                template = AgentTemplate.from_yaml(content)
                template.category = "custom"
                self._custom_templates[template.name] = template
                logger.debug("[Templates] Cargada template custom: %s", template.name)
            except Exception as e:
                logger.warning("[Templates] Error cargando %s: %s", filepath.name, e)

        for filepath in self.templates_dir.glob("*.yml"):
            try:
                content = filepath.read_text(encoding="utf-8")
                template = AgentTemplate.from_yaml(content)
                template.category = "custom"
                self._custom_templates[template.name] = template
                logger.debug("[Templates] Cargada template custom: %s", template.name)
            except Exception as e:
                logger.warning("[Templates] Error cargando %s: %s", filepath.name, e)

    def reload(self) -> int:
        """Recarga las templates custom desde disco.

        Returns:
            Número de templates custom cargadas.
        """
        self._custom_templates.clear()
        self._load_custom_templates()
        return len(self._custom_templates)


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_library_instance: Optional[TemplateLibrary] = None


def get_template_library() -> TemplateLibrary:
    """Obtiene la instancia singleton de la TemplateLibrary."""
    global _library_instance
    if _library_instance is None:
        _library_instance = TemplateLibrary()
    return _library_instance