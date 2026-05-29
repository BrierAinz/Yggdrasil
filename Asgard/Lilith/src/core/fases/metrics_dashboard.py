# -*- coding: utf-8 -*-
"""
Lilith v2.1 - METRICS DASHBOARD
FASE E: Intelligence Collective - Project Health Monitoring

Features:
- Technical debt tracking over time
- Code quality trends
- Predictive bug risk analysis
- Sprint comparisons
- Team productivity metrics
"""

import hashlib
import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricsSnapshot:
    """Snapshot de mÃ©tricas en un punto del tiempo"""

    timestamp: str
    commit_hash: Optional[str]

    # MÃ©tricas de cÃ³digo
    total_lines: int
    total_files: int
    total_functions: int
    total_classes: int

    # MÃ©tricas de calidad
    avg_complexity: float
    max_complexity: int
    total_smells: int
    smells_by_severity: Dict[str, int]

    # MÃ©tricas de seguridad
    security_score: float
    vulnerabilities_found: int
    critical_issues: int

    # MÃ©tricas de documentaciÃ³n
    documentation_coverage: float
    missing_docstrings: int

    # MÃ©tricas de testing
    test_coverage: float
    test_count: int

    # Deuda tÃ©cnica calculada
    technical_debt_hours: float
    debt_ratio: float  # % del tiempo de desarrollo

    # Metadatos
    changed_files: int = 0
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class TrendAnalysis:
    """AnÃ¡lisis de tendencias"""

    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # "improving", "degrading", "stable"
    prediction: Optional[str] = None


class TechnicalDebtCalculator:
    """Calculadora de deuda tÃ©cnica"""

    # Horas estimadas para resolver cada tipo de issue
    DEBT_HOURS = {
        "critical_vulnerability": 8.0,
        "high_vulnerability": 4.0,
        "medium_vulnerability": 2.0,
        "complex_function": 3.0,
        "missing_docstring": 0.5,
        "code_smell": 1.0,
        "test_missing": 2.0,
        "security_issue": 6.0,
    }

    def calculate(self, metrics: MetricsSnapshot) -> float:
        """Calcular horas de deuda tÃ©cnica"""
        debt_hours = 0.0

        # Por vulnerabilidades
        debt_hours += (
            metrics.critical_issues * self.DEBT_HOURS["critical_vulnerability"]
        )
        debt_hours += (
            metrics.vulnerabilities_found * 0.3 * self.DEBT_HOURS["high_vulnerability"]
        )

        # Por complejidad
        high_complexity = max(0, metrics.max_complexity - 10)
        debt_hours += high_complexity * 0.5

        # Por smells
        debt_hours += metrics.total_smells * self.DEBT_HOURS["code_smell"]

        # Por documentaciÃ³n faltante
        debt_hours += metrics.missing_docstrings * self.DEBT_HOURS["missing_docstring"]

        # Por cobertura de tests
        if metrics.test_coverage < 80:
            debt_hours += (80 - metrics.test_coverage) * 0.5

        return round(debt_hours, 2)

    def calculate_ratio(self, debt_hours: float, total_lines: int) -> float:
        """Calcular ratio de deuda (%)"""
        if total_lines == 0:
            return 0.0

        # Asumir 100 lÃ­neas = 1 hora de desarrollo promedio
        total_development_hours = total_lines / 100

        if total_development_hours == 0:
            return 0.0

        return round((debt_hours / total_development_hours) * 100, 2)


class PredictiveAnalyzer:
    """Analizador predictivo de riesgos"""

    def predict_bug_risk(self, metrics: MetricsSnapshot) -> Dict:
        """Predecir riesgo de bugs basado en mÃ©tricas"""
        risk_factors = []
        risk_score = 0.0

        # Factor 1: Complejidad
        if metrics.avg_complexity > 10:
            risk_score += 20
            risk_factors.append("Alta complejidad promedio")

        # Factor 2: Code smells
        smell_density = metrics.total_smells / max(metrics.total_functions, 1)
        if smell_density > 0.5:
            risk_score += 15
            risk_factors.append("Alta densidad de code smells")

        # Factor 3: DocumentaciÃ³n
        if metrics.documentation_coverage < 50:
            risk_score += 15
            risk_factors.append("Baja cobertura de documentaciÃ³n")

        # Factor 4: Tests
        if metrics.test_coverage < 60:
            risk_score += 25
            risk_factors.append("Cobertura de tests insuficiente")

        # Factor 5: Vulnerabilidades
        if metrics.critical_issues > 0:
            risk_score += 25
            risk_factors.append(f"{metrics.critical_issues} vulnerabilidades crÃ­ticas")

        # Calcular nivel
        if risk_score >= 70:
            level = "CRITICAL"
            color = "#f85149"
        elif risk_score >= 50:
            level = "HIGH"
            color = "#d29922"
        elif risk_score >= 30:
            level = "MEDIUM"
            color = "#58a6ff"
        else:
            level = "LOW"
            color = "#3fb950"

        return {
            "score": min(100, risk_score),
            "level": level,
            "color": color,
            "factors": risk_factors,
            "prediction": f"Riesgo de bugs: {level}",
            "recommendation": self._get_recommendation(risk_score),
        }

    def _get_recommendation(self, risk_score: float) -> str:
        """Obtener recomendaciÃ³n basada en riesgo"""
        if risk_score >= 70:
            return "Priorizar refactoring inmediato. Considerar pausar features nuevas."
        elif risk_score >= 50:
            return "Planificar sprint de deuda tÃ©cnica. Abordar vulnerabilidades crÃ­ticas."
        elif risk_score >= 30:
            return "Buen estado general. Mantener cobertura de tests y documentaciÃ³n."
        else:
            return "Excelente estado de salud del cÃ³digo. Continuar con buenas prÃ¡cticas."

    def predict_completion_time(
        self, current_metrics: MetricsSnapshot, target_coverage: float = 80
    ) -> Dict:
        """Predecir tiempo para alcanzar mÃ©tricas objetivo"""
        hours_needed = 0
        tasks = []

        # Tests
        if current_metrics.test_coverage < target_coverage:
            coverage_gap = target_coverage - current_metrics.test_coverage
            test_hours = coverage_gap * 2  # 2 horas por cada % de cobertura
            hours_needed += test_hours
            tasks.append(f"Aumentar cobertura de tests: {test_hours:.1f}h")

        # DocumentaciÃ³n
        if current_metrics.missing_docstrings > 0:
            doc_hours = current_metrics.missing_docstrings * 0.5
            hours_needed += doc_hours
            tasks.append(f"Documentar funciones: {doc_hours:.1f}h")

        # Vulnerabilidades
        if current_metrics.vulnerabilities_found > 0:
            sec_hours = current_metrics.vulnerabilities_found * 3
            hours_needed += sec_hours
            tasks.append(f"Fix vulnerabilidades: {sec_hours:.1f}h")

        return {
            "estimated_hours": round(hours_needed, 1),
            "estimated_days": round(hours_needed / 8, 1),
            "tasks": tasks,
        }


class MetricsHistory:
    """Historial de mÃ©tricas del proyecto"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".lilith" / "metrics_history"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.debt_calculator = TechnicalDebtCalculator()
        self.predictive = PredictiveAnalyzer()

    def _get_history_file(self, project_path: Path) -> Path:
        """Obtener archivo de historial para proyecto"""
        project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:12]
        return self.storage_path / f"{project_hash}_history.json"

    def save_snapshot(self, project_path: Path, snapshot: MetricsSnapshot):
        """Guardar snapshot de mÃ©tricas"""
        history_file = self._get_history_file(project_path)

        history = []
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)

        history.append(asdict(snapshot))

        # Mantener solo Ãºltimos 100 snapshots
        history = history[-100:]

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

        logger.info(f"Metrics snapshot saved: {snapshot.timestamp}")

    def load_history(self, project_path: Path, days: int = 30) -> List[MetricsSnapshot]:
        """Cargar historial de mÃ©tricas"""
        history_file = self._get_history_file(project_path)

        if not history_file.exists():
            return []

        with open(history_file) as f:
            data = json.load(f)

        # Filtrar por dÃ­as
        cutoff = datetime.now() - timedelta(days=days)

        snapshots = []
        for item in data:
            try:
                item_date = datetime.fromisoformat(item["timestamp"])
                if item_date >= cutoff:
                    snapshots.append(MetricsSnapshot(**item))
            except:
                continue

        return snapshots

    def analyze_trends(self, project_path: Path) -> List[TrendAnalysis]:
        """Analizar tendencias del proyecto"""
        history = self.load_history(project_path, days=14)

        if len(history) < 2:
            return []

        trends = []

        # Comparar Ãºltimo vs anterior
        current = history[-1]
        previous = history[-7] if len(history) >= 7 else history[0]  # Semana vs ahora

        metrics_to_track = [
            (
                "avg_complexity",
                current.avg_complexity,
                previous.avg_complexity,
                "lower",
            ),
            ("test_coverage", current.test_coverage, previous.test_coverage, "higher"),
            (
                "security_score",
                current.security_score,
                previous.security_score,
                "higher",
            ),
            (
                "technical_debt",
                current.technical_debt_hours,
                previous.technical_debt_hours,
                "lower",
            ),
            (
                "documentation_coverage",
                current.documentation_coverage,
                previous.documentation_coverage,
                "higher",
            ),
        ]

        for name, curr, prev, direction in metrics_to_track:
            if prev == 0:
                change = 0
            else:
                change = ((curr - prev) / prev) * 100

            if direction == "lower":
                trend = (
                    "improving"
                    if change < 0
                    else "degrading"
                    if change > 10
                    else "stable"
                )
            else:
                trend = (
                    "improving"
                    if change > 0
                    else "degrading"
                    if change < -10
                    else "stable"
                )

            trends.append(
                TrendAnalysis(
                    metric_name=name,
                    current_value=round(curr, 2),
                    previous_value=round(prev, 2),
                    change_percent=round(change, 1),
                    trend=trend,
                )
            )

        return trends

    def generate_dashboard_data(self, project_path: Path) -> Dict:
        """Generar datos para el dashboard"""
        history = self.load_history(project_path, days=30)

        if not history:
            return {"error": "No hay datos histÃ³ricos disponibles"}

        current = history[-1]

        # AnÃ¡lisis predictivo
        bug_risk = self.predictive.predict_bug_risk(current)
        completion_prediction = self.predictive.predict_completion_time(current)

        # Tendencias
        trends = self.analyze_trends(project_path)

        # GrÃ¡ficos de tiempo
        timeline = self._generate_timeline(history)

        return {
            "current_snapshot": {
                "timestamp": current.timestamp,
                "lines_of_code": current.total_lines,
                "files": current.total_files,
                "functions": current.total_functions,
                "avg_complexity": current.avg_complexity,
                "test_coverage": current.test_coverage,
                "documentation_coverage": current.documentation_coverage,
                "security_score": current.security_score,
            },
            "health_score": self._calculate_health_score(current),
            "bug_risk": bug_risk,
            "technical_debt": {
                "hours": current.technical_debt_hours,
                "ratio": current.debt_ratio,
                "category": self._debt_category(current.debt_ratio),
            },
            "predictions": completion_prediction,
            "trends": [asdict(t) for t in trends],
            "timeline": timeline,
            "recommendations": self._generate_recommendations(current, trends),
        }

    def _calculate_health_score(self, metrics: MetricsSnapshot) -> int:
        """Calcular score de salud general (0-100)"""
        score = 100

        # Penalizar por complejidad
        if metrics.avg_complexity > 10:
            score -= min(20, (metrics.avg_complexity - 10) * 2)

        # Penalizar por falta de tests
        score -= min(30, (100 - metrics.test_coverage) * 0.3)

        # Penalizar por documentaciÃ³n
        score -= min(15, (100 - metrics.documentation_coverage) * 0.15)

        # Penalizar por vulnerabilidades
        score -= metrics.critical_issues * 10
        score -= metrics.vulnerabilities_found * 2

        # Penalizar por deuda
        score -= min(25, metrics.debt_ratio * 0.5)

        return max(0, min(100, int(score)))

    def _debt_category(self, ratio: float) -> str:
        """Categorizar nivel de deuda"""
        if ratio < 5:
            return "Healthy"
        elif ratio < 15:
            return "Moderate"
        elif ratio < 30:
            return "High"
        else:
            return "Critical"

    def _generate_timeline(self, history: List[MetricsSnapshot]) -> Dict:
        """Generar datos para grÃ¡ficos de tiempo"""
        return {
            "dates": [h.timestamp for h in history],
            "complexity": [h.avg_complexity for h in history],
            "test_coverage": [h.test_coverage for h in history],
            "debt_hours": [h.technical_debt_hours for h in history],
            "security_score": [h.security_score for h in history],
        }

    def _generate_recommendations(
        self, current: MetricsSnapshot, trends: List[TrendAnalysis]
    ) -> List[str]:
        """Generar recomendaciones personalizadas"""
        recommendations = []

        # Basado en mÃ©tricas actuales
        if current.test_coverage < 70:
            recommendations.append("Aumentar cobertura de tests a 70%+")

        if current.critical_issues > 0:
            recommendations.append(
                f"Priorizar {current.critical_issues} vulnerabilidades crÃ­ticas"
            )

        if current.avg_complexity > 15:
            recommendations.append("Refactorizar funciones con alta complejidad")

        # Basado en tendencias
        for trend in trends:
            if trend.trend == "degrading" and trend.metric_name == "technical_debt":
                recommendations.append(
                    "La deuda tÃ©cnica estÃ¡ creciendo. Planificar sprint de mantenimiento."
                )

        return recommendations[:5]


class MetricsCollector:
    """Recolector de mÃ©tricas desde los otros mÃ³dulos de Lilith"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.debt_calculator = TechnicalDebtCalculator()

    async def collect_from_analyzers(
        self, security_result=None, review_result=None, doc_result=None
    ) -> MetricsSnapshot:
        """Recolectar mÃ©tricas desde los analizadores existentes"""

        # Contar lÃ­neas y archivos
        total_lines = 0
        total_files = 0
        py_files = list(self.project_path.rglob("*.py"))
        py_files = [
            f
            for f in py_files
            if not any(x in str(f) for x in ["__pycache__", ".git", "venv"])
        ]

        for f in py_files:
            try:
                content = f.read_text()
                total_lines += len(content.split("\n"))
                total_files += 1
            except:
                pass

        # MÃ©tricas de calidad
        avg_complexity = 5.0  # Default
        max_complexity = 10
        total_smells = 0
        smells_by_severity = defaultdict(int)

        if review_result:
            avg_complexity = review_result.get("avg_complexity", 5.0)
            max_complexity = review_result.get("max_complexity", 10)
            total_smells = len(review_result.get("reviews", []))

        # MÃ©tricas de seguridad
        security_score = 100.0
        vulnerabilities = 0
        critical = 0

        if security_result:
            vulnerabilities = len(security_result.get("findings", []))
            critical = sum(
                1
                for f in security_result.get("findings", [])
                if f.get("severity") == "critical"
            )
            security_score = max(0, 100 - (vulnerabilities * 5) - (critical * 20))

        # MÃ©tricas de documentaciÃ³n
        doc_coverage = 0.0
        missing_docs = 0

        if doc_result:
            doc_coverage = doc_result.get("coverage", 0.0)
            missing_docs = doc_result.get("missing", 0)

        # Crear snapshot
        snapshot = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            commit_hash=None,
            total_lines=total_lines,
            total_files=total_files,
            total_functions=0,  # Se calcularÃ­a con AST
            total_classes=0,
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
            total_smells=total_smells,
            smells_by_severity=dict(smells_by_severity),
            security_score=security_score,
            vulnerabilities_found=vulnerabilities,
            critical_issues=critical,
            documentation_coverage=doc_coverage,
            missing_docstrings=missing_docs,
            test_coverage=0.0,  # Se obtendrÃ­a de coverage.py
            test_count=0,
            technical_debt_hours=0.0,
            debt_ratio=0.0,
        )

        # Calcular deuda
        snapshot.technical_debt_hours = self.debt_calculator.calculate(snapshot)
        snapshot.debt_ratio = self.debt_calculator.calculate_ratio(
            snapshot.technical_debt_hours, snapshot.total_lines
        )

        return snapshot


# Instancias globales
_metrics_history = None
_metrics_collector = None


def get_metrics_history(storage_path: Path = None) -> MetricsHistory:
    """Obtener historial de mÃ©tricas"""
    global _metrics_history
    if _metrics_history is None:
        _metrics_history = MetricsHistory(storage_path)
    return _metrics_history


def get_metrics_collector(project_path: Path) -> MetricsCollector:
    """Obtener recolector de mÃ©tricas"""
    global _metrics_collector
    if _metrics_collector is None or _metrics_collector.project_path != project_path:
        _metrics_collector = MetricsCollector(project_path)
    return _metrics_collector
