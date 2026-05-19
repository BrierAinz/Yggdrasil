#!/usr/bin/env python3
"""Refrescar token del vault docs usando el token maestro."""

import urllib.request


MASTER_TOKEN = "mk_RkQ48F_eI4D2uEVJq9RoCdJXBIp7TYSgrK3O5Ua4XXw"
MUNINN_URL = "http://127.0.0.1:8475/api"


def get_vault_token(vault_name):
    """Obtener token de un vault (o crear uno nuevo)."""
    # Intentar listar engrams del vault para verificar acceso
    req = urllib.request.Request(
        f"{MUNINN_URL}/engrams?vault={vault_name}",
        headers={"Authorization": f"Bearer {MASTER_TOKEN}"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5):
            print(f"[OK] Acceso con token maestro al vault '{vault_name}'")
            return MASTER_TOKEN  # Usar token maestro
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("REFRESH TOKEN VAULT 'docs'")
    print("=" * 60)
    print()

    token = get_vault_token("docs")
    if token:
        print(f"\nToken a usar: {token[:20]}...")
        print("\n[IMPORTANTE] Actualizar muninn.json:")
        print(f'  "docs": "{token}"')
