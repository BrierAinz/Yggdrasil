#!/usr/bin/env python3
"""Test query directo a Muninn vault docs."""
import json
import urllib.request


MUNINN_URL = "http://127.0.0.1:8475/api"
TOKEN = "mk_GOTOOZRB5dWooMIZ2A8Mg_pdBpIRloo8Xzca6Oqyd-s"

def test_query():
    """Query directo a Muninn."""
    req = urllib.request.Request(
        f'{MUNINN_URL}/activate',
        data=json.dumps({
            'vault': 'docs',
            'context': ['DAG Executor'],
            'max_results': 5
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
            print(f"Resultados encontrados: {len(activations)}")
            for a in activations:
                concept = a.get('concept', 'N/A')
                content = a.get('content', '')[:80]
                print(f"  - {concept}: {content}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
