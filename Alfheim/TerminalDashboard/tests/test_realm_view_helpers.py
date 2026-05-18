"""Tests for realm view helper functions.

Tests _count_files, _total_size, _format_size, _find_key_files.
"""

from __future__ import annotations

from pathlib import Path

from tui.widgets.realm_views import (
    _count_files,
    _find_key_files,
    _format_size,
    _total_size,
)


class TestCountFiles:
    """Tests for _count_files helper."""

    def test_count_files_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns 0."""
        assert _count_files(tmp_path) == 0

    def test_count_files_with_files(self, tmp_path: Path) -> None:
        """Count files in directory."""
        (tmp_path / "file1.py").write_text("x")
        (tmp_path / "file2.py").write_text("x")
        assert _count_files(tmp_path) == 2

    def test_count_files_nested(self, tmp_path: Path) -> None:
        """Count files in nested directories."""
        subdir = tmp_path / "src"
        subdir.mkdir()
        (tmp_path / "root.py").write_text("x")
        (subdir / "nested.py").write_text("x")
        assert _count_files(tmp_path) == 2

    def test_count_files_excludes_hidden_dirs(self, tmp_path: Path) -> None:
        """Files inside hidden directories should be excluded."""
        hidden_dir = tmp_path / ".git"
        hidden_dir.mkdir()
        (hidden_dir / "config").write_text("x")
        (tmp_path / "visible.py").write_text("x")
        assert _count_files(tmp_path) == 1

    def test_count_files_nonexistent_dir(self) -> None:
        """Non-existent directory returns 0."""
        assert _count_files(Path("/nonexistent/path")) == 0

    def test_count_files_excludes_pycache(self, tmp_path: Path) -> None:
        """Files inside __pycache__ should be excluded."""
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.pyc").write_text("x")
        (tmp_path / "module.py").write_text("x")
        assert _count_files(tmp_path) == 1


class TestTotalSize:
    """Tests for _total_size helper."""

    def test_total_size_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns 0."""
        assert _total_size(tmp_path) == 0

    def test_total_size_with_files(self, tmp_path: Path) -> None:
        """Calculate total size of files."""
        (tmp_path / "file1.py").write_text("a" * 100)
        (tmp_path / "file2.py").write_text("b" * 200)
        total = _total_size(tmp_path)
        assert total >= 300

    def test_total_size_nonexistent_dir(self) -> None:
        """Non-existent directory returns 0."""
        assert _total_size(Path("/nonexistent/path")) == 0

    def test_total_size_excludes_hidden(self, tmp_path: Path) -> None:
        """Files in hidden directories excluded from size."""
        hidden_dir = tmp_path / ".git"
        hidden_dir.mkdir()
        (hidden_dir / "config").write_text("x" * 1000)
        (tmp_path / "visible.py").write_text("x" * 10)
        total = _total_size(tmp_path)
        assert total <= 100  # Only the visible file (~10 bytes)


class TestFormatSize:
    """Tests for _format_size helper."""

    def test_bytes(self) -> None:
        assert _format_size(500) == "500 B"

    def test_kilobytes(self) -> None:
        result = _format_size(1500)
        assert "KB" in result

    def test_megabytes(self) -> None:
        result = _format_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self) -> None:
        result = _format_size(3 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_zero(self) -> None:
        assert _format_size(0) == "0 B"


class TestFindKeyFiles:
    """Tests for _find_key_files helper."""

    def test_find_key_files_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns empty list."""
        assert _find_key_files(tmp_path) == []

    def test_find_key_files_with_readme(self, tmp_path: Path) -> None:
        """Directory with README.md returns it."""
        (tmp_path / "README.md").write_text("# Project")
        result = _find_key_files(tmp_path)
        assert "README.md" in result

    def test_find_key_files_multiple(self, tmp_path: Path) -> None:
        """Directory with multiple key files."""
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "REGLAS.md").write_text("# Rules")
        result = _find_key_files(tmp_path)
        assert "README.md" in result
        assert "pyproject.toml" in result
        assert "REGLAS.md" in result

    def test_find_key_files_no_match(self, tmp_path: Path) -> None:
        """Directory with non-key files returns empty."""
        (tmp_path / "main.py").write_text("print('hello')")
        assert _find_key_files(tmp_path) == []

    def test_find_key_files_nonexistent_dir(self) -> None:
        """Non-existent directory returns empty list."""
        assert _find_key_files(Path("/nonexistent/path")) == []
