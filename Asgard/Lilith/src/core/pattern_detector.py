"""
Lilith v5.2 — PatternDetector
=============================

Detecta patrones en secuencias de operaciones PC.

Algoritmos implementados:
- Longest Common Subsequence (LCS) para similitud de secuencias
- Edit Distance (Levenshtein) para comparación de strings
- N-gram analysis para patrones temporales
- Clustering por similitud usando threshold
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.macro.pattern_detector")


@dataclass
class Operation:
    """Representa una operación PC."""

    operation: str  # 'mkdir', 'copy', 'move', 'delete', 'exec'
    params: Dict[str, Any]
    timestamp: float = 0.0

    def signature(self) -> str:
        """Genera firma única de la operación (sin valores específicos)."""
        # Normalizar params para firma (solo keys y tipos de valores)
        param_sig = "|".join(sorted(self.params.keys()))
        return f"{self.operation}({param_sig})"

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "operation": self.operation,
            "params": self.params.copy(),
            "timestamp": self.timestamp,
        }


@dataclass
class Pattern:
    """Patrón detectado en secuencias de operaciones."""

    operations: List[Operation]
    count: int
    confidence: float
    last_timestamp: float
    source_sequences: List[
        List[Operation]
    ]  # Secuencias originales que forman este patrón

    def get_template(self) -> List[Dict[str, Any]]:
        """Genera template de macro desde el patrón."""
        template = []
        for op in self.operations:
            template.append(
                {
                    "operation": op.operation,
                    "params": op.params,
                }
            )
        return template

    def estimate_params(self) -> Dict[str, Dict[str, Any]]:
        """Estima parámetros variables del patrón."""
        if not self.source_sequences or len(self.source_sequences) < 2:
            return {}

        params = {}
        # Comparar valores entre secuencias para detectar variaciones
        for i, op in enumerate(self.operations):
            for key, value in op.params.items():
                values_across_sequences = [
                    seq[i].params.get(key) if i < len(seq) else None
                    for seq in self.source_sequences
                ]

                # Si hay variación, es un parámetro candidato
                unique_values = set(
                    str(v) for v in values_across_sequences if v is not None
                )
                if len(unique_values) > 1:
                    param_key = f"{op.operation}_{i}_{key}"
                    params[param_key] = {
                        "type": "string" if isinstance(value, str) else "path",
                        "required": True,
                        "description": f"Parámetro {key} para operación {op.operation}",
                    }

        return params


class PatternDetector:
    """
    Detecta patrones repetidos en secuencias de operaciones.

    Usa LCS (Longest Common Subsequence) para encontrar similitudes
    entre secuencias y agruparlas en patrones.
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """
        Inicializa el detector.

        Args:
            similarity_threshold: Umbral de similitud (0-1) para considerar
                                 dos secuencias como del mismo patrón
        """
        self.similarity_threshold = similarity_threshold

    def find_patterns(
        self,
        sequences: List[List[Operation]],
        min_frequency: int = 3,
    ) -> List[Pattern]:
        """
        Encuentra patrones repetidos en las secuencias.

        Args:
            sequences: Lista de secuencias de operaciones
            min_frequency: Mínimo de ocurrencias para considerar un patrón

        Returns:
            Lista de patrones detectados ordenados por confianza
        """
        if not sequences:
            return []

        logger.info("[PatternDetector] Analizando %d secuencias", len(sequences))

        # Agrupar secuencias similares
        clusters = self._cluster_by_similarity(sequences)
        logger.debug("[PatternDetector] Formados %d clusters", len(clusters))

        patterns = []
        for cluster in clusters:
            if len(cluster) >= min_frequency:
                common_pattern = self._extract_common_pattern(cluster)
                if common_pattern:
                    confidence = self._calculate_confidence(cluster, common_pattern)

                    patterns.append(
                        Pattern(
                            operations=common_pattern,
                            count=len(cluster),
                            confidence=confidence,
                            last_timestamp=max(
                                seq[-1].timestamp for seq in cluster if seq
                            ),
                            source_sequences=cluster,
                        )
                    )

        # Ordenar por confianza descendente
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        logger.info("[PatternDetector] Detectados %d patrones", len(patterns))
        return patterns

    def _cluster_by_similarity(
        self,
        sequences: List[List[Operation]],
    ) -> List[List[List[Operation]]]:
        """
        Agrupa secuencias por similitud usando clustering jerárquico simple.

        Args:
            sequences: Lista de secuencias

        Returns:
            Lista de clusters (cada cluster es lista de secuencias)
        """
        n = len(sequences)
        if n == 0:
            return []

        # Calcular matriz de similitud
        similarity_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    sim = self._sequence_similarity(sequences[i], sequences[j])
                    similarity_matrix[i][j] = sim
                    similarity_matrix[j][i] = sim

        # Clustering: unir secuencias con similitud >= threshold
        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            cluster = [sequences[i]]
            visited[i] = True

            for j in range(i + 1, n):
                if (
                    not visited[j]
                    and similarity_matrix[i][j] >= self.similarity_threshold
                ):
                    cluster.append(sequences[j])
                    visited[j] = True

            clusters.append(cluster)

        return clusters

    def _sequence_similarity(
        self,
        seq1: List[Operation],
        seq2: List[Operation],
    ) -> float:
        """
        Calcula similitud entre dos secuencias usando LCS.

        Returns:
            Coeficiente de similitud (0-1)
        """
        if not seq1 and not seq2:
            return 1.0
        if not seq1 or not seq2:
            return 0.0

        # Convertir a firmas para comparación
        sig1 = [op.signature() for op in seq1]
        sig2 = [op.signature() for op in seq2]

        # Calcular LCS
        lcs_length = self._lcs_length(sig1, sig2)
        max_len = max(len(sig1), len(sig2))

        return lcs_length / max_len if max_len > 0 else 0.0

    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """
        Calcula longitud de Longest Common Subsequence usando DP.

        Complejidad: O(n*m)
        """
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]

    def _extract_common_pattern(
        self,
        cluster: List[List[Operation]],
    ) -> Optional[List[Operation]]:
        """
        Extrae el patrón común de un cluster de secuencias.

        Usa la mediana de las secuencias como representante.
        """
        if not cluster:
            return None

        # Encontrar secuencia mediana (la más similar a todas las demás)
        best_seq = None
        best_score = -1

        for seq in cluster:
            score = sum(self._sequence_similarity(seq, other) for other in cluster)
            if score > best_score:
                best_score = score
                best_seq = seq

        return best_seq

    def _calculate_confidence(
        self,
        cluster: List[List[Operation]],
        pattern: List[Operation],
    ) -> float:
        """
        Calcula confianza del patrón basado en:
        - Frecuencia (más ocurrencias = más confianza)
        - Cohesión (qué tan similares son las secuencias del cluster)
        """
        # Factor de frecuencia (logarítmico para no penalizar demasiado)
        frequency_factor = min(1.0, 0.3 + 0.7 * (len(cluster) / 10))

        # Factor de cohesión (similitud promedio dentro del cluster)
        if len(cluster) <= 1:
            cohesion = 1.0
        else:
            similarities = []
            for i, seq1 in enumerate(cluster):
                for seq2 in cluster[i + 1 :]:
                    similarities.append(self._sequence_similarity(seq1, seq2))
            cohesion = sum(similarities) / len(similarities) if similarities else 0.0

        # Ponderación: 40% frecuencia, 60% cohesión
        confidence = 0.4 * frequency_factor + 0.6 * cohesion

        return round(confidence, 3)

    def analyze_ngrams(
        self,
        sequences: List[List[Operation]],
        n: int = 2,
        min_frequency: int = 3,
    ) -> List[Tuple[List[str], int]]:
        """
        Análisis de n-grams para detectar sub-secuencias comunes.

        Args:
            sequences: Lista de secuencias
            n: Tamaño del n-gram
            min_frequency: Frecuencia mínima

        Returns:
            Lista de (n-gram, frecuencia) ordenada por frecuencia
        """
        ngram_counts: Dict[tuple, int] = {}

        for seq in sequences:
            sigs = tuple(op.signature() for op in seq)
            for i in range(len(sigs) - n + 1):
                ngram = sigs[i : i + n]
                ngram_counts[ngram] = ngram_counts.get(ngram, 0) + 1

        # Filtrar por frecuencia mínima y ordenar
        frequent_ngrams = [
            (list(ngram), count)
            for ngram, count in ngram_counts.items()
            if count >= min_frequency
        ]
        frequent_ngrams.sort(key=lambda x: x[1], reverse=True)

        return frequent_ngrams


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcula distancia de Levenshtein entre dos strings.

    Útil para comparar nombres de archivos/rutas.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def string_similarity(s1: str, s2: str) -> float:
    """
    Calcula similitud entre strings (0-1) usando SequenceMatcher.
    """
    return SequenceMatcher(None, s1, s2).ratio()
