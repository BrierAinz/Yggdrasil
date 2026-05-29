"""
Fases A-E Tools - Adaptadores para el sistema IPC
Expone los mÃ³dulos de Fases A-E como Tools registrables
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger("FasesTools")


@dataclass
class ToolResult:
    """Resultado estandarizado de una tool"""

    success: bool
    message: str
    data: Dict[str, Any] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.errors is None:
            self.errors = []


class SecurityScannerTool:
    """
    Tool: Security Scanner (FASE C)
    Escanea cÃ³digo en busca de vulnerabilidades de seguridad
    """

    def __init__(self):
        self.name = "SecurityScanner"
        self.description = "Escanea cÃ³digo en busca de vulnerabilidades (15+ CWEs)"
        self.version = "1.0.0"
        self.category = "security"
        self.risk_level = "LOW"
        self._scanner = None

    def _get_scanner(self):
        """Lazy load del scanner"""
        if self._scanner is None:
            try:
                from src.core.fases.security_scanner import get_security_scanner

                self._scanner = get_security_scanner()
            except Exception as e:
                logger.error(f"Failed to load SecurityScanner: {e}")
                return None
        return self._scanner

    def check_dependencies(self) -> bool:
        """Verificar que el mÃ³dulo estÃ¡ disponible"""
        try:
            from src.core.fases import security_scanner

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Ejecutar acciÃ³n del scanner

        Actions:
        - scan_project: Escanear proyecto completo
        - scan_file: Escanear archivo especÃ­fico
        - get_status: Obtener estado del scanner
        """
        scanner = self._get_scanner()
        if not scanner:
            return ToolResult(
                success=False,
                message="SecurityScanner no disponible",
                errors=["Module not loaded"],
            )

        try:
            if action == "scan_project":
                include_deps = kwargs.get("include_dependencies", True)
                # Adaptar a la API del mÃ³dulo de fases
                result = scanner.scan_project(include_deps)
                return ToolResult(
                    success=True,
                    message=f"Escaneo completado. {len(result.findings)} hallazgos.",
                    data={
                        "findings_count": len(result.findings),
                        "findings": [f.to_dict() for f in result.findings[:20]],
                        "severity_counts": result.get_summary(),
                    },
                )

            elif action == "scan_file":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return ToolResult(
                        success=False,
                        message="file_path requerido",
                        errors=["Missing file_path parameter"],
                    )
                result = scanner.scan_file(Path(file_path))
                return ToolResult(
                    success=True,
                    message=f"Archivo escaneado. {len(result)} hallazgos.",
                    data={"findings": [f.to_dict() for f in result]},
                )

            elif action == "get_status":
                return ToolResult(
                    success=True,
                    message="SecurityScanner disponible",
                    data={"available": True, "version": self.version},
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"AcciÃ³n '{action}' no soportada",
                    errors=["Invalid action"],
                )

        except Exception as e:
            logger.error(f"SecurityScanner error: {e}")
            return ToolResult(
                success=False, message=f"Error: {str(e)}", errors=[str(e)]
            )


class CodeReviewTool:
    """
    Tool: Code Review AI (FASE C)
    RevisiÃ³n automÃ¡tica de calidad de cÃ³digo
    """

    def __init__(self):
        self.name = "CodeReviewAI"
        self.description = "RevisiÃ³n automÃ¡tica de calidad de cÃ³digo (8 categorÃ­as)"
        self.version = "1.0.0"
        self.category = "code_quality"
        self.risk_level = "LOW"
        self._reviewer = None

    def _get_reviewer(self):
        if self._reviewer is None:
            try:
                from src.core.fases.code_review_ai import get_code_review_ai

                self._reviewer = get_code_review_ai()
            except Exception as e:
                logger.error(f"Failed to load CodeReviewAI: {e}")
                return None
        return self._reviewer

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import code_review_ai

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - review_project: Revisar proyecto completo
        - review_file: Revisar archivo especÃ­fico
        """
        reviewer = self._get_reviewer()
        if not reviewer:
            return ToolResult(success=False, message="CodeReviewAI no disponible")

        try:
            if action == "review_project":
                result = reviewer.review_project()
                return ToolResult(
                    success=True,
                    message=f"RevisiÃ³n completada. {len(result.reviews)} hallazgos.",
                    data={
                        "reviews_count": len(result.reviews),
                        "score": result.overall_score,
                        "reviews": [r.to_dict() for r in result.reviews[:10]],
                    },
                )

            elif action == "review_file":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return ToolResult(success=False, message="file_path requerido")
                reviews, metrics = reviewer.review_file(Path(file_path))
                return ToolResult(
                    success=True,
                    message=f"Archivo revisado. {len(reviews)} hallazgos.",
                    data={
                        "reviews": [r.to_dict() for r in reviews],
                        "metrics": metrics.to_dict() if metrics else None,
                    },
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class TestGeneratorTool:
    """
    Tool: Test Generator (FASE C)
    Genera tests automÃ¡ticamente
    """

    def __init__(self):
        self.name = "TestGenerator"
        self.description = "Genera tests automÃ¡ticamente para archivos Python"
        self.version = "1.0.0"
        self.category = "testing"
        self.risk_level = "LOW"
        self._generator = None

    def _get_generator(self):
        if self._generator is None:
            try:
                from src.core.fases.test_generator import get_test_generator

                self._generator = get_test_generator()
            except Exception as e:
                logger.error(f"Failed to load TestGenerator: {e}")
                return None
        return self._generator

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import test_generator

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - generate_tests: Generar tests para archivo
        - apply_tests: Generar y guardar tests
        """
        generator = self._get_generator()
        if not generator:
            return ToolResult(success=False, message="TestGenerator no disponible")

        try:
            if action == "generate_tests":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return ToolResult(success=False, message="file_path requerido")

                suite = generator.generate_tests_for_file(Path(file_path))
                return ToolResult(
                    success=True,
                    message=f"Tests generados: {len(suite.test_cases)} casos",
                    data={
                        "test_count": len(suite.test_cases),
                        "test_file": str(suite.test_file_path),
                        "tests": [t.to_dict() for t in suite.test_cases],
                        "full_content": suite.generate_full_file(),
                    },
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class AutoDocumenterTool:
    """
    Tool: Auto Documenter (FASE B)
    Genera documentaciÃ³n automÃ¡ticamente
    """

    def __init__(self):
        self.name = "AutoDocumenter"
        self.description = "Genera docstrings y documentaciÃ³n automÃ¡ticamente"
        self.version = "1.0.0"
        self.category = "documentation"
        self.risk_level = "LOW"
        self._documenter = None

    def _get_documenter(self):
        if self._documenter is None:
            try:
                from src.core.fases.auto_documenter import get_auto_documenter

                self._documenter = get_auto_documenter()
            except Exception as e:
                logger.error(f"Failed to load AutoDocumenter: {e}")
                return None
        return self._documenter

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import auto_documenter

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - scan_missing: Escanear docstrings faltantes
        - generate_docstring: Generar docstring para funciÃ³n
        """
        documenter = self._get_documenter()
        if not documenter:
            return ToolResult(success=False, message="AutoDocumenter no disponible")

        try:
            if action == "scan_missing":
                file_path = kwargs.get("file_path")
                target = Path(file_path) if file_path else None
                missing = documenter.scan_for_missing_docstrings(target)
                return ToolResult(
                    success=True,
                    message=f"{len(missing)} funciones sin docstring encontradas",
                    data={
                        "count": len(missing),
                        "functions": [
                            {"name": f.name, "file": f.file_path} for f in missing[:50]
                        ],
                    },
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class SmartCommitTool:
    """
    Tool: Smart Commit (FASE B)
    Sugiere mensajes de commit inteligentes
    """

    def __init__(self):
        self.name = "SmartCommit"
        self.description = "Sugiere mensajes de commit basados en cambios"
        self.version = "1.0.0"
        self.category = "git"
        self.risk_level = "MEDIUM"
        self._commit_engine = None

    def _get_engine(self):
        if self._commit_engine is None:
            try:
                from src.core.fases.smart_commit import get_smart_commit_engine

                self._commit_engine = get_smart_commit_engine()
            except Exception as e:
                logger.error(f"Failed to load SmartCommit: {e}")
                return None
        return self._commit_engine

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import smart_commit

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - get_suggestions: Obtener sugerencias de mensajes
        - analyze_staged: Analizar cambios staged
        """
        engine = self._get_engine()
        if not engine:
            return ToolResult(success=False, message="SmartCommit no disponible")

        try:
            if action == "get_suggestions":
                count = kwargs.get("count", 3)
                suggestions = engine.get_suggestions(count)
                return ToolResult(
                    success=True,
                    message=f"{len(suggestions)} sugerencias generadas",
                    data={
                        "suggestions": [
                            {"message": s.format_message(), "confidence": s.confidence}
                            for s in suggestions
                        ]
                    },
                )

            elif action == "analyze_staged":
                analysis = engine.analyze_staged()
                return ToolResult(
                    success=True, message="AnÃ¡lisis completado", data=analysis
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class MLAnalyzerTool:
    """
    Tool: ML Code Analyzer (FASE E)
    AnÃ¡lisis de cÃ³digo con ML
    """

    def __init__(self):
        self.name = "MLCodeAnalyzer"
        self.description = (
            "AnÃ¡lisis ML de cÃ³digo: duplicados, anomalÃ­as, anti-patterns"
        )
        self.version = "1.0.0"
        self.category = "analysis"
        self.risk_level = "LOW"
        self._analyzer = None

    def _get_analyzer(self):
        if self._analyzer is None:
            try:
                from src.core.fases.ml_code_analyzer import get_ml_analyzer

                self._analyzer = get_ml_analyzer()
            except Exception as e:
                logger.error(f"Failed to load MLAnalyzer: {e}")
                return None
        return self._analyzer

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import ml_code_analyzer

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - analyze_project: AnÃ¡lisis completo del proyecto
        - find_duplicates: Encontrar cÃ³digo duplicado
        """
        analyzer = self._get_analyzer()
        if not analyzer:
            return ToolResult(success=False, message="MLCodeAnalyzer no disponible")

        try:
            if action == "analyze_project":
                result = analyzer.analyze_project()
                return ToolResult(
                    success=True, message="AnÃ¡lisis ML completado", data=result
                )

            elif action == "find_duplicates":
                threshold = kwargs.get("similarity", 0.85)
                duplicates = analyzer.duplicate_detector.find_duplicates()
                return ToolResult(
                    success=True,
                    message=f"{len(duplicates)} duplicados encontrados",
                    data={
                        "count": len(duplicates),
                        "duplicates": [
                            {"func1": d[0], "func2": d[1], "similarity": d[2]}
                            for d in duplicates[:20]
                        ],
                    },
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class ConversationTool:
    """
    Tool: Conversation Engine v2 (FASE A/B)
    Motor de conversaciÃ³n avanzado
    """

    def __init__(self):
        self.name = "ConversationEngine"
        self.description = "Motor de conversaciÃ³n con intenciones y contexto"
        self.version = "2.0.0"
        self.category = "conversation"
        self.risk_level = "LOW"
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from src.core.fases.conversation_engine_v2 import (
                    get_advanced_conversation_engine,
                )

                self._engine = get_advanced_conversation_engine()
            except Exception as e:
                logger.error(f"Failed to load ConversationEngine: {e}")
                return None
        return self._engine

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import conversation_engine_v2

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - process_message: Procesar mensaje y obtener respuesta
        - get_intent: Detectar intenciÃ³n del mensaje
        """
        engine = self._get_engine()
        if not engine:
            return ToolResult(success=False, message="ConversationEngine no disponible")

        try:
            if action == "process_message":
                message = kwargs.get("message", "")
                context = kwargs.get("context", {})
                response, intent = engine.process_message(message, context)
                return ToolResult(
                    success=True,
                    message="Mensaje procesado",
                    data={
                        "response": response,
                        "intent": intent.value if intent else None,
                    },
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class PairProgrammingTool:
    """
    Tool: Pair Programming (FASE E)
    Asistente de programaciÃ³n en tiempo real
    """

    def __init__(self):
        self.name = "PairProgramming"
        self.description = (
            "Asistente de programaciÃ³n en tiempo real con autocompletado"
        )
        self.version = "1.0.0"
        self.category = "analysis"
        self.risk_level = "LOW"
        self._pair_engine = None

    def _get_engine(self):
        if self._pair_engine is None:
            try:
                from src.core.fases.pair_programming import get_pair_programming_manager

                self._pair_engine = get_pair_programming_manager()
            except Exception as e:
                logger.error(f"Failed to load PairProgramming: {e}")
                return None
        return self._pair_engine

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import pair_programming

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - start_session: Iniciar sesiÃ³n para archivo
        - get_suggestions: Obtener sugerencias en tiempo real
        - autocomplete: Obtener autocompletado
        """
        engine = self._get_engine()
        if not engine:
            return ToolResult(success=False, message="PairProgramming no disponible")

        try:
            if action == "start_session":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return ToolResult(success=False, message="file_path requerido")

                session = engine.start_session(file_path)
                return ToolResult(
                    success=True,
                    message=f"SesiÃ³n iniciada para {file_path}",
                    data={
                        "session_id": getattr(session, "session_id", "unknown"),
                        "file": file_path,
                    },
                )

            elif action == "get_suggestions":
                file_path = kwargs.get("file_path")
                if not file_path:
                    return ToolResult(success=False, message="file_path requerido")

                session = engine.get_session(file_path)
                if not session:
                    return ToolResult(
                        success=False, message="No hay sesiÃ³n activa para este archivo"
                    )

                suggestions = session.get_live_suggestions()
                return ToolResult(
                    success=True,
                    message=f"{len(suggestions)} sugerencias disponibles",
                    data={"suggestions": [str(s) for s in suggestions[:10]]},
                )

            elif action == "autocomplete":
                file_path = kwargs.get("file_path")
                prefix = kwargs.get("prefix", "")

                if not file_path:
                    return ToolResult(success=False, message="file_path requerido")

                session = engine.get_session(file_path)
                if not session:
                    return ToolResult(success=False, message="No hay sesiÃ³n activa")

                suggestions = session.get_autocomplete_suggestions(prefix)
                return ToolResult(
                    success=True,
                    message=f"{len(suggestions)} sugerencias de autocompletado",
                    data={"suggestions": suggestions},
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


class MetricsDashboardTool:
    """
    Tool: Metrics Dashboard (FASE E)
    Dashboard de mÃ©tricas y deuda tÃ©cnica
    """

    def __init__(self):
        self.name = "MetricsDashboard"
        self.description = "Dashboard de mÃ©tricas, deuda tÃ©cnica y tendencias"
        self.version = "1.0.0"
        self.category = "analysis"
        self.risk_level = "LOW"
        self._metrics = None

    def _get_metrics(self):
        if self._metrics is None:
            try:
                from src.core.fases.metrics_dashboard import get_metrics_history

                self._metrics = get_metrics_history()
            except Exception as e:
                logger.error(f"Failed to load MetricsDashboard: {e}")
                return None
        return self._metrics

    def check_dependencies(self) -> bool:
        try:
            from src.core.fases import metrics_dashboard

            return True
        except ImportError:
            return False

    def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Actions:
        - get_dashboard: Obtener dashboard completo
        - get_trends: Obtener tendencias
        - save_snapshot: Guardar snapshot actual
        """
        metrics = self._get_metrics()
        if not metrics:
            return ToolResult(success=False, message="MetricsDashboard no disponible")

        try:
            if action == "get_dashboard":
                from pathlib import Path

                project_path = kwargs.get("project_path", Path.cwd())

                data = metrics.generate_dashboard_data(Path(project_path))
                return ToolResult(success=True, message="Dashboard generado", data=data)

            elif action == "get_trends":
                from pathlib import Path

                project_path = kwargs.get("project_path", Path.cwd())
                days = kwargs.get("days", 14)

                trends = metrics.analyze_trends(Path(project_path))
                return ToolResult(
                    success=True,
                    message=f"{len(trends)} tendencias analizadas",
                    data={
                        "days": days,
                        "trends": [
                            {"metric": t.metric_name, "change": t.change_percent}
                            for t in trends
                        ],
                    },
                )

            elif action == "save_snapshot":
                from pathlib import Path

                from src.core.fases.metrics_dashboard import get_metrics_collector

                project_path = kwargs.get("project_path", Path.cwd())
                collector = get_metrics_collector(Path(project_path))

                # AquÃ­ necesitarÃ­amos analizadores, usamos datos bÃ¡sicos
                snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "note": "Snapshot manual desde CLI",
                }

                metrics.save_snapshot(Path(project_path), snapshot)

                return ToolResult(
                    success=True,
                    message="Snapshot guardado",
                    data={"timestamp": snapshot["timestamp"]},
                )

            else:
                return ToolResult(
                    success=False, message=f"AcciÃ³n '{action}' no soportada"
                )

        except Exception as e:
            return ToolResult(success=False, message=f"Error: {str(e)}")


def register_all_fases_tools(registry):
    """
    Registra todas las tools de Fases A-E en el ToolRegistry

    Args:
        registry: Instancia de ToolRegistry
    """
    tools = [
        SecurityScannerTool(),
        CodeReviewTool(),
        TestGeneratorTool(),
        AutoDocumenterTool(),
        SmartCommitTool(),
        MLAnalyzerTool(),
        ConversationTool(),
        PairProgrammingTool(),
        MetricsDashboardTool(),
    ]

    registered = 0
    for tool in tools:
        if tool.check_dependencies():
            # Registrar en el sistema IPC
            from src.core.tool_registry import ToolCategory, ToolMetadata, ToolRisk

            category_map = {
                "security": ToolCategory.CODE_ANALYSIS,
                "code_quality": ToolCategory.CODE_ANALYSIS,
                "testing": ToolCategory.CODE_ANALYSIS,
                "documentation": ToolCategory.FILE_MANAGEMENT,
                "git": ToolCategory.VERSION_CONTROL,
                "analysis": ToolCategory.CODE_ANALYSIS,
                "conversation": ToolCategory.UNKNOWN,
            }

            risk_map = {
                "LOW": ToolRisk.LOW,
                "MEDIUM": ToolRisk.MEDIUM,
                "HIGH": ToolRisk.HIGH,
            }

            metadata = ToolMetadata(
                name=tool.name,
                category=category_map.get(tool.category, ToolCategory.UNKNOWN),
                description=tool.description,
                long_description=tool.description,
                risk_level=risk_map.get(tool.risk_level, ToolRisk.LOW),
            )

            registry.register_tool(tool.name, tool, metadata)
            registered += 1
            logger.info(f"Registered Fases tool: {tool.name}")
        else:
            logger.warning(f"Could not register {tool.name}: dependencies missing")

    return registered
