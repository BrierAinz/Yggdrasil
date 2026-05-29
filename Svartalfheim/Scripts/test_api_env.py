#!/usr/bin/env python3
"""Test si el API puede ver las variables de entorno."""
import urllib.request
import json

req = urllib.request.Request('http://localhost:8000/api/status')
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read().decode())
        print("Status:", result)
except Exception as e:
    print(f"Error: {e}")

# Test custom endpoint to check env
req = urllib.request.Request('http://localhost:8000/api/debug/env')
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read().decode())
        print("Env:", result)
except Exception as e:
    print(f"Debug endpoint not found (expected): {e}")
