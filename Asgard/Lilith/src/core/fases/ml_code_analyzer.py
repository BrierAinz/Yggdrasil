# -*- coding: utf-8 -*-
"""
Lilith v2.1 - ML CODE ANALYZER
FASE E: Intelligence Collective - Machine Learning Code Analysis

Features:
- Semantic code duplication detection
- Anomaly detection for unusual patterns
- Code similarity using AST vectors
- Predictive refactoring suggestions
- Anti-pattern detection with ML
"""

import ast
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class SmellType(Enum):
    """Tipos de code smells avanzados"""

    SEMANTIC_DUPLICATION = "semantic_duplication"
    GOD_FUNCTION = "god_function"
    FEATURE_ENVY = "feature_envy"
    SHOTGUN_SURGERY = "shotgun_surgery"
    DIVERGENT_CHANGE = "divergent_change"
    PARALLEL_INHERITANCE = "parallel_inheritance"
    PRIMITIVE_OBSSESSION = "primitive_obsession"
    DATA_CLASS = "data_class"
    REFUSED_BEQUEST = "refused_bequest"
    TEMPORARY_FIELD = "temporary_field"
    MESSAGE_CHAIN = "message_chain"
    MIDDLE_MAN = "middle_man"
    INSIDER_TRADING = "insider_trading"
    LARGE_CLASS = "large_class"
    LONG_PARAMETER_LIST = "long_parameter_list"


@dataclass
class MLCodeSmell:
    """Code smell detectado con ML"""

    smell_type: SmellType
    severity: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    file_path: str
    line_start: int
    line_end: int
    description: str
    affected_symbols: List[str] = field(default_factory=list)
    similar_code_refs: List[str] = field(default_factory=list)
    suggested_refactoring: Optional[str] = None
    metrics: Dict = field(default_factory=dict)


class ASTVectorizer:
    """Vectoriza cÃ³digo AST para comparaciÃ³n semÃ¡ntica"""

    def __init__(self):
        self.node_weights = {
            "FunctionDef": 1.0,
            "ClassDef": 1.0,
            "If": 0.8,
            "For": 0.8,
            "While": 0.8,
            "Try": 0.7,
            "With": 0.6,
            "Call": 0.9,
            "Attribute": 0.5,
            "Name": 0.3,
        }

    def vectorize(self, node: ast.AST) -> Dict[str, float]:
        """Crear vector de caracterÃ­sticas del AST"""
        vector = defaultdict(float)

        for child in ast.walk(node):
            node_type = type(child).__name__
            weight = self.node_weights.get(node_type, 0.1)
            vector[node_type] += weight

            # CaracterÃ­sticas especÃ­ficas
            if isinstance(child, ast.Call):
                vector["call_count"] += 1
            elif isinstance(child, (ast.If, ast.IfExp)):
                vector["branch_count"] += 1
            elif isinstance(child, (ast.For, ast.While, ast.comprehension)):
                vector["loop_count"] += 1
            elif isinstance(child, ast.ExceptHandler):
                vector["exception_count"] += 1

        return dict(vector)

    def cosine_similarity(self, vec1: Dict, vec2: Dict) -> float:
        """Calcular similitud coseno entre vectores"""
        all_keys = set(vec1.keys()) | set(vec2.keys())

        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v**2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class SemanticDuplicateDetector:
    """Detecta duplicaciÃ³n semÃ¡ntica (no textual)"""

    def __init__(self, similarity_threshold: float = 0.85):
        self.vectorizer = ASTVectorizer()
        self.threshold = similarity_threshold
        self.function_vectors: Dict[str, Dict] = {}

    def add_function(self, name: str, node: ast.FunctionDef, file_path: str):
        """Agregar funciÃ³n para anÃ¡lisis"""
        vec = self.vectorizer.vectorize(node)
        vec["_name"] = name
        vec["_file"] = file_path
        vec["_lines"] = (
            node.lineno,
            node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
        )
        self.function_vectors[f"{file_path}::{name}"] = vec

    def find_duplicates(self) -> List[Tuple[str, str, float]]:
        """Encontrar funciones duplicadas semÃ¡nticamente"""
        duplicates = []
        items = list(self.function_vectors.items())

        for i, (name1, vec1) in enumerate(items):
            for name2, vec2 in items[i + 1 :]:
                # Ignorar si son el mismo archivo y misma funciÃ³n
                if name1 == name2:
                    continue

                similarity = self.vectorizer.cosine_similarity(vec1, vec2)

                if similarity >= self.threshold:
                    duplicates.append((name1, name2, similarity))

        return sorted(duplicates, key=lambda x: x[2], reverse=True)

    def find_structural_patterns(self) -> List[Dict]:
        """Encontrar patrones estructurales comunes"""
        patterns = defaultdict(list)

        for name, vec in self.function_vectors.items():
            # Crear fingerprint estructural
            structure_key = tuple(
                sorted(
                    [
                        k
                        for k, v in vec.items()
                        if isinstance(v, float) and v > 0.5 and not k.startswith("_")
                    ]
                )
            )

            if len(structure_key) >= 3:  # Patrones significativos
                patterns[structure_key].append(name)

        # Retornar patrones con mÃºltiples ocurrencias
        return [
            {"pattern": k, "functions": v, "count": len(v)}
            for k, v in patterns.items()
            if len(v) >= 2
        ]


class AnomalyDetector:
    """Detecta anomalÃ­as en el cÃ³digo usando estadÃ­sticas"""

    def __init__(self):
        self.baseline_stats = {}
        self.project_stats = {}

    def analyze_project_baseline(self, functions: List[Dict]):
        """Establecer baseline estadÃ­stico del proyecto"""
        if not functions:
            return

        # Calcular estadÃ­sticas
        complexities = [f.get("complexity", 0) for f in functions]
        lengths = [f.get("length", 0) for f in functions]
        param_counts = [f.get("param_count", 0) for f in functions]

        self.baseline_stats = {
            "avg_complexity": sum(complexities) / len(complexities),
            "std_complexity": self._std(complexities),
            "avg_length": sum(lengths) / len(lengths),
            "std_length": self._std(lengths),
            "avg_params": sum(param_counts) / len(param_counts),
            "std_params": self._std(param_counts),
        }

    def _std(self, values: List[float]) -> float:
        """Calcular desviaciÃ³n estÃ¡ndar"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def is_anomalous(
        self, func_stats: Dict, z_threshold: float = 2.5
    ) -> Tuple[bool, List[str]]:
        """Detectar si una funciÃ³n es anÃ³mala"""
        if not self.baseline_stats:
            return False, []

        anomalies = []

        # Check complexity
        if self.baseline_stats["std_complexity"] > 0:
            z_complexity = (
                func_stats.get("complexity", 0) - self.baseline_stats["avg_complexity"]
            ) / self.baseline_stats["std_complexity"]
            if z_complexity > z_threshold:
                anomalies.append(f"Complexity {z_complexity:.1f}Ïƒ above average")

        # Check length
        if self.baseline_stats["std_length"] > 0:
            z_length = (
                func_stats.get("length", 0) - self.baseline_stats["avg_length"]
            ) / self.baseline_stats["std_length"]
            if z_length > z_threshold:
                anomalies.append(f"Length {z_length:.1f}Ïƒ above average")

        # Check parameters
        if self.baseline_stats["std_params"] > 0:
            z_params = (
                func_stats.get("param_count", 0) - self.baseline_stats["avg_params"]
            ) / self.baseline_stats["std_params"]
            if z_params > z_threshold:
                anomalies.append(f"Parameter count {z_params:.1f}Ïƒ above average")

        return len(anomalies) > 0, anomalies


class AntiPatternMLDetector:
    """Detecta anti-patrones usando heurÃ­sticas ML"""

    def __init__(self):
        self.class_methods = defaultdict(list)
        self.function_calls = defaultdict(list)

    def analyze_file(self, source: str, file_path: str) -> List[MLCodeSmell]:
        """Analizar archivo completo"""
        smells = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return smells

        # Detectar diferentes smells
        smells.extend(self._detect_god_classes(tree, file_path))
        smells.extend(self._detect_feature_envy(tree, file_path))
        smells.extend(self._detect_data_classes(tree, file_path))
        smells.extend(self._detect_primitive_obsession(tree, file_path))
        smells.extend(self._detect_refused_bequest(tree, file_path))

        return smells

    def _detect_god_classes(self, tree: ast.AST, file_path: str) -> List[MLCodeSmell]:
        """Detectar clases con demasiadas responsabilidades"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                attributes = [n for n in node.body if isinstance(n, ast.Assign)]

                # HeurÃ­stica: mÃ¡s de 15 mÃ©todos o mÃ¡s de 10 atributos
                if len(methods) > 15 or len(attributes) > 10:
                    smells.append(
                        MLCodeSmell(
                            smell_type=SmellType.LARGE_CLASS,
                            severity=min(1.0, len(methods) / 20),
                            confidence=0.75,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno,
                            description=f"Class '{node.name}' has {len(methods)} methods and {len(attributes)} attributes",
                            affected_symbols=[node.name],
                            suggested_refactoring="Consider splitting into smaller classes following Single Responsibility Principle",
                            metrics={
                                "methods": len(methods),
                                "attributes": len(attributes),
                            },
                        )
                    )

                # Detectar God Class (mÃºltiples tipos de mÃ©todos)
                method_types = self._categorize_methods(methods)
                if len(method_types) > 4:  # Demasiadas responsabilidades
                    smells.append(
                        MLCodeSmell(
                            smell_type=SmellType.GOD_FUNCTION,
                            severity=0.8,
                            confidence=0.7,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno,
                            description=f"Class '{node.name}' appears to be a God Class with mixed responsibilities",
                            affected_symbols=[node.name],
                            suggested_refactoring="Split into specialized classes",
                            metrics={"responsibilities": len(method_types)},
                        )
                    )

        return smells

    def _categorize_methods(self, methods: List[ast.FunctionDef]) -> Set[str]:
        """Categorizar mÃ©todos por tipo"""
        categories = set()

        for method in methods:
            name = method.name.lower()

            if any(x in name for x in ["get", "fetch", "retrieve", "load"]):
                categories.add("data_access")
            elif any(x in name for x in ["save", "update", "create", "delete"]):
                categories.add("data_modification")
            elif any(x in name for x in ["validate", "check", "verify"]):
                categories.add("validation")
            elif any(x in name for x in ["calculate", "compute", "process"]):
                categories.add("computation")
            elif any(x in name for x in ["send", "notify", "dispatch"]):
                categories.add("communication")
            elif any(x in name for x in ["render", "display", "show"]):
                categories.add("presentation")
            else:
                categories.add("other")

        return categories

    def _detect_feature_envy(self, tree: ast.AST, file_path: str) -> List[MLCodeSmell]:
        """Detectar Feature Envy (mÃ©todo que usa mÃ¡s de otra clase)"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Contar accesos a atributos de otras clases vs propios
                self_accesses = 0
                other_accesses = 0

                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        # HeurÃ­stica simple: si empieza con self o cls
                        if isinstance(child.value, ast.Name) and child.value.id in (
                            "self",
                            "cls",
                        ):
                            self_accesses += 1
                        else:
                            other_accesses += 1

                # Si usa mÃ¡s atributos de otros que propios
                if other_accesses > self_accesses * 2 and other_accesses > 5:
                    smells.append(
                        MLCodeSmell(
                            smell_type=SmellType.FEATURE_ENVY,
                            severity=0.7,
                            confidence=0.6,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno,
                            description=f"Method '{node.name}' may have Feature Envy",
                            affected_symbols=[node.name],
                            suggested_refactoring="Consider moving this method to the class it uses most",
                            metrics={
                                "self_accesses": self_accesses,
                                "other_accesses": other_accesses,
                            },
                        )
                    )

        return smells

    def _detect_data_classes(self, tree: ast.AST, file_path: str) -> List[MLCodeSmell]:
        """Detectar clases que solo almacenan datos"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                # Verificar si solo tiene __init__ y getters/setters
                non_boilerplate = [
                    m
                    for m in methods
                    if m.name not in ("__init__", "__repr__", "__str__", "__eq__")
                    and not (m.name.startswith("get_") or m.name.startswith("set_"))
                ]

                if len(methods) > 0 and len(non_boilerplate) == 0:
                    smells.append(
                        MLCodeSmell(
                            smell_type=SmellType.DATA_CLASS,
                            severity=0.6,
                            confidence=0.8,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno,
                            description=f"Class '{node.name}' appears to be a Data Class",
                            affected_symbols=[node.name],
                            suggested_refactoring="Consider using @dataclass or adding behavior methods",
                            metrics={"total_methods": len(methods)},
                        )
                    )

        return smells

    def _detect_primitive_obsession(
        self, tree: ast.AST, file_path: str
    ) -> List[MLCodeSmell]:
        """Detectar uso excesivo de primitivos"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Contar parÃ¡metros primitivos
                primitive_count = 0

                for arg in node.args.args:
                    # Sin anotaciÃ³n de tipo = probablemente primitivo
                    if not arg.annotation:
                        primitive_count += 1

                if primitive_count >= 4:
                    smells.append(
                        MLCodeSmell(
                            smell_type=SmellType.PRIMITIVE_OBSSESSION,
                            severity=min(1.0, primitive_count / 6),
                            confidence=0.65,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno
                            if hasattr(node, "end_lineno")
                            else node.lineno,
                            description=f"Method '{node.name}' has {primitive_count} primitive parameters",
                            affected_symbols=[node.name],
                            suggested_refactoring="Consider creating a parameter object",
                            metrics={"primitive_params": primitive_count},
                        )
                    )

        return smells

    def _detect_refused_bequest(
        self, tree: ast.AST, file_path: str
    ) -> List[MLCodeSmell]:
        """Detectar subclases que no usan mÃ©todos de padre"""
        smells = []

        # Mapear clases y herencias
        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [
                    base.id if isinstance(base, ast.Name) else "" for base in node.bases
                ]
                methods = set(
                    m.name for m in node.body if isinstance(m, ast.FunctionDef)
                )
                classes[node.name] = {
                    "bases": [b for b in bases if b],
                    "methods": methods,
                    "line": node.lineno,
                }

        # Analizar herencia
        for name, info in classes.items():
            for base in info["bases"]:
                if base in classes:
                    parent_methods = classes[base]["methods"]
                    own_methods = info["methods"]

                    # Si no usa muchos mÃ©todos del padre
                    if (
                        parent_methods
                        and len(own_methods.intersection(parent_methods))
                        < len(parent_methods) * 0.3
                    ):
                        smells.append(
                            MLCodeSmell(
                                smell_type=SmellType.REFUSED_BEQUEST,
                                severity=0.6,
                                confidence=0.55,
                                file_path=file_path,
                                line_start=info["line"],
                                line_end=info["line"],
                                description=f"Class '{name}' may be refusing bequest from '{base}'",
                                affected_symbols=[name],
                                suggested_refactoring="Review inheritance hierarchy",
                                metrics={
                                    "parent_methods": len(parent_methods),
                                    "overridden": len(
                                        own_methods.intersection(parent_methods)
                                    ),
                                },
                            )
                        )

        return smells


class MLCodeAnalyzer:
    """Analizador ML principal"""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.duplicate_detector = SemanticDuplicateDetector()
        self.anomaly_detector = AnomalyDetector()
        self.anti_pattern_detector = AntiPatternMLDetector()
        self.vectorizer = ASTVectorizer()

    async def analyze_project(self) -> Dict:
        """Analizar proyecto completo con ML"""
        all_functions = []
        all_smells = []
        py_files = list(self.project_path.rglob("*.py"))
        py_files = [
            f
            for f in py_files
            if not any(
                x in str(f) for x in ["__pycache__", ".git", "venv", "node_modules"]
            )
        ]

        # Fase 1: Recolectar informaciÃ³n
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                # Recolectar funciones
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(node, source)
                        all_functions.append(func_info)

                        # Agregar a detector de duplicados
                        self.duplicate_detector.add_function(
                            node.name, node, str(py_file.relative_to(self.project_path))
                        )

                # Detectar anti-patrones
                smells = self.anti_pattern_detector.analyze_file(
                    source, str(py_file.relative_to(self.project_path))
                )
                all_smells.extend(smells)

            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")

        # Fase 2: AnÃ¡lisis estadÃ­stico
        self.anomaly_detector.analyze_project_baseline(all_functions)

        # Detectar anomalÃ­as
        for func in all_functions:
            is_anomaly, reasons = self.anomaly_detector.is_anomalous(func)
            if is_anomaly:
                all_smells.append(
                    MLCodeSmell(
                        smell_type=SmellType.GOD_FUNCTION
                        if func.get("complexity", 0) > 20
                        else SmellType.LARGE_CLASS,
                        severity=0.8,
                        confidence=0.7,
                        file_path=func["file_path"],
                        line_start=func["line_start"],
                        line_end=func["line_end"],
                        description=f"Function '{func['name']}' is anomalous: {', '.join(reasons)}",
                        affected_symbols=[func["name"]],
                        metrics=func,
                    )
                )

        # Fase 3: Detectar duplicados semÃ¡nticos
        duplicates = self.duplicate_detector.find_duplicates()
        for name1, name2, similarity in duplicates[:10]:  # Top 10
            file1, func1 = name1.split("::")
            file2, func2 = name2.split("::")

            all_smells.append(
                MLCodeSmell(
                    smell_type=SmellType.SEMANTIC_DUPLICATION,
                    severity=similarity,
                    confidence=similarity,
                    file_path=file1,
                    line_start=0,
                    line_end=0,
                    description=f"Function '{func1}' is semantically similar to '{func2}' ({similarity:.0%} match)",
                    affected_symbols=[func1, func2],
                    similar_code_refs=[file2],
                    suggested_refactoring="Consider extracting common logic",
                    metrics={"similarity": similarity},
                )
            )

        # Agrupar resultados
        smells_by_type = defaultdict(list)
        for smell in all_smells:
            smells_by_type[smell.smell_type.value].append(
                {
                    "severity": smell.severity,
                    "confidence": smell.confidence,
                    "file": smell.file_path,
                    "description": smell.description,
                    "suggestion": smell.suggested_refactoring,
                    "metrics": smell.metrics,
                }
            )

        return {
            "files_analyzed": len(py_files),
            "functions_analyzed": len(all_functions),
            "total_smells": len(all_smells),
            "smells_by_type": dict(smells_by_type),
            "baseline_stats": self.anomaly_detector.baseline_stats,
            "top_issues": sorted(
                [
                    {
                        "type": k,
                        "count": len(v),
                        "avg_severity": sum(s["severity"] for s in v) / len(v),
                    }
                    for k, v in smells_by_type.items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )[:5],
        }

    def _extract_function_info(self, node: ast.FunctionDef, source: str) -> Dict:
        """Extraer informaciÃ³n de funciÃ³n"""
        lines = source.split("\n")
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line

        # Calcular complejidad
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert),
            ):
                complexity += 1

        return {
            "name": node.name,
            "line_start": start_line,
            "line_end": end_line,
            "length": end_line - start_line,
            "complexity": complexity,
            "param_count": len(node.args.args),
            "file_path": "",  # Se llena externamente
        }


# Instancia global
_ml_analyzer = None


def get_ml_analyzer(project_path: Optional[Path] = None) -> MLCodeAnalyzer:
    """Obtener instancia del analizador ML"""
    global _ml_analyzer
    if _ml_analyzer is None:
        _ml_analyzer = MLCodeAnalyzer(project_path)
    return _ml_analyzer
