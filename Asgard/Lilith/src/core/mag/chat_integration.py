"""
MAG Chat Integration - Integración de MAG con flujo de chat

v5.0: Enriquece automáticamente los mensajes con contexto semántico relevante.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.mag import get_context_augmenter, get_mag_engine
from src.core.mag.context_augmenter import AugmentedPrompt

logger = logging.getLogger("lilith.mag.chat_integration")


@dataclass
class ChatContext:
    """Contexto de chat enriquecido."""

    original_message: str
    enriched_message: str
    context_used: bool
    sources: List[str]
    context_tokens: int


class MAGChatIntegration:
    """
    Integra MAG con el flujo de chat.

    Features:
    - Recuperación automática de contexto relevante
    - Inyección transparente en prompts
    - Tracking de fuentes utilizadas
    - Configuración por sesión/canal
    """

    def __init__(
        self,
        collection: str = "chat_knowledge",
        auto_augment: bool = True,
        min_relevance: float = 0.7,
    ):
        self.mag = get_mag_engine()
        self.augmenter = get_context_augmenter()
        self.collection = collection
        self.auto_augment = auto_augment
        self.min_relevance = min_relevance

        # Configuración por canal
        self._channel_config: Dict[str, Dict] = {}

    def configure_channel(
        self,
        channel_id: str,
        auto_augment: Optional[bool] = None,
        collection: Optional[str] = None,
        min_relevance: Optional[float] = None,
    ):
        """Configura MAG para un canal específico."""
        self._channel_config[channel_id] = {
            "auto_augment": auto_augment
            if auto_augment is not None
            else self.auto_augment,
            "collection": collection or self.collection,
            "min_relevance": min_relevance
            if min_relevance is not None
            else self.min_relevance,
        }

    async def enrich_message(
        self,
        message: str,
        channel_id: str = "default",
        context: Optional[Dict[str, Any]] = None,
    ) -> ChatContext:
        """
        Enriquece un mensaje con contexto recuperado.

        Args:
            message: Mensaje del usuario
            channel_id: ID del canal/sesión
            context: Contexto adicional

        Returns:
            ChatContext enriquecido
        """
        config = self._channel_config.get(
            channel_id,
            {
                "auto_augment": self.auto_augment,
                "collection": self.collection,
                "min_relevance": self.min_relevance,
            },
        )

        if not config["auto_augment"]:
            return ChatContext(
                original_message=message,
                enriched_message=message,
                context_used=False,
                sources=[],
                context_tokens=0,
            )

        try:
            # Recuperar contexto relevante
            augmented = await self.augmenter.augment(
                prompt=message, collection=config["collection"], top_k=5
            )

            return ChatContext(
                original_message=message,
                enriched_message=augmented.augmented_prompt,
                context_used=augmented.context_used,
                sources=augmented.sources,
                context_tokens=augmented.context_tokens,
            )

        except Exception as e:
            logger.error(f"Error enriqueciendo mensaje: {e}")
            # Fallback: retornar mensaje original
            return ChatContext(
                original_message=message,
                enriched_message=message,
                context_used=False,
                sources=[],
                context_tokens=0,
            )

    async def index_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict] = None,
    ):
        """
        Indexa una conversación para búsqueda futura.

        Args:
            conversation_id: ID de la conversación
            messages: Lista de mensajes {"role": "user/assistant", "content": "..."}
            metadata: Metadata adicional
        """
        # Combinar mensajes en un documento
        content_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            content_parts.append(f"[{role.upper()}]: {content}")

        full_content = "\n\n".join(content_parts)

        # Indexar
        await self.mag.index_document(
            content=full_content,
            metadata={
                **(metadata or {}),
                "conversation_id": conversation_id,
                "message_count": len(messages),
            },
            source=f"conversation:{conversation_id}",
            doc_id=conversation_id,
            collection=self.collection,
        )

        logger.debug(f"Conversación {conversation_id} indexada")

    async def get_relevant_history(
        self, query: str, channel_id: str = "default", limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Obtiene conversaciones históricas relevantes.

        Args:
            query: Consulta actual
            channel_id: Canal
            limit: Máximo de resultados

        Returns:
            Lista de conversaciones relevantes
        """
        config = self._channel_config.get(channel_id, {"collection": self.collection})

        retrieval = await self.mag.retrieve(
            query=query,
            collection=config["collection"],
            top_k=limit,
            min_score=self.min_relevance,
        )

        results = []
        for doc_result in retrieval.documents:
            doc = doc_result.document
            results.append(
                {
                    "conversation_id": doc.metadata.get("conversation_id"),
                    "content": doc.content[:500] + "..."
                    if len(doc.content) > 500
                    else doc.content,
                    "relevance": doc_result.score,
                    "source": doc.source,
                }
            )

        return results


# Singleton global
_mag_chat: Optional[MAGChatIntegration] = None


def get_mag_chat_integration() -> MAGChatIntegration:
    """Obtiene instancia singleton de la integración MAG-Chat."""
    global _mag_chat
    if _mag_chat is None:
        _mag_chat = MAGChatIntegration()
    return _mag_chat
