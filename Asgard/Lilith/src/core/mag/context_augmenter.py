"""
Context Augmenter - Integración de MAG con prompts

v5.0: Inyecta contexto relevante recuperado por MAG en los prompts del sistema.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .mag_engine import MAGEngine, RetrievalResult, get_mag_engine

logger = logging.getLogger("lilith.mag.augmenter")


@dataclass
class AugmentedPrompt:
    """Prompt con contexto augmentado."""

    original_prompt: str
    augmented_prompt: str
    context_used: bool
    context_tokens: int
    sources: List[str]


class ContextAugmenter:
    """
    Augmentador de contexto para prompts.

    Integra MAG con el sistema de prompts para proporcionar
    contexto relevante basado en recuperación semántica.
    """

    def __init__(
        self,
        mag_engine: Optional[MAGEngine] = None,
        max_context_tokens: int = 2000,
        min_relevance_score: float = 0.7,
        context_template: Optional[str] = None,
    ):
        self.mag = mag_engine or get_mag_engine()
        self.max_context_tokens = max_context_tokens
        self.min_relevance_score = min_relevance_score

        self.context_template = (
            context_template
            or """# Contexto Relevante

La siguiente información puede ser útil para responder la consulta:

{context}

---
# Consulta del Usuario

{prompt}
"""
        )

    async def augment(
        self,
        prompt: str,
        collection: Optional[str] = None,
        top_k: int = 5,
        force_context: bool = False,
    ) -> AugmentedPrompt:
        """
        Augmenta un prompt con contexto recuperado.

        Args:
            prompt: Prompt original
            collection: Colección a buscar
            top_k: Número de documentos
            force_context: Si True, siempre incluye contexto aunque sea vacío

        Returns:
            Prompt augmentado
        """
        try:
            # Recuperar contexto
            retrieval = await self.mag.retrieve(
                query=prompt,
                top_k=top_k,
                min_score=self.min_relevance_score,
                collection=collection,
            )

            # Verificar si hay contexto relevante
            if not retrieval.documents and not force_context:
                return AugmentedPrompt(
                    original_prompt=prompt,
                    augmented_prompt=prompt,
                    context_used=False,
                    context_tokens=0,
                    sources=[],
                )

            # Limitar tokens de contexto si es necesario
            context_text = retrieval.context_text
            if retrieval.total_tokens > self.max_context_tokens:
                context_text = self._truncate_context(
                    retrieval, max_tokens=self.max_context_tokens
                )

            # Construir prompt augmentado
            augmented = self.context_template.format(
                context=context_text, prompt=prompt
            )

            # Extraer fuentes
            sources = list(
                set(
                    doc.document.source
                    for doc in retrieval.documents
                    if doc.document.source
                )
            )

            return AugmentedPrompt(
                original_prompt=prompt,
                augmented_prompt=augmented,
                context_used=True,
                context_tokens=len(context_text.split()),
                sources=sources,
            )

        except Exception as e:
            logger.error(f"Error augmentando prompt: {e}")
            # Fallback: retornar prompt original
            return AugmentedPrompt(
                original_prompt=prompt,
                augmented_prompt=prompt,
                context_used=False,
                context_tokens=0,
                sources=[],
            )

    def _truncate_context(self, retrieval: RetrievalResult, max_tokens: int) -> str:
        """Trunca el contexto para respetar límite de tokens."""
        # Estrategia simple: mantener documentos más relevantes hasta llenar tokens
        parts = []
        current_tokens = 0

        for result in retrieval.documents:
            doc_text = result.document.content
            doc_tokens = len(doc_text.split())

            if current_tokens + doc_tokens > max_tokens:
                # Truncar este documento
                remaining = max_tokens - current_tokens
                words = doc_text.split()[:remaining]
                parts.append(" ".join(words))
                break

            parts.append(doc_text)
            current_tokens += doc_tokens

        return "\n\n".join(parts)

    async def augment_with_metadata(
        self,
        prompt: str,
        metadata_filter: Dict[str, Any],
        collection: Optional[str] = None,
    ) -> AugmentedPrompt:
        """
        Augmenta con filtrado por metadata.

        Args:
            prompt: Prompt original
            metadata_filter: Filtro de metadata (e.g., {"source": "docs"})
            collection: Colección

        Returns:
            Prompt augmentado
        """

        # Crear filtro
        def filter_fn(meta: Dict) -> bool:
            return all(meta.get(key) == value for key, value in metadata_filter.items())

        # Recuperar con filtro
        retrieval = await self.mag.retrieve(
            query=prompt, collection=collection, filter_fn=filter_fn
        )

        if not retrieval.documents:
            return AugmentedPrompt(
                original_prompt=prompt,
                augmented_prompt=prompt,
                context_used=False,
                context_tokens=0,
                sources=[],
            )

        context_text = retrieval.context_text
        if retrieval.total_tokens > self.max_context_tokens:
            context_text = self._truncate_context(retrieval, self.max_context_tokens)

        augmented = self.context_template.format(context=context_text, prompt=prompt)

        sources = list(
            set(
                doc.document.source
                for doc in retrieval.documents
                if doc.document.source
            )
        )

        return AugmentedPrompt(
            original_prompt=prompt,
            augmented_prompt=augmented,
            context_used=True,
            context_tokens=len(context_text.split()),
            sources=sources,
        )


# Singleton global
_augmenter: Optional[ContextAugmenter] = None


def get_context_augmenter() -> ContextAugmenter:
    """Obtiene instancia singleton del augmenter."""
    global _augmenter
    if _augmenter is None:
        _augmenter = ContextAugmenter()
    return _augmenter


def initialize_context_augmenter(
    max_context_tokens: int = 2000, min_relevance_score: float = 0.7
):
    """Inicializa el augmenter con configuración personalizada."""
    global _augmenter
    _augmenter = ContextAugmenter(
        max_context_tokens=max_context_tokens, min_relevance_score=min_relevance_score
    )
