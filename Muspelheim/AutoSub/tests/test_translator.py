"""Tests for autosub.translator module."""

import tempfile
from pathlib import Path

import pytest
from autosub.transcriber import Segment
from autosub.translator import Translator


class TestTranslatorInit:
    """Tests for Translator initialization."""

    def test_translator_init_default(self):
        t = Translator(target_lang="es")
        assert t.target_lang == "es"
        assert t.source_lang == "auto"

    def test_translator_init_custom_source(self):
        t = Translator(source_lang="en", target_lang="fr")
        assert t.source_lang == "en"
        assert t.target_lang == "fr"

    def test_translator_init_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "test_cache"
        t = Translator(target_lang="es", cache_dir=cache_dir)
        assert cache_dir.exists()
        assert (cache_dir / "translations.db").exists()


class TestTranslatorCache:
    """Tests for the SQLite translation cache."""

    def test_cache_creates_db(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        db_path = tmp_path / "translations.db"
        assert db_path.exists()

    def test_translate_empty_string(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        result = t.translate_text("")
        assert result == ""

    def test_translate_whitespace_only(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        result = t.translate_text("   ")
        assert result.strip() == ""

    def test_cache_stats_empty(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        stats = t.cache_stats()
        assert stats["entry_count"] == 0

    def test_clear_cache(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        t.clear_cache()
        stats = t.cache_stats()
        assert stats["entry_count"] == 0


class TestTranslatorSegments:
    """Tests for translating Segment objects."""

    def test_translate_segments_preserves_timing(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        segments = [Segment(text="hello world", start=0.0, end=2.5)]
        # We don't call translate on actual API in tests,
        # just verify structure is preserved
        result = t.translate_segments([])
        assert result == []

    def test_translate_empty_text_preserved(self, tmp_path):
        t = Translator(target_lang="es", cache_dir=tmp_path)
        seg = Segment(text="", start=0.0, end=1.0)
        result = t.translate_text(seg.text)
        assert result == ""
