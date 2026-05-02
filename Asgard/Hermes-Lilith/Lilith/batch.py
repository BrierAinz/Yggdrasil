#!/usr/bin/env python3
"""
Lilith Batch Mode — Non-interactive LLM invocation
=====================================================
Allows programmatic access to Lilith for delegating tasks from
external agents (like Hermes). Sends a prompt, receives a response,
optionally streams tokens, and exits cleanly.

Usage:
    python -m Lilith.batch "Explain quantum entanglement"
    python -m Lilith.batch --json "Summarize this text"
    python -m Lilith.batch --model kimi "Translate to Norse"
    cat file.txt | python -m Lilith.batch --stdin
    python -m Lilith.batch --stream "Tell me a story"
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Lilith import __version__
from Lilith.Core.llm_provider import get_provider
from Lilith.Core.orchestrator import LilithOrchestrator


def run_batch(prompt: str, model: str = None, stream: bool = False,
              json_output: bool = False, system_prompt: str = None,
              max_tokens: int = 4096, temperature: float = 0.7,
              no_tools: bool = False, session_id: str = None) -> int:
    """Execute a single LLM request and output the result.

    Returns:
        0 on success, 1 on error, 2 on connection failure.
    """
    try:
        # Attempt connection — fail fast if no provider available
        try:
            provider = get_provider()
        except ConnectionError as e:
            if json_output:
                print(json.dumps({"error": str(e), "status": "no_provider"}, ensure_ascii=False))
            else:
                print(f"ERROR: No LLM provider available — {e}", file=sys.stderr)
            return 2

        # Override model if specified
        if model:
            provider.model = model

        # Build orchestrator for this request
        orch = LilithOrchestrator()
        if system_prompt:
            orch.messages = [{"role": "system", "content": system_prompt}]

        # Disable tools if requested — force empty tool list
        if no_tools:
            orch._force_no_tools = True

        # Set session for memory tracking
        if session_id:
            orch.session_id = session_id

        # ── Stream mode ──────────────────────────────────────────
        if stream:
            full_response = []
            try:
                for token in orch.chat_stream(prompt):
                    if json_output:
                        full_response.append(token)
                    else:
                        sys.stdout.write(token)
                        sys.stdout.flush()
            except Exception as e:
                if json_output:
                    print(json.dumps({"error": str(e), "status": "stream_error"}, ensure_ascii=False))
                else:
                    print(f"\nSTREAM ERROR: {e}", file=sys.stderr)
                return 1

            if json_output:
                result = {
                    "response": "".join(full_response),
                    "model": f"{provider.name}/{provider.model}",
                    "version": __version__,
                    "status": "ok",
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print()  # trailing newline after stream
            return 0

        # ── Normal (non-stream) mode ─────────────────────────────
        response = orch.chat(prompt)

        if json_output:
            result = {
                "response": response,
                "model": f"{provider.name}/{provider.model}",
                "version": __version__,
                "session_id": orch.session_id,
                "status": "ok",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(response)

        # Cleanup
        try:
            orch.close()
        except Exception:
            pass

        return 0

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "status": "error"}, ensure_ascii=False))
        else:
            print(f"FATAL: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="lilith-batch",
        description="Lilith Batch Mode — Non-interactive LLM invocation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lilith-batch "Explain quantum entanglement"
  lilith-batch --json "Summarize this text"
  lilith-batch --model kimi "Translate to Norse"
  cat file.txt | lilith-batch --stdin
  lilith-batch --stream "Tell me a story"
  lilith-batch --no-tools --sys "You are a poet" "Write a haiku"
        """.strip(),
    )
    parser.add_argument(
        "prompt", nargs="?", default=None,
        help="The prompt to send to Lilith (or use --stdin)",
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="Read prompt from stdin",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override the LLM model (e.g. 'kimi-for-coding')",
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream tokens to stdout as they arrive",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output result as JSON (includes model, version, status)",
    )
    parser.add_argument(
        "--sys", default=None, dest="system_prompt",
        help="Custom system prompt",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=4096,
        help="Maximum tokens in response (default: 4096)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7,
        help="Sampling temperature 0.0-1.0 (default: 0.7)",
    )
    parser.add_argument(
        "--no-tools", action="store_true",
        help="Disable tool use — text-only response",
    )
    parser.add_argument(
        "--session", default=None, dest="session_id",
        help="Session ID for memory continuity",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"Lilith v{__version__} — Batch Mode",
    )

    args = parser.parse_args()

    # Resolve prompt
    if args.stdin:
        prompt = sys.stdin.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.error("Provide a prompt argument or use --stdin")

    if not prompt:
        parser.error("Empty prompt — cannot send empty request")

    exit_code = run_batch(
        prompt=prompt,
        model=args.model,
        stream=args.stream,
        json_output=args.json_output,
        system_prompt=args.system_prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        no_tools=args.no_tools,
        session_id=args.session_id,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()