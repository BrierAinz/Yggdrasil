#!/usr/bin/env python3
"""Test de búsqueda en MuninnDB via HTTP directo."""

import asyncio
import json
from pathlib import Path

import httpx


MUNINN_URL = "http://127.0.0.1:8475/api"

# Cargar token
YGG_ROOT = Path(__file__).resolve().parents[2]
config_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
token = ""
if config_path.exists():
    with config_path.open() as f:
        cfg = json.load(f)
        token = (cfg.get("muninn_token") or cfg.get("token") or "").strip()

headers = {}
if token:
    headers["Authorization"] = f"Bearer {token}"


async def search(query: str, limit: int = 3):
    """Busca en vault docs."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Usar vault "default" (cambiar a "docs" cuando esté configurado)
        payload = {
            "vault": "default",
            "context": [query],
            "max_results": limit,
        }
        r = await client.post(f"{MUNINN_URL}/activate", json=payload, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return data.get("activations", [])
        return []


async def main():
    print("[TEST] Buscando en vault 'docs' via HTTP\n")

    queries = [
        "DAG Executor",
        "sistema de memoria",
        "MuninnDB",
    ]

    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 60)

        results = await search(query, limit=3)

        print(f"  Resultados: {len(results)}\n")

        for i, r in enumerate(results, 1):
            concept = r.get("concept", "N/A")
            content = r.get("content", "")[:150]
            score = r.get("score", 0)
            why = r.get("why", {})
            print(f"  {i}. {concept}")
            print(
                f"     Score: {score:.3f} (bm25: {why.get('bm25', 0):.2f}, hebbian: {why.get('hebbian', 0):.2f})"
            )
            print(f"     {content[:100]}...")
            print()

        print()


if __name__ == "__main__":
    asyncio.run(main())
