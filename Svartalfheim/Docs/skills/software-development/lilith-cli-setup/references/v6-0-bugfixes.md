# Yggdrasil CLI v6.0 Bugfixes (Session 2026-05-08)

Bugs found and fixed during the v6.0 development session. Documented here for future reference since these are subtle and could recur.

## 1. GLM-5.1 `reasoning_content` in Streaming Deltas

**Symptom:** Streaming output prints content twice — once as `reasoning_content`, once as `content`.

**Root cause:** GLM-5.1 (via OpenCode API) sends `reasoning_content` in SSE delta chunks. These are chain-of-thought tokens that should NOT be displayed to the user. Some deltas have only `reasoning_content` with no `content`, causing garbled/duplicated output.

**Fix in `providers.py` `stream()` method:**
```python
# Skip reasoning-only deltas (GLM-5.1 quirk)
if delta.get("reasoning_content") and not delta.get("content") and not delta.get("tool_calls"):
    continue
```

**Fix in `providers.py` `_normalise_response()` for non-streaming path:**
```python
# Strip reasoning_content from message content
if isinstance(message.get("content"), str) and "reasoning_content" in message:
    # reasoning_content is metadata, not user-visible output
    pass  # content field already has what we need
```

## 2. `PromptSession` `enable_open_brackets` TypeError

**Symptom:** `TypeError: PromptSession.__init__() got an unexpected keyword argument 'enable_open_brackets'`

**Root cause:** `prompt_toolkit.PromptSession` does not accept `enable_open_brackets` as a parameter. This is a readline/libedit concept that doesn't exist in prompt_toolkit's API.

**Fix in `repl.py`:**
```python
# WRONG:
self.session = PromptSession(enable_open_brackets=True, ...)

# CORRECT:
self.session = PromptSession(history=self.history, ...)

# prompt_toolkit handles bracket matching internally, no config needed.
```

## 3. `prompt_async` with `asyncio.to_thread()` — Coroutine Crash

**Symptom:** `AttributeError: 'coroutine' object has no attribute 'strip'` or `TypeError: object coroutine can't be used in 'await' expression`

**Root cause:** `prompt_session.prompt_async()` is already an async coroutine (returns `Awaitable[str]`). Wrapping it in `asyncio.to_thread()` causes double-await or type confusion.

**Fix in `repl.py`:**
```python
# WRONG:
line = await asyncio.to_thread(self.session.prompt_async, "> ")

# CORRECT:
line = await self.session.prompt_async("> ")
```

`prompt_async()` must be `await`ed directly — it manages its own event loop integration with prompt_toolkit's asyncio support.

## 4. `/help` NameError — Lambda Variable Scoping

**Symptom:** `NameError: name 'c' is not defined` when running `/help` in REPL.

**Root cause:** In `commands.py`, the `/help` command builder used a variable `c` in an f-string inside a loop, but the loop variable was actually named `cmd`. The f-string captured `c` which didn't exist.

**Fix in `commands.py`:**
```python
# WRONG (line ~55):
for cmd in self.registry.values():
    aliases = ", ".join(f"!{a}" for a in c.aliases)  # ← 'c' instead of 'cmd'

# CORRECT:
for cmd in self.registry.values():
    aliases = ", ".join(f"!{a}" for a in cmd.aliases)
```

## 5. `_resolve_model()` Ignoring Provider Profile

**Symptom:** `yggdrasil chat --provider opencode` still uses `config.model` instead of `providers.opencode.model`.

**Root cause:** `_resolve_model()` only returned `self.config.model` without checking the provider-specific profile override.

**Fix in `providers.py`:**
```python
def _resolve_model(self) -> str:
    profile = self._get_profile()
    # Provider profile model takes precedence
    if profile and profile.get("model"):
        return profile["model"]
    return self.config.model
```

This mirrors how `_resolve_api_key()` and `_resolve_base_url()` already work — check provider profile first, fall back to top-level config.

## 6. Streaming Text Rendering Double-Print

**Symptom:** Each streaming chunk prints twice in the REPL.

**Root cause:** The `repl.py` streaming handler was both accumulating text AND printing each chunk raw, causing double output when the final render also printed.

**Fix:** Ensure streaming chunks are printed once via a simple `print(chunk, end="", flush=True)` with no accumulation/Delta rendering overlap. The `render.py` module should NOT re-render previously printed text.

---

## Pattern: Debugging Non-TTY REPL Issues

The REPL (`yggdrasil chat`) requires a real TTY (terminal) to function — prompt_toolkit needs terminal capabilities for input handling. You CANNOT test it via `echo "/help" | yggdrasil chat` or pipe input because:

1. `prompt_async()` requires a terminal (no stdin pipe)
2. Rich rendering needs terminal capabilities
3. The event loop for streaming won't have a proper event source

For testing, use the one-shot command instead:
```bash
yggdrasil prompt "test message"
```

Or test individual components (providers, commands, config) in isolation with Python imports.