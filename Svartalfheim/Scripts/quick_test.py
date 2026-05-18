#!/usr/bin/env python3
"""Tests rápidos del sistema sin auto-mode."""
import json
import sys
import urllib.request


def test_endpoint(name, url, method='GET', data=None, timeout=10):
    """Test un endpoint."""
    try:
        if data:
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method=method)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}

print("=" * 60)
print("TESTS RÁPIDOS DEL SISTEMA")
print("=" * 60)
print()

# Test 1: Backend status
print("[1/5] Backend /api/status...")
result = test_endpoint("status", "http://localhost:8000/api/status")
if 'error' not in result:
    print(f"   [OK] Online - v{result.get('version', '?')} - Tools: {result.get('tools_registered', 0)}")
else:
    print(f"   [ERROR] {result['error']}")

# Test 2: Docs query
print("\n[2/5] RAG /api/docs/query...")
data = json.dumps({'question': 'DAG Executor', 'context': ''}).encode()
result = test_endpoint("docs", "http://localhost:8000/api/docs/query", method='POST', data=data, timeout=30)
if 'error' not in result and result.get('sources'):
    print(f"   [OK] RAG funciona - Fuentes: {len(result['sources'])}, Conf: {result.get('confidence', 0):.0%}")
else:
    print(f"   ❌ {result.get('error', 'Sin resultados')}")

# Test 3: Tools registry
print("\n[3/5] Tools registry...")
result = test_endpoint("tools", "http://localhost:8000/api/tools")
if 'error' not in result:
    print(f"   [OK] {result.get('count', 0)} tools disponibles")
else:
    print(f"   [ERROR] {result['error']}")

# Test 4: Vault stats
print("\n[4/5] Docs vault stats...")
result = test_endpoint("vault", "http://localhost:8000/api/docs/stats")
if 'error' not in result:
    print(f"   [OK] Vault '{result.get('vault', '?')}': {result.get('chunks', 0)} chunks")
else:
    print(f"   [ERROR] {result['error']}")

# Test 5: Health extended
print("\n[5/5] Health extended...")
result = test_endpoint("health", "http://localhost:8000/api/health/full")
if 'error' not in result:
    overall = result.get('overall', 'unknown')
    status_emoji = "[OK]" if overall == "healthy" else "[WARN]"
    print(f"   {status_emoji} Overall: {overall}")
else:
    print(f"   [WARN] {result['error']}")

print()
print("=" * 60)
print("Tests completados")
print("=" * 60)
