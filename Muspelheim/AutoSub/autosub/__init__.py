"""AutoSub — Automatic subtitle generator with translation."""

__version__ = "0.1.0"

from autosub.aligner import Aligner, Word
from autosub.batch import BatchProcessor
from autosub.config import AutoSubConfig
from autosub.exporter import export_segments
from autosub.pipeline import Pipeline, PipelineResult
from autosub.transcriber import LanguageInfo, Segment, Transcriber
from autosub.translator import Translator

__all__ = [
    "Aligner",
    "AutoSubConfig",
    "BatchProcessor",
    "LanguageInfo",
    "Pipeline",
    "PipelineResult",
    "Segment",
    "Transcriber",
    "Translator",
    "Word",
    "export_segments",
]
