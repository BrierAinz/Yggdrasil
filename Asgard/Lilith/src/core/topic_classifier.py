"""
Topic Classifier - D.12: Clasificación de contenido por temas/taxonomía.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("lilith.topic_classifier")


class TopicClassifier:
    """
    Clasificador de contenido por temas usando taxonomía definida.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.taxonomy = self._load_taxonomy()
        self.settings = self.taxonomy.get("classification_settings", {})

    def _load_taxonomy(self) -> Dict[str, Any]:
        """Carga taxonomía desde memory_topics.json"""
        taxonomy_path = self.base_path / "Config" / "memory_topics.json"
        try:
            if taxonomy_path.exists():
                return json.loads(taxonomy_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[TopicClassifier] Error loading taxonomy: {e}")

        # Taxonomía por defecto mínima
        return {
            "topics": {
                "codigo": {"keywords": ["code", "function", "class"]},
                "documentacion": {"keywords": ["docs", "README", "guide"]},
            },
            "classification_settings": {
                "min_keyword_matches": 2,
                "score_threshold": 0.3,
            },
        }

    def classify(self, content: str) -> List[str]:
        """
        Clasifica contenido y retorna lista de topics relevantes.

        Args:
            content: Texto a clasificar

        Returns:
            Lista de topic IDs
        """
        content_lower = content.lower()
        topic_scores: Dict[str, float] = {}

        for topic_id, topic_config in self.taxonomy.get("topics", {}).items():
            score = self._score_topic(content_lower, topic_id, topic_config)
            if score > 0:
                topic_scores[topic_id] = score

        # Filtrar por threshold y ordenar por score
        threshold = self.settings.get("score_threshold", 0.3)
        min_matches = self.settings.get("min_keyword_matches", 2)

        # Calcular score máximo para normalizar
        max_score = max(topic_scores.values()) if topic_scores else 1

        results = []
        for topic_id, score in sorted(
            topic_scores.items(), key=lambda x: x[1], reverse=True
        ):
            normalized_score = score / max_score if max_score > 0 else 0

            # Aceptar si pasa threshold o tiene suficientes matches
            if normalized_score >= threshold or score >= min_matches:
                results.append(topic_id)

        if results:
            logger.info(f"[TopicClassifier] Topics detected: {results}")

        return results

    def _score_topic(self, content: str, topic_id: str, topic_config: Dict) -> float:
        """
        Calcula score de coincidencia para un topic.

        Args:
            content: Contenido en minúsculas
            topic_id: ID del topic
            topic_config: Configuración del topic

        Returns:
            Score numérico
        """
        score = 0.0
        keywords = topic_config.get("keywords", [])

        # Coincidencias con keywords principales
        for keyword in keywords:
            if keyword.lower() in content:
                score += 1.0

        # Coincidencias con subtopics (con boost)
        subtopics = topic_config.get("subtopics", {})
        boost = self.settings.get("boost_subtopic_match", 1.5)

        for subtopic_id, subtopic_config in subtopics.items():
            sub_keywords = subtopic_config.get("keywords", [])
            for keyword in sub_keywords:
                if keyword.lower() in content:
                    score += boost

        return score

    def classify_with_confidence(self, content: str) -> List[Dict[str, Any]]:
        """
        Clasifica contenido con scores de confianza.

        Returns:
            Lista de dicts con topic_id, name, confidence
        """
        content_lower = content.lower()
        topic_scores: Dict[str, float] = {}

        for topic_id, topic_config in self.taxonomy.get("topics", {}).items():
            score = self._score_topic(content_lower, topic_id, topic_config)
            if score > 0:
                topic_scores[topic_id] = score

        # Normalizar scores
        max_score = max(topic_scores.values()) if topic_scores else 1

        results = []
        for topic_id, score in sorted(
            topic_scores.items(), key=lambda x: x[1], reverse=True
        ):
            confidence = score / max_score if max_score > 0 else 0
            topic_config = self.taxonomy["topics"].get(topic_id, {})

            results.append(
                {
                    "topic_id": topic_id,
                    "name": topic_config.get("name", topic_id),
                    "confidence": round(confidence, 3),
                    "score": score,
                }
            )

        return results

    def get_topic_info(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un topic.

        Args:
            topic_id: ID del topic

        Returns:
            Config del topic o None
        """
        return self.taxonomy.get("topics", {}).get(topic_id)

    def get_all_topics(self) -> List[str]:
        """Retorna lista de todos los topic IDs."""
        return list(self.taxonomy.get("topics", {}).keys())

    def get_subtopics(self, topic_id: str) -> List[str]:
        """
        Retorna lista de subtopics para un topic.

        Args:
            topic_id: ID del topic padre

        Returns:
            Lista de subtopic IDs
        """
        topic_config = self.taxonomy.get("topics", {}).get(topic_id, {})
        return list(topic_config.get("subtopics", {}).keys())

    def suggest_tags_from_topics(self, topics: List[str]) -> List[str]:
        """
        Sugiere tags basado en topics detectados.

        Args:
            topics: Lista de topic IDs

        Returns:
            Lista de tags sugeridos
        """
        tags = set()

        for topic_id in topics:
            topic_config = self.taxonomy.get("topics", {}).get(topic_id, {})
            # Añadir keywords del topic como tags
            tags.update(topic_config.get("keywords", [])[:5])  # Top 5 keywords

        return list(tags)


# Singleton
classifier_instance: Optional[TopicClassifier] = None


def get_topic_classifier(base_path: Optional[Path] = None) -> TopicClassifier:
    """Obtiene instancia singleton del TopicClassifier"""
    global classifier_instance
    if classifier_instance is None:
        classifier_instance = TopicClassifier(base_path)
    return classifier_instance


def classify_content(content: str, base_path: Optional[Path] = None) -> List[str]:
    """Función conveniencia para clasificar contenido"""
    classifier = get_topic_classifier(base_path)
    return classifier.classify(content)


def classify_with_confidence(
    content: str, base_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Función conveniencia para clasificar con confianza"""
    classifier = get_topic_classifier(base_path)
    return classifier.classify_with_confidence(content)
