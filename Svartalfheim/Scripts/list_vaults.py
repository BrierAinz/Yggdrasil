#!/usr/bin/env python3
"""Listar vaults disponibles en MuninnDB."""
<<<<<<< HEAD
import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8475/api/vaults',
    headers={'Authorization': 'Bearer mk_RkQ48F_eI4D2uEVJq9RoCdJXBIp7TYSgrK3O5Ua4XXw'}
=======

import json
import urllib.request


req = urllib.request.Request(
    "http://127.0.0.1:8475/api/vaults",
    headers={"Authorization": "Bearer mk_RkQ48F_eI4D2uEVJq9RoCdJXBIp7TYSgrK3O5Ua4XXw"},
>>>>>>> origin/main
)

try:
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
<<<<<<< HEAD
        print('Vaults disponibles:')
        vaults = data if isinstance(data, list) else data.get('vaults', [])
        for vault in vaults:
            print(f"  - {vault}")
except Exception as e:
    print(f'Error: {e}')
=======
        print("Vaults disponibles:")
        vaults = data if isinstance(data, list) else data.get("vaults", [])
        for vault in vaults:
            print(f"  - {vault}")
except Exception as e:
    print(f"Error: {e}")
>>>>>>> origin/main
