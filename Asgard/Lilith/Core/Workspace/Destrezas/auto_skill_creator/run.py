"""
Skill: auto_skill_creator
La habilidad mas avanzada de Lilith: crear nuevas skills autonomamente.
Lilith analiza una descripcion, genera el codigo, crea la estructura y registra la skill.
"""
import json
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

SKILL_TEMPLATE = '''"""
Skill: {nombre}
{descripcion}
Auto-generada por Lilith el {fecha}.
"""
import sys, os, time

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


{code}


if __name__ == "__main__":
    print(ejecutar())
'''


def ejecutar(nombre: str = "", descripcion: str = "") -> str:
    """Genera una nueva skill completa a partir de una descripcion."""
    from src.llm.gemini_client import GeminiClient

    if not nombre or not descripcion:
        return "ERROR: Se necesita 'nombre' (snake_case) y 'descripcion' de la skill."

    nombre = nombre.lower().replace(" ", "_").replace("-", "_")
    destrezas_dir = os.path.join(workspace_root, "Destrezas")
    skill_path = os.path.join(destrezas_dir, nombre)

    if os.path.exists(skill_path):
        return f"ERROR: Ya existe una skill con el nombre '{nombre}'."

    gemini = GeminiClient()

    # Step 1: Generate the skill code
    prompt = f"""Eres Lilith, una IA tactica. Necesitas crear el codigo Python para una nueva SKILL.

Nombre: {nombre}
Descripcion: {descripcion}

REGLAS ESTRICTAS:
1. Genera SOLO la funcion `ejecutar()` con sus parametros y logica
2. La funcion DEBE llamarse `ejecutar` y retornar un string
3. Los imports que necesites van DENTRO de la funcion
4. Usa solo librerias estandar de Python + requests si es necesario
5. El resultado debe ser informativo y util
6. Guarda archivos de output en: os.path.join(workspace_root, "Taller", ...)
7. Maneja errores con try/except

EJEMPLO de formato de respuesta (SOLO el codigo, sin markdown):
def ejecutar(param1: str = "", param2: str = "") -> str:
    import json
    # logica aqui
    return "SUCCESS: resultado"

RESPONDE SOLO CON EL CODIGO DE LA FUNCION. Sin explicaciones, sin markdown, sin ```.
"""
    generated_code = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not generated_code:
        return "ERROR: Gemini no genero codigo."

    # Clean the generated code (remove markdown artifacts if any)
    generated_code = generated_code.strip()
    if generated_code.startswith("```"):
        lines = generated_code.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        generated_code = "\n".join(lines)

    # Validate that it has ejecutar function
    if "def ejecutar" not in generated_code:
        return "ERROR: El codigo generado no contiene la funcion 'ejecutar'. Reintentando..."

    # Step 2: Generate skill.json parameters
    param_prompt = f"""Analiza esta funcion Python y genera un JSON con los parametros.

{generated_code}

Responde SOLO con un JSON valido (sin markdown) en este formato exacto:
{{"param_name": {{"type": "string", "required": true, "description": "descripcion"}}}}

Si no tiene parametros responde: {{}}
"""
    params_raw = gemini.generate_text(param_prompt, model="gemini-2.0-flash")
    try:
        if params_raw:
            params_raw = params_raw.strip()
            if params_raw.startswith("```"):
                lines = params_raw.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                params_raw = "\n".join(lines)
            params = json.loads(params_raw)
        else:
            params = {}
    except json.JSONDecodeError:
        params = {}

    # Step 3: Create skill directory and files
    os.makedirs(skill_path, exist_ok=True)

    # skill.json
    manifest = {
        "name": nombre,
        "description": descripcion,
        "version": "1.0",
        "author": "Lilith (auto-generada)",
        "parameters": params,
        "output": f"Resultado de {nombre}",
        "tools_required": [],
        "auto_generated": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    with open(os.path.join(skill_path, "skill.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # run.py
    full_code = SKILL_TEMPLATE.format(
        nombre=nombre,
        descripcion=descripcion,
        fecha=time.strftime("%Y-%m-%d %H:%M"),
        code=generated_code,
    )
    with open(os.path.join(skill_path, "run.py"), "w", encoding="utf-8") as f:
        f.write(full_code)

    # Step 4: Update registry
    registry_path = os.path.join(destrezas_dir, "skill_registry.json")
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except:
        registry = {"skills": []}

    registry["skills"].append(
        {
            "name": nombre,
            "path": f"Destrezas/{nombre}",
            "active": True,
            "auto_generated": True,
        }
    )

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    # Step 5: Log the creation
    log_path = os.path.join(workspace_root, "Mente", "skill_creation_log.md")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {nombre}\n")
        f.write(f"- **Creada:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- **Descripcion:** {descripcion}\n")
        f.write(f"- **Auto-generada:** Si\n")
        f.write(f"- **Path:** Destrezas/{nombre}/\n\n")

    return (
        f"SUCCESS: Skill '{nombre}' creada exitosamente!\n"
        f"- Directorio: Destrezas/{nombre}/\n"
        f"- Archivos: skill.json + run.py\n"
        f"- Registrada en skill_registry.json\n"
        f"- Parametros detectados: {list(params.keys()) if params else 'ninguno'}"
    )


if __name__ == "__main__":
    n = sys.argv[1] if len(sys.argv) > 1 else ""
    d = sys.argv[2] if len(sys.argv) > 2 else ""
    print(ejecutar(n, d))
