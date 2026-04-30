"""
Fases A-E Integration Module
Integra los mÃ³dulos de Fases A-E con el sistema de Tools IPC
"""

from .fases_tools import (
    AutoDocumenterTool,
    CodeReviewTool,
    ConversationTool,
    MetricsDashboardTool,
    MLAnalyzerTool,
    PairProgrammingTool,
    SecurityScannerTool,
    SmartCommitTool,
    TestGeneratorTool,
    register_all_fases_tools,
)

__all__ = [
    "SecurityScannerTool",
    "CodeReviewTool",
    "TestGeneratorTool",
    "AutoDocumenterTool",
    "SmartCommitTool",
    "MLAnalyzerTool",
    "ConversationTool",
    "PairProgrammingTool",
    "MetricsDashboardTool",
    "register_all_fases_tools",
]
