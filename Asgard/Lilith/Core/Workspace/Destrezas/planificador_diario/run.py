"""
Skill: planificador_diario
Revisa recordatorios, learnings, skills y estado del proyecto para proponer un plan del dia.
"""
import glob
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


def _gather_context() -> str:
    """Recopila info del workspace para generar el plan."""
    ctx = []

    # Recordatorios
    rec_path = os.path.join(workspace_root, "Mente", "recordatorios.json")
    if os.path.exists(rec_path):
        with open(rec_path, "r", encoding="utf-8") as f:
            recs = json.load(f)
        if recs:
            ctx.append("## Recordatorios pendientes")
            for r in recs[-10:]:
                ctx.append(f"- [{r.get('timestamp', '')}] {r.get('nota', '')}")

    # Learnings recientes
    learn_path = os.path.join(workspace_root, "Mente", "learnings.jsonl")
    if os.path.exists(learn_path):
        with open(learn_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-5:]
        if lines:
            ctx.append("\n## Ultimos aprendizajes")
            for l in lines:
                try:
                    data = json.loads(l.strip())
                    ctx.append(f"- {data.get('content', '')[:100]}")
                except:
                    pass

    # Conceptos recientes en Mente
    conceptos_dir = os.path.join(workspace_root, "Mente", "conceptos_clave")
    if os.path.exists(conceptos_dir):
        files = sorted(
            glob.glob(os.path.join(conceptos_dir, "*.md")),
            key=os.path.getmtime,
            reverse=True,
        )[:5]
        if files:
            ctx.append("\n## Conceptos estudiados recientemente")
            for f in files:
                ctx.append(f"- {os.path.basename(f)}")

    # Skills disponibles
    reg_path = os.path.join(workspace_root, "Destrezas", "skill_registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        skills = reg.get("skills", [])
        ctx.append(f"\n## Skills disponibles: {len(skills)}")
        for s in skills:
            ctx.append(f"- {s.get('name', '?')} [{s.get('category', '')}]")

    # Archivos recientes en Taller
    taller_dir = os.path.join(workspace_root, "Taller")
    if os.path.exists(taller_dir):
        files = sorted(
            glob.glob(os.path.join(taller_dir, "*")), key=os.path.getmtime, reverse=True
        )[:5]
        if files:
            ctx.append("\n## Trabajo reciente en Taller")
            for f in files:
                ctx.append(f"- {os.path.basename(f)}")

    return "\n".join(ctx) if ctx else "No hay contexto disponible."


def ejecutar() -> str:
    """Genera el plan del dia basado en el contexto del workspace."""
    from src.llm.gemini_client import GeminiClient

    contexto = _gather_context()
    dia = time.strftime("%A %d de %B, %Y")

    gemini = GeminiClient()
    prompt = f"""Eres Lilith, IA tactica de Ainz. Es {dia}.

Basandote en el siguiente contexto del workspace, genera un PLAN DEL DIA:

{contexto}

Formato del plan:
1. **Buenos dias** (saludo breve personalizado)
2. **Estado actual** (resumen de donde esta el proyecto)
3. **Prioridades del dia** (3-5 tareas ordenadas por importancia)
4. **Recordatorios** (si hay pendientes)
5. **Sugerencia** (algo proactivo que no haya pedido pero seria util)

Responde en ESPAÃ‘OL, tono amigable pero profesional."""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo generar el plan."

    # Guardar
    output = os.path.join(
        workspace_root, "Taller", f"plan_{time.strftime('%Y%m%d')}.md"
    )
    with open(output, "w", encoding="utf-8") as f:
        f.write(f"# Plan del Dia - {dia}\n\n{resultado}")

    return f"SUCCESS: Plan del dia generado.\n\n{resultado}"


if __name__ == "__main__":
    print(ejecutar())
