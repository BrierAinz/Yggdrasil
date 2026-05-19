#!/usr/bin/env python3
"""
Reindexa documentos al vault "docs" recién creado.
"""

import json
import sys
from pathlib import Path

import httpx


YGG_ROOT = Path(__file__).resolve().parents[2]

MUNINN_URL = "http://127.0.0.1:8475/api"
KB_ROOT = YGG_ROOT / "Svartalfheim" / "Knowledge_Base"
VAULT_NAME = "docs"


def get_docs_token():
    """Carga token del vault docs."""
    config_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
    with config_path.open() as f:
        cfg = json.load(f)
        return cfg.get("vault_tokens", {}).get("docs", "")


def main():
    print("=" * 60)
    print("REINDEXANDO DOCUMENTOS AL VAULT 'docs'")
    print("=" * 60)
    print()

    token = get_docs_token()
    if not token:
        print("[ERROR] No se encontro token para vault 'docs'")
        sys.exit(1)

    print(f"[OK] Token cargado: {token[:15]}...{token[-8:]}")
    print()

    # Buscar documentos
    md_files = list(KB_ROOT.rglob("*.md"))
    print(f"[INFO] Encontrados {len(md_files)} documentos")
    print()

    headers = {"Authorization": f"Bearer {token}"}
    total_chunks = 0

    with httpx.Client(timeout=30.0) as client:
        for i, md_file in enumerate(md_files, 1):
            try:
                content = md_file.read_text(encoding="utf-8")
                chunks = content.split("\n### ")
                doc_chunks = 0

                for j, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue

                    payload = {
                        "vault": VAULT_NAME,
                        "concept": f"{md_file.name}:section_{j}",
                        "content": chunk[:2000],
                        "tags": [f"doc:{md_file.name}", "type:documentation"],
                    }

                    response = client.post(
                        f"{MUNINN_URL}/engrams",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code in (200, 201):
                        total_chunks += 1
                        doc_chunks += 1

                if i % 10 == 0 or i == len(md_files):
                    print(f"  [{i}/{len(md_files)}] {md_file.name} -> {doc_chunks} chunks")

            except Exception as e:
                print(f"  [ERROR] {md_file.name}: {e}")

    print()
    print(f"[OK] Total indexado: {total_chunks} chunks")
    print()

    # Verificar
    print("[Verificando] Query de prueba...")
    response = client.post(
        f"{MUNINN_URL}/activate",
        headers=headers,
        json={"vault": VAULT_NAME, "context": ["DAG Executor"], "max_results": 3},
    )

    if response.status_code == 200:
        data = response.json()
        activations = data.get("activations", [])
        print(f"  [OK] {len(activations)} resultados encontrados")
    else:
        print(f"  [ERROR] HTTP {response.status_code}")

    print()
    print("=" * 60)
    print("REINDEXACION COMPLETA")
    print("=" * 60)
    print()
    print("El Archivero ahora usa el vault 'docs' dedicado.")
    print("Reinicia el backend para aplicar cambios.")


if __name__ == "__main__":
    main()
