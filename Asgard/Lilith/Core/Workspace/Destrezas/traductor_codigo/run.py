"""
Skill: traductor_codigo
Convierte codigo entre lenguajes de programacion manteniendo la logica.
"""
import os
import sys
import time

skill_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(skill_dir))
project_root = os.path.dirname(workspace_root)
sys.path.insert(0, project_root)

secrets_path = os.path.join(project_root, "Config", "secrets.env")
if os.path.exists(secrets_path):
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

EXTENSIONES = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "csharp": ".cs",
    "rust": ".rs",
    "go": ".go",
    "lua": ".lua",
    "gdscript": ".gd",
    "cpp": ".cpp",
    "java": ".java",
}


def ejecutar(filepath: str = "", destino: str = "javascript") -> str:
    """Traduce un archivo de un lenguaje a otro."""
    from src.llm.gemini_client import GeminiClient

    if not filepath:
        return "ERROR: Se necesita 'filepath' del archivo a traducir."

    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
        return f"ERROR: Archivo no encontrado: {full_path}"

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    if len(code) > 10000:
        code = code[:10000] + "\n... (truncado)"

    # Detect source language
    ext = os.path.splitext(filepath)[1]
    lang_map = {v: k for k, v in EXTENSIONES.items()}
    origen = lang_map.get(ext, "python")

    destino = destino.lower()

    gemini = GeminiClient()
    prompt = f"""Traduce este codigo de {origen} a {destino}.

Reglas:
1. Mantener la misma logica y estructura
2. Usar convenciones idiomaticas del lenguaje destino
3. Adaptar tipos de datos y patrones al destino
4. Si hay imports, usar los equivalentes del destino
5. Agregar comentarios donde la traduccion no sea directa
6. El codigo debe compilar/ejecutar correctamente

Codigo fuente ({origen}):
```{origen}
{code}
```

Genera SOLO el codigo traducido a {destino}, sin explicaciones."""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo traducir."

    # Clean
    if f"```{destino}" in resultado:
        resultado = resultado.split(f"```{destino}")[1].split("```")[0]
    elif "```" in resultado:
        parts = resultado.split("```")
        if len(parts) >= 3:
            resultado = parts[1]
            if resultado.startswith(destino):
                resultado = resultado[len(destino) :]

    # Save
    nombre = os.path.basename(filepath).replace(ext, "")
    dest_ext = EXTENSIONES.get(destino, ".txt")
    out_path = os.path.join(workspace_root, "Taller", f"{nombre}_translated{dest_ext}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(resultado)

    return f"SUCCESS: {origen} â†’ {destino} guardado en Taller/{nombre}_translated{dest_ext}\n\n{resultado[:500]}..."


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "Backend/llm/gemini_client.py"
    d = sys.argv[2] if len(sys.argv) > 2 else "javascript"
    print(ejecutar(f, d))
