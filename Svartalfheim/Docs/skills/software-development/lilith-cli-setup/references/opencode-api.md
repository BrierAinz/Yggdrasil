# OpenCode API Reference

## Endpoint

- **Base URL:** `https://opencode.ai/zen/go/v1`
- **Auth:** `Authorization: Bearer <api_key>` (standard OpenAI format)
- **Protocol:** OpenAI Chat Completions API compatible

## Available Models (as of 2026-05)

```
glm-5.1          (GLM-5.1 — Zhipu AI, recommended)
glm-5            (GLM-5)
deepseek-v4-pro
deepseek-v4-flash
kimi-k2.6
kimi-k2.5
minimax-m2.7
minimax-m2.5
qwen3.6-plus
qwen3.5-plus
```

## Verified Working Config

```yaml
provider: opencode
model: glm-5.1
base_url: https://opencode.ai/zen/go/v1
api_key: sk-...  # Hardcode or use env var IF it's set
providers:
  opencode:
    api_key: sk-...
    base_url: https://opencode.ai/zen/go/v1
    model: glm-5.1
```

## Quirks

1. **`reasoning_content` field (CRITICAL):** GLM-5.1 returns `reasoning_content` in two places:
   - **Streaming:** SSE delta chunks may contain `reasoning_content` alongside or instead of `content`. These MUST be filtered — if a delta has `reasoning_content` but no `content` and no `tool_calls`, skip it entirely. Otherwise the reasoning text appears as duplicate/garbled output.
   - **Non-streaming:** The `message` object in `/chat/completions` response may include `reasoning_content` as a top-level key. It should be ignored (not treated as `content`).
   - The providers.py `stream()` method has a filter: `if delta.get("reasoning_content") and not delta.get("content") and not delta.get("tool_calls"): continue` — do NOT remove this guard.

2. **Streaming:** Works identically to OpenAI's SSE format (`data: {...}` lines, `data: [DONE]` terminator). Tool call streaming with index-based accumulation works correctly.

3. **Tool calling:** Supports OpenAI-style function calling. Models return `tool_calls` array in assistant messages.

4. **`model` field in responses:** Returns `frank/GLM-5.1` (prefixed) in the response even when you send `glm-5.1` as the request model.

## Testing Connection

```bash
# Quick connectivity test
curl -s https://opencode.ai/zen/go/v1/models \
  -H "Authorization: Bearer sk-YOUR_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"

# Chat completion test
curl -s https://opencode.ai/zen/go/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-YOUR_KEY" \
  -d '{"model":"glm-5.1","messages":[{"role":"user","content":"hi"}]}'
```

## Important: Provider Name in Config

The `provider` field determines which profile is looked up from the `providers:` block. Using `provider: openai` will look for `providers.openai` (which has `${OPENAI_API_KEY}` env var). **Use `provider: opencode`** to match the `providers.opencode` profile that has the correct API key and base URL.