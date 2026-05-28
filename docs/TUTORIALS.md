# Yggdrasil Tutorials by Realm

Step-by-step guides for each realm in the ecosystem.

---

## Asgard — Core Technology

### Setup Lilith from scratch

```bash
# 1. Clone
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# 2. Configure environment
cp Asgard/Hermes-Lilith/.env.example Asgard/Hermes-Lilith/.env
# Edit .env with your Telegram token and LM Studio settings

# 3. Install globally (Windows)
cd Asgard/Hermes-Lilith
install.bat

# 4. Run
lilith
```

### Adding a New Tool

1. Create `Asgard/Hermes-Lilith/tools/my_tool.py`
2. Inherit from `BaseTool`
3. Implement `execute()` and `get_schema()`
4. Register in `ToolRegistry`
5. Restart Lilith

---

## Vanaheim — AI Agents

### Spawning a Sub-Agent

```python
from lilith_agents import AgentPool

pool = AgentPool()
agent = pool.spawn(
    name="code-reviewer",
    model="qwen2.5-coder-14b",
    system_prompt="You are a senior code reviewer. Focus on security and performance."
)

result = agent.run("Review this Python file for SQL injection risks.", context={"file": "api.py"})
print(result)
```

### Agent Communication Pattern

Agents communicate via the orchestrator. Never spawn an agent that talks directly to another agent — always route through the main orchestrator to maintain context and memory consistency.

---

## Alfheim — UI / Frontend

### Running the Web Dashboard

```bash
cd Alfheim/ui-seed
npm install
npm run dev
```

### Connecting to Lilith API

```typescript
const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello Lilith' })
});
const data = await response.json();
console.log(data.response);
```

---

## Svartalfheim — Documentation & Knowledge

### Writing a New Skill

1. Create directory: `Asgard/Hermes-Lilith/skills/my-skill/`
2. Add `SKILL.md` with:
   - Description
   - Trigger conditions
   - Step-by-step workflow
   - Example usage
3. Register in `skills/registry.yaml`

### Updating Architecture Docs

When you change the system architecture:
1. Update `docs/ARCHITECTURE.md`
2. Update `Svartalfheim/Docs/ARQUITECTURA_YGGDRASIL.md` (Spanish)
3. Regenerate Mermaid diagrams if needed

---

## Muspelheim — Active Development

### WIP Workflow

1. Create feature branch from `main`
2. Work in `Muspelheim/` or realm-specific folder
3. Test locally with `lilith --no-banner`
4. When stable, promote to target realm:
   ```bash
   # Move from Muspelheim to Asgard
   git mv Muspelheim/my-feature Asgard/my-feature
   ```
5. Open PR, merge to `main`

### Hot-Reloading Lilith During Dev

```bash
# Terminal 1: Watch and restart
watchmedo auto-restart --directory=Asgard/Hermes-Lilith --pattern="*.py" --recursive -- lilith

# Terminal 2: Send test messages
curl -X POST http://localhost:8000/api/chat -d '{"message":"test"}'
```

---

## Niflheim — Resources & Assets

### Managing Datasets

Store large files in `Niflheim/` and symlink from active realms:

```bash
# Store dataset
mv large-dataset.zip Niflheim/Datasets/

# Symlink to active project
cd Muspelheim/my-ml-project
ln -s ../../Niflheim/Datasets/large-dataset.zip data.zip
```

### Model Weights Storage

```bash
Niflheim/
  Models/
    gguf/
      qwen2.5-14b-q4_k_m.gguf
    onnx/
      whisper-base.onnx
```

Reference in `config.py`:
```python
MODEL_PATH = "Niflheim/Models/gguf/qwen2.5-14b-q4_k_m.gguf"
```

---

## Midgard — Personal Applications

### Creating a Personal App

1. Create folder: `Midgard/my-app/`
2. Add `README.md` with purpose and setup
3. If it needs Lilith integration, use the API:
   ```python
   import requests
   requests.post("http://localhost:8000/api/chat", json={"message": "..."})
   ```
4. Keep it simple — Midgard is for utilities, not core infrastructure

---

## Jotunheim — Massive Projects

### Structuring Large Projects

```
Jotunheim/
  my-huge-project/
    README.md
    docs/
    src/
    tests/
    scripts/
    .gitignore
```

Rules:
- One project per folder
- Must have `README.md` with architecture overview
- Use `scripts/` for build/deploy automation
- When project matures, consider promoting to its own repo

---

## Helheim — Archive

### Archiving a Deprecated Component

1. Move folder to `Helheim/Archives_<name>_<date>/`
2. Add `README.md` explaining:
   - Why it was archived
   - What replaced it
   - Last working version
3. Update `Helheim/README.md` index
4. Remove from active realms

### Restoring from Archive

```bash
git mv Helheim/Archives_my_old_core_2026-04-29 Asgard/my-old-core
# Update imports and config, then test
```
