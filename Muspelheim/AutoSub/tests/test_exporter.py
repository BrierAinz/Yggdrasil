"""Tests for autosub.exporter module."""

import pytest

from autosub.exporter import export_segments, export_srt, export_txt, export_vtt
from autosub.transcriber import Segment


# Sample segments for testing
SAMPLE_SEGMENTS = [
    Segment(text="Hello world", start=0.0, end=2.5),
    Segment(text="This is a test", start=2.5, end=5.0),
]


class TestExportSrt:
    """Tests for SRT format export."""

    def test_srt_format_single(self):
        segments = [Segment(text="Hello world", start=0.0, end=2.5)]
        result = export_srt(segments)
        assert "1\n" in result
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "Hello world" in result

    def test_srt_format_multiple(self):
        result = export_srt(SAMPLE_SEGMENTS)
        assert "1\n" in result
        assert "2\n" in result
        assert "Hello world" in result
        assert "This is a test" in result
        assert "00:00:02,500 --> 00:00:05,000" in result

    def test_srt_time_format(self):
        seg = Segment(text="test", start=3661.5, end=3662.5)
        result = export_srt([seg])
        assert "01:01:01,500" in result

    def test_srt_empty_segments(self):
        result = export_srt([])
        assert result == ""


class TestExportVtt:
    """Tests for WebVTT format export."""

    def test_vtt_format(self):
        segments = [Segment(text="Hello world", start=0.0, end=2.5)]
        result = export_vtt(segments)
        assert "WEBVTT" in result
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "Hello world" in result

    def test_vtt_no_index(self):
        result = export_vtt(SAMPLE_SEGMENTS)
        # VTT doesn't have numeric indices like SRT
        lines = result.split("\n")
        assert "WEBVTT" in lines

    def test_vtt_empty_segments(self):
        result = export_vtt([])
        assert "WEBVTT" in result


class TestExportTxt:
    """Tests for plain text export."""

    def test_txt_format(self):
        segments = [Segment(text="Hello world", start=0.0, end=2.5)]
        result = export_txt(segments)
        assert result == "Hello world"

    def test_txt_multiple(self):
        result = export_txt(SAMPLE_SEGMENTS)
        assert result == "Hello world\nThis is a test"

    def test_txt_empty(self):
        result = export_txt([])
        assert result == ""


class TestExportSegments:
    """Tests for the unified export function."""

    def test_export_srt_format(self):
        result = export_segments(SAMPLE_SEGMENTS, fmt="srt")
        assert "Hello world" in result
        assert "-->" in result

    def test_export_vtt_format(self):
        result = export_segments(SAMPLE_SEGMENTS, fmt="vtt")
        assert "WEBVTT" in result

    def test_export_txt_format(self):
        result = export_segments(SAMPLE_SEGMENTS, fmt="txt")
        assert "Hello world" in result

    def test_export_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            export_segments(SAMPLE_SEGMENTS, fmt="pdf")
