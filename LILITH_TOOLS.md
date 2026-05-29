# Lilith Agent — Tool Reference

Quick reference for all 35 tools.

## File Operations

### `terminal`
Execute shell commands.
```
terminal(command="ls -la", workdir="src/", timeout=30)
```

### `read_file`
Read file with line numbers.
```
read_file(path="src/main.py", offset=10, limit=50)
```

### `write_file`
Write content to file. Creates dirs. Auto-backup for undo.
```
write_file(path="new_file.py", content="print('hello')")
```

### `patch_file`
Find-and-replace edit. Auto-backup for undo.
```
patch_file(path="main.py", old_string="def old():", new_string="def new():")
```

### `search_files`
Regex search across files.
```
search_files(pattern="def .*function", glob="*.py", max_results=20)
```

### `list_files`
List files and directories.
```
list_files(path="src/", pattern="*.py", recursive=true)
```

### `multi_edit`
Apply multiple edits in one operation.
```
multi_edit(edits=[
  {"path": "a.py", "old_string": "old", "new_string": "new"},
  {"path": "b.py", "old_string": "old", "new_string": "new"}
])
```

### `undo`
Revert last file change.
```
undo(path="src/main.py")
```

## Git

### `git`
Run git commands.
```
git(args="status")
git(args="log --oneline -5")
git(args="add -A && commit -m 'fix'")
```

### `git_workflow`
Automated git operations.
```
git_workflow(action="branch", name="feature-x")
git_workflow(action="commit", message="add feature", files="-A")
git_workflow(action="push")
git_workflow(action="pr")
git_workflow(action="status")
```

## Code Execution

### `python_exec`
Run Python code in the venv.
```
python_exec(code="import sys; print(sys.version)")
```

### `run_tests`
Run pytest and analyze failures.
```
run_tests(path="tests/", verbose=true)
```

## Memory

### `remember`
Save a fact to persistent memory.
```
remember(category="user", key="editor", value="neovim")
remember(category="preference", key="style", value="nordic frost")
```

Categories: `user` `environment` `project` `preference` `convention` `pitfall`

### `recall`
Search persistent memory.
```
recall(query="editor")
recall(query="python version")
```

## Skills

### `save_skill`
Save a reusable procedure.
```
save_skill(name="deploy-frontend", description="Deploy to Vercel", content="1. Run tests\n2. Build\n3. Push", trigger="when deploying frontend")
```

### `load_skill`
Load a saved skill.
```
load_skill(name="deploy-frontend")
```

## Planning

### `create_plan`
Create a step-by-step plan.
```
create_plan(task="Add dark mode", steps=["1. Update CSS", "2. Add toggle", "3. Test"])
```

### `todo`
Manage task list.
```
todo(action="add", content="Fix login bug")
todo(action="update", item_id="1", status="in_progress")
todo(action="list")
todo(action="clear")
```

## Background Processes

### `bg_run`
Start background process.
```
bg_run(command="npm run build", workdir="frontend/")
```

### `bg_status`
Check process status.
```
bg_status(pid="a1b2c3d4")
```

### `bg_log`
Get process output.
```
bg_log(pid="a1b2c3d4", lines=50)
```

### `bg_kill`
Kill background process.
```
bg_kill(pid="a1b2c3d4")
```

## Sessions

### `save_session`
Save conversation for later.
```
save_session(title="Feature X discussion")
```

### `restore_session`
Restore a saved session.
```
restore_session(session_id="a1b2c3d4")
```

### `fork`
Save conversation branch.
```
fork(name="approach-a")
```

## Web

### `web_fetch`
Fetch URL and extract text.
```
web_fetch(url="https://docs.python.org/3/library/json.html", max_chars=4000)
```

### `open_browser`
Open URL in browser.
```
open_browser(url="https://github.com")
```

## Vision

### `screenshot`
Take desktop screenshot.
```
screenshot(question="What's on screen?")
```

### `analyze_image`
Analyze an image file.
```
analyze_image(path="screenshot.png", question="What does this show?")
```

## System

### `clipboard`
Read/write clipboard.
```
clipboard(action="get")
clipboard(action="set", content="copied text")
```

### `notify`
Desktop notification.
```
notify(title="Build complete", message="All tests passed")
```

### `workspace_info`
Detect project type and dependencies.
```
workspace_info(path=".")
```

### `profile`
Show performance stats.
```
profile()
```

## Reasoning

### `think`
Step-by-step reasoning (visible to user).
```
think(thought="The user wants X. I should first check Y, then do Z.")
```

## MCP

### `mcp_tools`
List available MCP tools.
```
mcp_tools()
```

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
