# Batch Mode Reference

Added in v4.0.0. Enables programmatic LLM invocation without interactive REPL.

## Architecture

`Lilith/batch.py` contains:

- `BatchRunner` class — creates a `LilithOrchestrator`, sends prompt, returns response
- `run_batch()` — convenience function wrapping `BatchRunner`
- CLI argument parsing (`sys.argv` based) for `python3 -m Lilith.batch`

### BatchRunner Flow

```
BatchRunner(prompt, options)
  → instantiate LilithOrchestrator(provider)
  → if --batch-no-tools: set orchestrator._force_no_tools = True
  → if system_prompt: add system message to chat history
  → orchestrator.chat(prompt, tools=[])
  → format output (plain / JSON / stream)
  → exit(0|1|2)
```

### _force_no_tools Mechanism

When `_force_no_tools` is set on the orchestrator instance, `_get_tools_for_llm()` returns `[]` regardless of available tools. This prevents the LLM from attempting function calls in batch queries where no tool execution is desired.

## CLI Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--batch` | — | Enable batch mode (prompt follows) |
| `--batch-json` | — | Output structured JSON |
| `--batch-stream` | — | Stream tokens to stdout |
| `--batch-no-tools` | — | Disable all tools |
| `--batch-sys` | — | Custom system prompt |
| `--model` | — | Override model selection |

Note: `--batch` is parsed in `main.py` argparse. Module invocation (`python3 -m Lilith.batch`) parses from `sys.argv` directly in `batch.py`.

## JSON Output Format

```json
{
  "status": "success" | "error",
  "model": "kimi-for-coding",
  "version": "4.0.0",
  "response": "The LLM response text...",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 150,
    "total_tokens": 192
  }
}
```

On error:
```json
{
  "status": "error",
  "error": "No LLM provider available",
  "version": "4.0.0"
}
```

## Use Cases

1. **External agent delegation** — Hermes or other agents call `python3 -m Lilith.batch --json "prompt"`
2. **Pipelining** — Chain Lilith in Unix pipes: `cat file | python3 -m Lilith.batch "summarize"`
3. **CI/CD** — Use batch mode in automated workflows
4. **Testing** — Verify LLM connectivity in health checks

## Test Coverage

`Lilith/Core/tests/test_batch.py` — 18 tests covering:

- `run_batch()` basic invocation (mocked provider)
- `--batch-no-tools` disabling tools
- `--batch-json` structured output
- `--batch-sys` custom system prompt
- Error handling (no provider, provider error)
- Exit codes (0, 1, 2)
- Streaming mode