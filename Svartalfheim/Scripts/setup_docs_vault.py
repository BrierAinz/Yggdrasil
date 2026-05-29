<<<<<<< HEAD
#!/usr/bin/env python3
"""
Setup del vault "docs" en MuninnDB para el Archivero.
Si el vault no existe, usa "default" y muestra instrucciones.
"""
import json
import httpx
import sys
from pathlib import Path

# Configuración
MUNINN_URL = "http://127.0.0.1:8475/api"
KB_ROOT = Path("D:/Proyectos/Yggdrasil/Svartalfheim/Knowledge_Base")
VAULT_NAME = "docs"
FALLBACK_VAULT = "default"

def load_token():
    """Carga token de Muninn desde config."""
    config_path = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/muninn.json")
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
            token = cfg.get("muninn_token") or cfg.get("token") or ""
            return token.strip()
    return ""

def check_vault_exists(token: str, vault_name: str):
    """Verifica si un vault existe."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{MUNINN_URL}/engrams?vault={vault_name}&limit=1", headers=headers)
            return response.status_code == 200
    except:
        return False

def index_documents(token: str, vault_name: str):
    """Indexa documentos markdown al vault."""
    print(f"\n[Indexando] Documentos al vault '{vault_name}'...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    md_files = list(KB_ROOT.rglob("*.md"))
    print(f"  Encontrados {len(md_files)} documentos")
    if not md_files:
        print("  [ERROR] No se encontraron documentos markdown")
        return 0
    
    total_chunks = 0
    with httpx.Client(timeout=30.0) as client:
        for i, md_file in enumerate(md_files, 1):
            try:
                content = md_file.read_text(encoding='utf-8')
                chunks = content.split('\n### ')
                doc_chunks = 0
                for j, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    payload = {
                        "vault": vault_name,
                        "concept": f"{md_file.name}:section_{j}",
                        "content": chunk[:2000],
                        "tags": [f"doc:{md_file.name}", "type:documentation"]
                    }
                    response = client.post(f"{MUNINN_URL}/engrams", headers=headers, json=payload)
                    if response.status_code in (200, 201):
                        total_chunks += 1
                        doc_chunks += 1
                if i % 10 == 0 or i == len(md_files):
                    print(f"  [{i}/{len(md_files)}] {md_file.name} -> {doc_chunks} chunks")
            except Exception as e:
                print(f"  [ERROR] {md_file.name}: {e}")
    
    print(f"\n  [OK] Total indexado: {total_chunks} chunks desde {len(md_files)} docs")
    return total_chunks

def verify_index(token: str, vault_name: str):
    """Verifica que el índice funciona."""
    print(f"\n[Verificando] Query de prueba en vault '{vault_name}'...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MUNINN_URL}/activate",
                headers=headers,
                json={"vault": vault_name, "context": ["DAG Executor"], "max_results": 3}
            )
            if response.status_code == 200:
                data = response.json()
                activations = data.get("activations", [])
                print(f"  [OK] Query test OK - {len(activations)} resultados")
                if activations:
                    print("\n  Resultados:")
                    for i, act in enumerate(activations[:3], 1):
                        print(f"    {i}. {act.get('concept', 'N/A')[:50]}...")
                return True
            else:
                print(f"  [ERROR] HTTP {response.status_code}: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    print("=" * 60)
    print("SETUP VAULT 'docs' PARA ARCHIVERO")
    print("=" * 60)
    print()
    
    token = load_token()
    if token:
        print(f"[OK] Token: {token[:10]}...{token[-4:]}")
    else:
        print("[WARN] Sin token, intentando sin autenticacion...")
    
    print()
    
    # Verificar vault "docs"
    print("[1/3] Verificando vault 'docs'...")
    if check_vault_exists(token, VAULT_NAME):
        print(f"  [OK] Vault '{VAULT_NAME}' existe y es accesible")
        target_vault = VAULT_NAME
    else:
        print(f"  [WARN] Vault '{VAULT_NAME}' no existe o no es accesible")
        print(f"  [INFO] Intentando con vault '{FALLBACK_VAULT}'...")
        if check_vault_exists(token, FALLBACK_VAULT):
            print(f"  [OK] Usando vault '{FALLBACK_VAULT}'")
            target_vault = FALLBACK_VAULT
        else:
            print(f"  [ERROR] Ningun vault disponible")
            sys.exit(1)
    
    # Indexar documentos
    chunks = index_documents(token, target_vault)
    if chunks == 0:
        print("\n[WARN] No se indexo ningun chunk")
    
    # Verificar
    verify_index(token, target_vault)
    
    print()
    print("=" * 60)
    print("SETUP COMPLETO")
    print("=" * 60)
    print()
    print(f"Vault usado: {target_vault}")
    print(f"Chunks indexados: {chunks}")
    print()
    print("El Archivero deberia funcionar ahora.")
    print("Prueba: /docs ¿Que es el DAG Executor?")
    print()

if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
"""
Setup del vault "docs" en MuninnDB para el Archivero.
Si el vault no existe, usa "default" y muestra instrucciones.
"""

import json
import sys
from pathlib import Path

import httpx


# Configuración
YGG_ROOT = Path(__file__).resolve().parents[2]
MUNINN_URL = "http://127.0.0.1:8475/api"
KB_ROOT = YGG_ROOT / "Svartalfheim" / "Knowledge_Base"
VAULT_NAME = "docs"
FALLBACK_VAULT = "default"


def load_token():
    """Carga token de Muninn desde config."""
    config_path = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
    if config_path.exists():
        with config_path.open() as f:
            cfg = json.load(f)
            token = cfg.get("muninn_token") or cfg.get("token") or ""
            return token.strip()
    return ""


def check_vault_exists(token: str, vault_name: str):
    """Verifica si un vault existe."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{MUNINN_URL}/engrams?vault={vault_name}&limit=1", headers=headers
            )
            return response.status_code == 200
    except Exception:
        return False


def index_documents(token: str, vault_name: str):
    """Indexa documentos markdown al vault."""
    print(f"\n[Indexando] Documentos al vault '{vault_name}'...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    md_files = list(KB_ROOT.rglob("*.md"))
    print(f"  Encontrados {len(md_files)} documentos")
    if not md_files:
        print("  [ERROR] No se encontraron documentos markdown")
        return 0

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
                        "vault": vault_name,
                        "concept": f"{md_file.name}:section_{j}",
                        "content": chunk[:2000],
                        "tags": [f"doc:{md_file.name}", "type:documentation"],
                    }
                    response = client.post(f"{MUNINN_URL}/engrams", headers=headers, json=payload)
                    if response.status_code in (200, 201):
                        total_chunks += 1
                        doc_chunks += 1
                if i % 10 == 0 or i == len(md_files):
                    print(f"  [{i}/{len(md_files)}] {md_file.name} -> {doc_chunks} chunks")
            except Exception as e:
                print(f"  [ERROR] {md_file.name}: {e}")

    print(f"\n  [OK] Total indexado: {total_chunks} chunks desde {len(md_files)} docs")
    return total_chunks


def verify_index(token: str, vault_name: str):
    """Verifica que el índice funciona."""
    print(f"\n[Verificando] Query de prueba en vault '{vault_name}'...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{MUNINN_URL}/activate",
                headers=headers,
                json={"vault": vault_name, "context": ["DAG Executor"], "max_results": 3},
            )
            if response.status_code == 200:
                data = response.json()
                activations = data.get("activations", [])
                print(f"  [OK] Query test OK - {len(activations)} resultados")
                if activations:
                    print("\n  Resultados:")
                    for i, act in enumerate(activations[:3], 1):
                        print(f"    {i}. {act.get('concept', 'N/A')[:50]}...")
                return True
            else:
                print(f"  [ERROR] HTTP {response.status_code}: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    print("=" * 60)
    print("SETUP VAULT 'docs' PARA ARCHIVERO")
    print("=" * 60)
    print()

    token = load_token()
    if token:
        print(f"[OK] Token: {token[:10]}...{token[-4:]}")
    else:
        print("[WARN] Sin token, intentando sin autenticacion...")

    print()

    # Verificar vault "docs"
    print("[1/3] Verificando vault 'docs'...")
    if check_vault_exists(token, VAULT_NAME):
        print(f"  [OK] Vault '{VAULT_NAME}' existe y es accesible")
        target_vault = VAULT_NAME
    else:
        print(f"  [WARN] Vault '{VAULT_NAME}' no existe o no es accesible")
        print(f"  [INFO] Intentando con vault '{FALLBACK_VAULT}'...")
        if check_vault_exists(token, FALLBACK_VAULT):
            print(f"  [OK] Usando vault '{FALLBACK_VAULT}'")
            target_vault = FALLBACK_VAULT
        else:
            print("  [ERROR] Ningun vault disponible")
            sys.exit(1)

    # Indexar documentos
    chunks = index_documents(token, target_vault)
    if chunks == 0:
        print("\n[WARN] No se indexo ningun chunk")

    # Verificar
    verify_index(token, target_vault)

    print()
    print("=" * 60)
    print("SETUP COMPLETO")
    print("=" * 60)
    print()
    print(f"Vault usado: {target_vault}")
    print(f"Chunks indexados: {chunks}")
    print()
    print("El Archivero deberia funcionar ahora.")
    print("Prueba: /docs ¿Que es el DAG Executor?")
    print()


if __name__ == "__main__":
    main()
>>>>>>> origin/main
