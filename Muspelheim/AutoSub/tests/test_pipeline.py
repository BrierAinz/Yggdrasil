"""Tests for autosub.pipeline module."""

import pytest
from autosub.pipeline import Pipeline, PipelineResult


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_pipeline_result_fields(self):
        result = PipelineResult(
            input_path="/test/video.mp4",
            segments_count=10,
            output_path="/test/video.srt",
            format="srt",
            translated=False,
        )
        assert result.input_path == "/test/video.mp4"
        assert result.segments_count == 10
        assert result.format == "srt"
        assert result.translated is False

    def test_pipeline_result_with_translation(self):
        result = PipelineResult(
            input_path="/test/video.mp4",
            segments_count=10,
            output_path="/test/video.es.srt",
            format="srt",
            translated=True,
            target_lang="es",
        )
        assert result.translated is True
        assert result.target_lang == "es"


class TestPipelineInit:
    """Tests for Pipeline initialization."""

    def test_pipeline_init_defaults(self):
        p = Pipeline()
        assert p.model_size == "base"

    def test_pipeline_init_custom(self):
        p = Pipeline(model_size="large-v3", device="cuda")
        assert p.model_size == "large-v3"
        assert p.device == "cuda"

    def test_pipeline_missing_file_raises(self):
        p = Pipeline()
        with pytest.raises(FileNotFoundError):
            p.run("/nonexistent/file.wav")
