#!/usr/bin/env python3
"""Test si el API puede ver las variables de entorno."""
<<<<<<< HEAD
import urllib.request
import json

req = urllib.request.Request('http://localhost:8000/api/status')
=======

import json
import urllib.request


req = urllib.request.Request("http://localhost:8000/api/status")
>>>>>>> origin/main
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read().decode())
        print("Status:", result)
except Exception as e:
    print(f"Error: {e}")

# Test custom endpoint to check env
<<<<<<< HEAD
req = urllib.request.Request('http://localhost:8000/api/debug/env')
=======
req = urllib.request.Request("http://localhost:8000/api/debug/env")
>>>>>>> origin/main
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        result = json.loads(r.read().decode())
        print("Env:", result)
except Exception as e:
    print(f"Debug endpoint not found (expected): {e}")
