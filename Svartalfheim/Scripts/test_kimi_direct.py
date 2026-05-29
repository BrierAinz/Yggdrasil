<<<<<<< HEAD
#!/usr/bin/env python3
"""Test directo de Kimi API para diagnosticar error 401."""
import os
import sys
import requests

# Cargar desde secrets.env
env_path = "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/secrets.env"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val

API_KEY = os.environ.get("KIMI_API_KEY", "")

print("=" * 60)
print("DIAGNÓSTICO KIMI API")
print("=" * 60)
print()

# 1. Verificar que tenemos API key
if not API_KEY:
    print("[ERROR] KIMI_API_KEY no encontrada")
    print(f"        Buscada en: {env_path}")
    sys.exit(1)

print(f"[OK] API Key encontrada: {API_KEY[:15]}...{API_KEY[-8:]}")
print(f"     Longitud: {len(API_KEY)} caracteres")
print()

# 2. Test endpoint de modelos (health check)
print("[Test 1] GET /v1/models...")
url = "https://api.kimi.com/coding/v1/models"
headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"         Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        models = data.get('data', [])
        print(f"         [OK] {len(models)} modelos disponibles")
        for m in models[:3]:
            print(f"              - {m.get('id', 'N/A')}")
    else:
        print(f"         [ERROR] {resp.text[:200]}")
except Exception as e:
    print(f"         [ERROR] {e}")

print()

# 3. Test chat completion simple
print("[Test 2] POST /v1/messages...")
url = "https://api.kimi.com/coding/v1/messages"
payload = {
    "model": "kimi-for-coding",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hola, responde 'OK' si funcionas."}]
}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"         Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        content = data.get('content', [])
        text = ""
        if isinstance(content, list):
            text = "".join(b.get('text', '') for b in content if b.get('type') == 'text')
        elif isinstance(content, str):
            text = content
        print(f"         [OK] Respuesta: {text[:100]}")
    else:
        print(f"         [ERROR] HTTP {resp.status_code}")
        try:
            err = resp.json()
            print(f"                 {err}")
        except:
            print(f"                 {resp.text[:200]}")
except Exception as e:
    print(f"         [ERROR] {e}")

print()
print("=" * 60)
=======
#!/usr/bin/env python3
"""Test directo de Kimi API para diagnosticar error 401."""

import os
import sys
from pathlib import Path

import requests


# Cargar desde secrets.env
YGG_ROOT = Path(__file__).resolve().parents[2]
env_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "secrets.env"
if env_path.exists():
    with env_path.open() as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

API_KEY = os.environ.get("KIMI_API_KEY", "")

print("=" * 60)
print("DIAGNÓSTICO KIMI API")
print("=" * 60)
print()

# 1. Verificar que tenemos API key
if not API_KEY:
    print("[ERROR] KIMI_API_KEY no encontrada")
    print(f"        Buscada en: {env_path}")
    sys.exit(1)

print(f"[OK] API Key encontrada: {API_KEY[:15]}...{API_KEY[-8:]}")
print(f"     Longitud: {len(API_KEY)} caracteres")
print()

# 2. Test endpoint de modelos (health check)
print("[Test 1] GET /v1/models...")
url = "https://api.kimi.com/coding/v1/models"
headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"         Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        models = data.get("data", [])
        print(f"         [OK] {len(models)} modelos disponibles")
        for m in models[:3]:
            print(f"              - {m.get('id', 'N/A')}")
    else:
        print(f"         [ERROR] {resp.text[:200]}")
except Exception as e:
    print(f"         [ERROR] {e}")

print()

# 3. Test chat completion simple
print("[Test 2] POST /v1/messages...")
url = "https://api.kimi.com/coding/v1/messages"
payload = {
    "model": "kimi-for-coding",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hola, responde 'OK' si funcionas."}],
}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"         Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        content = data.get("content", [])
        text = ""
        if isinstance(content, list):
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        elif isinstance(content, str):
            text = content
        print(f"         [OK] Respuesta: {text[:100]}")
    else:
        print(f"         [ERROR] HTTP {resp.status_code}")
        try:
            err = resp.json()
            print(f"                 {err}")
        except Exception:
            print(f"                 {resp.text[:200]}")
except Exception as e:
    print(f"         [ERROR] {e}")

print()
print("=" * 60)
>>>>>>> origin/main
