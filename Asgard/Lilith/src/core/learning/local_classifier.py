"""
Lilith 3.0 — Clasificador local de intención (Fase 4).
Carga el modelo entrenado (joblib) y predice la tool más probable para un mensaje.
Si no hay modelo o falla la carga, predict() devuelve None y el Planner usa reglas.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("LocalIntentClassifier")


class LocalIntentClassifier:
    """
    Clasificador local (TF-IDF + LogisticRegression) para predecir tool_name desde el mensaje.
    Modelo en memory/episodic/intent_classifier.joblib; si no existe, predict devuelve None.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._model_path = (
            self.base_path / "memory" / "episodic" / "intent_classifier.joblib"
        )
        self._pipeline = None
        self._classes: list = []
        self._load()

    def _load(self) -> None:
        if not self._model_path.exists():
            logger.debug("LocalIntentClassifier: no model at %s", self._model_path)
            return
        try:
            import joblib

            data = joblib.load(self._model_path)
            self._pipeline = data.get("pipeline")
            self._classes = data.get("classes") or []
        except Exception as e:
            logger.warning("LocalIntentClassifier: failed to load model: %s", e)

    def is_available(self) -> bool:
        return self._pipeline is not None and len(self._classes) > 0

    def predict(self, message: str) -> Optional[str]:
        """
        Predice la tool más probable para el mensaje.
        Devuelve None si no hay modelo o el mensaje está vacío.
        """
        if not message or not message.strip():
            return None
        if not self.is_available():
            return None
        try:
            out = self._pipeline.predict([message.strip()])
            return str(out[0]) if out is not None and len(out) else None
        except Exception as e:
            logger.debug("LocalIntentClassifier predict error: %s", e)
            return None
