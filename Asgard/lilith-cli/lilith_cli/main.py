import argparse
import sys
from pathlib import Path

from lilith_cli.client import LilithClient
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine


def print_banner():
    print("""
    ╔════════════════════════════════════╗
    ║        LILITH CLI v2.1 (API+Local)        ║
    ║   Modo API por defecto. Usa --local para modo directo   ║
    ╚════════════════════════════════════╝
    """)


def run_api_mode(client: LilithClient):
    print("[API] Conectado a Lilith API")
    try:
        health = client.health()
        print(f"[API] Status: {health['status']} | Tools: {health['tools']} | v{health['version']}")
    except Exception as e:
        print(f"[API] Error conectando: {e}")
        print("[API] Tip: inicia la API con 'python3 -m uvicorn lilith_api.main:app'")
        return

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input in ("/salir", "/quit", "/exit"):
            break
        if user_input == "/tools":
            tools = client.list_tools()
            for name, desc in tools.items():
                print(f"  • {name}: {desc}")
            continue
        if user_input.startswith("/memory "):
            query = user_input[8:]
            results = client.memory_recall(query)
            for r in results:
                print(f"  [{r.get('distance', 0):.3f}] {r.get('text', '')[:100]}...")
            continue

        if not user_input:
            continue

        try:
            result = client.chat(user_input)
            print(f"[Lilith] {result['response']}")
            if result.get("tool_call"):
                print(f"[Tool] {result['tool_call']}")
        except Exception as e:
            print(f"[Error] {e}")


def run_local_mode(config: Config, memory: MemoryStore):
    engine = LilithEngine(config, memory)
    print("[Local] Modo directo (sin API)")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input in ("/salir", "/quit", "/exit"):
            break

        if not user_input:
            continue

        result = engine.process(user_input)
        print(f"[PROMPT] {result['prompt'][:200]}...")
        if result["tool_call"]:
            print(f"[TOOL] {result['tool_call']}")


def main():
    parser = argparse.ArgumentParser(description="Lilith CLI v2.1")
    parser.add_argument("--config", type=Path, help="Path to config directory")
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--local", action="store_true", help="Modo local directo (sin API)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL de la API")
    args = parser.parse_args()

    if args.version:
        print("Lilith v2.1.0")
        sys.exit(0)

    print_banner()

    if args.local:
        config = Config(root_path=args.config)
        if args.model:
            config.set("model", args.model)
        db_path = (args.config or Path.home() / ".lilith") / "memory.db"
        memory = MemoryStore(db_path)
        run_local_mode(config, memory)
    else:
        client = LilithClient(base_url=args.api_url)
        run_api_mode(client)


if __name__ == "__main__":
    main()
