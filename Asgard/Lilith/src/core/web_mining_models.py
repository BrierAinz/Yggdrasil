"""
Lilith 4.2 — Modelos de datos para el pipeline de minería web.

Define las estructuras de datos que fluyen a través del pipeline:
ScrapedContent → CleanedContent → QualityScore → StructuredData → SemanticFact
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ScrapingStrategy(Enum):
    """Estrategias de extracción de contenido web."""

    FULL_PAGE = "full_page"
    ARTICLE_ONLY = "article_only"
    STRUCTURED_DATA = "structured_data"


class ContentCategory(Enum):
    """Categorías de contenido para clasificación."""

    CODE = "code"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    NEWS = "news"
    BLOG = "blog"
    ACADEMIC = "academic"
    GENERAL = "general"


@dataclass
class ScrapedContent:
    """
    Contenido crudo extraído de una URL.

    Attributes:
        url: URL fuente del contenido
        raw_html: HTML completo de la página
        text: Texto extraído
        metadata: Metadatos extraídos (título, autor, fecha, etc.)
        strategy: Estrategia de scraping utilizada
        timestamp: Timestamp de la extracción
    """

    url: str
    raw_html: str = ""
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    strategy: ScrapingStrategy = ScrapingStrategy.FULL_PAGE
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def __post_init__(self):
        if not self.raw_html and self.text:
            # Si solo tenemos texto, lo usamos como raw también
            self.raw_html = self.text


@dataclass
class CleanedContent:
    """
    Contenido limpio después de procesar ScrapedContent.

    Attributes:
        url: URL fuente original
        cleaned_text: Texto limpio sin ads/navegación
        original_length: Longitud del texto original
        cleaned_length: Longitud después de limpieza
        metadata: Metadatos preservados
        hash: Hash del contenido para detección de duplicados
    """

    url: str
    cleaned_text: str = ""
    original_length: int = 0
    cleaned_length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.cleaned_length and self.cleaned_text:
            self.cleaned_length = len(self.cleaned_text)
        if not self.content_hash and self.cleaned_text:
            import hashlib

            self.content_hash = hashlib.md5(
                self.cleaned_text.encode("utf-8", errors="ignore")
            ).hexdigest()[:16]


@dataclass
class QualityScore:
    """
    Puntuación de calidad del contenido.

    Attributes:
        score: Puntuación 0.0-1.0
        reasons: Razones de la puntuación
        details: Métricas detalladas
        is_accepted: Si pasa el umbral de calidad
    """

    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    is_accepted: bool = False

    def __post_init__(self):
        self.score = max(0.0, min(1.0, self.score))


@dataclass
class Entity:
    """
    Entidad extraída del contenido.

    Attributes:
        name: Nombre de la entidad
        type: Tipo (persona, organización, tecnología, etc.)
        confidence: Confianza de la extracción
    """

    name: str
    type: str = "unknown"
    confidence: float = 1.0


@dataclass
class Relation:
    """
    Relación entre entidades.

    Attributes:
        source: Entidad origen
        target: Entidad destino
        relation: Tipo de relación
    """

    source: str
    target: str
    relation: str


@dataclass
class StructuredData:
    """
    Datos estructurados extraídos del contenido.

    Attributes:
        url: URL fuente
        summary: Resumen del contenido
        entities: Entidades extraídas
        relations: Relaciones entre entidades
        keywords: Palabras clave
        category: Categoría del contenido
        metadata: Metadatos adicionales
    """

    url: str
    summary: str = ""
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    category: ContentCategory = ContentCategory.GENERAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticFact:
    """
    Facto semántico listo para almacenar en memoria.

    Attributes:
        content: Contenido del facto
        source: Fuente (URL)
        category: Categoría
        topics: Tópicos relacionados
        metadata: Metadatos adicionales
        entities: Entidades relacionadas
    """

    content: str
    source: str
    category: str = "general"
    topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)

    def to_memory_format(self) -> Dict[str, Any]:
        """Convierte a formato para MemoryStore."""
        return {
            "domain": self.category,
            "entity": self.source[:50],  # Truncar URL
            "fact": self.content,
            "tags": self.topics + self.entities,
        }


@dataclass
class MiningResult:
    """
    Resultado completo del pipeline de minería.

    Attributes:
        url: URL procesada
        success: Si el proceso fue exitoso
        facts: Facts generados
        quality_score: Puntuación de calidad
        error: Mensaje de error si falló
        processing_time: Tiempo de procesamiento en segundos
    """

    url: str
    success: bool = False
    facts: List[SemanticFact] = field(default_factory=list)
    quality_score: Optional[QualityScore] = None
    error: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class BatchMiningResult:
    """
    Resultado de procesamiento batch de múltiples URLs.

    Attributes:
        total: Total de URLs procesadas
        success: URLs exitosas
        rejected: URLs rechazadas por calidad
        failed: URLs con error
        facts_generated: Total de facts generados
        results: Resultados individuales
    """

    total: int = 0
    success: int = 0
    rejected: int = 0
    failed: int = 0
    facts_generated: int = 0
    results: List[MiningResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para reporting."""
        return {
            "total": self.total,
            "success": self.success,
            "rejected": self.rejected,
            "failed": self.failed,
            "facts_generated": self.facts_generated,
            "success_rate": round(self.success / max(1, self.total), 2),
        }


# Fuentes de calidad predefinidas
HIGH_QUALITY_SOURCES = frozenset(
    [
        "wikipedia.org",
        "github.com",
        "stackoverflow.com",
        "docs.python.org",
        "developer.mozilla.org",
        "docs.microsoft.com",
        "docs.aws.amazon.com",
        "cloud.google.com",
        "kubernetes.io",
        "docker.com",
        "postgresql.org",
        "redis.io",
        "nodejs.org",
        "react.dev",
        "vuejs.org",
        "angular.io",
        "typescriptlang.org",
        "rust-lang.org",
        "golang.org",
        "docs.rs",
        "readthedocs.io",
        "arxiv.org",
        "ieee.org",
        "acm.org",
    ]
)

MEDIUM_QUALITY_SOURCES = frozenset(
    [
        "medium.com",
        "dev.to",
        "hashnode.com",
        "freecodecamp.org",
        "tutorialspoint.com",
        "geeksforgeeks.org",
        "w3schools.com",
        "codecademy.com",
        "udemy.com",
        "coursera.org",
    ]
)

LOW_QUALITY_INDICATORS = frozenset(
    [
        "clickbait",
        "ads",
        "popup",
        "tracking",
    ]
)


def classify_source_quality(url: str) -> str:
    """
    Clasifica la calidad de una fuente basada en su URL.

    Returns:
        "high", "medium", "low", o "unknown"
    """
    from urllib.parse import urlparse

    try:
        domain = urlparse(url).netloc.lower()
        if not domain:
            return "unknown"

        # Remover www. si existe
        if domain.startswith("www."):
            domain = domain[4:]

        # Verificar contra listas
        for high in HIGH_QUALITY_SOURCES:
            if high in domain or domain.endswith("." + high):
                return "high"

        for medium in MEDIUM_QUALITY_SOURCES:
            if medium in domain or domain.endswith("." + medium):
                return "medium"

        # Verificar indicadores de baja calidad
        for low in LOW_QUALITY_INDICATORS:
            if low in domain:
                return "low"

        return "unknown"
    except Exception:
        return "unknown"


def get_strategy_for_source(url: str) -> ScrapingStrategy:
    """
    Determina la estrategia de scraping óptima para una URL.

    Returns:
        ScrapingStrategy recomendada
    """
    quality = classify_source_quality(url)

    if quality == "high":
        return ScrapingStrategy.ARTICLE_ONLY
    elif quality == "medium":
        return ScrapingStrategy.ARTICLE_ONLY
    else:
        return ScrapingStrategy.FULL_PAGE


__all__ = [
    "ScrapingStrategy",
    "ContentCategory",
    "ScrapedContent",
    "CleanedContent",
    "QualityScore",
    "Entity",
    "Relation",
    "StructuredData",
    "SemanticFact",
    "MiningResult",
    "BatchMiningResult",
    "HIGH_QUALITY_SOURCES",
    "MEDIUM_QUALITY_SOURCES",
    "LOW_QUALITY_INDICATORS",
    "classify_source_quality",
    "get_strategy_for_source",
]
