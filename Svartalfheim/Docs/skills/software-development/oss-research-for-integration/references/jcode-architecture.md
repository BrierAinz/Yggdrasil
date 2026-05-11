# jcode Coding Agent Harness — Architecture Analysis for Yggdrasil

**Source:** https://github.com/1jehuang/jcode  
**Language:** Rust | **Stars:** 2,235 | **License:** MIT | **Version:** 0.11.4 | **Size:** 383MB

## Key Differentiators
- **Ultra-lightweight:** 27.8 MB RAM (embedding off) vs 386 MB Claude Code
- **Multi-session workflows** natively designed
- **Swarm coordination:** Agents collaborate automatically with conflict detection
- **Semantic memory** with embeddings + graph + cosine similarity
- **Memory sideagent** verifies relevance before injecting into conversation
- **Session search** (RAG over previous sessions)
- **Memory consolidation** automatic via ambient mode
- **MCP support** + hot-reload skills + dynamic tool registration
- **30+ built-in tools**
- **Multi-provider:** Claude, OpenAI, Gemini, Copilot, Azure, LM Studio, Ollama, vLLM, OpenRouter
- **1000+ FPS rendering** in TUI

## Crate Workspace Architecture

```
jcode/ (workspace)
├── src/main.rs              — CLI entry
├── src/lib.rs               — Library entry
├── src/bin/
│   ├── harness.rs           — jcode-harness binary
│   └── test_api.rs          — API test binary
│
├── crates/
│   ├── jcode-core               — Core types and logic
│   ├── jcode-agent-runtime      — Agent execution runtime
│   ├── jcode-memory-types       — Memory data structures
│   ├── jcode-embedding          — Local embedding inference (optional, heavy)
│   ├── jcode-gateway-types      — Gateway/protocol types
│   ├── jcode-plan               — Planning system
│   ├── jcode-protocol           — Communication protocol
│   ├── jcode-session-types      — Session management types
│   ├── jcode-task-types         — Task definitions
│   ├── jcode-batch-types        — Batch processing
│   ├── jcode-background-types   — Background task types
│   ├── jcode-config-types       — Configuration types
│   ├── jcode-selfdev-types      — Self-development types
│   ├── jcode-ambient-types      — Ambient/consolidation types
│   ├── jcode-auth-types         — Authentication types
│   ├── jcode-azure-auth         — Azure OAuth implementation
│   ├── jcode-provider-metadata  — Provider metadata
│   ├── jcode-provider-core      — Provider abstraction
│   ├── jcode-provider-openrouter — OpenRouter integration
│   ├── jcode-provider-gemini    — Gemini integration
│   ├── jcode-tui-core           — TUI core engine
│   ├── jcode-tui-markdown     — Markdown rendering
│   ├── jcode-tui-mermaid      — Mermaid diagram rendering (1800x faster)
│   ├── jcode-tui-render         — Rendering engine (1000+ FPS)
│   ├── jcode-tui-workspace      — Workspace UI
│   ├── jcode-terminal-launch    — Terminal launcher
│   ├── jcode-pdf                — PDF processing
│   ├── jcode-notify-email       — Email notifications
│   ├── jcode-mobile-core        — Mobile core
│   ├── jcode-mobile-sim         — Mobile simulator
│   └── jcode-desktop            — Desktop app
```

## Memory System (Key Innovation)

### Semantic Memory
- Every turn/response embedded as semantic vector
- Graph of memories queried via cosine similarity
- Embedding hits fed into conversation automatically
- Optional memory sideagent verifies relevance before injection

### Memory Extraction
- Triggered by: semantic drift, K turns since last extraction, session end
- Memory sideagent extracts and stores into memory graph
- Background ambient mode consolidates, checks staleness, resolves conflicts

### Explicit Memory Tools
- `memory_search` — active search
- `memory_store` — active storage
- `session_search` — RAG over previous sessions

### Configuration
- `~/.jcode/config.toml` — main config
- `~/.jcode/mcp.json` — MCP servers (global)
- `.jcode/mcp.json` — MCP servers (project-local)
- `~/.jcode/logs/` — daily log files

## Provider System

### Supported Providers
- **OAuth/subscription:** Claude, OpenAI/ChatGPT/Codex, Gemini, GitHub Copilot, Azure, Alibaba, Fireworks, MiniMax
- **Local/self-hosted:** LM Studio, Ollama, custom OpenAI-compatible
- **Aggregator:** OpenRouter, OpenAI-compatible

### Provider Profiles
```toml
[provider]
default_provider = "my-api"
default_model = "my-model-id"

[providers.my-api]
type = "openai-compatible"
base_url = "https://llm.example.com/v1"
api_key_env = "JCODE_PROVIDER_MY_API_API_KEY"
default_model = "my-model-id"

[[providers.my-api.models]]
id = "my-model-id"
context_window = 128000
```

### One-shot setup:
```bash
jcode provider add my-api \
  --base-url https://llm.example.com/v1 \
  --model my-model-id \
  --api-key-stdin \
  --set-default \
  --json
```

## MCP (Model Context Protocol) Support

### Config Format
```json
{
  "servers": {
    "filesystem": {
      "command": "/path/to/mcp-server",
      "args": ["--root", "/workspace"],
      "env": {},
      "shared": true
    }
  }
}
```

### Agent Self-Configuration Tools
- `mcp_list` — List connected MCP servers
- `mcp_connect` — Start a new MCP server
- `mcp_disconnect` — Stop an MCP server
- `mcp_reload` — Reload all MCP servers

## Swarm Coordination
- Spawn 2+ agents in same repo → automatic conflict management
- When agent A edits file that agent B read → server notifies agent B
- Agent B can check diff to avoid conflicts
- Messaging: DM one agent, broadcast all, or repo-only agents
- Agents can spawn their own swarms autonomously (coordinator + workers)
- Groups, channels, completion statuses auto-managed

## For Yggdrasil Integration

### Immediate (Phase 1)
1. **Modularize Lilith** into separate modules/packages:
   - `lilith-core` — orchestrator
   - `lilith-memory` — vector DB, embeddings
   - `lilith-tools` — tool registry
   - `lilith-providers` — LM Studio, OpenRouter, etc.
   - `lilith-swarm` — multi-agent coordination
   - `lilith-mcp` — MCP client

2. **Complete semantic memory** (partially implemented):
   - Embeddings per turn
   - Graph with cosine similarity
   - Memory sideagent for relevance verification
   - Session search with RAG
   - Memory consolidation (ambient mode)

3. **Provider profiles** in config.toml style

### Short-term (Phase 2)
4. **MCP support** for dynamic tools
5. **Hot-reload skills** without restart
6. **Side panels** in dashboard: diff viewer, mermaid diagrams, file viewer
7. **Batch processing** for massive tasks
8. **Background tasks** with notifications

### Medium-term (Phase 3)
9. **Swarm coordination** for multiple agents
10. **GPU-accelerated dashboard** rendering
11. **Custom terminal** integration
