"""SQLite database for YggdrasilForge — generations and assets history."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from backend.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    prompt TEXT,
    input_image TEXT,
    result_object TEXT,
    result_path TEXT,
    error TEXT,
    provider_job_id TEXT,
    provider_data TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    source_id TEXT,
    file_path TEXT,
    thumbnail TEXT,
    tags TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gen_status ON generations(status);
CREATE INDEX IF NOT EXISTS idx_gen_provider ON generations(provider);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generations(created_at);
CREATE INDEX IF NOT EXISTS idx_asset_provider ON assets(provider);
CREATE INDEX IF NOT EXISTS idx_asset_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_asset_created ON assets(created_at);
"""

_db_connection: aiosqlite.Connection | None = None


async def init_db(db_path: str | None = None) -> None:
    """Initialize the database, creating tables if needed."""
    global _db_connection
    path = db_path or settings.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _db_connection = await aiosqlite.connect(path)
    _db_connection.row_factory = aiosqlite.Row
    await _db_connection.executescript(SCHEMA)
    await _db_connection.commit()


async def get_db() -> aiosqlite.Connection:
    """Get the database connection. Must call init_db() first."""
    if _db_connection is None:
        await init_db()
    return _db_connection  # type: ignore


async def close_db() -> None:
    """Close the database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None


# ── Generation CRUD ──────────────────────────────────────────────────────


async def create_generation(
    id: str,
    type: str,
    provider: str,
    prompt: str | None = None,
    input_image: str | None = None,
    provider_job_id: str | None = None,
    provider_data: dict | None = None,
) -> None:
    """Insert a new generation record."""
    db = await get_db()
    await db.execute(
        """INSERT INTO generations (id, type, provider, status, prompt, input_image,
           provider_job_id, provider_data, created_at)
           VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?)""",
        (
            id,
            type,
            provider,
            prompt,
            input_image,
            provider_job_id,
            json.dumps(provider_data) if provider_data else None,
            datetime.now(UTC).isoformat(),
        ),
    )
    await db.commit()


async def update_generation(
    id: str,
    status: str | None = None,
    result_object: str | None = None,
    result_path: str | None = None,
    error: str | None = None,
    provider_job_id: str | None = None,
    provider_data: dict | None = None,
) -> None:
    """Update a generation record."""
    db = await get_db()
    sets: list[str] = []
    vals: list[Any] = []
    if status is not None:
        sets.append("status = ?")
        vals.append(status)
    if result_object is not None:
        sets.append("result_object = ?")
        vals.append(result_object)
    if result_path is not None:
        sets.append("result_path = ?")
        vals.append(result_path)
    if error is not None:
        sets.append("error = ?")
        vals.append(error)
    if provider_job_id is not None:
        sets.append("provider_job_id = ?")
        vals.append(provider_job_id)
    if provider_data is not None:
        sets.append("provider_data = ?")
        vals.append(json.dumps(provider_data))
    if status in ("completed", "failed"):
        sets.append("completed_at = ?")
        vals.append(datetime.now(UTC).isoformat())
    if sets:
        vals.append(id)
        await db.execute(f"UPDATE generations SET {', '.join(sets)} WHERE id = ?", vals)
        await db.commit()


async def get_generation(id: str) -> dict | None:
    """Get a single generation by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM generations WHERE id = ?", (id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("provider_data"):
        d["provider_data"] = json.loads(d["provider_data"])
    return d


async def list_generations(
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List generations with optional filters. Returns (items, total)."""
    db = await get_db()
    where_clauses = []
    params: list[Any] = []
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if provider:
        where_clauses.append("provider = ?")
        params.append(provider)
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_cursor = await db.execute(f"SELECT COUNT(*) FROM generations {where}", params)
    total = (await count_cursor.fetchone())[0]

    cursor = await db.execute(
        f"SELECT * FROM generations {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    rows = await cursor.fetchall()
    items = []
    for row in rows:
        d = dict(row)
        if d.get("provider_data"):
            d["provider_data"] = json.loads(d["provider_data"])
        items.append(d)
    return items, total


# ── Asset CRUD ────────────────────────────────────────────────────────────


async def create_asset(
    id: str,
    name: str,
    provider: str,
    asset_type: str,
    source_id: str | None = None,
    file_path: str | None = None,
    thumbnail: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> None:
    """Insert a new asset record."""
    db = await get_db()
    await db.execute(
        """INSERT INTO assets (id, name, provider, asset_type, source_id, file_path,
           thumbnail, tags, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            id,
            name,
            provider,
            asset_type,
            source_id,
            file_path,
            thumbnail,
            json.dumps(tags) if tags else None,
            json.dumps(metadata) if metadata else None,
            datetime.now(UTC).isoformat(),
        ),
    )
    await db.commit()


async def get_asset(id: str) -> dict | None:
    """Get a single asset by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM assets WHERE id = ?", (id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    for key in ("tags", "metadata"):
        if d.get(key) and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d


async def list_assets(
    provider: str | None = None,
    asset_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List assets with optional filters. Returns (items, total)."""
    db = await get_db()
    where_clauses = []
    params: list[Any] = []
    if provider:
        where_clauses.append("provider = ?")
        params.append(provider)
    if asset_type:
        where_clauses.append("asset_type = ?")
        params.append(asset_type)
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_cursor = await db.execute(f"SELECT COUNT(*) FROM assets {where}", params)
    total = (await count_cursor.fetchone())[0]

    cursor = await db.execute(
        f"SELECT * FROM assets {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    rows = await cursor.fetchall()
    items = []
    for row in rows:
        d = dict(row)
        for key in ("tags", "metadata"):
            if d.get(key) and isinstance(d[key], str):
                d[key] = json.loads(d[key])
        items.append(d)
    return items, total
