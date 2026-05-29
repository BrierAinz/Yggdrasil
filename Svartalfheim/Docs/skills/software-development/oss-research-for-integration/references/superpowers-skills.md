# Superpowers Skills Framework — Extracted Definitions for Yggdrasil

**Source:** https://github.com/obra/superpowers  
**Type:** Agentic skills framework & software development methodology  
**Stars:** 175,382 | **License:** MIT

## Core Philosophy
- **Spec-first:** No code without a written specification
- **RED-GREEN-REFACTOR:** Strict TDD — write failing test first, watch it fail, minimal code to pass, refactor
- **YAGNI + DRY:** No over-engineering, no duplication
- **Subagent-driven-development:** Fresh subagent per task + 2-stage review (spec compliance → code quality)
- **Verification-before-completion:** Nothing ships without review

## Skill Inventory (13 Skills)

### 1. brainstorming
- Generate specs from vague ideas
- Break into sub-project specs if multiple independent subsystems

### 2. writing-plans
- Comprehensive implementation plans for agents with "zero context"
- Bite-sized tasks: 2-5 minutes each
- Exact file paths, complete code, expected commands/output
- Saved to: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- **NO PLACEHOLDERS:** No "TBD", "TODO", "implement later", "add appropriate error handling"

### 3. test-driven-development
- **Iron Law:** NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
- If you wrote code before the test → DELETE IT and start over
- Watch test fail (mandatory), write minimal code, watch it pass (mandatory), then refactor
- One behavior per test, clear names, real code (no mocks unless unavoidable)

### 4. subagent-driven-development
- Same session, fresh subagent per task (no context pollution)
- Two-stage review after each task: spec reviewer → code quality reviewer
- Implementer asks questions → answer → implement → self-review → dispatch reviewers
- Mark complete in TodoWrite, move to next task

### 5. executing-plans
- For parallel execution in separate sessions (vs. subagent-driven in same session)
- Use when tasks are independent and can run in parallel worktrees

### 6. systematic-debugging
- 4-phase approach: understand → reproduce → isolate → fix
- Don't guess, gather evidence

### 7. receiving-code-review
- How to handle incoming PR reviews
- Address feedback systematically

### 8. requesting-code-review
- Pre-commit review: security scan, quality gates, auto-fix
- Show complete diff to human partner before submitting

### 9. finishing-a-development-branch
- Clean up, final tests, merge preparation
- Ensure nothing left behind

### 10. dispatching-parallel-agents
- Swarm coordination for multiple agents
- Worktree isolation per agent

### 11. using-git-worktrees
- Create isolated worktrees per feature/plan
- Avoid branch switching contamination

### 12. using-superpowers
- Onboarding skill for new users

### 13. writing-skills
- How to create new skills following Superpowers conventions

## Multi-Platform Plugin Structure
```
.claude-plugin/     — Claude Code marketplace plugin
.codex-plugin/      — OpenAI Codex CLI plugin
.cursor-plugin/     — Cursor IDE plugin
.opencode/          — OpenCode plugin
skills/             — Core skill definitions (SKILL.md per skill)
```

## For Yggdrasil Integration
1. **Adopt methodology:** spec → plan → implement → review for every feature
2. **Create Yggdrasil skills:** Adapt Superpowers skills for Hermes/Yggdrasil conventions
3. **Git worktrees:** Use for isolated feature development in each realm
4. **Plan directory:** `docs/superpowers/plans/` in each active realm
5. **TDD enforcement:** All new Lilith code must follow RED-GREEN-REFACTOR
