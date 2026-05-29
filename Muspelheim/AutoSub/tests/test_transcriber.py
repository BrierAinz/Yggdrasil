"""Tests for autosub.transcriber module."""

import pytest

from autosub.transcriber import LanguageInfo, Segment, Transcriber


class TestSegment:
    """Tests for the Segment dataclass."""

    def test_segment_fields(self):
        s = Segment(text="hello world", start=0.0, end=2.5)
        assert s.text == "hello world"
        assert s.start == 0.0
        assert s.end == 2.5

    def test_segment_str(self):
        s = Segment(text="hello", start=1.0, end=3.0)
        result = str(s)
        assert "hello" in result
        assert "1.00" in result
        assert "3.00" in result


class TestLanguageInfo:
    """Tests for the LanguageInfo dataclass."""

    def test_language_info_fields(self):
        li = LanguageInfo(language="es", language_probability=0.95)
        assert li.language == "es"
        assert li.language_probability == 0.95

    def test_language_info_english(self):
        li = LanguageInfo(language="en", language_probability=0.88)
        assert li.language == "en"


class TestTranscriber:
    """Tests for the Transcriber class."""

    def test_transcriber_init_defaults(self):
        t = Transcriber()
        assert t.model_size == "base"
        assert t.device == "auto"
        assert t.compute_type == "int8"

    def test_transcriber_init_custom(self):
        t = Transcriber(model_size="tiny", device="cpu", compute_type="float16")
        assert t.model_size == "tiny"
        assert t.device == "cpu"
        assert t.compute_type == "float16"

    def test_transcriber_model_size_attribute(self):
        t = Transcriber(model_size="tiny")
        assert t.model_size == "tiny"

    def test_transcriber_invalid_path_raises(self):
        t = Transcriber(model_size="tiny")
        with pytest.raises(FileNotFoundError):
            t.transcribe("/nonexistent/file.wav")

    def test_detect_language_invalid_path_raises(self):
        t = Transcriber(model_size="tiny")
        with pytest.raises(FileNotFoundError):
            t.detect_language("/nonexistent/file.wav")

    def test_has_gpu_returns_bool(self):
        result = Transcriber._has_gpu()
        assert isinstance(result, bool)

    def test_model_none_initially(self):
        t = Transcriber(model_size="tiny")
        assert t._model is None
