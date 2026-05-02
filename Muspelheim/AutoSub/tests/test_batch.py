"""Tests for autosub.batch module."""

import pytest
from autosub.batch import (
    AUDIO_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    VIDEO_EXTENSIONS,
    BatchProcessor,
)


class TestBatchProcessorInit:
    """Tests for BatchProcessor initialization."""

    def test_batch_init_defaults(self):
        bp = BatchProcessor()
        assert bp.model_size == "base"

    def test_batch_init_custom(self):
        bp = BatchProcessor(model_size="large-v3", device="cuda")
        assert bp.model_size == "large-v3"
        assert bp.device == "cuda"


class TestScanDirectory:
    """Tests for directory scanning."""

    def test_scan_empty_directory(self, tmp_path):
        bp = BatchProcessor()
        files = bp.scan_directory(str(tmp_path))
        assert files == []

    def test_scan_nonexistent_directory(self):
        bp = BatchProcessor()
        with pytest.raises(FileNotFoundError):
            bp.scan_directory("/nonexistent/directory")

    def test_scan_finds_audio_files(self, tmp_path):
        # Create dummy audio files
        (tmp_path / "test.mp3").write_bytes(b"fake audio")
        (tmp_path / "test.wav").write_bytes(b"RIFF" + b"\x00" * 100)
        (tmp_path / "readme.txt").write_text("not audio")

        bp = BatchProcessor()
        files = bp.scan_directory(str(tmp_path))
        assert len(files) == 2
        assert all(f.suffix.lower() in SUPPORTED_EXTENSIONS for f in files)

    def test_scan_finds_video_files(self, tmp_path):
        (tmp_path / "video.mp4").write_bytes(b"fake video")
        bp = BatchProcessor()
        files = bp.scan_directory(str(tmp_path))
        assert len(files) == 1

    def test_scan_not_directory(self, tmp_path):
        filepath = tmp_path / "file.txt"
        filepath.write_text("hello")
        bp = BatchProcessor()
        with pytest.raises(ValueError):
            bp.scan_directory(str(filepath))


class TestExtensions:
    """Tests for supported file extensions."""

    def test_audio_extensions_include_mp3(self):
        assert ".mp3" in AUDIO_EXTENSIONS

    def test_audio_extensions_include_wav(self):
        assert ".wav" in AUDIO_EXTENSIONS

    def test_video_extensions_include_mp4(self):
        assert ".mp4" in VIDEO_EXTENSIONS

    def test_video_extensions_include_mkv(self):
        assert ".mkv" in VIDEO_EXTENSIONS

    def test_supported_is_union(self):
        assert SUPPORTED_EXTENSIONS == AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
