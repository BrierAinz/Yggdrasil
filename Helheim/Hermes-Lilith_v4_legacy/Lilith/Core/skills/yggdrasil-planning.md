---
name: yggdrasil-planning
description: Use when asked to implement any feature, fix any bug, or refactor any code in Yggdrasil/Lilith
trigger:
  - "implement"
  - "feature"
  - "bugfix"
  - "refactor"
  - "crear"
  - "hacer"
  - "agregar"
  - "nuevo"
  - "plan"
priority: 100
---

# Yggdrasil Planning Protocol

## Iron Law
**NO PRODUCTION CODE WITHOUT A PLAN FIRST.**

Every feature, bugfix, or refactor MUST have a written plan before touching code.

## Steps

### 1. Understand the Request
- Read the user's request carefully
- Identify the scope: is it a new feature, bugfix, or refactor?
- Determine which realm of Yggdrasil is affected (Asgard, Vanaheim, etc.)

### 2. Write the Plan
- Create a markdown file in `docs/superpowers/plans/`
- Name format: `YYYY-MM-DD-{feature-name}.md`
- The plan MUST include:
  - **Goal**: What are we trying to achieve?
  - **Scope**: What is in scope and what is NOT?
  - **Files to touch**: Exact file paths
  - **Dependencies**: What needs to be done first?
  - **Tests**: How will we verify it works?
  - **Rollback plan**: How to undo if it breaks?

### 3. Get Approval (or proceed if user said "do it")
- Present the plan to the user
- Wait for approval OR proceed if user explicitly said to go ahead
- If the plan changes during implementation, UPDATE the plan file

### 4. Execute in Bite-Sized Tasks
- Break the plan into tasks of 15-30 minutes each
- Complete one task at a time
- Mark tasks as done in the plan
- Commit after each major milestone

### 5. Verify
- Run tests (if they exist)
- Test manually
- Update documentation if needed
- Mark plan as COMPLETE

## Plan Template

```markdown
# Plan: {Feature Name}

## Goal
One sentence describing what we're building.

## Scope
- IN: What we're doing
- OUT: What we're NOT doing (resist scope creep!)

## Files
- `path/to/file1.py` - what to change
- `path/to/file2.py` - what to add

## Dependencies
- [ ] Dependency 1 (link to other plan if needed)

## Tasks
- [ ] Task 1 (15 min)
- [ ] Task 2 (30 min)
- [ ] Task 3 (15 min)

## Tests
- How to verify this works

## Rollback
- `git revert` or manual steps to undo

## Notes
Any additional context
```

## Examples

### Good Plan
```
Goal: Add hot-reload to skill registry
Scope: Only skill registry, NOT the parser or orchestrator
Files:
  - Lilith/Core/skill_registry.py - add reload() method
  - Lilith/Core/config.py - add skills_dir path
Tasks:
  - [ ] Add file watcher to registry
  - [ ] Implement reload() method
  - [ ] Add tests
Tests: Modify a skill file, verify reload picks it up
```

### Bad Plan (too vague)
```
Goal: Make skills better
Files: Some files in Core/
Tasks: Improve stuff
```

## Anti-Patterns
- ❌ Starting to code before writing the plan
- ❌ Plans longer than 2 pages (break into smaller plans)
- ❌ Plans without file paths
- ❌ Plans without tests/verification
- ❌ Changing scope mid-implementation without updating plan

## Yggdrasil-Specific Notes
- Asgard = Core tech (Lilith, Hermes)
- Vanaheim = AI agents
- Alfheim = UI prototypes
- Svartalfheim = Docs/knowledge
- Muspelheim = Active dev/WIP
- Niflheim = Resources/assets
- Helheim = Graveyard/archive
- Jotunheim = Massive projects
- Midgard = Personal apps

Always specify which realm a change affects.
