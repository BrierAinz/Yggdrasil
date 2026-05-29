# Svartalfheim/capabilities/knowledge_updater.py
import os
import sys
from pathlib import Path

# Map topics to files
KB_MAP = {
    "pytorch": "pytorch_crash_course.md",
    "sd": "stable_diffusion_workflow.md",
    "stable_diffusion": "stable_diffusion_workflow.md",
    "project": "my_project_structure.md",
    "structure": "my_project_structure.md",
}

# Adjust path to locate memory/knowledge_base relative to this file
# d:/Proyectos/Proyectos Alpha/Yggdrasil IA/Svartalfheim/capabilities/knowledge_updater.py
KB_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "knowledge_base"


def learn(topic: str, content: str):
    """Appends new knowledge to the specified topic file."""
    topic = topic.lower()
    filename = KB_MAP.get(topic)

    if not filename:
        return f"Error: Unknown topic '{topic}'. Available topics: {', '.join(KB_MAP.keys())}"

    filepath = KB_DIR / filename

    if not filepath.exists():
        return f"Error: Knowledge file not found: {filepath}"

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Learned Insight (Auto-added)\n{content}\n")
        return f"Successfully added insight to {filename}."
    except Exception as e:
        return f"Failed to update knowledge base: {e}"


if __name__ == "__main__":
    # Usage: python knowledge_updater.py <topic> <content>
    if len(sys.argv) < 3:
        print('Usage: python knowledge_updater.py <topic> "content"')
        sys.exit(1)

    topic = sys.argv[1]
    content = " ".join(sys.argv[2:])
    print(learn(topic, content))
