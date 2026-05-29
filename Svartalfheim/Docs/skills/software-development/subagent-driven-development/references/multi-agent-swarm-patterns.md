# Multi-Agent Swarm Patterns

Session reference: FASE 3 implementation for Hermes-Lilith project (2026-05-01).
Condensed architecture patterns for building local multi-agent systems.

## Three-Layer Architecture

```
┌─────────────────────────────────────┐
│  Orchestration (Manager)            │  ← spawn, kill, wait, status
│  - Conflict detection & resolution    │
│  - Lifecycle coordination           │
├─────────────────────────────────────┤
│  Domain (Agent/Worker)              │  ← lifecycle, file locks, task exec
│  - States: idle → working → complete │
│  - Stop event handling (threading)  │
├─────────────────────────────────────┤
│  Infrastructure (Message Bus)       │  ← pub/sub, priority, privacy
│  - Thread-safe queue operations     │
│  - Message routing by recipient     │
└─────────────────────────────────────┘
```

## Message Bus Design Decisions

**Priority queue vs FIFO:** Use `queue.PriorityQueue` with `(priority, timestamp, message)` tuples. Lower number = higher priority. This prevents urgent control messages from being stuck behind bulk task updates.

**Private message routing:** Messages with `to_id != None` are ONLY delivered to that agent. The `get_messages()` method must drain the queue, filter by recipient, and **re-enqueue** messages not meant for the caller. Without re-enqueue, private messages are lost when the wrong agent polls.

**History retention:** Keep a separate `deque(maxlen=N)` for history. The live queue is for pending delivery; history is for audit/debug. Don't conflate them.

## Agent Lifecycle & The Stop Race Condition

When `stop()` is called externally while `_run()` is executing:

1. `stop()` sets `_stop_event` and changes status to STOPPED
2. `_run()` may be mid-execution and will eventually finish `_execute_task()`
3. **Bug:** `_run()` then overwrites STOPPED with ERROR because the stopped task returns `success=False`
4. **Fix:** In the completion handler, check `if self.status == AgentStatus.STOPPED: pass` before setting COMPLETE/ERROR
5. **Fix:** In the exception handler, check `if self.status != AgentStatus.STOPPED:` before setting ERROR

```python
# WRONG — overwrites the STOPPED status
self.status = AgentStatus.COMPLETE if result.success else AgentStatus.ERROR

# RIGHT — respects external stop
with self._lock:
    if self.status == AgentStatus.STOPPED:
        pass  # preserve external stop
    else:
        self.status = AgentStatus.COMPLETE if result.success else AgentStatus.ERROR
```

## File Lock Tracking for Conflict Detection

Each agent tracks `files_read` and `files_written` as sets. The manager aggregates across all agents to detect conflicts:

```python
file_mods = {}
for aid, agent in mgr.agents.items():
    for f in agent.files_written:
        file_mods.setdefault(f, []).append((aid, diff))

conflicts = resolver.detect_conflicts(file_mods)
# A conflict exists when len(file_mods[f]) > 1
```

**Severity heuristic:**
- HIGH: >2 agents, or file in `CRITICAL_FILES` list
- MEDIUM: 2 agents, file not critical
- LOW: 2 agents, trivial file (config, log, etc.)

**Resolution strategy:**
- LOW severity → auto-merge (concatenate diffs, mark resolved)
- MEDIUM/HIGH → mark MANUAL_REQUIRED, notify user

## OpenAI-Style Tool Integration

For LLM-accessible swarm control, expose functions matching the OpenAI tool schema:

```python
def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "spawn_swarm",
                "description": "Spawn N agents to work on a task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                        "num_agents": {"type": "integer", "default": 3},
                    },
                    "required": ["task"],
                },
            },
        },
    ]
```

Register in the tools package `__init__.py`:
```python
from .swarm import get_tools as swarm_tools
# In get_all_tools(): all_tools.extend(swarm_tools())
```

## Testing Multi-Agent Systems

**Timing is the enemy.** Agent tests are inherently flaky due to thread scheduling. Strategies:

1. **Generous sleeps:** Use `time.sleep(0.8-1.0)` instead of `0.1-0.3`. The cost is negligible; flakiness is expensive.
2. **Wait loops with timeout:** For `wait_for_completion()`, poll status with a max timeout rather than fixed sleep.
3. **Isolate tests:** Each test gets a fresh `SwarmManager()` and `MessageBus()`. Never share state.
4. **Test the seams:** Unit test message_bus, agent, manager, and resolver separately. Integration test only the full workflow.

## CLI Integration Pattern

For terminal-based agents, add a `/swarm` command namespace:

```
/swarm spawn <task> [n]  → create agents
/swarm status            → table view
/swarm kill <id>         → stop agent
/swarm killall           → stop all
```

Parse with simple split: `parts = args.split(); subcmd = parts[0]`.

## Singleton Pattern for Manager

The manager should be a singleton (one swarm per session):

```python
_manager_instance = None

def get_swarm_manager() -> SwarmManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SwarmManager()
    return _manager_instance
```

This allows both CLI commands and tool functions to access the same swarm instance.
