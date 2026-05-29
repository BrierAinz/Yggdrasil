"""
Skill: comparador_apis
Envia el mismo prompt a multiples providers LLM y compara calidad/velocidad.
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

PROVIDER_MAP = {
    "gemini": ("Backend.llm.gemini_client", "GeminiClient"),
    "grok": ("Backend.llm.grok_client", "GrokClient"),
    "venice": ("Backend.llm.venice_client", "VeniceClient"),
}


def _call_provider(name: str, prompt: str) -> dict:
    """Llama a un provider y mide tiempo + respuesta."""
    try:
        module_path, class_name = PROVIDER_MAP[name]
        import importlib

        mod = importlib.import_module(module_path)
        client_class = getattr(mod, class_name)
        client = client_class()

        start = time.time()
        response = client.generate_text(prompt)
        elapsed = time.time() - start

        return {
            "provider": name,
            "response": response or "(sin respuesta)",
            "time_sec": round(elapsed, 2),
            "chars": len(response) if response else 0,
            "status": "OK" if response else "FALLO",
        }
    except Exception as e:
        return {
            "provider": name,
            "response": f"ERROR: {e}",
            "time_sec": 0,
            "chars": 0,
            "status": "ERROR",
        }


def ejecutar(prompt: str = "", providers: str = "gemini,grok") -> str:
    """Compara respuestas de multiples providers."""
    if not prompt:
        return "ERROR: Se necesita 'prompt' para comparar."

    provider_list = [p.strip() for p in providers.split(",")]
    invalid = [p for p in provider_list if p not in PROVIDER_MAP]
    if invalid:
        return f"ERROR: Providers no validos: {invalid}. Disponibles: {list(PROVIDER_MAP.keys())}"

    results = []
    for p in provider_list:
        result = _call_provider(p, prompt)
        results.append(result)

    # Build comparison report
    reporte = [f"# Comparacion de APIs"]
    reporte.append(f'*Prompt: "{prompt[:80]}..."*\n')
    reporte.append(f"| Provider | Tiempo | Caracteres | Status |")
    reporte.append(f"|----------|--------|------------|--------|")
    for r in results:
        reporte.append(
            f"| {r['provider']} | {r['time_sec']}s | {r['chars']} | {r['status']} |"
        )

    reporte.append("")
    for r in results:
        reporte.append(f"\n## {r['provider'].upper()}")
        reporte.append(f"*{r['time_sec']}s | {r['chars']} chars*\n")
        reporte.append(r["response"][:500])
        if len(r["response"]) > 500:
            reporte.append("...(truncado)")

    # Guardar
    output = os.path.join(
        workspace_root, "Taller", f"comparacion_apis_{time.strftime('%Y%m%d_%H%M')}.md"
    )
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(reporte))

    return "\n".join(reporte)


if __name__ == "__main__":
    p = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Explica que es un closure en Python en 2 oraciones"
    )
    print(ejecutar(p, "gemini,grok"))
