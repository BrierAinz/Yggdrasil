#!/usr/bin/env python3
"""Test ArchiveroAgent directamente."""

import asyncio
import sys
from pathlib import Path


# Add Backend to path
sys.path.insert(0, str(Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend")))

from Backend.core.agents.archivero_agent import ArchiveroAgent


async def test():
    """Test query al Archivero."""
    print("=" * 60)
    print("TEST ARCHIVERO AGENT")
    print("=" * 60)
    print()

    agent = ArchiveroAgent()
    print("[OK] Agente creado")
    print(f"  - Vault: {agent.muninn_docs.vault_name}")
    print(f"  - Top K: {agent.top_k}")
    print()

    # Test retrieve chunks directo
    print("[Test] _retrieve_chunks('DAG Executor')...")
    results = await agent._retrieve_chunks("DAG Executor")
    print(f"  Resultados: {len(results)}")
    for r in results:
        print(f"    - {r.get('concept', 'N/A')}")
    print()

    # Test query completa
    print("[Test] query_with_metadata()...")
    result = await agent.query_with_metadata("¿Qué es el DAG Executor?")
    print(f"  Respuesta: {result['answer'][:200]}...")
    print(f"  Fuentes: {result['sources']}")
    print(f"  Confianza: {result['confidence']}")


if __name__ == "__main__":
    asyncio.run(test())
