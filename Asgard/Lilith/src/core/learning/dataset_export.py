"""
Lilith 3.0 — Exportación de dataset para entrenamiento del clasificador local (Fase 4).
Lee memory/episodic/interactions.jsonl y genera CSV message,tool_name para entrenar un modelo.
"""
import json
import sys
from pathlib import Path


def get_episodic_path(base_path: Path) -> Path:
    """Ruta al archivo JSONL de interacciones."""
    return base_path / "memory" / "episodic" / "interactions.jsonl"


def export_to_csv(base_path: Path, output_csv: Path, limit: int = 5000) -> int:
    """
    Lee interactions.jsonl y escribe un CSV con columnas message,tool_name.
    tool_name es el primer paso del plan (tool o tool_name).
    Devuelve el número de filas escritas.
    """
    src = get_episodic_path(base_path)
    if not src.exists():
        return 0
    rows: list[tuple[str, str]] = []
    with open(src, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = (data.get("message") or "").strip()
            plan = data.get("plan") or []
            if not message or not plan:
                continue
            first = plan[0] if isinstance(plan[0], dict) else {}
            tool = first.get("tool") or first.get("tool_name") or "generate_reply"
            rows.append((message.replace("\n", " ").replace(",", " "), tool))
    if not rows:
        return 0
    with open(output_csv, "w", encoding="utf-8") as out:
        out.write("message,tool_name\n")
        for msg, tool in rows:
            out.write(f'"{msg}",{tool}\n')
    return len(rows)


def main() -> None:
    base = Path(__file__).resolve().parent.parent.parent.parent
    if len(sys.argv) > 1:
        base = Path(sys.argv[1])
    output = base / "memory" / "episodic" / "dataset_train.csv"
    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    n = export_to_csv(base, output)
    print(f"Exportadas {n} filas a {output}")


if __name__ == "__main__":
    main()
