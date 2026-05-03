"""SQLite catalog for persistent model storage."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path

    from forgemaster.scanner import ModelInfo


@dataclass
class GPUProfile:
    """GPU profile for VRAM tracking."""

    id: int | None = None
    name: str = ""
    vram_total_gb: float = 0.0
    vram_available_gb: float = 0.0


# SQL for creating tables
_CREATE_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    size_bytes INTEGER DEFAULT 0,
    format TEXT DEFAULT '',
    architecture TEXT DEFAULT '',
    parameters INTEGER,
    context_length INTEGER,
    quantization TEXT,
    vram_required_gb REAL,
    download_date TEXT,
    source TEXT,
    tags TEXT DEFAULT '{}',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
)
"""

_CREATE_GPU_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS gpu_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    vram_total_gb REAL NOT NULL,
    vram_available_gb REAL NOT NULL
)
"""

_CREATE_MODELS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)
"""

_CREATE_MODELS_FORMAT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_models_format ON models(format)
"""

_CREATE_MODELS_ARCH_INDEX = """
CREATE INDEX IF NOT EXISTS idx_models_architecture ON models(architecture)
"""


class Catalog:
    """SQLite-based catalog for model metadata and GPU profiles."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        """Initialize catalog with SQLite database.

        Args:
            db_path: Path to SQLite database file. Use ':memory:' for in-memory DB.
        """
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection to the database."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._create_tables()
        return self._conn

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute(_CREATE_MODELS_TABLE)
        cursor.execute(_CREATE_GPU_PROFILES_TABLE)
        cursor.execute(_CREATE_MODELS_INDEX)
        cursor.execute(_CREATE_MODELS_FORMAT_INDEX)
        cursor.execute(_CREATE_MODELS_ARCH_INDEX)
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def add_model(self, model: ModelInfo, tags: dict | None = None, notes: str = "") -> int:
        """Add a model to the catalog.

        Args:
            model: ModelInfo to add.
            tags: Optional dict of tags.
            notes: Optional notes.

        Returns:
            The ID of the inserted model.
        """
        tags_json = json.dumps(tags or {})
        now = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO models
                (name, path, size_bytes, format, architecture, parameters,
                 context_length, quantization, vram_required_gb, download_date,
                 source, tags, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model.name,
                model.path,
                model.size_bytes,
                model.format,
                model.architecture,
                model.parameters,
                model.context_length,
                model.quantization,
                model.vram_required_gb,
                model.download_date,
                model.source,
                tags_json,
                notes,
                now,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def get_model(self, model_id: int) -> dict[str, Any] | None:
        """Get a model by ID.

        Args:
            model_id: The ID of the model.

        Returns:
            Dict with model data, or None if not found.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models WHERE id = ?", (model_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        result["tags"] = json.loads(result.get("tags", "{}"))
        return result

    def list_models(
        self,
        format: str | None = None,
        architecture: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List models with optional filtering.

        Args:
            format: Filter by model format (gguf, safetensors, etc.)
            architecture: Filter by architecture (llama, etc.)
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of model dicts.
        """
        query = "SELECT * FROM models WHERE 1=1"
        params: list[Any] = []

        if format:
            query += " AND format = ?"
            params.append(format)
        if architecture:
            query += " AND architecture = ?"
            params.append(architecture)

        query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["tags"] = json.loads(result.get("tags", "{}"))
            results.append(result)
        return results

    def search_models(self, query: str) -> list[dict[str, Any]]:
        """Search models by name, architecture, or path.

        Args:
            query: Search string.

        Returns:
            List of matching model dicts.
        """
        search_term = f"%{query}%"
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM models
            WHERE name LIKE ? OR architecture LIKE ? OR path LIKE ?
            ORDER BY name
            """,
            (search_term, search_term, search_term),
        )
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["tags"] = json.loads(result.get("tags", "{}"))
            results.append(result)
        return results

    def delete_model(self, model_id: int) -> bool:
        """Delete a model from the catalog.

        Args:
            model_id: The ID of the model to delete.

        Returns:
            True if a model was deleted, False otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_gpu_profile(self, profile: GPUProfile) -> int:
        """Add a GPU profile to the catalog.

        Args:
            profile: GPUProfile to add.

        Returns:
            The ID of the inserted profile.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO gpu_profiles (name, vram_total_gb, vram_available_gb)
            VALUES (?, ?, ?)
            """,
            (profile.name, profile.vram_total_gb, profile.vram_available_gb),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def get_gpu_profiles(self) -> list[GPUProfile]:
        """Get all GPU profiles.

        Returns:
            List of GPUProfile objects.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM gpu_profiles ORDER BY name")
        profiles = []
        for row in cursor.fetchall():
            profiles.append(
                GPUProfile(
                    id=row["id"],
                    name=row["name"],
                    vram_total_gb=row["vram_total_gb"],
                    vram_available_gb=row["vram_available_gb"],
                )
            )
        return profiles

    def count_models(self) -> int:
        """Count total number of models in the catalog."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM models")
        result = cursor.fetchone()
        return int(result[0]) if result else 0

    def total_size_bytes(self) -> int:
        """Get total size of all models in the catalog."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM models")
        result = cursor.fetchone()
        return int(result[0]) if result else 0
