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
- [ ] Fix: undo doesn't work for multi_edit

### 1.2 Reliability
- [ ] Add retry with exponential backoff for transient API errors
- [ ] Add timeout handling for each tool (not just subprocess)
- [ ] Add graceful degradation when tools fail
- [ ] Add message validation before sending to API
- [ ] Test all 35 tools work correctly with DeepSeek

### 1.3 Performance
- [ ] Cache system prompt between calls (don't rebuild every time)
- [ ] Lazy-load codebase index (only on first use)
- [ ] Optimize _detect_dependencies (avoid reading large files)
- [ ] Add token counting for streaming responses

---

## Phase 2: Intelligence (Week 2)

### 2.1 Multi-Model Routing
- [x] Basic routing (simple → cheap, complex → expensive)
- [ ] Implement actual model switching (use gpt-oss for complex reasoning)
- [ ] Add model fallback chain (deepseek → gpt-oss → glm)
- [ ] Track which model works best for which task type
- [ ] Auto-switch based on task complexity heuristics

### 2.2 Context Awareness
- [x] Load project rules (REGLAS_YGGDRASIL.md)
- [x] Detect dependencies (pyproject.toml, package.json)
- [x] Load shell history
- [x] Codebase index (top-level)
- [ ] Deep codebase indexing (search by function/class name)
- [ ] Git context (current branch, recent commits, pending changes)
- [ ] Test coverage awareness (which files have tests)
- [ ] Dependency version tracking

### 2.3 Learning
- [x] Remember facts across sessions
- [x] Save/load skills
- [ ] Auto-suggest skills after complex workflows
- [ ] Learn from user corrections (when user says "no, do X instead")
- [ ] Track which approaches work best for which tasks
- [ ] Build project-specific knowledge over time

---

## Phase 3: Developer Experience (Week 3)

### 3.1 Streaming
- [ ] Re-enable streaming with proper duplicate prevention
- [ ] Add typing indicator while waiting for response
- [ ] Show tool execution progress in real-time
- [ ] Add streaming for tool results (show as they complete)

### 3.2 UI Polish
- [x] Beautiful banner with runes
- [x] Status table on startup
- [x] Token/cost in prompt
- [x] Separator between responses
- [ ] Syntax highlighting for code blocks
- [ ] Diff view for file changes (before/after)
- [ ] Progress bar for long operations
- [ ] Compact mode for tool calls (collapse after completion)

### 3.3 Interactive Features
- [ ] Tab completion for commands and file paths
- [ ] History navigation (up/down arrows)
- [ ] Multi-line input support
- [ ] Inline image display (for screenshots)
- [ ] Confirmation dialog for large file writes

---

## Phase 4: Ecosystem (Week 4)

### 4.1 MCP Integration
- [x] Basic MCP client (list tools)
- [ ] Connect to MCP servers (stdio transport)
- [ ] Call MCP tools from the agent
- [ ] Auto-discover MCP servers from config
- [ ] Support HTTP MCP transport

### 4.2 Plugin System
- [x] Load external tool definitions from JSON
- [ ] Plugin validation (schema check)
- [ ] Plugin hot-reload (detect changes)
- [ ] Plugin marketplace / sharing
- [ ] Plugin versioning

### 4.3 Integration
- [ ] Hermes Agent integration (shared memory/skills)
- [ ] Obsidian integration (read/write notes)
- [ ] GitHub integration (PR review, issue management)
- [ ] ComfyUI integration (generate images from prompts)
- [ ] Spotify integration (music while coding)

---

## Phase 5: Advanced (Month 2)

### 5.1 Code Intelligence
- [ ] AST-aware code editing (not just text replacement)
- [ ] Type checking integration (mypy, pyright)
- [ ] Linting integration (ruff, flake8)
- [ ] Auto-fix common errors
- [ ] Code generation with test validation

### 5.2 Workflow Automation
- [ ] Git workflow automation (branch → code → test → PR)
- [ ] CI/CD integration (GitHub Actions)
- [ ] Deployment automation
- [ ] Dependency update automation
- [ ] Changelog generation

### 5.3 Collaboration
- [ ] Multi-user support (shared sessions)
- [ ] Code review mode (review PRs)
- [ ] Pair programming mode (two agents)
- [ ] Knowledge sharing between instances

---

## Phase 6: Production (Month 3)

### 6.1 Packaging
- [ ] pip install lilith-agent
- [ ] AUR package
- [ ] Docker container
- [ ] Standalone binary (PyInstaller)

### 6.2 Documentation
- [x] README.md
- [x] Tool reference
- [ ] Architecture documentation
- [ ] API documentation
- [ ] Contributing guide
- [ ] Video tutorial

### 6.3 Testing
- [ ] Unit tests for all tools
- [ ] Integration tests for agent loop
- [ ] E2E tests for common workflows
- [ ] Performance benchmarks
- [ ] Security audit

---

## Technical Debt

- [ ] Refactor: split lilith_agent.py into modules (tools/, agent/, ui/)
- [ ] Refactor: use async for API calls
- [ ] Refactor: proper error hierarchy
- [ ] Refactor: configuration management (YAML instead of hardcoded)
- [ ] Add type hints throughout
- [ ] Add docstrings to all public methods
- [ ] Remove unused imports and dead code

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
