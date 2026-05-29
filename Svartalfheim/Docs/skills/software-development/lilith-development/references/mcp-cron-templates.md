# MCP Server, Cron Scheduler & Agent Templates (FASE 14)

## MCP Server (`Lilith/MCP/server.py`)

`LilithMCPServer` exposes Lilith capabilities to external agents via JSON-RPC MCP protocol over stdio.

### Architecture
- Transport: stdio (stdin/stdout JSON-RPC framing)
- Protocol: MCP v1 (compatible with Hermes and other MCP clients)
- Tool registration: converts internal Lilith skills + DynamicToolRegistry tools into MCP tool schemas
- Request routing: `handle_request(method, params)` dispatches to skill execution or tool invocation

### Key Classes
- `LilithMCPServer` — main server, tool registration, request handler
- Uses `skill_registry.get_triggered_skills()` to discover available skills
- Uses `dynamic_tools.get_openai_tools()` for tool schemas

### Integration Points
- `Lilith/MCP/__init__.py` exports `LilithMCPServer`
- External agents (Hermes, Vanaheim) connect via MCP client → stdio subprocess

---

## Cron Scheduler (`Lilith/MCP/cron.py`)

Periodic task execution within Lilith using SQLite persistence.

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS cron_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    interval TEXT NOT NULL,          -- '1h', '30m', '1d', '24h'
    task_type TEXT NOT NULL,         -- 'skill', 'command', 'template'
    task_config TEXT,                -- JSON config for the task
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    created_at TEXT
);
```

### Key Methods
- `schedule(name, interval, task_type, config)` — add new cron job
- `unschedule(name)` — remove a cron job
- `enable(name)` / `disable(name)` — toggle job
- `run(name)` — manually trigger a job
- `get_due_jobs()` — returns jobs where `next_run <= now`
- `tick()` — execute all due jobs (called by daemon thread or manually)
- `get_status()` — list all jobs with stats

### Safety
- Thread-safe: uses `threading.Lock()` for all DB operations
- Each job run is isolated: failures don't affect other jobs
- `fail_count` tracks consecutive failures (not reset on success)

---

## Agent Templates (`Lilith/MCP/templates.py`)

Predefined and custom agent templates for consistent agent creation.

### Built-in Templates (5)

| Template | Role | Tools | Priority |
|----------|------|-------|----------|
| `researcher` | Deep investigation, fact-gathering | web_search, web_extract | 80 |
| `coder` | Code generation, refactoring, debugging | shell, python, file | 90 |
| `analyst` | Data analysis, comparison, evaluation | shell, python | 70 |
| `reviewer` | Code/text review, quality assessment | shell, file | 75 |
| `creative` | Creative writing, brainstorming | — | 65 |

### Template Structure
```python
@dataclass
class AgentTemplate:
    name: str
    description: str
    system_prompt: str
    tools: List[str]        # tool names from DynamicToolRegistry
    model_hint: str = ""    # preferred model (optional)
    variables: Dict[str, str] = {}  # {{variable}} substitutions
    version: str = "1.0.0"
```

### Custom Templates
Users can create `~/.lilith/templates/*.yaml`:
```yaml
name: my-analyst
description: Custom data analyst
system_prompt: |
  You are a data analyst specializing in {{domain}}.
  Focus on {{focus_area}}.
tools:
  - python
  - shell
variables:
  domain: "financial data"
  focus_area: "trend analysis"
```

### Template Rendering
`TemplateRenderer.render(template, context)` — substitutes `{{variable}}` placeholders with context dict values. Unmatched variables are left as-is (not stripped).

### CLI Integration
- `/templates list` — shows all (built-in + custom) with description
- `/templates info <name>` — full template details including system_prompt
- `/templates run <name>` — execute with variable prompts if needed