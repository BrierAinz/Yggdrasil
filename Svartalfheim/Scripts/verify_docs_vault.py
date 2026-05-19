#!/usr/bin/env python3
"""
Verifica que el vault "docs" funcione correctamente.
"""

import json
from pathlib import Path

import httpx


YGG_ROOT = Path(__file__).resolve().parents[2]

MUNINN_URL = "http://127.0.0.1:8475/api"
VAULT_NAME = "docs"


def get_docs_token():
    config_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
    with config_path.open() as f:
        cfg = json.load(f)
        return cfg.get("vault_tokens", {}).get("docs", "")


def main():
    print("=" * 60)
    print("VERIFICACION DEL VAULT 'docs'")
    print("=" * 60)
    print()

    token = get_docs_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Test query
    queries = [
        "DAG Executor",
        "sistema de memoria",
        "MuninnDB",
    ]

    with httpx.Client(timeout=10.0) as client:
        for query in queries:
            print(f"Query: '{query}'")
            response = client.post(
                f"{MUNINN_URL}/activate",
                headers=headers,
                json={"vault": VAULT_NAME, "context": [query], "max_results": 3},
            )

            if response.status_code == 200:
                data = response.json()
                activations = data.get("activations", [])
                print(f"  [OK] {len(activations)} resultados")
                for i, act in enumerate(activations[:2], 1):
                    print(f"    {i}. {act.get('concept', 'N/A')[:40]}...")
            else:
                print(f"  [ERROR] HTTP {response.status_code}")
            print()

    print("=" * 60)
    print("Verificacion completa")
    print("=" * 60)


if __name__ == "__main__":
    main()
