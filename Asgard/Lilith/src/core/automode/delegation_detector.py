"""
DelegationDetector: Analiza tareas y recomienda delegación a especialistas.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class TaskComplexity(Enum):
    """Niveles de complejidad de tareas."""

    TRIVIAL = 1  # 1 paso, <5 min
    SIMPLE = 2  # 2-3 pasos, <15 min
    MODERATE = 3  # 4-6 pasos, <1h
    COMPLEX = 4  # 7-10 pasos, <4h
    EXPERT = 5  # 10+ pasos, >4h


@dataclass
class DelegationRecommendation:
    """Recomendación de delegación para una tarea."""

    should_delegate: bool
    recommended_agent: Optional[str]
    complexity: TaskComplexity
    reasoning: str
    confidence: float


class DelegationDetector:
    """
    Detector de complejidad y recomendador de delegación.

    Analiza descripciones de tareas y decide:
    - Si debe delegarse a un agente especialista
    - Qué agente es el más adecuado
    - Nivel de complejidad estimado
    """

    # Keywords que indican complejidad
    COMPLEXITY_KEYWORDS = {
        "refactor": TaskComplexity.COMPLEX,
        "refactorizar": TaskComplexity.COMPLEX,
        "arquitectura": TaskComplexity.EXPERT,
        "architecture": TaskComplexity.EXPERT,
        "diseñar": TaskComplexity.EXPERT,
        "design": TaskComplexity.EXPERT,
        "optimizar": TaskComplexity.MODERATE,
        "optimize": TaskComplexity.MODERATE,
        "documentar": TaskComplexity.SIMPLE,
        "document": TaskComplexity.SIMPLE,
        "fix bug": TaskComplexity.MODERATE,
        "bugfix": TaskComplexity.MODERATE,
        "investigar": TaskComplexity.COMPLEX,
        "research": TaskComplexity.COMPLEX,
        "analizar": TaskComplexity.MODERATE,
        "analyze": TaskComplexity.MODERATE,
        "implementar": TaskComplexity.MODERATE,
        "implement": TaskComplexity.MODERATE,
        "crear": TaskComplexity.SIMPLE,
        "create": TaskComplexity.SIMPLE,
        "test": TaskComplexity.SIMPLE,
        "probar": TaskComplexity.SIMPLE,
        "actualizar": TaskComplexity.SIMPLE,
        "update": TaskComplexity.SIMPLE,
        "eliminar": TaskComplexity.SIMPLE,
        "delete": TaskComplexity.SIMPLE,
        "migrar": TaskComplexity.COMPLEX,
        "migrate": TaskComplexity.COMPLEX,
    }

    # Agentes y sus especialidades
    AGENT_PATTERNS = {
        "adan": {
            "keywords": [
                "código",
                "code",
                "refactor",
                "bug",
                "test",
                "fix",
                "implementar",
                "implement",
                "debug",
            ],
            "file_patterns": [".py", ".js", ".ts", ".java", ".cpp", ".go"],
            "description": "Código, refactor, tests, debugging",
        },
        "eva": {
            "keywords": [
                "investigar",
                "research",
                "analizar",
                "analyze",
                "documentar",
                "document",
                "evaluar",
                "evaluar",
            ],
            "description": "Análisis, investigación, documentación",
        },
        "odin": {
            "keywords": [
                "arquitectura",
                "architecture",
                "diseñar",
                "design",
                "planificar",
                "plan",
                "estrategia",
                "strategy",
            ],
            "description": "Arquitectura, diseño, planificación estratégica",
},
        "shalltear": {
            "keywords": [
                "creativo",
                "creative",
                "diálogo",
                "dialogue",
                "story",
                "historia",
                "narrativa",
            ],
            "description": "Creativo, narrativa, diálogos",
        },
    }

    def __init__(self):
        self.thresholds = {
            "code_lines": 50,  # >50 líneas → delegar a Adán
            "analysis_depth": 3,  # Análisis profundo → Odín
            "research_needed": True,  # Research → Eva
            "docs_involved": 5,  # >5 docs → Archivero
        }

    def analyze_task(
        self, task_description: str, context: Optional[Dict] = None
    ) -> DelegationRecommendation:
        """
        Analiza una tarea y recomienda si delegar y a quién.

        Args:
            task_description: Descripción de la tarea
            context: Contexto adicional (opcional)

        Returns:
            DelegationRecommendation con la decisión
        """
        context = context or {}

        # Estimar complejidad
        complexity = self._estimate_complexity(task_description)

        # Decidir si delegar
        if complexity.value >= TaskComplexity.COMPLEX.value:
            agent = self._select_agent(task_description, context)

            return DelegationRecommendation(
                should_delegate=True,
                recommended_agent=agent,
                complexity=complexity,
                reasoning=f"Tarea compleja ({complexity.name}): {self._get_complexity_reason(task_description)}",
                confidence=0.8,
            )
        else:
            return DelegationRecommendation(
                should_delegate=False,
                recommended_agent=None,
                complexity=complexity,
                reasoning=f"Tarea simple ({complexity.name}): ejecutable directamente",
                confidence=0.9,
            )

    def _estimate_complexity(self, task: str) -> TaskComplexity:
        """
        Estima complejidad basada en keywords y características.
        """
        task_lower = task.lower()

        # Buscar keywords de complejidad
        for keyword, complexity in self.COMPLEXITY_KEYWORDS.items():
            if keyword in task_lower:
                return complexity

        # Heurísticas adicionales
        word_count = len(task.split())

        # Contar verbos de acción
        action_verbs = [
            "create",
            "implement",
            "refactor",
            "analyze",
            "design",
            "optimize",
            "migrate",
        ]
        action_count = sum(1 for verb in action_verbs if verb in task_lower)

        # Longitud y estructura
        if word_count < 10 and action_count <= 1:
            return TaskComplexity.SIMPLE
        elif word_count < 30 and action_count <= 2:
            return TaskComplexity.MODERATE
        elif word_count < 50 or action_count >= 3:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPERT

    def _select_agent(self, task: str, context: Dict) -> str:
        """
        Selecciona el agente más adecuado para la tarea.
        """
        task_lower = task.lower()
        scores = {agent: 0 for agent in self.AGENT_PATTERNS}

        # Puntuar por keywords
        for agent, data in self.AGENT_PATTERNS.items():
            for keyword in data["keywords"]:
                if keyword in task_lower:
                    scores[agent] += 1

        # Bonus por contexto
        if "file_path" in context:
            path = context["file_path"].lower()
            for agent, data in self.AGENT_PATTERNS.items():
                if "file_patterns" in data:
                    for pattern in data["file_patterns"]:
                        if pattern in path:
                            scores[agent] += 2

        # Seleccionar agente con mayor score
        best_agent = max(scores, key=scores.get)

        # Default a Eva si no hay match claro
        if scores[best_agent] == 0:
            return "eva"

        return best_agent

    def _get_complexity_reason(self, task: str) -> str:
        """Genera explicación de por qué es compleja."""
        task_lower = task.lower()
        reasons = []

        if any(kw in task_lower for kw in ["refactor", "refactorizar"]):
            reasons.append("involucra refactorización")
        if any(
            kw in task_lower
            for kw in ["arquitectura", "architecture", "design", "diseñar"]
        ):
            reasons.append("cambios arquitectónicos")
        if any(kw in task_lower for kw in ["migrar", "migrate"]):
            reasons.append("migración de sistemas")
        if any(kw in task_lower for kw in ["investigar", "research", "analizar"]):
            reasons.append("requiere análisis profundo")

        if not reasons:
            reasons.append("múltiples pasos o dependencias")

        return ", ".join(reasons)

    def batch_analyze(self, tasks: List[str]) -> List[DelegationRecommendation]:
        """
        Analiza múltiples tareas.
        """
        return [self.analyze_task(task) for task in tasks]


# Instancia global
delegation_detector = DelegationDetector()
