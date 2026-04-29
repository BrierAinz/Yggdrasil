import argparse
import sys
from pathlib import Path

from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine


def main():
    parser = argparse.ArgumentParser(description="Lilith CLI v2.0")
    parser.add_argument("--config", type=Path, help="Path to config directory")
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print("Lilith v2.0.0")
        sys.exit(0)

    config = Config(root_path=args.config)
    if args.model:
        config.set("model", args.model)

    db_path = (args.config or Path.home() / ".lilith") / "memory.db"
    memory = MemoryStore(db_path)
    engine = LilithEngine(config, memory)

    print("Lilith v2.0 lista. Escribe /salir para terminar.")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input in ("/salir", "/quit", "/exit"):
            break

        result = engine.process(user_input)
        print(f"[PROMPT] {result['prompt'][:200]}...")
        if result["tool_call"]:
            print(f"[TOOL] {result['tool_call']}")


if __name__ == "__main__":
    main()
