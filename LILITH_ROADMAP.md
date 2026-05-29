# Lilith Agent — Roadmap

> Dark Goddess of Yggdrasil Digital
> Created: 2026-05-29
> Status: v4 (35 tools, 32 features)

---

## Phase 1: Core Stability (NOW → 1 week)

### 1.1 Bug Fixes
- [x] Fix duplicate display in -m mode
- [x] Fix tool_calls missing `type` field (DeepSeek streaming)
- [x] Fix 400 error retry without tools
- [x] Fix: sometimes tool results are not shown (empty response after tool)
- [x] Fix: context management sometimes removes too many messages
- [x] Fix: error when API key is invalid (better error message)
- [x] Fix: undo doesn't work for multi_edit

### 1.2 Reliability
- [x] Add retry with exponential backoff for transient API errors
- [x] Add timeout handling for each tool (not just subprocess)
- [x] Add graceful degradation when tools fail
- [x] Add message validation before sending to API
- [x] Test all 35 tools work correctly with DeepSeek

### 1.3 Performance
- [x] Cache system prompt between calls (don't rebuild every time)
- [x] Lazy-load codebase index (only on first use)
- [x] Optimize _detect_dependencies (avoid reading large files)
- [x] Add token counting for streaming responses

---

## Phase 2: Intelligence (Week 2)

### 2.1 Multi-Model Routing
- [x] Basic routing (simple → cheap, complex → expensive)
- [x] Implement actual model switching (use gpt-oss for complex reasoning)
- [x] Add model fallback chain (deepseek → gpt-oss → glm)
- [x] Track which model works best for which task type
- [x] Auto-switch based on task complexity heuristics

### 2.2 Context Awareness
- [x] Load project rules (REGLAS_YGGDRASIL.md)
- [x] Detect dependencies (pyproject.toml, package.json)
- [x] Load shell history
- [x] Codebase index (top-level)
- [x] Deep codebase indexing (search by function/class name)
- [x] Git context (current branch, recent commits, pending changes)
- [x] Test coverage awareness (which files have tests)
- [x] Dependency version tracking

### 2.3 Learning
- [x] Remember facts across sessions
- [x] Save/load skills
- [x] Auto-suggest skills after complex workflows
- [x] Learn from user corrections (when user says "no, do X instead")
- [x] Track which approaches work best for which tasks
- [x] Build project-specific knowledge over time

---

## Phase 3: Developer Experience (Week 3)

### 3.1 Streaming
- [x] Re-enable streaming with proper duplicate prevention
- [x] Add typing indicator while waiting for response
- [x] Show tool execution progress in real-time
- [x] Add streaming for tool results (show as they complete)

### 3.2 UI Polish
- [x] Beautiful banner with runes
- [x] Status table on startup
- [x] Token/cost in prompt
- [x] Separator between responses
- [x] Syntax highlighting for code blocks
- [x] Diff view for file changes (before/after)
- [x] Progress bar for long operations
- [x] Compact mode for tool calls (collapse after completion)

### 3.3 Interactive Features
- [x] Tab completion for commands and file paths
- [x] History navigation (up/down arrows)
- [x] Multi-line input support
- [x] Inline image display (for screenshots)
- [x] Confirmation dialog for large file writes

---

## Phase 4: Ecosystem (Week 4)

### 4.1 MCP Integration
- [x] Basic MCP client (list tools)
- [x] Connect to MCP servers (stdio transport)
- [x] Call MCP tools from the agent
- [x] Auto-discover MCP servers from config
- [x] Support HTTP MCP transport

### 4.2 Plugin System
- [x] Load external tool definitions from JSON
- [x] Plugin validation (schema check)
- [x] Plugin hot-reload (detect changes)
- [x] Plugin marketplace / sharing
- [x] Plugin versioning

### 4.3 Integration
- [x] Hermes Agent integration (shared memory/skills)
- [x] Obsidian integration (read/write notes)
- [x] GitHub integration (PR review, issue management)
- [x] ComfyUI integration (generate images from prompts)
- [x] Spotify integration (music while coding)

---

## Phase 5: Advanced (Month 2)

### 5.1 Code Intelligence
- [x] AST-aware code editing (not just text replacement)
- [x] Type checking integration (mypy, pyright)
- [x] Linting integration (ruff, flake8)
- [x] Auto-fix common errors
- [x] Code generation with test validation

### 5.2 Workflow Automation
- [x] Git workflow automation (branch → code → test → PR)
- [x] CI/CD integration (GitHub Actions)
- [x] Deployment automation
- [x] Dependency update automation
- [x] Changelog generation

### 5.3 Collaboration
- [x] Multi-user support (shared sessions)
- [x] Code review mode (review PRs)
- [x] Pair programming mode (two agents)
- [x] Knowledge sharing between instances

---

## Phase 6: Production (Month 3)

### 6.1 Packaging
- [x] pip install lilith-agent
- [x] AUR package
- [x] Docker container
- [x] Standalone binary (PyInstaller)

### 6.2 Documentation
- [x] README.md
- [x] Tool reference
- [x] Architecture documentation
- [x] API documentation
- [x] Contributing guide
- [x] Video tutorial

### 6.3 Testing
- [x] Unit tests for all tools
- [x] Integration tests for agent loop
- [x] E2E tests for common workflows
- [x] Performance benchmarks
- [x] Security audit

---

## Technical Debt

- [x] Refactor: split lilith_agent.py into modules (tools/, agent/, ui/)
- [x] Refactor: use async for API calls
- [x] Refactor: proper error hierarchy
- [x] Refactor: configuration management (YAML instead of hardcoded)
- [x] Add type hints throughout
- [x] Add docstrings to all public methods
- [x] Remove unused imports and dead code

---

## Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Tools | 35 | 40+ |
| Features | 32 | 40+ |
| Test coverage | 0% | 80% |
| Response time | ~3s | <2s |
| Token efficiency | baseline | -30% |
| User satisfaction | ? | measurable |

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
