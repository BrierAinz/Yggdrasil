# ᛚ Lilith Agent

> Dark Goddess of Yggdrasil Digital — Full coding CLI agent with memory, skills, and autonomous thinking.

## Overview

Lilith is a powerful AI coding agent that lives in your terminal. She can execute code, edit files, manage projects, remember facts across sessions, and learn reusable skills. Inspired by Hermes Agent and Claude Code.

## Quick Start

```bash
# Interactive mode
ygg chat
# or
lilith

# Single message
lilith -m "what files are in the project?"

# Choose provider
lilith --provider deepseek
lilith --provider gpt-oss
lilith --provider glm
```

## Features

### 35 Tools

| Category | Tools |
|----------|-------|
| **Files** | `terminal` `read_file` `write_file` `patch_file` `search_files` `list_files` `multi_edit` `undo` |
| **Git** | `git` `git_workflow` (branch/commit/push/pr) |
| **Code** | `python_exec` `run_tests` |
| **Memory** | `remember` `recall` (persistent across sessions) |
| **Skills** | `save_skill` `load_skill` (reusable procedures) |
| **Planning** | `create_plan` `todo` (task tracking) |
| **Processes** | `bg_run` `bg_status` `bg_log` `bg_kill` (background) |
| **Sessions** | `save_session` `restore_session` `fork` (branching) |
| **Web** | `web_fetch` `open_browser` |
| **Vision** | `screenshot` `analyze_image` |
| **System** | `clipboard` `notify` `workspace_info` `profile` |
| **Reasoning** | `think` (step-by-step reasoning) |
| **MCP** | `mcp_tools` (Model Context Protocol) |

### Memory System

Lilith remembers facts across sessions:

```
You: remember that I prefer dark themes
Lilith: Remembered: [preference] theme = dark

You: what do you know about my preferences?
Lilith: [preference] theme = dark
        [preference] response_style = short, direct
        [environment] os = CachyOS
```

Knowledge is stored in SQLite (`lilith_memory.db`) and automatically loaded into context.

### Skills

Save reusable procedures after complex tasks:

```
You: save this as a skill called "deploy-pipeline"
Lilith: Skill 'deploy-pipeline' saved.
```

Skills are stored as markdown files in `.lilith/skills/`.

### Safety

Destructive operations require confirmation:
- `rm -rf`, `git push --force`, `git reset --hard`
- `DROP TABLE`, `DROP DATABASE`
- Overwriting large files (>10KB)
- Writing to system files (`/etc/`)

### Background Processes

Run long tasks without blocking:

```
You: run the tests in the background
Lilith: Started background process: a1b2c3d4

You: check the test results
Lilith: [shows bg_log output]
```

### Conversation Branching

Explore alternative approaches:

```
You: /fork approach-a
Lilith: Forked as: approach-a

You: try a different approach
...

You: /fork approach-b
Lilith: Forked as: approach-b
```

### Auto-Context

Lilith automatically loads:
- **Project rules** (REGLAS_YGGDRASIL.md, AGENTS.md, CLAUDE.md)
- **Dependencies** (pyproject.toml, package.json)
- **Shell history** (last 10 commands)
- **Codebase structure** (top-level files and directories)
- **Plugin tools** (from `.lilith/plugins/*.json`)

## Commands

| Command | Description |
|---------|-------------|
| `/quit` | Exit |
| `/clear` | Reload context |
| `/memory` | Show saved sessions |
| `/skills` | List saved skills |
| `/knowledge` | Show all known facts |
| `/sessions` | List saved sessions |
| `/profile` | Show token/cost/performance stats |
| `/fork [name]` | Save conversation branch |
| `/provider <name>` | Switch LLM provider |

## Providers

| Provider | Model | Best For |
|----------|-------|----------|
| `deepseek` (default) | deepseek-chat | General coding, fast, cheap |
| `gpt-oss` | GPT-OSS-120B | Complex reasoning |
| `glm` | GLM-4.7 | Alternative option |

## Architecture

```
lilith_agent.py          # Main agent (35 tools, all features)
.lilith/
  skills/                # Saved skills (*.md)
  plugins/               # External tool plugins (*.json)
  context/               # Current plan, todo list
  sessions/              # Saved conversations
  undo/                  # File backup for undo
  .deepseek_key          # API key (gitignored)
  mcp.json               # MCP server config
lilith_memory.db         # SQLite memory store
```

## Configuration

### API Keys

Keys are read from:
1. Environment variables (`DEEPSEEK_API_KEY`, `BYTEPLUS_API_KEY`)
2. `.lilith/.deepseek_key` file
3. Hardcoded fallbacks

### MCP Servers

Create `.lilith/mcp.json`:

```json
{
  "servers": {
    "my-server": {
      "command": "node",
      "args": ["server.js"],
      "description": "My custom MCP server"
    }
  }
}
```

### Plugins

Create `.lilith/plugins/my-tools.json`:

```json
{
  "tools": [
    {
      "name": "my_tool",
      "description": "Does something useful",
      "parameters": {
        "type": "object",
        "properties": {
          "input": {"type": "string"}
        },
        "required": ["input"]
      }
    }
  ]
}
```

## Token/Cost Tracking

The prompt shows cumulative token usage and cost:

```
ᚦ You [12,345tok $0.003] »
```

Use `/profile` for detailed breakdown:

```
Session: a1b2c3d4
Tools used: 15
Input tokens: 12,345
Output tokens: 3,456
Total cost: $0.0032

Tool performance (avg time):
  terminal: 0.45s (8 calls)
  read_file: 0.12s (5 calls)
  web_fetch: 2.30s (2 calls)
```

## Development

```bash
# Run directly
cd ~/Proyectos/Yggdrasil
python3 lilith_agent.py

# With specific provider
python3 lilith_agent.py --provider gpt-oss

# Single message mode
python3 lilith_agent.py -m "run tests"
```

## Theme

Nordic Frost palette:
- Frost (#7eb8c4) — primary accent
- Amethyst (#8b6cc7) — secondary
- Gold (#c9a55a) — highlights
- Ember (#c94f4f) — errors
- Pine (#5b8a72) — success
- Snow (#c8d0e0) — text
- Steel (#3d4162) — muted

Runes: ᛚ ᛏ ᛒ ᚨ ᛟ ᚱ ᛊ

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
