"""
Lilith 3.5 C.1 — DelegationClassifier: decide si una tarea puede ir a Lucifer en lugar de Eva.
Optimiza coste: tareas simples → Lucifer; análisis pesados → Eva.
"""
from typing import Optional

# Palabras que indican que Eva es más adecuada (análisis profundo, auditoría, etc.)
EVA_KEYWORDS = (
    "análisis profundo",
    "analisis profundo",
    "auditoría",
    "auditoria",
    "explicación experta",
    "explicacion experta",
    "documentación exhaustiva",
    "documentacion exhaustiva",
    "arquitectura completa",
    "revisión completa",
    "revision completa",
    "hallazgo",
    "evidencia",
    "recomendacion",
)
# Longitud mínima del texto para considerar "complejo" (más allá de esto preferir Eva si hay ambigüedad)
SIMPLE_THRESHOLD_CHARS = 300


def should_use_lucifer(task: str, context: Optional[str] = None) -> bool:
    """
    True si la tarea puede resolverse con Lucifer en lugar de Eva (evitar coste innecesario).
    Heurística: tareas cortas sin keywords de análisis pesado → Lucifer.
    """
    if not (task or "").strip():
        return True
    text = f"{(task or '').strip()} {(context or '').strip()}".strip().lower()
    for kw in EVA_KEYWORDS:
        if kw in text:
            return False
    # Tarea muy larga → mejor Eva por capacidad
    if len(text) > SIMPLE_THRESHOLD_CHARS:
        return False
    return True
