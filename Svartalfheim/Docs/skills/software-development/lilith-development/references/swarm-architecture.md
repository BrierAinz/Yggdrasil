# Swarm Module Architecture

Detailed reference for the FASE 3 Swarm Coordination system.

## Module Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `Swarm/manager.py` | 404 | SwarmManager (spawn/kill, background coordinator, persistence) |
| `Swarm/agent.py` | 321 | SwarmAgent (thread lifecycle, file tracking, locking, code shifts) |
| `Swarm/conflict_resolver.py` | 340 | ConflictResolver (detect, auto-merge, severity analysis) |
| `Swarm/database.py` | 328 | SwarmDatabase (SQLite persistence, thread-local connections) |
| `Swarm/message_bus.py` | 177 | MessageBus (thread-safe pub/sub with broadcast/history) |
| `Swarm/executor.py` | 218 | SwarmExecutor (LLM + tools execution loop) |
| `Swarm/prompts.py` | 46 | System prompts for swarm workers |
| `tools/swarm.py` | 232 | CLI tool functions + OpenAI function definitions |

## Test Files

| File | Tests | Covers |
|------|-------|--------|
| `Swarm/tests/test_swarm.py` | 25 | MessageBus, SwarmAgent, SwarmManager, ConflictResolver, Integration |
| `Swarm/tests/test_fase4_5.py` | 15 | SwarmDatabase, Persistence, SwarmAgentLLMMode, SwarmExecutor |

All 40 tests pass.

## Key Classes and APIs

### SwarmManager (`manager.py`)

```python
class SwarmManager:
    def spawn_agent(self, task, capabilities=None, context=None, use_llm=False) -> str
    def spawn_swarm(self, task, num_agents=2, use_llm=False) -> List[str]
    def kill_agent(self, agent_id) -> bool
    def kill_all(self) -> None
    def get_status_report(self) -> dict  # {total_agents, active, complete, errors, agents, conflicts, file_locks, pending_messages}
    def get_agent_results(self, agent_id) -> dict  # {status, result, duration}
    def wait_for_completion(self, agent_ids, timeout=30.0) -> bool
    def enable_persistence(self) -> None
    def save_session(self, task=None) -> str  # Returns session ID
    def load_session(self, session_id) -> bool
    def list_saved_sessions(self, limit=20) -> list
    def get_session_history(self, session_id) -> dict  # {session, agents, messages, conflicts}
    def stop_coordinator(self) -> None

# Global singleton
_manager: Optional[SwarmManager] = None
def get_swarm_manager() -> SwarmManager
```

### SwarmAgent (`agent.py`)

```python
class AgentStatus(Enum):
    IDLE, WORKING, COMPLETE, ERROR, STOPPED

class TaskResult:
    success: bool
    output: str
    files_modified: list
    files_read: list
    error: str = None

class SwarmAgent(threading.Thread):
    # Key attributes
    agent_id: str
    task: str
    capabilities: list
    status: AgentStatus
    result: TaskResult
    files_read: set
    files_written: set

    # Key methods
    def start(self) -> None       # Thread.start()
    def stop(self) -> None        # Set stop event
    def run(self) -> None         # Main execution loop
    def _acquire_lock(self, file_path) -> bool
    def _release_lock(self, file_path) -> None
    def _assess_relevance(self, file_path, diff) -> float  # 0.0-1.0
    def notify_code_shift(self, file_path, diff) -> None
```

### MessageBus (`message_bus.py`)

```python
class MessageType(Enum):
    TASK_ASSIGN, TASK_COMPLETE, STATUS_UPDATE, ERROR,
    LOCK_REQUEST, LOCK_GRANTED, LOCK_DENIED,
    CODE_SHIFT, BROADCAST

class Message:
    msg_type: MessageType
    from_id: str
    to_id: Optional[str]  # None = broadcast
    data: dict
    timestamp: float

class MessageBus:
    def send(self, message) -> bool
    def broadcast(self, from_id, msg_type, data) -> bool
    def get_messages(self, agent_id) -> List[Message]
    def subscribe(self, agent_id) -> None
    def get_history(self, limit=100) -> List[Message]
    def clear(self) -> None
    # Properties: size
```

### ConflictResolver (`conflict_resolver.py`)

```python
class ConflictSeverity(Enum):
    LOW, MEDIUM, HIGH, CRITICAL

class ConflictResolution(Enum):
    PENDING, AUTO_MERGED, MANUAL_REQUIRED, RESOLVED

class Conflict:  # dataclass
    file_path: str
    agent_ids: List[str]
    diffs: List[str]
    severity: ConflictSeverity
    resolution: ConflictResolution = PENDING
    merge_result: Optional[str] = None
    created_at: float

class ConflictResolver:
    def detect_conflicts(self, file_modifications: Dict[str, List[Tuple]]) -> List[Conflict]
    def attempt_auto_merge(self, conflict: Conflict) -> bool
    def resolve_manually(self, conflict, resolution, merge_result) -> None
    def get_stats(self) -> dict  # {total, pending, auto_merged, manual}
```

### SwarmDatabase (`database.py`)

```python
class SwarmDatabase:
    def __init__(self, db_path=None)  # Default: project/data/swarm.db
    def save_session(self, session_id, task, **kwargs) -> None
    def get_session(self, session_id) -> Optional[dict]
    def list_sessions(self, limit=50) -> list
    def delete_session(self, session_id) -> None
    def save_agent(self, session_id, agent_data) -> None
    def get_agents(self, session_id) -> list
    def save_message(self, session_id, message_data) -> None
    def get_messages(self, session_id) -> list
    def save_conflict(self, session_id, conflict_data) -> None
    def get_conflicts(self, session_id) -> list
    def update_conflict_resolution(self, conflict_id, resolution) -> None
    def close(self) -> None

# Global singleton
_db: Optional[SwarmDatabase] = None
def get_swarm_db() -> SwarmDatabase
```

### SwarmExecutor (`executor.py`)

```python
class SwarmExecutor:
    def __init__(self, llm_client=None)  # Optional LMStudioClient
    def execute_task(self, task, context=None, capabilities=None, on_progress=None) -> dict
    # Returns: {success: bool, output: str, files_modified: list, tool_calls: int}

# Tool executor mapping
TOOL_EXECUTORS = {
    "read_file": ..., "write_file": ..., "run_terminal": ...,
    "list_directory": ..., "file_exists": ..., ...
}
```

## CLI Commands

All accessed via `/swarm <subcmd>`:

| Subcommand | Args | Description |
|-----------|------|-------------|
| `spawn` | `<task> [--agents N] [--llm]` | Create a swarm of N agents for a task |
| `status` | (none) | Show active agents, locks, conflicts |
| `kill` | `<agent_id>` | Kill specific agent |
| `killall` | (none) | Kill all agents |
| `result` | `<agent_id>` | Show agent result |
| `save` | (none) | Save current session to SQLite |
| `load` | `<session_id>` | Load a saved session |
| `history` | (none) | List saved sessions |

## Data Flow

```
User → /swarm spawn "fix auth bug" --agents 3
  → SwarmManager.spawn_swarm()
    → SwarmAgent x3 (threads)
      → SwarmExecutor.execute_task() [if --llm]
        → LMStudioClient.chat() + tool dispatch
      OR simulation mode (default)
    → MessageBus broadcast/task_complete
  → Background coordinator checks conflicts
    → ConflictResolver.detect_conflicts()
    → ConflictResolver.attempt_auto_merge() [LOW severity]
    → Notify agents via CODE_SHIFT messages

User → /swarm status
  → SwarmManager.get_status_report()

User → /swarm save
  → SwarmManager.save_session()
    → SwarmDatabase.save_session/agents/messages/conflicts