#!/usr/bin/env python3
"""Listar vaults disponibles en MuninnDB."""
import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8475/api/vaults',
    headers={'Authorization': 'Bearer mk_RkQ48F_eI4D2uEVJq9RoCdJXBIp7TYSgrK3O5Ua4XXw'}
)

try:
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        print('Vaults disponibles:')
        vaults = data if isinstance(data, list) else data.get('vaults', [])
        for vault in vaults:
            print(f"  - {vault}")
except Exception as e:
    print(f'Error: {e}')
