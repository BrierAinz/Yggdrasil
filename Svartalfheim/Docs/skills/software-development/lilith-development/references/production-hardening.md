# Production Hardening (FASE 9) — Reference

## Module Architecture

```
Core/
  resilience.py          # CircuitBreaker, RetryConfig, retry_with_backoff, TimeoutConfig
  error_handler.py       # LilithError hierarchy, sanitize_output, format_error
  lilith_logger.py       # Structured logging with runic prefixes
  graceful_shutdown.py   # Signal handlers, atexit, crash markers, shutdown hooks LIFO
```

## CircuitBreaker State Machine

```
CLOSED ──(failure_threshold reached)──> OPEN ──(recovery_timeout elapsed)──> HALF_OPEN
  ↑                                                                         │
  └──────────────────────(success)──────────────────────────────────────────┘
  HALF_OPEN + failure → back to OPEN
```

- Default `failure_threshold=5`, `recovery_timeout=30s`
- Each LLMProvider instance gets its own CircuitBreaker
- `CircuitBreakerError` raised when circuit is OPEN

## sanitize_output Pattern Catalog

| Pattern | Regex | Example |
|---------|-------|---------|
| Bearer token | `Bearer\s+\S+` | `Bearer abc123` |
| OpenAI key | `\bsk-[a-zA-Z0-9_-]{4,}\b` | `sk-proj-xxxx` |
| GitHub PAT | `\bghp_[a-zA-Z0-9]{4,}\b` | `ghp_ABCD1234` |
| GitLab PAT | `\bglpat-[a-zA-Z0-9]{4,}\b` | `glpat-xxxx` |
| API key assignment | `(?i)(api_?key|secret|token|password)\s*[=:]\s*["\']?\S+["\']?` | `api_key=xxxx` |
| URL credentials | `https?://[^:]+:[^@]+@` | `https://user:pass@host` |
| Generic secret | `(?i)(secret|token|api_key)\s*[=:]\s*\S+` | `SECRET=xxxx` |
| Email | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `user@host.com` |

**Critical:** Use `{4,}` (not `{20,}`) for token min-length — test fixtures use short tokens.

## Error Hierarchy

```
LilithError (base)
  ├── ProviderError(provider, status_code)
  ├── ToolError(tool_name, original_error)
  ├── MemoryError
  └── ConfigError
```

`format_error()` maps exception types to dark fantasy messages with emojis.

## Graceful Shutdown Flow

```
SIGINT/SIGTERM received
  → request_shutdown() sets threading.Event
  → execute_shutdown() runs registered hooks in LIFO order
  → Hooks: save_session(), stop_consolidator(), clear_crash_marker()
  → atexit handler also calls execute_shutdown() (idempotent)

Startup:
  → check_crash_recovery() → finds ~/.lilith/.crash_marker
  → Prompt user: "Previous session detected. Restore with /session load <id>"
```

## Logger Runic Prefixes

| Level | Rune | Prefix |
|-------|------|--------|
| DEBUG | ᛏ | ᛏ |
| INFO | ᚱ | ᚱ |
| WARNING | ᚨ | ᚨ |
| ERROR | ᛃ | ᛃ |
| CRITICAL | ᛬ | ᛬ |

Module-specific emojis: 🖥️ (provider), 🔧 (tools), 🧠 (memory), ⚙️ (config), 🧵 (swarm), etc.

## Test Count: 561 (93 new for FASE 9)

- `test_resilience.py`: 46 tests (circuit breaker states, retry with backoff, timeout config)
- `test_error_handler.py`: 21 tests (hierarchy, sanitize patterns, format_error, None handling)
- `test_graceful_shutdown.py`: 26 tests (hooks, markers, signal handling, idempotency)