"""
Crystal Learning - Sistema de aprendizaje de FAQs

Módulo para Crystal que detecta preguntas frecuentes y almacena
respuestas para respuesta rápida sin llamar a la API.

Uso:
    from core.agents.crystal_learning import CrystalLearning

    learning = CrystalLearning()

    # Antes de procesar con LLM
    cached = await learning.find_similar_faq(message)
    if cached:
        return cached["response"]

    # Después de obtener respuesta del LLM
    await learning.learn_from_interaction(message, response)
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FAQEntry:
    """Entrada de FAQ aprendida."""

    question_hash: str
    question_normalized: str
    response: str
    question_variants: List[str]
    hit_count: int
    first_seen: datetime
    last_used: datetime
    confidence_score: float
    source_backend: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_hash": self.question_hash,
            "question_normalized": self.question_normalized,
            "response": self.response,
            "question_variants": self.question_variants,
            "hit_count": self.hit_count,
            "first_seen": self.first_seen.isoformat(),
            "last_used": self.last_used.isoformat(),
            "confidence_score": self.confidence_score,
            "source_backend": self.source_backend,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FAQEntry":
        return cls(
            question_hash=data["question_hash"],
            question_normalized=data["question_normalized"],
            response=data["response"],
            question_variants=data.get("question_variants", []),
            hit_count=data.get("hit_count", 1),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            confidence_score=data.get("confidence_score", 0.5),
            source_backend=data.get("source_backend", "unknown"),
        )


class CrystalLearning:
    """
    Sistema de aprendizaje de FAQs para Crystal.

    Características:
    - Detección de preguntas similares usando similitud de texto
    - Almacenamiento persistente en MuninnDB (automático)
    - TTL automático para FAQs antiguas
    - Estadísticas de uso
    - Carga inicial desde persistencia
    """

    def __init__(
        self,
        min_hits_to_learn: int = 2,
        similarity_threshold: float = 0.85,
        max_faqs: int = 100,
        ttl_days: int = 30,
        auto_persist: bool = True,
        persist_on_update: bool = True,
    ):
        """
        Args:
            min_hits_to_learn: Mínimo de veces que debe preguntarse para aprender
            similarity_threshold: Umbral de similitud (0-1) para considerar match
            max_faqs: Máximo de FAQs a mantener en caché
            ttl_days: Días antes de expirar una FAQ
            auto_persist: Guardar automáticamente en MuninnDB al aprender
            persist_on_update: Actualizar en MuninnDB cuando cambia una FAQ
        """
        self.min_hits_to_learn = min_hits_to_learn
        self.similarity_threshold = similarity_threshold
        self.max_faqs = max_faqs
        self.ttl_days = ttl_days
        self.auto_persist = auto_persist
        self.persist_on_update = persist_on_update

        # Caché en memoria
        self._cache: Dict[str, FAQEntry] = {}
        self._pending_interactions: Dict[str, Dict[str, Any]] = {}

        # Contador de accesos recientes (para detectar frecuencia)
        self._recent_queries: Dict[str, List[datetime]] = {}

        # Flag de inicialización
        self._initialized = False
        self._muninn_available = False

        # Inicializar (cargar desde persistencia)
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        """Inicializar el sistema cargando FAQs desde persistencia."""
        if self._initialized:
            return

        try:
            # Verificar si Muninn está disponible
            from src.core.memory.muninn_memory import MuninnMemory

            self._muninn_available = True

            # Cargar FAQs existentes
            loaded = await self.load_from_muninn(limit=self.max_faqs)
            logger.info(
                "Crystal Learning: Initialized with %d FAQs from storage", loaded
            )

        except ImportError:
            logger.warning(
                "Crystal Learning: MuninnMemory not available, running without persistence"
            )
            self._muninn_available = False
        except Exception as e:
            logger.error("Crystal Learning: Failed to initialize: %s", e)
            self._muninn_available = False

        self._initialized = True

    async def _persist_faq(self, entry: FAQEntry, update: bool = False) -> bool:
        """
        Guardar o actualizar FAQ en MuninnDB.

        Args:
            entry: FAQEntry a persistir
            update: Si es True, actualiza entrada existente

        Returns:
            True si se guardó correctamente
        """
        if not self._muninn_available or not self.auto_persist:
            return False

        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()
            content = json.dumps(entry.to_dict(), ensure_ascii=False)

            if update:
                # Buscar y actualizar entrada existente
                events = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: muninn.search(
                        query=f"crystal_faq {entry.question_hash}",
                        vault="crystal",
                        limit=1,
                    ),
                )

                if events:
                    # Actualizar evento existente
                    event_id = events[0].get("id")
                    if event_id:
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: muninn.update_event(
                                event_id=event_id,
                                content=content,
                                metadata={
                                    "question_hash": entry.question_hash,
                                    "hit_count": entry.hit_count,
                                    "confidence": entry.confidence_score,
                                    "last_used": entry.last_used.isoformat(),
                                },
                            ),
                        )
                        logger.debug(
                            "Crystal Learning: Updated FAQ in MuninnDB: %s",
                            entry.question_hash,
                        )
                        return True

            # Crear nuevo evento
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: muninn.add_event(
                    content=content,
                    event_type="crystal_faq",
                    tags=["crystal", "faq", "learned"],
                    metadata={
                        "question_hash": entry.question_hash,
                        "hit_count": entry.hit_count,
                        "confidence": entry.confidence_score,
                    },
                ),
            )

            logger.debug(
                "Crystal Learning: Saved FAQ to MuninnDB: %s", entry.question_hash
            )
            return True

        except Exception as e:
            logger.warning("Crystal Learning: Failed to persist FAQ: %s", e)
            return False

    def _normalize_question(self, question: str) -> str:
        """
        Normalizar pregunta para comparación.
        Elimina puntuación, convierte a minúsculas, ordena palabras.
        """
        # Convertir a minúsculas y eliminar puntuación básica
        normalized = question.lower().strip()
        for char in "¿?!¡.,;:":
            normalized = normalized.replace(char, "")

        # Ordenar palabras alfabéticamente para mejor matching
        words = sorted(normalized.split())
        return " ".join(words)

    def _compute_hash(self, normalized: str) -> str:
        """Computar hash de pregunta normalizada."""
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Computar similitud entre dos textos usando coeficiente de Jaccard.
        Retorna valor entre 0 y 1.
        """
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _is_question(self, text: str) -> bool:
        """Detectar si el texto es una pregunta."""
        text_lower = text.lower().strip()

        # Palabras interrogativas
        question_words = [
            "qué",
            "que",
            "cómo",
            "como",
            "cuál",
            "cual",
            "quién",
            "quien",
            "dónde",
            "donde",
            "cuándo",
            "cuando",
            "por qué",
            "porque",
            "cuántos",
            "cuantos",
            "cuántas",
            "cuantas",
        ]

        # Verificar palabras interrogativas
        for word in question_words:
            if text_lower.startswith(word):
                return True

        # Verificar signo de interrogación
        if text_lower.startswith("¿") or text_lower.endswith("?"):
            return True

        # Patrones comunes de pregunta
        patterns = [
            "puedes",
            "podrías",
            "podrias",
            "sabes",
            "conoces",
            "explícame",
            "explicame",
            "dime",
            "cuéntame",
            "cuentame",
            "ayúdame",
            "ayudame",
            "necesito saber",
            "quiero saber",
        ]

        for pattern in patterns:
            if text_lower.startswith(pattern):
                return True

        return False

    def _should_cache_response(self, response: str) -> bool:
        """
        Determinar si una respuesta debería ser cacheada.
        Evita cachear respuestas de error, muy cortas, o dinámicas.
        """
        # No cachear respuestas de error
        error_indicators = [
            "error",
            "falló",
            "fallo",
            "no puedo",
            "disculpa",
            "tengo dificultades",
            "intentar de nuevo",
        ]

        response_lower = response.lower()
        for indicator in error_indicators:
            if indicator in response_lower:
                return False

        # No cachear respuestas muy cortas o muy largas
        if len(response) < 50 or len(response) > 4000:
            return False

        return True

    async def find_similar_faq(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Buscar FAQ similar en caché.

        Args:
            question: Pregunta del usuario

        Returns:
            Dict con response y metadata si encuentra match, None si no
        """
        if not self._is_question(question):
            return None

        normalized = self._normalize_question(question)

        # Buscar en caché con similitud
        best_match: Optional[FAQEntry] = None
        best_score = 0.0

        for entry in self._cache.values():
            score = self._compute_similarity(normalized, entry.question_normalized)

            # También comparar con variantes
            for variant in entry.question_variants:
                variant_normalized = self._normalize_question(variant)
                score = max(
                    score, self._compute_similarity(normalized, variant_normalized)
                )

            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = entry

        if best_match:
            # Actualizar estadísticas
            best_match.hit_count += 1
            best_match.last_used = datetime.now()

            # Agregar variante si es diferente
            if normalized != best_match.question_normalized:
                if question not in best_match.question_variants:
                    best_match.question_variants.append(question)
                    # Limitar variantes
                    best_match.question_variants = best_match.question_variants[-5:]

            # Persistir actualización si está habilitado
            if self.persist_on_update and best_match.hit_count % 5 == 0:  # Cada 5 hits
                asyncio.create_task(self._persist_faq(best_match, update=True))

            logger.info(
                "Crystal Learning: FAQ hit (score=%.2f, hits=%d): %s...",
                best_score,
                best_match.hit_count,
                question[:50],
            )

            return {
                "found": True,
                "response": best_match.response,
                "confidence": best_score,
                "hit_count": best_match.hit_count,
                "source": best_match.source_backend,
                "cached": True,
            }

        return None

    async def learn_from_interaction(
        self, question: str, response: str, backend: str = "unknown"
    ) -> bool:
        """
        Aprender de una interacción usuario-asistente.

        Args:
            question: Pregunta del usuario
            response: Respuesta del asistente
            backend: Backend que generó la respuesta

        Returns:
            True si se aprendió/almacenó, False si no
        """
        # Verificar si es pregunta y respuesta cacheable
        if not self._is_question(question):
            return False

        if not self._should_cache_response(response):
            return False

        normalized = self._normalize_question(question)
        question_hash = self._compute_hash(normalized)

        now = datetime.now()

        # Verificar si ya existe
        if question_hash in self._cache:
            entry = self._cache[question_hash]
            entry.hit_count += 1
            entry.last_used = now

            # Si se ha usado mucho, aumentar confianza
            if entry.hit_count >= self.min_hits_to_learn:
                entry.confidence_score = min(0.95, 0.7 + (entry.hit_count * 0.02))

            logger.debug("Crystal Learning: Updated existing FAQ: %s", question[:50])
            return True

        # Registrar interacción pendiente
        if question_hash not in self._pending_interactions:
            self._pending_interactions[question_hash] = {
                "question": question,
                "normalized": normalized,
                "response": response,
                "count": 1,
                "backend": backend,
                "first_seen": now,
            }
        else:
            self._pending_interactions[question_hash]["count"] += 1

        # Verificar si alcanzó umbral para aprender
        pending = self._pending_interactions[question_hash]
        if pending["count"] >= self.min_hits_to_learn:
            # Crear entrada permanente
            entry = FAQEntry(
                question_hash=question_hash,
                question_normalized=normalized,
                response=response,
                question_variants=[question],
                hit_count=pending["count"],
                first_seen=pending["first_seen"],
                last_used=now,
                confidence_score=0.7 + (pending["count"] * 0.02),
                source_backend=backend,
            )

            self._cache[question_hash] = entry
            del self._pending_interactions[question_hash]

            # Guardar en MuninnDB usando persistencia robusta
            await self._persist_faq(entry, update=False)

            logger.info(
                "Crystal Learning: New FAQ learned (hits=%d): %s...",
                entry.hit_count,
                question[:50],
            )

            return True

        return False

    async def _save_to_muninn(self, entry: FAQEntry) -> None:
        """Guardar entrada FAQ en MuninnDB para persistencia."""
        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()

            # Guardar como evento de memoria
            content = json.dumps(entry.to_dict(), ensure_ascii=False)

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: muninn.add_event(
                    content=content,
                    event_type="crystal_faq",
                    tags=["crystal", "faq", "learned"],
                    metadata={
                        "question_hash": entry.question_hash,
                        "hit_count": entry.hit_count,
                        "confidence": entry.confidence_score,
                    },
                ),
            )

        except Exception as e:
            logger.warning("Crystal Learning: Failed to save to Muninn: %s", e)

    async def load_from_muninn(self, limit: int = 100) -> int:
        """
        Cargar FAQs aprendidas desde MuninnDB.

        Args:
            limit: Máximo de FAQs a cargar

        Returns:
            Número de FAQs cargadas
        """
        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()

            # Buscar eventos de tipo crystal_faq
            events = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: muninn.search(
                    query="crystal_faq learned", vault="crystal", limit=limit
                ),
            )

            loaded = 0
            for event in events:
                try:
                    data = json.loads(event.get("content", "{}"))
                    entry = FAQEntry.from_dict(data)

                    # Verificar TTL
                    age = datetime.now() - entry.last_used
                    if age.days > self.ttl_days:
                        continue

                    self._cache[entry.question_hash] = entry
                    loaded += 1

                except Exception as e:
                    logger.debug("Crystal Learning: Failed to load FAQ entry: %s", e)
                    continue

            logger.info("Crystal Learning: Loaded %d FAQs from Muninn", loaded)
            return loaded

        except Exception as e:
            logger.warning("Crystal Learning: Failed to load from Muninn: %s", e)
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema de aprendizaje."""
        if not self._cache:
            return {
                "total_faqs": 0,
                "pending_interactions": len(self._pending_interactions),
                "average_hits": 0,
                "average_confidence": 0,
            }

        total_hits = sum(e.hit_count for e in self._cache.values())
        total_confidence = sum(e.confidence_score for e in self._cache.values())

        return {
            "total_faqs": len(self._cache),
            "pending_interactions": len(self._pending_interactions),
            "average_hits": total_hits / len(self._cache),
            "average_confidence": total_confidence / len(self._cache),
            "most_used": max(
                self._cache.values(), key=lambda e: e.hit_count
            ).question_normalized[:50]
            if self._cache
            else None,
        }

    async def cleanup_expired(self) -> int:
        """
        Limpiar FAQs expiradas.

        Returns:
            Número de entradas eliminadas
        """
        now = datetime.now()
        expired = []

        for hash_key, entry in self._cache.items():
            age = now - entry.last_used
            if age.days > self.ttl_days:
                expired.append(hash_key)

        for hash_key in expired:
            del self._cache[hash_key]

        if expired:
            logger.info("Crystal Learning: Cleaned up %d expired FAQs", len(expired))

        return len(expired)

    def clear_cache(self) -> None:
        """Limpiar caché en memoria."""
        self._cache.clear()
        self._pending_interactions.clear()
        logger.info("Crystal Learning: Cache cleared")
