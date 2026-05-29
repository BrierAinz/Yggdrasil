#!/usr/bin/env python3
"""Test ArchiveroAgent directamente."""
<<<<<<< HEAD
import sys
import asyncio
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend")))

from Backend.core.agents.archivero_agent import ArchiveroAgent
=======

import asyncio
import sys
from pathlib import Path


# Add Backend to path (legacy monolith)
_YGG_ROOT = Path(__file__).resolve().parents[2]  # Svartalfheim/Scripts/ → Yggdrasil root
sys.path.insert(0, str(_YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Backend"))

# NOTE: ArchiveroAgent is archived — see Helheim/Hermes-Lilith_v4_legacy/
from Backend.core.agents.archivero_agent import ArchiveroAgent

>>>>>>> origin/main

async def test():
    """Test query al Archivero."""
    print("=" * 60)
    print("TEST ARCHIVERO AGENT")
    print("=" * 60)
    print()
<<<<<<< HEAD
    
    agent = ArchiveroAgent()
    print(f"[OK] Agente creado")
    print(f"  - Vault: {agent.muninn_docs.vault_name}")
    print(f"  - Top K: {agent.top_k}")
    print()
    
=======

    agent = ArchiveroAgent()
    print("[OK] Agente creado")
    print(f"  - Vault: {agent.muninn_docs.vault_name}")
    print(f"  - Top K: {agent.top_k}")
    print()

>>>>>>> origin/main
    # Test retrieve chunks directo
    print("[Test] _retrieve_chunks('DAG Executor')...")
    results = await agent._retrieve_chunks("DAG Executor")
    print(f"  Resultados: {len(results)}")
    for r in results:
        print(f"    - {r.get('concept', 'N/A')}")
    print()
<<<<<<< HEAD
    
=======

>>>>>>> origin/main
    # Test query completa
    print("[Test] query_with_metadata()...")
    result = await agent.query_with_metadata("¿Qué es el DAG Executor?")
    print(f"  Respuesta: {result['answer'][:200]}...")
    print(f"  Fuentes: {result['sources']}")
    print(f"  Confianza: {result['confidence']}")

<<<<<<< HEAD
=======

>>>>>>> origin/main
if __name__ == "__main__":
    asyncio.run(test())
