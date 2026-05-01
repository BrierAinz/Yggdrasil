---
name: yggdrasil-subagent
description: Use when a plan has multiple independent tasks that can be done in parallel
trigger:
  - "parallel"
  - "multiple tasks"
  - "swarm"
  - "subagent"
  - "delegar"
  - "varias cosas"
priority: 80
---

# Yggdrasil Subagent Development

## When to Use

Use subagents when:
- A plan has 3+ independent tasks
- Tasks can be done in parallel
- Tasks don't share files (or share read-only)
- The work would take >30 minutes total

## Two-Stage Review Process

### Stage 1: Dispatch

1. **Break the plan into independent tasks**
   ```
   Plan: Add MCP support

   Task A: Implement MCP client (30 min)
   Task B: Implement MCP manager (30 min)
   Task C: Write tests for MCP (20 min)
   ```

2. **Create subagent for each task**
   ```python
   subagent = Subagent(
       task="Implement MCP client",
       context={
           "files": ["Lilith/MCP/client.py"],
           "spec": "docs/superpowers/specs/mcp-client.md",
           "dependencies": []
       }
   )
   ```

3. **Run subagents in parallel**
   ```python
   results = await asyncio.gather(
       subagent_a.run(),
       subagent_b.run(),
       subagent_c.run()
   )
   ```

### Stage 2: Review

1. **Collect all changes**
   ```python
   changes = []
   for result in results:
       changes.extend(result.get_changed_files())
   ```

2. **Review for conflicts**
   - Check if two subagents touched the same file
   - Check if imports are consistent
   - Check if tests still pass

3. **Integration review**
   ```python
   def review_integration(changes):
       issues = []

       # Check for file conflicts
       file_counts = Counter(changes)
       for file, count in file_counts.items():
           if count > 1:
               issues.append(f"File {file} modified by multiple subagents")

       # Check imports
       for change in changes:
           if change.has_missing_imports():
               issues.append(f"Missing imports in {change.file}")

       return issues
   ```

4. **Fix issues or reject**
   - If issues found: send back to subagents with feedback
   - If clean: merge all changes

## Subagent Context

Every subagent MUST receive:

```python
context = {
    # What to do
    "task": "Clear description of the task",

    # Files to touch
    "files": ["exact/path/to/file.py"],

    # What NOT to touch
    "forbidden_files": ["other/file.py"],

    # Spec to follow
    "spec": "path/to/spec.md",

    # Dependencies that must be done first
    "dependencies": ["task_a_id"],

    # Style guide
    "style": "yggdrasil-dark-fantasy",

    # Testing requirements
    "tests_required": True,
    "test_files": ["tests/test_thing.py"]
}
```

## Communication

### Subagent → Parent

```python
class SubagentResult:
    status: "success" | "failure" | "partial"
    changed_files: List[Path]
    new_files: List[Path]
    deleted_files: List[Path]
    tests_passed: bool
    notes: str  # Any issues or decisions made
```

### Parent → Subagent (feedback)

```python
class ReviewFeedback:
    approved: bool
    issues: List[str]
    suggestions: List[str]
    required_changes: List[str]  # Must fix before merge
```

## Example: Adding Swarm Feature

```python
# Parent agent
plan = Plan("Add swarm coordination")
plan.add_task("Implement SwarmManager", files=["Lilith/Swarm/manager.py"])
plan.add_task("Implement SwarmAgent", files=["Lilith/Swarm/agent.py"])
plan.add_task("Implement MessageBus", files=["Lilith/Swarm/message_bus.py"])
plan.add_task("Write tests", files=["Lilith/Swarm/tests/"])

# Dispatch
results = await plan.execute_parallel(max_workers=3)

# Review
review = ReviewIntegration(results)
if review.has_conflicts():
    # Re-run conflicting tasks sequentially
    for conflict in review.conflicts:
        await conflict.resolve_sequential()
else:
    # Merge all
    await plan.merge_all(results)
```

## Anti-Patterns

- ❌ Using subagents for tasks <10 minutes
- ❌ Not providing clear specs
- ❌ Skipping the review stage
- ❌ Allowing subagents to modify shared files
- ❌ Not checking for missing imports
- ❌ Merging without running tests

## Yggdrasil-Specific

### Realm Isolation
- Asgard tasks → Asgard subagents only
- Vanaheim tasks → Vanaheim subagents only
- Cross-realm changes → Sequential, not parallel

### File Locking
```python
# Before dispatch, lock files
for task in plan.tasks:
    for file in task.files:
        if file in locked_files:
            # Move to sequential queue
            task.sequential = True
        else:
            locked_files.add(file)
```

### Memory Sharing
Subagents can READ from shared memory but must NOT write:
```python
# Shared read-only
subagent.context["memory"] = read_only_view(memory)

# Private write
subagent.context["private_memory"] = new_memory_instance()
```
