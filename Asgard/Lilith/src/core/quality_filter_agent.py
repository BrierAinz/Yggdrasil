"""
Lilith 4.2 — QualityFilterAgent: evalúa calidad del texto limpio.

Criterios heurísticos: longitud (muy corto = baja calidad), densidad de información
(proporción de palabras sustantivas vs. stopwords), legibilidad, calidad de fuente.
Clasifica fuentes en alta/media/baja calidad. Salida: QualityScore y decisión de filtrado.
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .agent_registry import Agent
from .tools_v3.protocol import ToolResult
from .web_mining_models import (
    HIGH_QUALITY_SOURCES,
    MEDIUM_QUALITY_SOURCES,
    CleanedContent,
    QualityScore,
    classify_source_quality,
)

logger = logging.getLogger("QualityFilterAgent")

# Stopwords ES/EN para estimar densidad de información (palabras vacías = menor densidad)
_STOPWORDS = frozenset(
    "a al algo alguna alguno de del en es esa ese eso esta este la las lo los me mi no "
    "por para que se si su sus te tu un una uno y el él ella ellos ellas nosotros "
    "the and to of in is it for on with as by at be this are from or was were been "
    "have has had do does did will would could should may might must can "
    "that which who what when where how why all each every both few more most "
    "other some such no nor not only own same so than too very just "
    "also ahora aquí así aunque bien pero como con cual cuando donde después "
    "durante entonces hasta mientras mucho muy nada nunca o porque pero pues "
    "sino sobre tanto todo tras otra otro".split()
)


def _load_config(base_path: Optional[Path]) -> Dict[str, Any]:
    """Carga Config/quality_filter.json."""
    if not base_path or not base_path.exists():
        return {}
    try:
        from .json_safe import safe_load

        path = base_path / "Config" / "quality_filter.json"
        if not path.exists():
            return {}
        data = safe_load(path, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _word_count(text: str) -> int:
    """Número de palabras (tokens separados por espacios)."""
    return len(text.split()) if text else 0


def _sentence_count(text: str) -> int:
    """Número aproximado de oraciones."""
    if not text:
        return 0
    # Contar finales de oración
    sentences = re.split(r"[.!?]+", text)
    return len([s for s in sentences if s.strip()])


def _syllable_count(word: str) -> int:
    """Cuenta sílabas aproximadas en una palabra (inglés)."""
    word = word.lower()
    count = 0
    vowels = "aeiouy"
    prev_was_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel

    # Ajustes comunes
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    if count == 0:
        count = 1

    return count


def _flesch_reading_ease(text: str) -> float:
    """
    Calcula Flesch Reading Ease (inglés).
    90-100: Muy fácil
    60-70: Estándar
    0-30: Muy difícil
    """
    words = _word_count(text)
    sentences = _sentence_count(text)

    if words == 0 or sentences == 0:
        return 0.0

    syllables = sum(_syllable_count(w) for w in text.split())

    # Fórmula Flesch
    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    return max(0.0, min(100.0, score))


def _information_density(text: str) -> float:
    """Ratio de palabras no stopword sobre total. Mayor = más densidad."""
    words = text.lower().split()
    if not words:
        return 0.0
    meaningful = sum(1 for w in words if re.sub(r"\W", "", w) and w not in _STOPWORDS)
    return meaningful / len(words)


def _length_score(
    text: str, min_length: int, ideal_min: int, ideal_max: int = 50_000
) -> float:
    """Score 0-1 por longitud: muy corto = 0, ideal = 1, muy largo = decrece."""
    n = len(text.strip())
    if n < min_length:
        return 0.0
    if n < ideal_min:
        # Lineal entre min_length e ideal_min
        return (n - min_length) / max(1, ideal_min - min_length)
    if n <= ideal_max:
        return 1.0
    # Penalizar contenido excesivamente largo
    return max(0.5, 1.0 - (n - ideal_max) / 100_000)


def _source_quality_score(url: str) -> float:
    """Score basado en la calidad de la fuente."""
    quality = classify_source_quality(url)
    scores = {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.3,
        "unknown": 0.5,
    }
    return scores.get(quality, 0.5)


def _is_recent(published_date: Optional[str]) -> bool:
    """Verifica si la fecha de publicación es reciente (< 1 año)."""
    if not published_date:
        return False

    try:
        from datetime import datetime, timedelta

        # Intentar parsear varios formatos
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]

        parsed = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(published_date[:19], fmt)
                break
            except ValueError:
                continue

        if not parsed:
            return False

        # Considerar reciente si es menos de 1 año
        one_year_ago = datetime.now() - timedelta(days=365)
        return parsed > one_year_ago
    except Exception:
        return False


# Patrones para bypass determinista: contenido técnico (código/logs) no penalizado por stopwords
_BYPASS_MARKDOWN_CODE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_BYPASS_ISO_TIMESTAMP = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", re.MULTILINE
)
_BYPASS_LOG_LEVEL = re.compile(
    r"\[(?:INFO|DEBUG|ERROR|WARN|WARNING|TRACE|CRITICAL)\]",
    re.IGNORECASE,
)
_BYPASS_ISO_IN_LINE = re.compile(
    r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)


def _bypass_deterministic(text: str, config: Dict[str, Any]) -> Optional[str]:
    """
    Si el texto parece código o logs, devuelve una etiqueta de bypass (no None).
    Así se asigna quality_score=1.0 sin calcular densidad por stopwords.
    """
    if not text or not config.get("bypass_deterministic", False):
        return None
    reasons = []
    if config.get("bypass_markdown_code", True) and _BYPASS_MARKDOWN_CODE.search(text):
        reasons.append("código Markdown")
    if config.get("bypass_log_patterns", True):
        if _BYPASS_ISO_TIMESTAMP.search(text) or _BYPASS_ISO_IN_LINE.search(text):
            reasons.append("timestamp ISO")
        if _BYPASS_LOG_LEVEL.search(text):
            reasons.append("nivel de log")
    if not reasons:
        return None
    return "código/log detectado (" + ", ".join(reasons) + ")"


def _compute_quality_score(
    text: str,
    url: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    min_length: int = 100,
    ideal_min_length: int = 500,
    ideal_max_length: int = 50_000,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calcula quality_score (0.0 - 1.0) y métricas auxiliares.
    Combina score de longitud, densidad de información, legibilidad y fuente.
    """
    metadata = metadata or {}
    words = _word_count(text)
    sentences = _sentence_count(text)

    # Score de longitud
    length_s = _length_score(text, min_length, ideal_min_length, ideal_max_length)

    # Densidad de información
    density = _information_density(text)

    # Legibilidad (solo si es suficientemente largo)
    readability = 0.5
    if words > 50:
        flesch = _flesch_reading_ease(text)
        # Normalizar: 60-70 es estándar, más alto es más fácil
        readability = min(1.0, max(0.0, flesch / 100))

    # Calidad de fuente
    source_quality = _source_quality_score(url)

    # Recencia (bonus)
    recency_bonus = 0.0
    pub_date = metadata.get("published_date") or metadata.get("date")
    if _is_recent(pub_date):
        recency_bonus = 0.05

    # Ponderación ajustable
    # Longitud: 30%, Densidad: 35%, Legibilidad: 15%, Fuente: 20%
    score = (
        0.30 * length_s
        + 0.35 * density
        + 0.15 * readability
        + 0.20 * source_quality
        + recency_bonus
    )

    score = max(0.0, min(1.0, score))

    details = {
        "word_count": words,
        "sentence_count": sentences,
        "length_score": round(length_s, 3),
        "density": round(density, 3),
        "readability": round(readability, 3),
        "source_quality": round(source_quality, 3),
        "recency_bonus": round(recency_bonus, 3),
    }

    return score, details


class QualityFilterAgent(Agent):
    """
    Agente que evalúa la calidad del texto limpio y lo acepta o descarta según umbral.
    Recibe texto en params['context'] o params['text']; devuelve el texto con quality_score
    o un mensaje de filtrado si no supera min_score.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = Path(base_path) if base_path else None
        self._config = _load_config(self._base_path)
        self._rejected_log: List[Dict[str, Any]] = []

    @property
    def agent_id(self) -> str:
        return "quality_filter"

    @property
    def tool_name(self) -> str:
        return "delegate_quality_filter"

    @property
    def description(self) -> str:
        return "Evalúa calidad del texto (longitud, densidad, legibilidad, fuente) y descarta contenido bajo umbral."

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecución síncrona compatible con AgentRegistry."""
        try:
            # Si viene CleanedContent
            cleaned = params.get("cleaned_content")
            if cleaned and isinstance(cleaned, CleanedContent):
                quality = self.assess_quality(cleaned)
            else:
                raw = (params.get("context") or params.get("text") or "").strip()
                url = params.get("url", "")
                if not raw:
                    return {
                        "response": "No hay texto que evaluar (pasa 'context' o 'text').",
                        "error": True,
                    }

                # Crear CleanedContent temporal
                temp_cleaned = CleanedContent(
                    url=url,
                    cleaned_text=raw,
                    cleaned_length=len(raw),
                )
                quality = self.assess_quality(temp_cleaned)

            if not quality.is_accepted:
                self._log_rejection(
                    cleaned.url if cleaned else params.get("url", ""), quality
                )
                return {
                    "response": (
                        f"Contenido filtrado por baja calidad (score {quality.score:.2f}, "
                        f"umbral {self._config.get('quality_threshold', 0.6)}). "
                        f"Razones: {', '.join(quality.reasons)}"
                    ),
                    "quality_score": quality,
                    "filtered_out": True,
                    "error": False,
                }

            reason_str = f" ({', '.join(quality.reasons)})" if quality.reasons else ""
            logger.info(
                "[QualityFilter] Accepted: score %.2f%s", quality.score, reason_str
            )

            return {
                "response": f"[Calidad validada: {quality.score:.2f}]{reason_str}",
                "quality_score": quality,
                "filtered_out": False,
                "error": False,
            }

        except Exception as e:
            logger.warning("QualityFilterAgent: %s", e)
            return {"response": str(e), "error": True}

    def assess_quality(self, content: CleanedContent) -> QualityScore:
        """
        Evalúa la calidad del contenido limpio.

        Args:
            content: Contenido a evaluar

        Returns:
            QualityScore con score y decisión
        """
        min_length = max(50, int(self._config.get("min_length", 100)))
        ideal_min = max(
            min_length + 100, int(self._config.get("ideal_min_length", 500))
        )
        ideal_max = int(self._config.get("ideal_max_length", 50_000))
        min_score = max(
            0.0, min(1.0, float(self._config.get("quality_threshold", 0.6)))
        )

        # Verificar bypass determinista
        bypass_label = _bypass_deterministic(content.cleaned_text, self._config)
        if bypass_label is not None:
            return QualityScore(
                score=1.0,
                reasons=[f"bypass: {bypass_label}"],
                details={"bypass": bypass_label},
                is_accepted=True,
            )

        # Calcular score
        score, details = _compute_quality_score(
            content.cleaned_text,
            url=content.url,
            metadata=content.metadata,
            min_length=min_length,
            ideal_min_length=ideal_min,
            ideal_max_length=ideal_max,
        )

        # Determinar razones
        reasons = []
        if details["length_score"] < 0.5:
            reasons.append("too_short")
        if details["density"] < 0.3:
            reasons.append("low_information_density")
        if details["readability"] < 0.3:
            reasons.append("low_readability")
        if details["source_quality"] < 0.5:
            reasons.append(f"source_quality_{classify_source_quality(content.url)}")

        # Score de fuente alta da bonus
        if details["source_quality"] >= 0.8:
            reasons.append("high_quality_source")

        # Verificar recencia
        pub_date = content.metadata.get("published_date") or content.metadata.get(
            "date"
        )
        if _is_recent(pub_date):
            reasons.append("recent_content")

        is_accepted = score >= min_score

        return QualityScore(
            score=score,
            reasons=reasons,
            details=details,
            is_accepted=is_accepted,
        )

    def should_keep(self, quality_score: QualityScore) -> bool:
        """Determina si el contenido debe mantenerse basado en su score."""
        return quality_score.is_accepted

    def _log_rejection(self, url: str, quality: QualityScore) -> None:
        """Loguea un rechazo para análisis posterior."""
        entry = {
            "url": url,
            "score": quality.score,
            "reasons": quality.reasons,
            "details": quality.details,
        }
        self._rejected_log.append(entry)

        # Guardar en archivo si hay muchos rechazos
        if len(self._rejected_log) >= 10:
            self._flush_rejected_log()

        logger.info(
            "[QualityFilter] Rejected: %s (score %.2f < %.2f)",
            url,
            quality.score,
            self._config.get("quality_threshold", 0.6),
        )

    def _flush_rejected_log(self) -> None:
        """Escribe los rechazos acumulados a archivo."""
        if not self._base_path or not self._rejected_log:
            return

        try:
            import json
            from datetime import datetime

            log_path = self._base_path / "Data" / "rejected_content.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(log_path, "a", encoding="utf-8") as f:
                for entry in self._rejected_log:
                    entry["timestamp"] = datetime.now().isoformat()
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            self._rejected_log.clear()
        except Exception as e:
            logger.warning("Error flushing rejected log: %s", e)

    def get_source_classification(self, url: str) -> Dict[str, Any]:
        """
        Retorna la clasificación completa de una fuente.

        Returns:
            Dict con quality_level, score, y fuentes de referencia
        """
        quality = classify_source_quality(url)
        score = _source_quality_score(url)

        return {
            "url": url,
            "quality_level": quality,
            "score": score,
            "is_high_quality": quality == "high",
            "reference_sources": {
                "high": list(HIGH_QUALITY_SOURCES)[:10],
                "medium": list(MEDIUM_QUALITY_SOURCES)[:10],
            },
        }
