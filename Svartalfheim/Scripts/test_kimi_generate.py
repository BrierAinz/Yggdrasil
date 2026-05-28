#!/usr/bin/env python3
"""Test KimiClient.generate_text directamente."""
import sys
import os

# Cargar secrets
env_path = "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/secrets.env"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val

sys.path.insert(0, "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend")

from Backend.llm.kimi_client import KimiClient

print("=" * 60)
print("TEST KimiClient.generate_text()")
print("=" * 60)
print()

client = KimiClient()
print(f"[OK] Cliente creado")
print(f"     API Key presente: {'Sí' if client.api_key else 'No'}")
print()

# Test generate_text
system_prompt = "Eres un asistente útil. Responde de forma concisa."
prompt = "¿Qué es el DAG Executor en 2 oraciones?"

print("[Test] Generando texto...")
print(f"       Prompt: {prompt[:50]}...")
print()

response = client.generate_text(
    prompt=prompt,
    system_prompt=system_prompt,
    max_tokens=200
)

print("=" * 60)
print("RESPUESTA:")
print("=" * 60)
print(response if response else "[VACÍA]")
print()

if not response:
    print("[ERROR] La respuesta está vacía!")
else:
    print(f"[OK] Longitud: {len(response)} caracteres")
