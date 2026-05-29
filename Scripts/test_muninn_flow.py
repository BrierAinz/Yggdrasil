#!/usr/bin/env python3
"""Test exacto del flujo de MuninnMemory."""

import json
from pathlib import Path


# Replicar exactamente lo que hace MuninnMemory
base_path = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core")
config_path = base_path / "Config" / "muninn.json"

print("=" * 60)
print("TEST FLUJO MUNINNMEMORY")
print("=" * 60)
print()

# Leer config igual que MuninnMemory
with open(config_path) as f:
    cfg = json.load(f)

print(f"[Config] URL: {cfg.get('url')}")
print(f"[Config] Token global: {cfg.get('token', 'NO')[:20]}...")
print()

# Vault tokens
vault_tokens = cfg.get("vault_tokens", {})
print(f"[Vault Tokens] Keys: {list(vault_tokens.keys())}")
print(f"[Vault Tokens] docs: {vault_tokens.get('docs', 'NO ENCONTRADO')[:30]}...")
print()

# Simular flujo de ArchiveroAgent
token_docs = vault_tokens.get("docs", "")
print(f"[Test] Token para vault 'docs': {token_docs[:30]}...")
print(f"[Test] Longitud: {len(token_docs)}")
print()

# Test request con este token exacto
import urllib.request


req = urllib.request.Request(
    "http://127.0.0.1:8475/api/activate",
    data=json.dumps({"vault": "docs", "context": ["DAG Executor"], "max_results": 3}).encode(),
    headers={"Authorization": f"Bearer {token_docs}", "Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        activations = data.get("activations", [])
        print(f"[OK] Resultados: {len(activations)}")
        for a in activations[:3]:
            print(f"  - {a.get('concept', 'N/A')}")
except urllib.error.HTTPError as e:
    print(f"[ERROR] HTTP {e.code}: {e.reason}")
    print(f"Body: {e.read().decode()}")
except Exception as e:
    print(f"[ERROR] {e}")
