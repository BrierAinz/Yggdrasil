<<<<<<< HEAD
#!/usr/bin/env python3
"""Test ArchiveroAgent con LLM."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend")
os.environ['PYTHONPATH'] = "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend"

from Backend.core.agents.archivero_agent import ArchiveroAgent

async def test():
    """Test query al Archivero con LLM."""
    print("=" * 60)
    print("TEST ARCHIVERO + LLM")
    print("=" * 60)
    print()
    
    agent = ArchiveroAgent()
    print("[OK] Agente creado")
    print()
    
    # Test query
    question = "¿Qué es el DAG Executor?"
    print(f"[Test] Pregunta: {question}")
    print()
    
    result = await agent.query_with_metadata(question)
    
    print("=" * 60)
    print("RESULTADO:")
    print("=" * 60)
    print(f"Respuesta: {result['answer'][:500]}...")
    print(f"Fuentes: {result['sources']}")
    print(f"Confianza: {result['confidence']}")

if __name__ == "__main__":
    import os
    asyncio.run(test())
=======
#!/usr/bin/env python3
"""Test ArchiveroAgent con LLM."""

import asyncio
import os
import sys
from pathlib import Path


_YGG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Backend"))
os.environ["PYTHONPATH"] = str(_YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Backend")

from Backend.core.agents.archivero_agent import ArchiveroAgent


async def test():
    """Test query al Archivero con LLM."""
    print("=" * 60)
    print("TEST ARCHIVERO + LLM")
    print("=" * 60)
    print()

    agent = ArchiveroAgent()
    print("[OK] Agente creado")
    print()

    # Test query
    question = "¿Qué es el DAG Executor?"
    print(f"[Test] Pregunta: {question}")
    print()

    result = await agent.query_with_metadata(question)

    print("=" * 60)
    print("RESULTADO:")
    print("=" * 60)
    print(f"Respuesta: {result['answer'][:500]}...")
    print(f"Fuentes: {result['sources']}")
    print(f"Confianza: {result['confidence']}")


if __name__ == "__main__":
    asyncio.run(test())
>>>>>>> origin/main
