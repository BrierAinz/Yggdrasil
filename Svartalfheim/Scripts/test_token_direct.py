#!/usr/bin/env python3
"""Test token directo de muninn.json."""
import urllib.request
import json

# Token exacto del archivo muninn.json
TOKEN = "mk_GOTOOZRB5dWooMIZ2A8Mg_pdBpIRloo8Xzca6Oqyd-s"
MUNINN_URL = "http://127.0.0.1:8475/api"

def test_token():
    """Test query con token específico."""
    print(f"Probando token: {TOKEN[:20]}...")
    print()
    
    req = urllib.request.Request(
        f'{MUNINN_URL}/activate',
        data=json.dumps({
            'vault': 'docs',
            'context': ['DAG Executor'],
            'max_results': 3
        }).encode(),
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            activations = data.get('activations', [])
            print(f"[OK] Resultados: {len(activations)}")
            for a in activations[:3]:
                print(f"  - {a.get('concept', 'N/A')}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}")
        print(f"Body: {e.read().decode()}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_token()
