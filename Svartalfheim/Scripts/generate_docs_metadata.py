<<<<<<< HEAD
#!/usr/bin/env python3
"""
Script para generar metadata de documentos en Svartalfheim Knowledge Base.
Uso: python Scripts/generate_docs_metadata.py
"""
import json
import re
from pathlib import Path
from datetime import datetime

KB_ROOT = Path("D:/Proyectos/Yggdrasil/Svartalfheim/Knowledge_Base")


def extract_metadata(md_file: Path) -> dict:
    """Extrae metadata de un archivo markdown."""
    try:
        content = md_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"⚠️ Error leyendo {md_file}: {e}")
        return None
    
    lines = content.split('\n')
    metadata = {
        'filename': md_file.name,
        'path': str(md_file.relative_to(KB_ROOT)).replace('\\', '/'),
        'size_bytes': md_file.stat().st_size,
        'indexed_at': datetime.now().isoformat(),
        'title': '',
        'version': '',
        'date': '',
        'description': ''
    }
    
    # Extraer título (primer #)
    for line in lines:
        if line.startswith('# '):
            metadata['title'] = line[2:].strip()
            break
    
    # Extraer metadata del header (bloque > **X:**)
    for line in lines[:30]:  # Revisar primeras 30 líneas
        if line.startswith('> **Versión:**'):
            match = re.search(r'\*\*Versión:\*\*\s*(.+)', line)
            if match:
                metadata['version'] = match.group(1).strip()
        elif line.startswith('> **Fecha:**'):
            match = re.search(r'\*\*Fecha:\*\*\s*(.+)', line)
            if match:
                metadata['date'] = match.group(1).strip()
        elif line.startswith('> **Descripción:**'):
            match = re.search(r'\*\*Descripción:\*\*\s*(.+)', line)
            if match:
                metadata['description'] = match.group(1).strip()
    
    # Si no hay título, usar nombre de archivo
    if not metadata['title']:
        metadata['title'] = md_file.stem.replace('_', ' ')
    
    # Contar secciones (##)
    section_count = len([l for l in lines if l.startswith('## ')])
    metadata['section_count'] = section_count
    
    # Extraer primer párrafo como descripción fallback
    if not metadata['description']:
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('>') and not line.startswith('---'):
                if len(line) > 20:  # Párrafo sustancial
                    metadata['description'] = line[:200] + ('...' if len(line) > 200 else '')
                    break
    
    return metadata


def main():
    print("[INDEX] Indexando documentos en Svartalfheim Knowledge Base...\n")
    
    docs = []
    md_files = list(KB_ROOT.rglob("*.md"))
    
    print(f"[INDEX] Encontrados {len(md_files)} archivos markdown\n")
    
    for i, md_file in enumerate(md_files, 1):
        print(f"  [{i}/{len(md_files)}] {md_file.name}...", end=' ')
        meta = extract_metadata(md_file)
        if meta:
            docs.append(meta)
            print(f"OK ({meta['size_bytes']//1024}KB, {meta.get('section_count', 0)} secciones)")
        else:
            print("ERROR")
    
    # Guardar index.json
    index_path = KB_ROOT / "index.json"
    index_data = {
        'generated_at': datetime.now().isoformat(),
        'total_documents': len(docs),
        'total_size_kb': sum(d['size_bytes'] for d in docs) // 1024,
        'documents': docs
    }
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Index generado: {index_path}")
    print(f"   Total documentos: {len(docs)}")
    print(f"   Tamaño total: {index_data['total_size_kb']} KB")
    
    # Estadísticas por categoría
    lilith_docs = len([d for d in docs if 'Lilith_Docs' in d['path']])
    legacy = len([d for d in docs if 'Lilith_Legacy' in d['path']])
    print(f"\n[STATS] Desglose:")
    print(f"   Lilith_Docs (00-17): {lilith_docs}")
    print(f"   Lilith_Legacy: {legacy}")


if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
"""
Script para generar metadata de documentos en Svartalfheim Knowledge Base.
Uso: python Scripts/generate_docs_metadata.py
"""

import json
import re
from datetime import datetime
from pathlib import Path


YGG_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = YGG_ROOT / "Svartalfheim" / "Knowledge_Base"


def extract_metadata(md_file: Path) -> dict | None:
    """Extrae metadata de un archivo markdown."""
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Error leyendo {md_file}: {e}")
        return None

    lines = content.split("\n")
    metadata = {
        "filename": md_file.name,
        "path": str(md_file.relative_to(KB_ROOT)).replace("\\", "/"),
        "size_bytes": md_file.stat().st_size,
        "indexed_at": datetime.now().isoformat(),
        "title": "",
        "version": "",
        "date": "",
        "description": "",
    }

    # Extraer título (primer #)
    for line in lines:
        if line.startswith("# "):
            metadata["title"] = line[2:].strip()
            break

    # Extraer metadata del header (bloque > **X:**)
    for line in lines[:30]:  # Revisar primeras 30 líneas
        if line.startswith("> **Versión:**"):
            match = re.search(r"\*\*Versión:\*\*\s*(.+)", line)
            if match:
                metadata["version"] = match.group(1).strip()
        elif line.startswith("> **Fecha:**"):
            match = re.search(r"\*\*Fecha:\*\*\s*(.+)", line)
            if match:
                metadata["date"] = match.group(1).strip()
        elif line.startswith("> **Descripción:**"):
            match = re.search(r"\*\*Descripción:\*\*\s*(.+)", line)
            if match:
                metadata["description"] = match.group(1).strip()

    # Si no hay título, usar nombre de archivo
    if not metadata["title"]:
        metadata["title"] = md_file.stem.replace("_", " ")

    # Contar secciones (##)
    section_count = len([l for l in lines if l.startswith("## ")])
    metadata["section_count"] = section_count

    # Extraer primer párrafo como descripción fallback
    if not metadata["description"]:
        for raw_line in lines:
            stripped_line = raw_line.strip()
            if (
                stripped_line
                and not stripped_line.startswith("#")
                and not stripped_line.startswith(">")
                and not stripped_line.startswith("---")
            ):
                if len(stripped_line) > 20:  # Párrafo sustancial
                    metadata["description"] = stripped_line[:200] + (
                        "..." if len(stripped_line) > 200 else ""
                    )
                    break

    return metadata


def main():
    print("[INDEX] Indexando documentos en Svartalfheim Knowledge Base...\n")

    docs = []
    md_files = list(KB_ROOT.rglob("*.md"))

    print(f"[INDEX] Encontrados {len(md_files)} archivos markdown\n")

    for i, md_file in enumerate(md_files, 1):
        print(f"  [{i}/{len(md_files)}] {md_file.name}...", end=" ")
        meta = extract_metadata(md_file)
        if meta:
            docs.append(meta)
            print(f"OK ({meta['size_bytes'] // 1024}KB, {meta.get('section_count', 0)} secciones)")
        else:
            print("ERROR")

    # Guardar index.json
    index_path = KB_ROOT / "index.json"
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "total_documents": len(docs),
        "total_size_kb": sum(d["size_bytes"] for d in docs) // 1024,
        "documents": docs,
    }

    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Index generado: {index_path}")
    print(f"   Total documentos: {len(docs)}")
    print(f"   Tamaño total: {index_data['total_size_kb']} KB")

    # Estadísticas por categoría
    lilith_docs = len([d for d in docs if "Lilith_Docs" in d["path"]])
    legacy = len([d for d in docs if "Lilith_Legacy" in d["path"]])
    print("\n[STATS] Desglose:")
    print(f"   Lilith_Docs (00-17): {lilith_docs}")
    print(f"   Lilith_Legacy: {legacy}")


if __name__ == "__main__":
    main()
>>>>>>> origin/main
