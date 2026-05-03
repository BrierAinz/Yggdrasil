# PROYECTO YGGDRASIL: LILITH EVOLUTION
## Plan Maestro de Integración Ghostty + Superpowers + jcode

**Fecha:** 2026-05-01
**Versión:** 1.0
**Duración Estimada:** 4-6 semanas (trabajo intensivo)
**Estado:** PLANNING

---

## RESUMEN EJECUTIVO

Este plan integra las mejores ideas de 3 proyectos líderes en agentes de código:

| Proyecto | Qué Tomamos | Para Qué |
|----------|-------------|----------|
| **Ghostty** | GPU rendering, libghostty, multi-pane | Dashboard de Lilith de alto rendimiento |
| **Superpowers** | Skills framework, TDD estricto, subagent-dev | Metodología de desarrollo para Yggdrasil |
| **jcode** | Semantic memory, swarm, MCP, hot-reload | Arquitectura modular de Lilith v3.0 |

**Resultado:** Lilith v3.0 - Un agente de código con memoria humana, swarm intelligence, UI GPU-accelerated, y metodología de desarrollo probada.

---

## ARQUITECTURA OBJETIVO: LILITH v3.0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LILITH v3.0 - ASGARD                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   lilith-    │  │   lilith-    │  │   lilith-    │  │   lilith-    │    │
│  │    core      │  │   memory     │  │    swarm     │  │     mcp      │    │
│  │  (orquestador)│  │  (semantic)  │  │ (multi-agent)│  │  (dynamic)   │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │              │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐  │
│  │   lilith-    │  │   lilith-    │  │   lilith-    │  │   lilith-    │  │
│  │    tools     │  │  providers   │  │    tui       │  │   config     │  │
│  │  (30+ tools) │  │ (multi-LLM)  │  │  (terminal)  │  │  (profiles)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    lilith-dashboard (GPU/WebGPU)                     │   │
│  │         Multi-pane · Terminal widget · Mermaid · Diff viewer        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## FASES DE IMPLEMENTACIÓN

### FASE 0: FOUNDATION (Días 1-3)
**Objetivo:** Preparar el terreno para el desarrollo masivo.

#### 0.1 Estructura de Directorios Superpowers
```
D:\Proyectos\Yggdrasil\Asgard\Hermes-Lilith\
├── docs\superpowers\plans\          # Plans de implementación
│   ├── 2026-05-01-fase0-foundation.md
│   ├── 2026-05-01-fase1-skills.md
│   ├── 2026-05-01-fase2-memory.md
│   ├── 2026-05-01-fase3-swarm.md
│   ├── 2026-05-01-fase4-mcp.md
│   ├── 2026-05-01-fase5-dashboard.md
│   └── 2026-05-01-fase6-integration.md
├── docs\superpowers\specs\          # Especificaciones de features
├── docs\superpowers\reviews\        # Code reviews
└── .worktrees\                       # Git worktrees para aislamiento
```

#### 0.2 Git Worktrees Setup
```bash
# Crear worktrees para desarrollo paralelo
# Cada feature se desarrolla en su propio worktree aislado
git worktree add ../Hermes-Lilith-fase1-skills fase1-skills
git worktree add ../Hermes-Lilith-fase2-memory fase2-memory
```

#### 0.3 Skills Base de Superpowers
Crear los siguientes skills en `~/.hermes/skills/`:

| Skill | Descripción | Trigger |
|-------|-------------|---------|
| `yggdrasil-planning` | Escribir planes bite-sized | Antes de tocar código |
| `yggdrasil-tdd` | RED-GREEN-REFACTOR estricto | Implementar cualquier feature |
| `yggdrasil-subagent` | Dispatch + 2-stage review | Planes con tareas independientes |
| `yggdrasil-debugging` | 4-phase systematic debugging | Cuando hay bugs |
| `yggdrasil-review` | Pre-commit code review | Antes de commitear |

**Tareas:**
- [ ] Crear directorio `docs/superpowers/`
- [ ] Escribir skill `yggdrasil-planning`
- [ ] Escribir skill `yggdrasil-tdd`
- [ ] Escribir skill `yggdrasil-subagent`
- [ ] Escribir skill `yggdrasil-debugging`
- [ ] Escribir skill `yggdrasil-review`
- [ ] Setup git worktrees
- [ ] Commit inicial con estructura

---

### FASE 1: SKILLS FRAMEWORK (Días 4-7)
**Objetivo:** Implementar hot-reload de skills y sistema de skills dinámico (inspirado en Superpowers + jcode).

#### 1.1 Skill Registry Hot-Reload
```python
# Lilith/Core/skill_registry.py
class SkillRegistry:
    """Registro de skills con hot-reload."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}
        self._watcher = FileWatcher(skills_dir)
        self._load_all()
        self._start_watching()

    def reload(self) -> List[str]:
        """Hot-reload skills sin restart."""
        reloaded = []
        for skill_file in self.skills_dir.glob("*.md"):
            skill = self._parse_skill(skill_file)
            if skill.name in self.skills:
                if self.skills[skill.name].version != skill.version:
                    self.skills[skill.name] = skill
                    reloaded.append(skill.name)
            else:
                self.skills[skill.name] = skill
                reloaded.append(skill.name)
        return reloaded

    def get_triggered_skills(self, context: str) -> List[Skill]:
        """Devuelve skills que deben activarse para este contexto."""
        triggered = []
        for skill in self.skills.values():
            if skill.should_trigger(context):
                triggered.append(skill)
        return sorted(triggered, key=lambda s: s.priority)
```

#### 1.2 Skill Parser (YAML frontmatter + markdown body)
```yaml
---
name: yggdrasil-tdd
description: Use when implementing any feature or bugfix
version: 1.0.0
trigger:
  - "implement"
  - "feature"
  - "bugfix"
  - "refactor"
priority: 100
---

# Test-Driven Development (TDD)

## Iron Law
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

## Red-Green-Refactor
...
```

#### 1.3 Skill Auto-Trigger
```python
# En el orchestrator, antes de cada respuesta:
def _inject_skills(self, user_input: str) -> str:
    """Inyecta skills relevantes en el contexto."""
    triggered = self.skill_registry.get_triggered_skills(user_input)
    if triggered:
        skill_context = "\n\n=== ACTIVE SKILLS ===\n"
        for skill in triggered:
            skill_context += f"\n[{skill.name}]\n{skill.content}\n"
        skill_context += "\n=== END SKILLS ===\n"
        return skill_context
    return ""
```

**Tareas:**
- [ ] Crear `Lilith/Core/skill_registry.py`
- [ ] Crear `Lilith/Core/skill_parser.py`
- [ ] Implementar hot-reload con watchdog
- [ ] Integrar auto-trigger en orchestrator
- [ ] Migrar skills existentes al nuevo formato
- [ ] Tests: skill parsing, hot-reload, auto-trigger
- [ ] Commit

---

### FASE 2: SEMANTIC MEMORY v2.0 (Días 8-14)
**Objetivo:** Replicar el sistema de memoria de jcode (semantic embeddings + graph + sideagent).

#### 2.1 Arquitectura de Memoria
```
┌─────────────────────────────────────────────────────────────┐
│                    SEMANTIC MEMORY v2.0                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Episodic   │───→│   Graph     │←───│  Semantic   │     │
│  │  (turnos)   │    │  (relations)│    │  (vectors)  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ↓                                │
│                   ┌─────────────┐                          │
│                   │   Memory    │                          │
│                   │  Sideagent │                          │
│                   │ (verifies)  │                          │
│                   └─────────────┘                          │
│                            ↓                                │
│                   ┌─────────────┐                          │
│                   │  Context    │                          │
│                   │  Injection  │                          │
│                   └─────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 Memory Graph (SQLite + NetworkX)
```python
# Lilith/memory/graph.py
class MemoryGraph:
    """Grafo de memoria con relaciones semánticas."""

    def __init__(self, db_path: Path):
        self.db = db_path
        self.graph = nx.DiGraph()  # NetworkX para análisis de grafos
        self._load_from_db()

    def add_episode(self, episode: Episode) -> str:
        """Agrega un episodio al grafo y devuelve su ID."""
        # Crear nodo
        self.graph.add_node(
            episode.id,
            type="episode",
            content=episode.content,
            embedding=episode.embedding,
            timestamp=episode.timestamp,
            entities=episode.entities
        )

        # Crear edges a entidades
        for entity in episode.entities:
            if entity.id not in self.graph:
                self.graph.add_node(entity.id, type="entity", **entity.to_dict())
            self.graph.add_edge(episode.id, entity.id, relation="mentions")

        # Crear edges a episodios similares
        similar = self.find_similar(episode.embedding, threshold=0.85)
        for sim_id, score in similar:
            self.graph.add_edge(episode.id, sim_id, relation="similar", weight=score)

        return episode.id

    def query(self, query_embedding: np.ndarray, max_hops: int = 2) -> List[MemoryNode]:
        """Query el grafo con un embedding, navegando por relaciones."""
        # 1. Encontrar nodos similares por cosine similarity
        seeds = self._cosine_search(query_embedding, top_k=5)

        # 2. Expandir por hops en el grafo
        results = set(seeds)
        for hop in range(max_hops):
            new_nodes = set()
            for node in results:
                neighbors = self.graph.neighbors(node)
                new_nodes.update(neighbors)
            results.update(new_nodes)

        # 3. Re-rank por relevancia combinada
        return self._rerank(results, query_embedding)
```

#### 2.3 Memory Sideagent
```python
# Lilith/memory/sideagent.py
class MemorySideagent:
    """Agente verificador de relevancia de memoria."""

    def __init__(self, llm_client: LMStudioClient):
        self.llm = llm_client

    async def verify_relevance(
        self,
        query: str,
        memories: List[MemoryNode]
    ) -> List[VerifiedMemory]:
        """Verifica que las memorias sean relevantes para la query."""

        prompt = f"""You are a memory relevance verifier.

Query: {query}

Memories to verify:
{self._format_memories(memories)}

For each memory, rate relevance 0-10 and explain why.
Return ONLY memories with score >= 7.
"""

        response = await self.llm.complete(prompt)
        verified = self._parse_verification(response)
        return verified

    async def consolidate(self, memories: List[MemoryNode]) -> MemoryNode:
        """Consolida múltiples memorias en una sola."""
        prompt = f"""Consolidate these related memories into one coherent memory:

{self._format_memories(memories)}

Output a single, comprehensive memory that captures all important information.
"""
        return MemoryNode(content=await self.llm.complete(prompt))
```

#### 2.4 Session Search (RAG)
```python
# Lilith/memory/session_search.py
class SessionSearch:
    """Búsqueda RAG sobre sesiones previas."""

    def __init__(self, sessions_dir: Path, embedder: EmbeddingModel):
        self.sessions_dir = sessions_dir
        self.embedder = embedder
        self.index = self._build_index()

    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Busca en sesiones previas."""
        query_emb = self.embedder.encode([query])[0]

        results = []
        for session_file in self.sessions_dir.glob("*.json"):
            session = self._load_session(session_file)
            for turn in session.turns:
                turn_emb = self.embedder.encode([turn.content])[0]
                score = cosine_similarity(query_emb, turn_emb)
                if score > 0.7:
                    results.append(SearchResult(
                        session_id=session.id,
                        turn=turn,
                        score=score
                    ))

        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]
```

#### 2.5 Ambient Mode (Memory Consolidation)
```python
# Lilith/memory/ambient.py
class AmbientMode:
    """Consolidación automática de memoria en background."""

    def __init__(self, memory_graph: MemoryGraph, sideagent: MemorySideagent):
        self.graph = memory_graph
        self.sideagent = sideagent
        self.consolidation_interval = timedelta(hours=1)

    async def run(self):
        """Loop de consolidación continua."""
        while True:
            await asyncio.sleep(self.consolidation_interval.total_seconds())

            # 1. Detectar memorias redundantes
            redundant = self._find_redundant_memories()

            # 2. Consolidar grupos relacionados
            for group in redundant:
                consolidated = await self.sideagent.consolidate(group)
                self.graph.replace_group(group, consolidated)

            # 3. Detectar memorias obsoletas
            stale = self._find_stale_memories()
            for memory in stale:
                memory.mark_stale()

            # 4. Resolver conflictos
            conflicts = self._find_conflicts()
            for conflict in conflicts:
                resolved = await self.sideagent.resolve_conflict(conflict)
                self.graph.update_conflict(conflict, resolved)
```

**Tareas:**
- [ ] Crear `Lilith/memory/graph.py` con NetworkX
- [ ] Crear `Lilith/memory/sideagent.py`
- [ ] Crear `Lilith/memory/session_search.py`
- [ ] Crear `Lilith/memory/ambient.py`
- [ ] Refactorizar `enhanced.py` a `semantic_memory.py`
- [ ] Implementar episodios con embeddings por turno
- [ ] Implementar memory injection en orchestrator
- [ ] Tests: graph query, sideagent, session search
- [ ] Commit

---

### FASE 3: SWARM COORDINATION (Días 15-21)
**Objetivo:** Implementar multi-agent coordination (inspirado en jcode swarm).

#### 3.1 Swarm Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      SWARM COORDINATION                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │ Coordinator │←────────→│  Message    │                   │
│  │   Agent     │         │   Bus       │                   │
│  └──────┬──────┘         └──────┬──────┘                   │
│         │                       │                           │
│    ┌────┴────┬────────┬────────┴────┐                      │
│    ↓         ↓        ↓             ↓                       │
│ ┌────┐   ┌────┐   ┌────┐       ┌────┐                     │
│ │W1  │   │W2  │   │W3  │  ...  │Wn  │                     │
│ │(fs)│   │(web)│  │(db)│       │(ai)│                     │
│ └────┘   └────┘   └────┘       └────┘                     │
│                                                             │
│  Conflict Resolution:                                       │
│  - File locking                                             │
│  - Diff notifications                                       │
│  - Auto-merge cuando sea seguro                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Swarm Manager
```python
# Lilith/Swarm/manager.py
class SwarmManager:
    """Gestiona múltiples agentes trabajando en el mismo repo."""

    def __init__(self, repo_path: Path):
        self.repo = repo_path
        self.agents: Dict[str, SwarmAgent] = {}
        self.message_bus = MessageBus()
        self.file_locks: Dict[str, str] = {}  # file -> agent_id
        self.conflict_resolver = ConflictResolver()

    def spawn_agent(
        self,
        task: str,
        capabilities: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Spawnea un nuevo agente worker."""
        agent_id = f"agent_{len(self.agents)}_{uuid4().hex[:8]}"

        agent = SwarmAgent(
            id=agent_id,
            task=task,
            capabilities=capabilities,
            context=context,
            message_bus=self.message_bus,
            file_locks=self.file_locks
        )

        self.agents[agent_id] = agent
        agent.start()
        return agent_id

    def notify_file_change(self, agent_id: str, file_path: str, diff: str):
        """Notifica a otros agentes cuando un archivo cambia."""
        for other_id, other_agent in self.agents.items():
            if other_id != agent_id:
                if file_path in other_agent.files_read:
                    # El otro agente había leído este archivo
                    other_agent.notify_code_shift(file_path, diff)

    async def coordinate(self):
        """Loop principal de coordinación."""
        while self.agents:
            # Revisar mensajes del bus
            messages = self.message_bus.get_messages()
            for msg in messages:
                await self._handle_message(msg)

            # Revisar conflictos
            conflicts = self.conflict_resolver.detect_conflicts(self.agents)
            for conflict in conflicts:
                await self._resolve_conflict(conflict)

            await asyncio.sleep(1)
```

#### 3.3 Agent Worker
```python
# Lilith/Swarm/agent.py
class SwarmAgent:
    """Agente worker en el swarm."""

    def __init__(
        self,
        id: str,
        task: str,
        capabilities: List[str],
        context: Dict[str, Any],
        message_bus: MessageBus,
        file_locks: Dict[str, str]
    ):
        self.id = id
        self.task = task
        self.capabilities = capabilities
        self.context = context
        self.message_bus = message_bus
        self.file_locks = file_locks
        self.files_read: Set[str] = set()
        self.files_written: Set[str] = set()
        self.status = AgentStatus.IDLE

    def notify_code_shift(self, file_path: str, diff: str):
        """Maneja cuando código cambia bajo sus pies."""
        # Decidir si el cambio es relevante
        relevance = self._assess_relevance(file_path, diff)

        if relevance > 0.8:
            # Es muy relevante, revisar el diff
            self.message_bus.send(
                to=self.id,
                from_="system",
                type="code_shift",
                data={"file": file_path, "diff": diff}
            )
            self.status = AgentStatus.REVIEWING
        elif relevance > 0.5:
            # Moderadamente relevante, notificar pero continuar
            self.message_bus.send(
                to=self.id,
                from_="system",
                type="code_shift_notice",
                data={"file": file_path, "summary": self._summarize_diff(diff)}
            )

    def run(self):
        """Ejecuta la tarea asignada."""
        self.status = AgentStatus.WORKING

        # 1. Leer contexto necesario
        for file in self.context.get("files_to_read", []):
            if self._acquire_lock(file):
                content = self._read_file(file)
                self.files_read.add(file)

        # 2. Ejecutar tarea
        result = self._execute_task()

        # 3. Liberar locks
        for file in self.files_written:
            self._release_lock(file)

        # 4. Notificar completado
        self.message_bus.broadcast(
            from_=self.id,
            type="task_complete",
            data={"result": result}
        )

        self.status = AgentStatus.COMPLETE
```

#### 3.4 Subagent Tool (para que un agente spawnee más agentes)
```python
# Lilith/tools/swarm.py
@tool("spawn_swarm")
def spawn_swarm(task: str, num_agents: int = 2, capabilities: List[str] = None) -> str:
    """
    Spawnea un swarm de agentes para trabajar en paralelo.

    Args:
        task: Descripción de la tarea a dividir
        num_agents: Número de agentes worker
        capabilities: Capacidades requeridas

    Returns:
        IDs de los agentes spawneados
    """
    swarm = get_swarm_manager()

    # Dividir la tarea en subtareas
    subtasks = divide_task(task, num_agents)

    agent_ids = []
    for subtask in subtasks:
        agent_id = swarm.spawn_agent(
            task=subtask,
            capabilities=capabilities or ["coding"],
            context={"parent_task": task}
        )
        agent_ids.append(agent_id)

    return f"Swarm spawned: {', '.join(agent_ids)}"

@tool("swarm_status")
def swarm_status() -> str:
    """Muestra el estado de todos los agentes en el swarm."""
    swarm = get_swarm_manager()
    return swarm.get_status_report()
```

**Tareas:**
- [ ] Crear `Lilith/Swarm/manager.py`
- [ ] Crear `Lilith/Swarm/agent.py`
- [ ] Crear `Lilith/Swarm/message_bus.py`
- [ ] Crear `Lilith/Swarm/conflict_resolver.py`
- [ ] Crear `Lilith/tools/swarm.py`
- [ ] Implementar file locking
- [ ] Implementar code shift notifications
- [ ] Tests: spawn, coordinate, conflict resolution
- [ ] Commit

---

### FASE 4: MCP + DYNAMIC TOOLS (Días 22-28)
**Objetivo:** Implementar MCP client y dynamic tool registration (jcode-style).

#### 4.1 MCP Client
```python
# Lilith/MCP/client.py
class MCPClient:
    """Cliente MCP para conectar con servers externos."""

    def __init__(self, server_config: Dict[str, Any]):
        self.name = server_config["name"]
        self.command = server_config["command"]
        self.args = server_config.get("args", [])
        self.env = server_config.get("env", {})
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: List[MCPTool] = []

    async def connect(self):
        """Inicia el proceso MCP y hace handshake."""
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env}
        )

        # MCP Initialize handshake
        await self._send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lilith", "version": "3.0.0"}
            }
        })

        init_response = await self._receive()

        # List tools
        await self._send({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })

        tools_response = await self._receive()
        self.tools = [MCPTool.from_dict(t) for t in tools_response["result"]["tools"]]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Llama a una tool del server MCP."""
        await self._send({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        })

        response = await self._receive()
        return response["result"]["content"]
```

#### 4.2 MCP Manager
```python
# Lilith/MCP/manager.py
class MCPManager:
    """Gestiona múltiples servers MCP."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.clients: Dict[str, MCPClient] = {}
        self._load_config()

    def _load_config(self):
        """Carga configuración de MCP servers."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = json.load(f)

            for name, server_config in config.get("servers", {}).items():
                self.clients[name] = MCPClient({**server_config, "name": name})

    async def connect_all(self):
        """Conecta a todos los servers configurados."""
        for client in self.clients.values():
            await client.connect()

    def get_all_tools(self) -> List[MCPTool]:
        """Devuelve todas las tools de todos los servers."""
        tools = []
        for client in self.clients.values():
            tools.extend(client.tools)
        return tools

    async def add_server(self, name: str, config: Dict[str, Any]):
        """Agrega un nuevo server MCP dinámicamente."""
        client = MCPClient({**config, "name": name})
        await client.connect()
        self.clients[name] = client

        # Guardar en config
        self._save_config()
```

#### 4.3 Dynamic Tool Registry
```python
# Lilith/Core/dynamic_tools.py
class DynamicToolRegistry:
    """Registro de tools con soporte para dinámico."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.mcp_manager: Optional[MCPManager] = None

    def register(self, tool: Tool):
        """Registra una tool nativa."""
        self.tools[tool.name] = tool

    def register_mcp_tools(self, mcp_manager: MCPManager):
        """Registra todas las tools de MCP servers."""
        self.mcp_manager = mcp_manager
        for tool in mcp_manager.get_all_tools():
            self.tools[tool.name] = tool

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Ejecuta una tool por nombre."""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        if isinstance(tool, MCPTool):
            # Es una tool MCP
            return await self.mcp_manager.clients[tool.server_name].call_tool(
                tool.name, arguments
            )
        else:
            # Es una tool nativa
            return await tool.execute(**arguments)

    def list_tools(self) -> List[ToolInfo]:
        """Lista todas las tools disponibles."""
        return [
            ToolInfo(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
                source="mcp" if isinstance(t, MCPTool) else "native"
            )
            for t in self.tools.values()
        ]
```

#### 4.4 MCP Config File
```json
// ~/.lilith/mcp.json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/home/user"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "~/data.db"],
      "env": {}
    }
  }
}
```

**Tareas:**
- [ ] Crear `Lilith/MCP/client.py`
- [ ] Crear `Lilith/MCP/manager.py`
- [ ] Crear `Lilith/MCP/protocol.py` (JSON-RPC types)
- [ ] Crear `Lilith/Core/dynamic_tools.py`
- [ ] Refactorizar tool registry actual
- [ ] Implementar `tools/mcp_connect`, `tools/mcp_list`, `tools/mcp_disconnect`
- [ ] Tests: MCP handshake, tool call, dynamic registration
- [ ] Commit

---

### FASE 5: DASHBOARD v2.0 GPU-ACCELERATED (Días 29-35)
**Objetivo:** Reemplazar React DOM con rendering GPU (inspirado en Ghostty).

#### 5.1 Dashboard Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                  LILITH DASHBOARD v2.0                      │
│                    (GPU-Accelerated)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WebGPU Canvas (60+ FPS)                             │   │
│  │  ┌──────────┐┌──────────┐┌──────────┐┌──────────┐ │   │
│  │  │  Pane 1  ││  Pane 2  ││  Pane 3  ││  Pane 4  │ │   │
│  │  │ (Chat)   ││(Terminal)││ (Files)  ││ (Memory) │ │   │
│  │  │          ││          ││          ││          │ │   │
│  │  │          ││          ││          ││          │ │   │
│  │  └──────────┘└──────────┘└──────────┘└──────────┘ │   │
│  │                                                     │   │
│  │  Info Widgets (negative space):                    │   │
│  │  ┌────┐ ┌────┐ ┌────┐                              │   │
│  │  │CPU │ │RAM │ │Net │                              │   │
│  │  └────┘ └────┘ └────┘                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Renderers:                                                │
│  • Text (glyph atlas GPU)                                  │
│  • Mermaid (native Rust/WASM, 1800x faster)               │
│  • Diff (side-by-side GPU)                                 │
│  • Terminal (xterm.js or native)                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Tech Stack
| Component | Tecnología | Razón |
|-----------|-----------|-------|
| Renderer | WebGPU / WebGL | GPU acceleration, 60+ FPS |
| UI Framework | Custom (no React) | Menor overhead, control total |
| Text Rendering | Glyph Atlas GPU | Rápido, escalable |
| Mermaid | mermaid-rs-renderer (WASM) | 1800x faster, no browser |
| Terminal | xterm.js + WebGL addon | Proven, embeddable |
| Layout | Flexbox custom | Multi-pane, drag-drop |
| Comms | WebSocket | Real-time con backend |

#### 5.3 Pane System
```typescript
// dashboard/src/panes/PaneManager.ts
interface PaneConfig {
  id: string;
  type: 'chat' | 'terminal' | 'files' | 'memory' | 'diff' | 'mermaid';
  position: { x: number; y: number };
  size: { width: number; height: number };
  title: string;
  content?: any;
}

class PaneManager {
  panes: Map<string, Pane>;
  layout: LayoutEngine;

  addPane(config: PaneConfig): Pane {
    const pane = new Pane(config);
    this.panes.set(config.id, pane);
    this.layout.add(pane);
    return pane;
  }

  splitPane(paneId: string, direction: 'horizontal' | 'vertical'): Pane {
    const original = this.panes.get(paneId);
    const newPane = original.clone();
    this.layout.split(original, newPane, direction);
    return newPane;
  }

  render(ctx: GPUCanvasContext) {
    // Render all panes in a single pass
    for (const pane of this.panes.values()) {
      pane.render(ctx);
    }
  }
}
```

#### 5.4 Info Widgets (Negative Space)
```typescript
// dashboard/src/widgets/InfoWidgets.ts
class InfoWidgetManager {
  widgets: Widget[];

  layoutWidgets(availableSpace: Rect) {
    // Only use negative space (corners, edges)
    // Never overlap main content
    const positions = this.findNegativeSpace(availableSpace);

    for (let i = 0; i < this.widgets.length; i++) {
      if (positions[i]) {
        this.widgets[i].position = positions[i];
        this.widgets[i].visible = true;
      } else {
        this.widgets[i].visible = false;
      }
    }
  }

  findNegativeSpace(container: Rect): Rect[] {
    // Find empty areas in the layout
    // Return array of rectangles for widgets
  }
}
```

#### 5.5 Terminal Widget (Ghostty-inspired)
```typescript
// dashboard/src/panes/TerminalPane.ts
class TerminalPane extends Pane {
  terminal: XTerm;

  constructor() {
    super({ type: 'terminal' });
    this.terminal = new XTerm({
      rendererType: 'webgl',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 14,
      theme: {
        background: '#0a0a0f',
        foreground: '#e0e0e0',
        cursor: '#ff3366',
        selection: '#ff336640',
        black: '#1a1a2e',
        red: '#ff3366',
        green: '#00ff88',
        yellow: '#ffcc00',
        blue: '#3366ff',
        magenta: '#ff00ff',
        cyan: '#00ffff',
        white: '#f0f0f0'
      }
    });
  }

  attachToProcess(process: Process) {
    // Conectar a proceso real (PowerShell, bash, etc.)
    process.stdout.on('data', data => this.terminal.write(data));
    this.terminal.onData(data => process.stdin.write(data));
  }
}
```

**Tareas:**
- [ ] Crear nuevo dashboard en `Lilith/Dashboard/v2/`
- [ ] Setup WebGPU canvas renderer
- [ ] Implementar PaneManager
- [ ] Implementar InfoWidgetManager
- [ ] Integrar xterm.js con WebGL
- [ ] Integrar mermaid-rs-renderer (WASM)
- [ ] Dark fantasy theme (colores de Lilith)
- [ ] WebSocket connection a backend
- [ ] Tests: rendering, layout, terminal
- [ ] Commit

---

### FASE 6: INTEGRACIÓN + POLISH (Días 36-42)
**Objetivo:** Integrar todo, testing, documentación, release.

#### 6.1 Integration Checklist
- [ ] Todos los módulos importan correctamente
- [ ] Orchestrator usa: skills + memory v2 + swarm + MCP + dynamic tools
- [ ] Dashboard se conecta a backend vía WebSocket
- [ ] CLI funciona sin dashboard (headless mode)
- [ ] Config unificada en `~/.lilith/config.toml`

#### 6.2 Config Unificada (jcode-style)
```toml
# ~/.lilith/config.toml
[provider]
default_provider = "lmstudio"
default_model = "auto"

[providers.lmstudio]
type = "openai-compatible"
base_url = "http://localhost:1234/v1"
api_key = "not-needed"

[providers.openrouter]
type = "openrouter"
api_key_env = "OPENROUTER_API_KEY"

[memory]
enabled = true
embedding_model = "all-MiniLM-L6-v2"
consolidation_interval = 3600  # seconds
max_episodes = 10000

[swarm]
enabled = true
max_agents = 5
conflict_resolution = "auto"

[mcp]
config_path = "~/.lilith/mcp.json"
auto_connect = true

[dashboard]
enabled = true
gpu_acceleration = true
theme = "dark-fantasy"
font = "JetBrains Mono"

[skills]
directory = "~/.lilith/skills"
hot_reload = true
auto_trigger = true
```

#### 6.3 Testing Suite
```python
# tests/test_integration.py
class TestLilithIntegration:
    """Tests de integración end-to-end."""

    async def test_full_conversation_flow(self):
        """Test: usuario → skill trigger → memory query → tool call → response."""
        lilith = LilithApp(config=TEST_CONFIG)
        await lilith.start()

        response = await lilith.chat("Busca en Google sobre Python async")

        assert response.contains("Python")
        assert lilith.memory.get_episode_count() > 0
        assert lilith.skill_registry.last_triggered == "yggdrasil-planning"

    async def test_swarm_coordination(self):
        """Test: múltiples agentes trabajando sin conflictos."""
        swarm = SwarmManager()

        agent1 = swarm.spawn_agent("Escribe tests para auth.py")
        agent2 = swarm.spawn_agent("Escribe tests para db.py")

        await swarm.coordinate()

        assert agent1.status == AgentStatus.COMPLETE
        assert agent2.status == AgentStatus.COMPLETE
        assert not swarm.conflict_resolver.has_conflicts()

    async def test_mcp_dynamic_tools(self):
        """Test: agregar server MCP dinámicamente."""
        lilith = LilithApp(config=TEST_CONFIG)

        await lilith.mcp.add_server("test", {
            "command": "echo",
            "args": ['{"tools": [{"name": "test_tool"}]}']
        })

        tools = lilith.tool_registry.list_tools()
        assert any(t.name == "test_tool" for t in tools)
```

#### 6.4 Documentation
- [ ] README.md actualizado con arquitectura v3.0
- [ ] docs/ARCHITECTURE.md con diagramas
- [ ] docs/SKILLS.md cómo escribir skills
- [ ] docs/API.md referencia de API
- [ ] docs/DEPLOYMENT.md cómo deployar

#### 6.5 Release
- [ ] Version bump a 3.0.0
- [ ] Tag `v3.0.0`
- [ ] Release notes con todas las features
- [ ] Backup de v2.x

---

## CRONOGRAMA DETALLADO

| Semana | Días | Fase | Entregable |
|--------|------|------|-----------|
| 1 | 1-3 | F0: Foundation | Estructura Superpowers, skills base, worktrees |
| 1 | 4-7 | F1: Skills | Hot-reload, auto-trigger, skill registry |
| 2 | 8-14 | F2: Memory v2 | Semantic memory, graph, sideagent, ambient |
| 3 | 15-21 | F3: Swarm | Multi-agent coordination, conflict resolution |
| 3 | 22-28 | F4: MCP | MCP client, dynamic tools, config |
| 4 | 29-35 | F5: Dashboard | GPU rendering, panes, terminal widget |
| 4 | 36-42 | F6: Integration | Testing, docs, release v3.0.0 |

---

## RECURSOS NECESARIOS

### Hardware (ya disponible)
- CPU: AMD Ryzen 5 5500 (6c/12t) ✓
- RAM: 48GB DDR4 ✓
- GPU: RTX 3060 4GB VRAM ✓
- SSD: 960GB + 500GB ✓

### Software
- Python 3.11+ ✓
- Node.js 20+ (para dashboard v2)
- Rust (para mermaid-rs-renderer WASM)
- LM Studio (ya configurado) ✓

### Dependencias Python Nuevas
```
networkx>=3.0          # Grafo de memoria
watchdog>=3.0          # Hot-reload de files
aiohttp>=3.9           # Async HTTP (MCP, swarm)
websockets>=12.0       # Dashboard real-time
python-socketio>=5.0   # Socket.IO para dashboard
```

### Dependencias Node Nuevas
```json
{
  "@webgpu/types": "^0.1.40",
  "xterm": "^5.3.0",
  "xterm-addon-webgl": "^0.16.0",
  "xterm-addon-fit": "^0.8.0"
}
```

---

## RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| WebGPU no soportado en Windows | Media | Alto | Fallback a WebGL |
| sentence-transformers lento en CPU | Alta | Medio | Usar modelo más ligero o GPU |
| MCP servers no disponibles | Baja | Medio | Graceful degradation |
| Swarm conflictos complejos | Media | Medio | Manual merge fallback |
| Memory graph crece indefinidamente | Media | Alto | Auto-pruning, TTL |

---

## MÉTRICAS DE ÉXITO

| Métrica | v2.x Actual | v3.0 Objetivo |
|---------|------------|---------------|
| RAM usage | ~200-500 MB | <100 MB (embedding off) |
| Boot time | ~5-10s | <2s |
| Dashboard FPS | ~30 (React) | 60+ (GPU) |
| Tool count | 25 | 30+ (incl. MCP) |
| Memory recall accuracy | ~60% | >85% |
| Multi-agent coordination | N/A | 5 agents sin conflictos |
| Skill hot-reload | N/A | <1s |

---

## PRÓXIMOS PASOS INMEDIATOS

1. **Aprobar este plan** (o modificar según prioridades)
2. **Crear branch `v3.0-dev`**
3. **Comenzar Fase 0** (Foundation)
4. **Setup git worktrees** para aislamiento
5. **Escribir skills base** de Superpowers

---

*"De las cenizas de la versión 2, renace Lilith más poderosa que nunca.*
*Con memoria de dioses, swarm de demonios, y visión de dragón.*
*El Ragnarök del código ha comenzado."*

— *Völundr, Forjador de Yggdrasil*
