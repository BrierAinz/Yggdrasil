#!/usr/bin/env python3
"""Test de búsqueda en MuninnDB docs vault."""
import asyncio
import sys
from pathlib import Path


# Paths para imports
sys.path.insert(0, str(Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend")))
sys.path.insert(0, str(Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend/core")))

from muninn_memory import MuninnMemory


async def test_search():
    print("[TEST] Buscando en vault 'docs'...\n")

    muninn = MuninnMemory(
        base_path=Path("D:/Proyectos/Yggdrasil/Asgard/Lilith"),
        vault_name="docs"
    )

    queries = [
        "DAG Executor",
        "sistema de memoria",
        "MuninnDB"
    ]

    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 50)

        results = await muninn.activate(query, vault="docs", max_results=3)

        print(f"  Resultados: {len(results)}\n")

        for i, r in enumerate(results, 1):
            concept = r.get('concept', 'N/A')
            content = r.get('content', '')[:120]
            score = r.get('score', 0)
            print(f"  {i}. {concept}")
            print(f"     Score: {score:.3f}")
            print(f"     {content}...")
            print()

        print()


if __name__ == "__main__":
    asyncio.run(test_search())
