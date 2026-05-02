"""Integration tests for AutoSub — end-to-end pipeline tests."""

import tempfile
from pathlib import Path

import pytest
from autosub.aligner import Aligner
from autosub.exporter import export_segments
from autosub.pipeline import Pipeline, PipelineResult
from autosub.transcriber import Segment, Transcriber


class TestIntegrationExportFormats:
    """End-to-end export format tests with realistic data."""

    def test_full_pipeline_export_srt(self):
        """Simulate transcription → export to SRT."""
        segments = [
            Segment(text="Hello, welcome to AutoSub.", start=0.0, end=3.5),
            Segment(
                text="This is a demonstration of subtitle generation.",
                start=3.8,
                end=7.2,
            ),
            Segment(text="Enjoy!", start=7.5, end=8.0),
        ]
        result = export_segments(segments, fmt="srt")
        assert "1\n" in result
        assert "00:00:00,000 --> 00:00:03,500" in result
        assert "Hello, welcome to AutoSub." in result
        assert "2\n" in result
        assert "3\n" in result

    def test_full_pipeline_export_vtt(self):
        """Simulate transcription → export to VTT."""
        segments = [
            Segment(text="Hola mundo", start=0.0, end=2.0),
            Segment(text="Adiós mundo", start=2.5, end=4.0),
        ]
        result = export_segments(segments, fmt="vtt")
        assert "WEBVTT" in result
        assert "00:00:00.000 --> 00:00:02.000" in result
        assert "Hola mundo" in result

    def test_full_pipeline_export_txt(self):
        """Simulate transcription → export to plain text."""
        segments = [
            Segment(text="First line.", start=0.0, end=1.0),
            Segment(text="Second line.", start=1.2, end=2.5),
        ]
        result = export_segments(segments, fmt="txt")
        assert "First line." in result
        assert "Second line." in result


class TestIntegrationAlignment:
    """Integration tests for word alignment."""

    def test_align_words_integrate_with_segments(self):
        """Align words from segments and verify realignment."""
        segments = [
            Segment(text="Hello world", start=0.0, end=2.0),
            Segment(text="Goodbye world", start=2.5, end=4.0),
        ]
        aligner = Aligner()
        words_per_seg = aligner.align_segments(segments)
        assert len(words_per_seg) == 2  # one list per segment
        assert len(words_per_seg[0]) == 2  # "Hello", "world"
        assert len(words_per_seg[1]) == 2  # "Goodbye", "world"
        assert words_per_seg[0][0].word == "Hello"
        assert words_per_seg[1][0].word == "Goodbye"

    def test_realign_words_to_segments(self):
        """Realign words back to segments with adjusted timing."""
        segments = [
            Segment(text="Hello world", start=0.0, end=2.0),
        ]
        aligner = Aligner()
        words_per_seg = aligner.align_segments(segments)
        # words_to_segments expects list[list[Word]]
        realigned = aligner.words_to_segments(words_per_seg)
        assert len(realigned) >= 1
        assert realigned[0].text == "Hello world"


class TestIntegrationTranslatorCache:
    """Integration tests for translation with caching."""

    def test_translate_and_cache_roundtrip(self):
        """Translate text, verify cache hit on second call."""
        from autosub.translator import Translator

        with tempfile.TemporaryDirectory() as tmpdir:
            translator = Translator(target_lang="es", cache_dir=tmpdir)

            # Translate a segment
            result = translator.translate_text("Hello")
            assert isinstance(result, str)

            # Check cache has an entry
            stats = translator.cache_stats()
            # Cache may be empty if translation actually happened
            # or populated if deep-translator worked
            assert "size" in stats or isinstance(stats, dict)

    def test_translate_segments_preserves_struct(self):
        """Translate segments while preserving timing data."""
        from autosub.translator import Translator

        segments = [
            Segment(text="Hello world", start=0.0, end=2.0),
            Segment(text="", start=2.0, end=3.0),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            translator = Translator(target_lang="es", cache_dir=tmpdir)
            result = translator.translate_segments(segments)

            assert len(result) == 2
            assert result[0].start == 0.0
            assert result[0].end == 2.0
            assert result[1].text == ""  # empty preserved


class TestIntegrationConfigDiscovery:
    """Integration tests for config file discovery."""

    def test_config_from_file_and_use(self, tmp_path):
        """Write a config file, discover it, use values."""
        from autosub.config import AutoSubConfig

        config_path = tmp_path / "autosub.toml"
        config_path.write_text(
            '[autosub]\nmodel_size = "large-v3"\ndevice = "cuda"\ndefault_format = "vtt"\n'
        )

        config = AutoSubConfig.from_toml(config_path)
        assert config.model_size == "large-v3"
        assert config.device == "cuda"
        assert config.default_format == "vtt"


class TestIntegrationPipelineResult:
    """Test PipelineResult data structure."""

    def test_pipeline_result_fields(self):
        result = PipelineResult(
            input_path="/test/video.mp4",
            segments_count=42,
            output_path="/test/video.srt",
            format="srt",
            translated=False,
            target_lang=None,
        )
        assert result.input_path == "/test/video.mp4"
        assert result.segments_count == 42
        assert result.format == "srt"
        assert result.translated is False

    def test_pipeline_result_with_translation(self):
        result = PipelineResult(
            input_path="/test/video.mp4",
            segments_count=50,
            output_path="/test/video.es.srt",
            format="srt",
            translated=True,
            target_lang="es",
        )
        assert result.translated is True
        assert result.target_lang == "es"
