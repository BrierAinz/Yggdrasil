#!/usr/bin/env python3
"""Test usando httpx como MuninnMemory."""

import asyncio

import httpx


TOKEN = "mk_GOTOOZRB5dWooMIZ2A8Mg_pdBpIRloo8Xzca6Oqyd-s"
URL = "http://127.0.0.1:8475"


async def test():
    """Test con httpx."""
    print("=" * 60)
    print("TEST CON HTTPX (como MuninnMemory)")
    print("=" * 60)
    print()

    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(base_url=URL + "/api", headers=headers, timeout=10.0) as client:
        payload = {"vault": "docs", "context": ["DAG Executor"], "max_results": 3}

        print(f"Token: {TOKEN[:30]}...")
        print(f"Headers: {headers}")
        print()

        r = await client.post("/activate", json=payload)
        print(f"Status: {r.status_code}")

        if r.status_code == 200:
            data = r.json()
            activations = data.get("activations", [])
            print(f"[OK] Resultados: {len(activations)}")
            for a in activations[:3]:
                print(f"  - {a.get('concept', 'N/A')}")
        else:
            print(f"[ERROR] {r.text}")


if __name__ == "__main__":
    asyncio.run(test())
