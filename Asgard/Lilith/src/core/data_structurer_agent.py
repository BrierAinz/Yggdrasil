"""
Lilith 4.2 — DataStructurerAgent: convierte texto validado en hecho estructurado.

Extrae conceptos/entidades (términos técnicos, ALL_CAPS, CamelCase), genera un resumen
extractivo, detecta relaciones entre entidades y asigna un tópico.
Salida: StructuredData y SemanticFacts listos para guardar en memoria semántica.
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .agent_registry import Agent
from .tools_v3.protocol import ToolResult
from .web_mining_models import (
    CleanedContent,
    ContentCategory,
    Entity,
    QualityScore,
    Relation,
    SemanticFact,
    StructuredData,
)

logger = logging.getLogger("DataStructurerAgent")

# Prefijo que puede añadir QualityFilterAgent
_QUALITY_PREFIX_RE = re.compile(r"^\[Calidad validada:[^\]]+\]\s*\n*", re.IGNORECASE)


def _strip_quality_prefix(text: str) -> str:
    """Quita el prefijo de calidad para procesar solo el contenido."""
    return _QUALITY_PREFIX_RE.sub("", text).strip()


def _extract_entities(text: str, max_entities: int = 25) -> List[Entity]:
    """Extrae posibles entidades: ALL_CAPS (VACUUM, SQL), CamelCase (PostgreSQL), términos técnicos conocidos."""
    seen: Set[str] = set()
    entities: List[Entity] = []

    # ALL_CAPS (mínimo 2 letras) - generalmente acrónimos
    for m in re.finditer(r"\b([A-Z][A-Z0-9_]{1,30})\b", text):
        w = m.group(1)
        if w not in seen and w not in (
            "HTML",
            "HTTP",
            "URL",
            "API",
            "ID",
            "JSON",
            "XML",
            "CSS",
        ):
            seen.add(w)
            entities.append(Entity(name=w, type="acronym", confidence=0.9))

    # CamelCase (PostgreSQL, GiST, BTree) - tecnologías/librerías
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b", text):
        w = m.group(1)
        if w not in seen:
            seen.add(w)
            entities.append(Entity(name=w, type="technology", confidence=0.85))

    # Términos técnicos conocidos con contexto
    tech_terms = {
        # Bases de datos
        "postgresql": ("database", 0.9),
        "postgres": ("database", 0.9),
        "mysql": ("database", 0.9),
        "mongodb": ("database", 0.9),
        "redis": ("database", 0.9),
        "elasticsearch": ("database", 0.9),
        "sqlite": ("database", 0.9),
        "vacuum": ("database_operation", 0.8),
        "explain": ("database_operation", 0.8),
        "analyze": ("database_operation", 0.8),
        "index": ("database_feature", 0.8),
        "b-tree": ("data_structure", 0.85),
        "gist": ("index_type", 0.85),
        "hash": ("data_structure", 0.8),
        "gin": ("index_type", 0.85),
        "query": ("database_operation", 0.8),
        "join": ("database_operation", 0.8),
        "trigger": ("database_feature", 0.8),
        "view": ("database_feature", 0.8),
        "transaction": ("database_feature", 0.8),
        "lock": ("database_feature", 0.8),
        "replication": ("database_feature", 0.8),
        # Machine Learning
        "machine learning": ("ml", 0.9),
        "tensorflow": ("ml_framework", 0.9),
        "pytorch": ("ml_framework", 0.9),
        "embedding": ("ml_technique", 0.85),
        "neural": ("ml_technique", 0.8),
        "deep learning": ("ml", 0.9),
        "transformer": ("ml_architecture", 0.9),
        "llm": ("ml_model", 0.9),
        "model": ("ml_concept", 0.7),
        "training": ("ml_process", 0.8),
        "inference": ("ml_process", 0.8),
        "fine-tuning": ("ml_process", 0.85),
        "vector": ("data_structure", 0.75),
        "classification": ("ml_task", 0.8),
        "regression": ("ml_task", 0.8),
        "clustering": ("ml_task", 0.8),
        # Lenguajes de programación
        "python": ("language", 0.95),
        "javascript": ("language", 0.95),
        "typescript": ("language", 0.95),
        "html": ("language", 0.9),
        "css": ("language", 0.9),
        "c++": ("language", 0.9),
        "cpp": ("language", 0.9),
        "c#": ("language", 0.9),
        "csharp": ("language", 0.9),
        "java": ("language", 0.95),
        "rust": ("language", 0.9),
        "go": ("language", 0.9),
        "golang": ("language", 0.9),
        "kotlin": ("language", 0.85),
        "swift": ("language", 0.85),
        "php": ("language", 0.85),
        "ruby": ("language", 0.85),
        "scala": ("language", 0.85),
        "r": ("language", 0.8),
        "matlab": ("language", 0.8),
        # Frameworks/Librerías web
        "react": ("frontend_framework", 0.9),
        "vue": ("frontend_framework", 0.9),
        "vue.js": ("frontend_framework", 0.9),
        "angular": ("frontend_framework", 0.9),
        "svelte": ("frontend_framework", 0.85),
        "next.js": ("fullstack_framework", 0.9),
        "nuxt": ("fullstack_framework", 0.85),
        "node.js": ("runtime", 0.9),
        "nodejs": ("runtime", 0.9),
        "npm": ("package_manager", 0.9),
        "yarn": ("package_manager", 0.85),
        "pnpm": ("package_manager", 0.85),
        "webpack": ("build_tool", 0.85),
        "vite": ("build_tool", 0.85),
        "rollup": ("build_tool", 0.8),
        "babel": ("compiler", 0.85),
        "eslint": ("linting_tool", 0.85),
        "prettier": ("formatting_tool", 0.85),
        # Backend/Frameworks
        "fastapi": ("backend_framework", 0.9),
        "django": ("backend_framework", 0.9),
        "flask": ("backend_framework", 0.9),
        "express": ("backend_framework", 0.9),
        "spring": ("backend_framework", 0.9),
        "rails": ("backend_framework", 0.85),
        "laravel": ("backend_framework", 0.85),
        "docker": ("containerization", 0.9),
        "kubernetes": ("orchestration", 0.9),
        "k8s": ("orchestration", 0.9),
        "aws": ("cloud_provider", 0.9),
        "azure": ("cloud_provider", 0.9),
        "gcp": ("cloud_provider", 0.9),
        "lambda": ("serverless", 0.85),
        "serverless": ("architecture", 0.8),
        "microservices": ("architecture", 0.8),
        "api": ("interface", 0.8),
        "rest": ("api_style", 0.85),
        "graphql": ("api_style", 0.9),
        "grpc": ("rpc_framework", 0.85),
        "websocket": ("protocol", 0.85),
        "oauth": ("auth_protocol", 0.85),
        "jwt": ("auth_token", 0.85),
        # Discord/Bots
        "discord": ("platform", 0.9),
        "discord.js": ("bot_framework", 0.9),
        "discord.py": ("bot_framework", 0.9),
        "bot": ("application_type", 0.7),
        "slash command": ("discord_feature", 0.85),
        "gateway": ("discord_feature", 0.8),
        "embed": ("discord_feature", 0.8),
        # Conceptos de programación
        "async": ("programming_concept", 0.8),
        "promise": ("programming_concept", 0.8),
        "callback": ("programming_concept", 0.8),
        "function": ("programming_concept", 0.75),
        "variable": ("programming_concept", 0.75),
        "loop": ("programming_concept", 0.75),
        "array": ("data_structure", 0.75),
        "object": ("data_structure", 0.75),
        "class": ("oop_concept", 0.8),
        "inheritance": ("oop_concept", 0.8),
        "interface": ("oop_concept", 0.8),
        "syntax": ("language_feature", 0.75),
        "refactor": ("process", 0.8),
        "testing": ("process", 0.8),
        "unit test": ("testing", 0.85),
        "integration test": ("testing", 0.85),
        "ci/cd": ("devops", 0.85),
        "github actions": ("ci_tool", 0.9),
        "gitlab ci": ("ci_tool", 0.85),
        "jenkins": ("ci_tool", 0.85),
        # Lilith específico
        "lilith": ("project", 0.95),
        "yggdrasil": ("project", 0.9),
        "nazarick": ("project", 0.9),
        "agent": ("lilith_concept", 0.85),
        "orchestrator": ("lilith_concept", 0.85),
        "planner": ("lilith_concept", 0.85),
        "memory": ("lilith_concept", 0.85),
        "semantic": ("memory_type", 0.8),
        "episodic": ("memory_type", 0.8),
        "tool": ("lilith_concept", 0.8),
    }

    lower = text.lower()
    for term, (etype, confidence) in tech_terms.items():
        # Buscar palabra completa
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, lower) and term not in seen:
            seen.add(term)
            entities.append(Entity(name=term, type=etype, confidence=confidence))

    return entities[:max_entities]


def _extract_relations(text: str, entities: List[Entity]) -> List[Relation]:
    """Detecta relaciones simples entre entidades basadas en proximidad y patrones."""
    if len(entities) < 2:
        return []

    relations = []
    entity_names = [e.name.lower() for e in entities]

    # Patrones de relación
    relation_patterns = [
        (r"(\w+)\s+usa\s+(\w+)", "uses"),
        (r"(\w+)\s+usando\s+(\w+)", "uses"),
        (r"(\w+)\s+implements\s+(\w+)", "implements"),
        (r"(\w+)\s+implementa\s+(\w+)", "implements"),
        (r"(\w+)\s+extends?\s+(\w+)", "extends"),
        (r"(\w+)\s+hereda\s+(?:de\s+)?(\w+)", "extends"),
        (r"(\w+)\s+depends?\s+on\s+(\w+)", "depends_on"),
        (r"(\w+)\s+depende\s+(?:de\s+)?(\w+)", "depends_on"),
        (r"(\w+)\s+built\s+(?:with|using)\s+(\w+)", "built_with"),
        (r"(\w+)\s+construido\s+(?:con|usando)\s+(\w+)", "built_with"),
        (r"(\w+)\s+requires?\s+(\w+)", "requires"),
        (r"(\w+)\s+requiere\s+(\w+)", "requires"),
        (r"(\w+)\s+supports?\s+(\w+)", "supports"),
        (r"(\w+)\s+soporta\s+(\w+)", "supports"),
    ]

    lower_text = text.lower()
    seen_pairs: Set[Tuple[str, str]] = set()

    for pattern, relation_type in relation_patterns:
        for match in re.finditer(pattern, lower_text):
            source = match.group(1)
            target = match.group(2)

            # Verificar que ambos están en entidades
            if source in entity_names and target in entity_names:
                pair = (source, target)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    relations.append(
                        Relation(
                            source=entities[entity_names.index(source)].name,
                            target=entities[entity_names.index(target)].name,
                            relation=relation_type,
                        )
                    )

    # Relaciones por proximidad (entidades cercanas en el mismo párrafo)
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        para_entities = []
        for i, name in enumerate(entity_names):
            if re.search(r"\b" + re.escape(name) + r"\b", para.lower()):
                para_entities.append((i, name))

        # Si hay pocas entidades en el párrafo, asumir relación contextual
        if 2 <= len(para_entities) <= 4:
            for i in range(len(para_entities) - 1):
                idx1, name1 = para_entities[i]
                idx2, name2 = para_entities[i + 1]
                pair = tuple(sorted([name1, name2]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    relations.append(
                        Relation(
                            source=entities[idx1].name,
                            target=entities[idx2].name,
                            relation="related_to",
                        )
                    )

    return relations[:15]  # Limitar relaciones


def _extract_summary(text: str, max_chars: int = 400) -> str:
    """Resumen extractivo: primeras frases o primeros max_chars."""
    text = text.strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    # Cortar por frase (punto + espacio)
    truncated = text[: max_chars + 100]
    last_period = truncated.rfind(". ")
    if last_period > max_chars // 2:
        return truncated[: last_period + 1].strip()

    return text[:max_chars].rstrip() + "…"


def _extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extrae palabras clave por frecuencia (excluyendo stopwords)."""
    from collections import Counter

    # Palabras comunes a ignorar
    stopwords = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "day",
        "get",
        "has",
        "him",
        "his",
        "how",
        "its",
        "may",
        "new",
        "now",
        "old",
        "see",
        "two",
        "who",
        "boy",
        "did",
        "she",
        "use",
        "her",
        "way",
        "many",
        "oil",
        "sit",
        "set",
        "run",
        "eat",
        "far",
        "sea",
        "eye",
        "ago",
        "off",
        "too",
        "any",
        "say",
        "man",
        "try",
        "ask",
        "end",
        "why",
        "let",
        "put",
        "say",
        "she",
        "try",
        "way",
        "own",
        "say",
        "too",
        "old",
        "tell",
        "very",
        "when",
        "much",
        "would",
        "there",
        "their",
        "el",
        "la",
        "de",
        "que",
        "y",
        "a",
        "en",
        "un",
        "ser",
        "se",
        "no",
        "haber",
        "por",
        "con",
        "su",
        "para",
        "como",
        "estar",
        "tener",
        "le",
        "lo",
        "pero",
        "más",
        "hacer",
        "o",
        "poder",
        "este",
        "otro",
        "ir",
        "ese",
        "la",
        "si",
        "me",
        "ya",
        "ver",
        "porque",
        "dar",
        "cuando",
        "él",
        "muy",
        "sin",
        "vez",
        "bien",
        "cada",
        "sobre",
        "algo",
        "ser",
    }

    # Extraer palabras significativas
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    words = [w for w in words if w not in stopwords]

    # Contar frecuencia
    counter = Counter(words)

    # Retornar las más frecuentes
    return [word for word, count in counter.most_common(max_keywords)]


# Palabras clave -> tópico para clasificación simple (incl. lenguajes de programación)
_TOPIC_KEYWORDS: List[Tuple[List[str], str]] = [
    (
        [
            "python",
            "pip",
            "pypi",
            "interpreted",
            "indentation",
            "def ",
            "lambda python",
        ],
        "Lenguajes / Python",
    ),
    (
        [
            "javascript",
            "ecmascript",
            "node.js",
            "npm",
            "dom",
            "callback",
            "promise",
            "async await",
        ],
        "Lenguajes / JavaScript",
    ),
    (["typescript", "type script", "ts config"], "Lenguajes / TypeScript"),
    (["html", "htm ", "tag ", "div", "span", "semantic html"], "Lenguajes / HTML"),
    (
        ["css", "stylesheet", "selector", "flexbox", "grid css", "media query"],
        "Lenguajes / CSS",
    ),
    (["c++", "cpp", "stl", "template c++", "namespace std"], "Lenguajes / C++"),
    (["c#", "csharp", ".net", "dotnet"], "Lenguajes / C#"),
    (["java", "jvm", "jdk", "maven", "spring java"], "Lenguajes / Java"),
    (["rust", "cargo", "ownership", "borrow checker"], "Lenguajes / Rust"),
    (["go ", "golang", "goroutine", "go module"], "Lenguajes / Go"),
    (
        [
            "postgresql",
            "postgres",
            "sql",
            "vacuum",
            "índice",
            "index",
            "query",
            "join",
            "gist",
            "b-tree",
        ],
        "Base de datos / PostgreSQL",
    ),
    (
        [
            "machine learning",
            "ml",
            "neural",
            "tensor",
            "modelo",
            "entrenar",
            "embedding",
        ],
        "Machine Learning",
    ),
    (
        [
            "discord",
            "discord.js",
            "discord.py",
            "bot discord",
            "slash command",
            "gateway discord",
            "embed discord",
            "developers/docs",
            "discord api",
            "application command",
        ],
        "Discord / API y bots",
    ),
    (["api", "rest", "http", "servidor", "backend", "frontend"], "Desarrollo web"),
    (["seguridad", "auth", "token", "cripto"], "Seguridad"),
    (
        ["código", "refactor", "test", "función", "variable", "syntax"],
        "Programación (general)",
    ),
    (["lilith", "yggdrasil", "nazarick", "agent", "orchestrator"], "Lilith / Proyecto"),
]


def _classify_topic(text: str) -> str:
    """Clasificación por tópico según palabras clave."""
    lower = text.lower()
    scores: Dict[str, int] = {}
    for keywords, topic in _TOPIC_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                scores[topic] = scores.get(topic, 0) + 1
    if not scores:
        return "General"
    return max(scores, key=scores.get)


def _classify_category(text: str) -> ContentCategory:
    """Clasifica el contenido en una categoría."""
    lower = text.lower()

    # Documentación
    if any(
        kw in lower
        for kw in ["documentation", "docs", "reference", "api reference", "guide"]
    ):
        return ContentCategory.DOCUMENTATION

    # Tutorial
    if any(
        kw in lower
        for kw in ["tutorial", "how to", "getting started", "learn", "course"]
    ):
        return ContentCategory.TUTORIAL

    # Código
    if "```" in text or text.count(";") > 5 or text.count("{") > 5:
        return ContentCategory.CODE

    # Noticias
    if any(
        kw in lower for kw in ["news", "announcing", "release", "update", "version"]
    ):
        return ContentCategory.NEWS

    # Blog
    if any(kw in lower for kw in ["blog", "post", "article", "opinion"]):
        return ContentCategory.BLOG

    return ContentCategory.GENERAL


def _format_fact(summary: str, entities: List[Entity], topic: str, excerpt: str) -> str:
    """Formato único para mostrar y guardar en memoria semántica."""
    parts = ["[Minería web]"]
    parts.append(f"Tópico: {topic}.")
    parts.append(f"Resumen: {summary}")
    if entities:
        entity_names = [e.name for e in entities[:15]]
        parts.append(f"Conceptos: {', '.join(entity_names)}.")
    if excerpt and excerpt != summary:
        parts.append(
            f"Fragmento: {excerpt[:200]}…"
            if len(excerpt) > 200
            else f"Fragmento: {excerpt}"
        )
    return "\n".join(parts).strip()


def _load_config(base_path: Optional[Path]) -> Dict[str, Any]:
    """Carga Config/data_structurer.json si existe."""
    if not base_path or not base_path.exists():
        return {}
    try:
        from .json_safe import safe_load

        path = base_path / "Config" / "data_structurer.json"
        if not path.exists():
            return {}
        data = safe_load(path, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class DataStructurerAgent(Agent):
    """
    Agente que estructura el texto validado: entidades, resumen, tópico.
    Salida formateada para lectura y para guardar como hecho en memoria semántica.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = Path(base_path) if base_path else None
        self._config = _load_config(self._base_path)

    @property
    def agent_id(self) -> str:
        return "data_structurer"

    @property
    def tool_name(self) -> str:
        return "delegate_data_structurer"

    @property
    def description(self) -> str:
        return "Estructura texto validado: extrae conceptos, resumen y tópico; genera facts semánticos."

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecución síncrona compatible con AgentRegistry."""
        try:
            # Si viene CleanedContent
            cleaned = params.get("cleaned_content")
            quality = params.get("quality_score")

            if cleaned and isinstance(cleaned, CleanedContent):
                structured = self.structure(cleaned)
            else:
                raw = (params.get("context") or params.get("text") or "").strip()
                if not raw:
                    return {
                        "response": "No hay texto que estructurar (pasa 'context' o 'text').",
                        "error": True,
                    }

                content = _strip_quality_prefix(raw)
                if not content or len(content) < 20:
                    return {
                        "response": "Contenido insuficiente tras quitar metadatos de calidad.",
                        "error": False,
                    }

                # Crear CleanedContent temporal
                temp_cleaned = CleanedContent(
                    url=params.get("url", ""),
                    cleaned_text=content,
                    cleaned_length=len(content),
                )
                structured = self.structure(temp_cleaned)

            # Generar facts
            facts = self.to_semantic_facts(structured)

            logger.info(
                "[DataStructurer] Extracted %d entities, %d relations, %d facts",
                len(structured.entities),
                len(structured.relations),
                len(facts),
            )

            fact_text = _format_fact(
                structured.summary,
                structured.entities,
                structured.category.value,
                structured.cleaned_text[:300]
                if hasattr(structured, "cleaned_text")
                else "",
            )

            return {
                "response": fact_text,
                "structured": {
                    "summary": structured.summary,
                    "entities": [
                        {"name": e.name, "type": e.type} for e in structured.entities
                    ],
                    "relations": [
                        {"source": r.source, "target": r.target, "relation": r.relation}
                        for r in structured.relations
                    ],
                    "keywords": structured.keywords,
                    "topic": _classify_topic(structured.summary),
                    "category": structured.category.value,
                },
                "facts": [f.content for f in facts],
                "error": False,
            }

        except Exception as e:
            logger.warning("DataStructurerAgent: %s", e)
            return {"response": str(e), "error": True}

    def structure(self, content: CleanedContent) -> StructuredData:
        """
        Estructura el contenido limpio.

        Args:
            content: Contenido limpio

        Returns:
            StructuredData con entidades, relaciones, etc.
        """
        max_summary = int(self._config.get("max_summary_chars", 400))
        max_entities = int(self._config.get("max_entities", 25))

        entities = _extract_entities(content.cleaned_text, max_entities=max_entities)
        relations = _extract_relations(content.cleaned_text, entities)
        summary = _extract_summary(content.cleaned_text, max_chars=max_summary)
        keywords = _extract_keywords(content.cleaned_text)
        category = _classify_category(content.cleaned_text)

        return StructuredData(
            url=content.url,
            summary=summary,
            entities=entities,
            relations=relations,
            keywords=keywords,
            category=category,
            metadata=content.metadata,
        )

    def to_semantic_facts(self, structured: StructuredData) -> List[SemanticFact]:
        """
        Convierte datos estructurados en facts semánticos.

        Args:
            structured: Datos estructurados

        Returns:
            Lista de SemanticFact
        """
        facts = []
        entity_names = [e.name for e in structured.entities]

        # Fact del resumen principal
        if structured.summary:
            facts.append(
                SemanticFact(
                    content=structured.summary,
                    source=structured.url,
                    category=structured.category.value,
                    topics=[_classify_topic(structured.summary)]
                    + structured.keywords[:3],
                    metadata={
                        "type": "summary",
                        "keywords": structured.keywords,
                    },
                    entities=entity_names[:10],
                )
            )

        # Facts de entidades
        for entity in structured.entities[:10]:  # Limitar a 10 entidades
            facts.append(
                SemanticFact(
                    content=f"{entity.name} es un {entity.type.replace('_', ' ')}",
                    source=structured.url,
                    category="entity",
                    topics=[entity.type, structured.category.value],
                    metadata={
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        "confidence": entity.confidence,
                    },
                    entities=[entity.name],
                )
            )

        # Facts de relaciones
        for relation in structured.relations[:5]:  # Limitar a 5 relaciones
            facts.append(
                SemanticFact(
                    content=f"{relation.source} {relation.relation.replace('_', ' ')} {relation.target}",
                    source=structured.url,
                    category="relation",
                    topics=[structured.category.value],
                    metadata={
                        "source_entity": relation.source,
                        "target_entity": relation.target,
                        "relation_type": relation.relation,
                    },
                    entities=[relation.source, relation.target],
                )
            )

        return facts

    def store_facts(
        self,
        facts: List[SemanticFact],
        memory_store=None,
        base_path: Optional[Path] = None,
    ) -> int:
        """
        Almacena facts en memoria semántica.

        Args:
            facts: Lista de facts a almacenar
            memory_store: Instancia de MemoryStore (opcional)
            base_path: Ruta base para crear MemoryStore si no se proporciona

        Returns:
            Número de facts almacenados
        """
        if not facts:
            return 0

        if memory_store is None:
            if base_path is None:
                base_path = self._base_path
            if base_path:
                from .memory_store import MemoryStore, SemanticMemory

                memory_store = MemoryStore(base_path)
            else:
                logger.warning("No memory store available")
                return 0

        stored = 0
        for fact in facts:
            try:
                from .memory_store import SemanticMemory

                memory = SemanticMemory(
                    domain=fact.category,
                    entity=fact.source[:50],
                    fact=fact.content,
                    tags=fact.topics + fact.entities,
                )

                memory_store.upsert_memory(memory)
                stored += 1

            except Exception as e:
                logger.warning("Error storing fact: %s", e)

        logger.info(
            "[DataStructurer] Stored %d/%d facts in semantic memory", stored, len(facts)
        )
        return stored
