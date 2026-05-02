"""AutoSub translation module — multi-language translation with SQLite cache."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from deep_translator import GoogleTranslator


class Translator:
    """Translate text with caching in SQLite to avoid redundant API calls."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "es",
        cache_dir: Path | None = None,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.cache_dir = (
            Path(cache_dir) if cache_dir else Path.home() / ".cache" / "autosub"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.cache_dir / "translations.db"
        self._init_db()

    def _init_db(self) -> None:
        """Create the translation cache table if it doesn't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_lang, target_lang, source_text)
                )
                """
            )
            conn.commit()

    def _lookup_cache(self, text: str) -> str | None:
        """Check if a translation exists in cache."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT translated_text FROM translations WHERE source_lang=? AND target_lang=? AND source_text=?",
                (self.source_lang, self.target_lang, text),
            ).fetchone()
            return row[0] if row else None

    def _store_cache(self, text: str, translated: str) -> None:
        """Store a translation in cache."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO translations (source_lang, target_lang, source_text, translated_text) VALUES (?, ?, ?, ?)",
                (self.source_lang, self.target_lang, text, translated),
            )
            conn.commit()

    def translate_text(self, text: str) -> str:
        """Translate a single text string.

        Uses cache first, falls back to Google Translate.

        Args:
            text: Source text to translate.

        Returns:
            Translated text string.
        """
        if not text.strip():
            return text

        # Check cache
        cached = self._lookup_cache(text)
        if cached is not None:
            return cached

        # Translate
        translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
        result = translator.translate(text)

        if result is None:
            return text

        # Store in cache
        self._store_cache(text, result)
        return result

    def translate_segments(self, segments: list) -> list:
        """Translate a list of Segment objects.

        Args:
            segments: List of Segment objects with .text attribute.

        Returns:
            New list of Segment objects with translated text.
        """
        from autosub.transcriber import Segment

        translated = []
        for seg in segments:
            translated_text = self.translate_text(seg.text)
            translated.append(
                Segment(text=translated_text, start=seg.start, end=seg.end)
            )
        return translated

    def clear_cache(self) -> None:
        """Clear all cached translations."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM translations")
            conn.commit()

    def cache_stats(self) -> dict:
        """Return cache statistics."""
        with sqlite3.connect(self._db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
            size_bytes = self._db_path.stat().st_size if self._db_path.exists() else 0
        return {"entry_count": count, "db_size_bytes": size_bytes}
