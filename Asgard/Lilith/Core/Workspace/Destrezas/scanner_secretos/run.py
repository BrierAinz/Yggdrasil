"""
Skill: scanner_secretos
Escanea el proyecto buscando API keys, passwords y secretos hardcodeados.
No necesita LLM - usa patrones regex.
"""
import glob
import os
import re
import sys
import time

skill_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(skill_dir))
project_root = os.path.dirname(workspace_root)

# Patterns to detect secrets
SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([^"\']{10,})["\']', "API Key", "ALTO"),
    (r'(?:password|passwd|pwd)\s*[=:]\s*["\']([^"\']{4,})["\']', "Password", "CRITICO"),
    (r'(?:secret|token)\s*[=:]\s*["\']([^"\']{10,})["\']', "Secret/Token", "ALTO"),
    (r'(?:aws_access_key_id)\s*[=:]\s*["\']?(AKIA[A-Z0-9]{16})', "AWS Key", "CRITICO"),
    (r"Bearer\s+([A-Za-z0-9_-]{20,})", "Bearer Token", "ALTO"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI Key", "CRITICO"),
    (r"AIzaSy[A-Za-z0-9_-]{33}", "Google API Key", "ALTO"),
    (r"xai-[A-Za-z0-9]{40,}", "Grok API Key", "ALTO"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Token", "CRITICO"),
]

IGNORE_DIRS = {".venv", "node_modules", "__pycache__", ".git", ".crush", "venv"}
SCAN_EXTENSIONS = {
    ".py",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".html",
}
# Files where secrets ARE expected
SAFE_FILES = {"secrets.env", ".env", "secrets.json"}


def ejecutar(directorio: str = "") -> str:
    """Escanea buscando secretos expuestos."""
    scan_root = os.path.join(project_root, directorio) if directorio else project_root

    if not os.path.exists(scan_root):
        return f"ERROR: Directorio no encontrado: {scan_root}"

    findings = []
    files_scanned = 0

    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext not in SCAN_EXTENSIONS:
                continue
            if fname in SAFE_FILES:
                continue

            filepath = os.path.join(root, fname)
            files_scanned += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pattern, name, severity in SECRET_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        rel_path = os.path.relpath(filepath, project_root)
                        secret_preview = (
                            match.group(0)[:20] + "..."
                            if len(match.group(0)) > 20
                            else match.group(0)
                        )
                        findings.append(
                            {
                                "file": rel_path,
                                "line": line_num,
                                "type": name,
                                "severity": severity,
                                "preview": secret_preview,
                            }
                        )
            except:
                pass

    # Build report
    reporte = [f"# Scan de Secretos"]
    reporte.append(f"*Escaneado el {time.strftime('%Y-%m-%d %H:%M')}*")
    reporte.append(f"*Directorio: {directorio or 'proyecto completo'}*")
    reporte.append(f"*Archivos escaneados: {files_scanned}*\n")

    if not findings:
        reporte.append("## Resultado: LIMPIO")
        reporte.append("No se encontraron secretos expuestos en el codigo.")
    else:
        reporte.append(f"## ALERTA: {len(findings)} secretos encontrados!\n")
        criticos = [f for f in findings if f["severity"] == "CRITICO"]
        altos = [f for f in findings if f["severity"] == "ALTO"]

        if criticos:
            reporte.append("### CRITICOS")
            for f in criticos:
                reporte.append(
                    f"- **{f['type']}** en `{f['file']}` linea {f['line']}: `{f['preview']}`"
                )

        if altos:
            reporte.append("\n### ALTOS")
            for f in altos:
                reporte.append(
                    f"- **{f['type']}** en `{f['file']}` linea {f['line']}: `{f['preview']}`"
                )

    # Save report
    output = os.path.join(
        workspace_root, "Taller", f"scan_secretos_{time.strftime('%Y%m%d')}.md"
    )
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(reporte))

    return "\n".join(reporte)


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else ""
    print(ejecutar(d))
