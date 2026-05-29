<<<<<<< HEAD
#!/usr/bin/env python3
"""
Script para migrar del vault 'default' al vault 'docs' cuando esté configurado.

Pasos:
1. Crear vault 'docs' en MuninnDB UI
2. Copiar el token del vault
3. Actualizar Core/Config/muninn.json con el token
4. Ejecutar este script para reindexar
"""
import json
import shutil
from pathlib import Path

CONFIG_PATH = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/muninn.json")
VAULT_CONFIG = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/muninn_docs_vault.json")

INDEXER_SCRIPT = Path("D:/Proyectos/Yggdrasil/Svartalfheim/Scripts/index_docs_to_muninn.py")
AGENT_SCRIPT = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend/core/agents/archivero_agent.py")
API_SCRIPT = Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend/api/docs_api.py")


def update_config():
    """Actualiza muninn.json con la config del vault docs."""
    if not CONFIG_PATH.exists():
        print(f"[ERROR] No se encontró {CONFIG_PATH}")
        return False
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Añadir vault_tokens si no existe
    if "vault_tokens" not in config:
        config["vault_tokens"] = {}
    
    # Aquí el usuario debe haber puesto el token real
    if config["vault_tokens"].get("docs", "").startswith("mk_"):
        print("[INFO] Token de vault 'docs' encontrado en config")
        return True
    else:
        print("[WARNING] No se encontró token para vault 'docs'")
        print(f"[INFO] Añade el token a {CONFIG_PATH}:")
        print('  "vault_tokens": {')
        print('    "docs": "mk_tu_token_aqui"')
        print('  }')
        return False


def update_scripts():
    """Actualiza scripts para usar vault 'docs'."""
    
    # 1. Indexador
    with open(INDEXER_SCRIPT, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace(
        'VAULT_NAME = "default"  # Fallback',
        'VAULT_NAME = "docs"  # Vault oficial del Archivero'
    )
    
    with open(INDEXER_SCRIPT, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Actualizado: {INDEXER_SCRIPT}")
    
    # 2. API
    with open(API_SCRIPT, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace(
        'VAULT_NAME = "default"  # Cambiar a "docs"',
        'VAULT_NAME = "docs"  # Vault oficial'
    )
    
    with open(API_SCRIPT, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Actualizado: {API_SCRIPT}")
    
    # 3. Test HTTP
    test_script = Path("D:/Proyectos/Yggdrasil/Svartalfheim/Scripts/test_search_http.py")
    if test_script.exists():
        with open(test_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace(
            '"vault": "default",  # cambiar a "docs"',
            '"vault": "docs",  # Vault oficial'
        )
        
        with open(test_script, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] Actualizado: {test_script}")


def main():
    print("=" * 60)
    print("MIGRACIÓN: default -> docs vault")
    print("=" * 60)
    print()
    
    if not update_config():
        print()
        print("[ABORTADO] Configura el token primero")
        return
    
    print()
    confirm = input("¿Actualizar scripts para usar vault 'docs'? (s/N): ")
    
    if confirm.lower() == 's':
        update_scripts()
        print()
        print("[OK] Scripts actualizados")
        print()
        print("Próximos pasos:")
        print("1. Reindexar documentos: python Scripts/index_docs_to_muninn.py")
        print("2. Probar búsqueda: python Scripts/test_search_http.py")
    else:
        print("[CANCELADO]")


if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
"""
Script para migrar del vault 'default' al vault 'docs' cuando esté configurado.

Pasos:
1. Crear vault 'docs' en MuninnDB UI
2. Copiar el token del vault
3. Actualizar Core/Config/muninn.json con el token
4. Ejecutar este script para reindexar
"""

import json
from pathlib import Path


YGG_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn.json"
VAULT_CONFIG = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Config" / "muninn_docs_vault.json"

INDEXER_SCRIPT = YGG_ROOT / "Svartalfheim" / "Scripts" / "index_docs_to_muninn.py"
AGENT_SCRIPT = (
    YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Backend" / "core" / "agents" / "archivero_agent.py"
)
API_SCRIPT = YGG_ROOT / "Asgard" / "Lilith" / "Core" / "Backend" / "api" / "docs_api.py"


def update_config():
    """Actualiza muninn.json con la config del vault docs."""
    if not CONFIG_PATH.exists():
        print(f"[ERROR] No se encontró {CONFIG_PATH}")
        return False

    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)

    # Añadir vault_tokens si no existe
    if "vault_tokens" not in config:
        config["vault_tokens"] = {}

    # Aquí el usuario debe haber puesto el token real
    if config["vault_tokens"].get("docs", "").startswith("mk_"):
        print("[INFO] Token de vault 'docs' encontrado en config")
        return True
    else:
        print("[WARNING] No se encontró token para vault 'docs'")
        print(f"[INFO] Añade el token a {CONFIG_PATH}:")
        print('  "vault_tokens": {')
        print('    "docs": "mk_tu_token_aqui"')
        print("  }")
        return False


def update_scripts():
    """Actualiza scripts para usar vault 'docs'."""

    # 1. Indexador
    content = INDEXER_SCRIPT.read_text(encoding="utf-8")
    content = content.replace(
        'VAULT_NAME = "default"  # Fallback',
        'VAULT_NAME = "docs"  # Vault oficial del Archivero',
    )
    INDEXER_SCRIPT.write_text(content, encoding="utf-8")
    print(f"[OK] Actualizado: {INDEXER_SCRIPT}")

    # 2. API
    content = API_SCRIPT.read_text(encoding="utf-8")
    content = content.replace(
        'VAULT_NAME = "default"  # Cambiar a "docs"',
        'VAULT_NAME = "docs"  # Vault oficial',
    )
    API_SCRIPT.write_text(content, encoding="utf-8")
    print(f"[OK] Actualizado: {API_SCRIPT}")

    # 3. Test HTTP
    test_script = YGG_ROOT / "Svartalfheim" / "Scripts" / "test_search_http.py"
    if test_script.exists():
        content = test_script.read_text(encoding="utf-8")
        content = content.replace(
            '"vault": "default",  # cambiar a "docs"',
            '"vault": "docs",  # Vault oficial',
        )
        test_script.write_text(content, encoding="utf-8")
        print(f"[OK] Actualizado: {test_script}")


def main():
    print("=" * 60)
    print("MIGRACIÓN: default -> docs vault")
    print("=" * 60)
    print()

    if not update_config():
        print()
        print("[ABORTADO] Configura el token primero")
        return

    print()
    confirm = input("¿Actualizar scripts para usar vault 'docs'? (s/N): ")

    if confirm.lower() == "s":
        update_scripts()
        print()
        print("[OK] Scripts actualizados")
        print()
        print("Próximos pasos:")
        print("1. Reindexar documentos: python Scripts/index_docs_to_muninn.py")
        print("2. Probar búsqueda: python Scripts/test_search_http.py")
    else:
        print("[CANCELADO]")


if __name__ == "__main__":
    main()
>>>>>>> origin/main
