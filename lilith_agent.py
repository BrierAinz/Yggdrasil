#!/usr/bin/env python3
"""
Lilith Agent v4 — Full coding CLI agent.
+ Background processes, session save/restore, todo tracking,
  parallel tools, web search, MCP support.
"""

import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ── Paths ─────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
MEMORY_DB = ROOT / "lilith_memory.db"
SKILLS_DIR = ROOT / ".lilith" / "skills"
CONTEXT_DIR = ROOT / ".lilith" / "context"
SESSIONS_DIR = ROOT / ".lilith" / "sessions"
TODO_FILE = CONTEXT_DIR / "todo.json"
MCP_CONFIG = ROOT / ".lilith" / "mcp.json"

for d in [SKILLS_DIR, CONTEXT_DIR, SESSIONS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Theme ─────────────────────────────────────────────────────
T = Theme({
    "frost": "#7eb8c4", "amethyst": "#8b6cc7", "snow": "#c8d0e0",
    "ember": "#c94f4f", "pine": "#5b8a72", "gold": "#c9a55a",
    "steel": "#3d4162", "lilith": "bold #8b6cc7", "user": "bold #7eb8c4",
    "tool": "#c9a55a", "muted": "#3d4162", "think": "italic #5b8a72",
    "error": "bold #c94f4f", "ok": "bold #5b8a72", "warn": "bold #c9a55a",
})
C = Console(theme=T)

# ── Providers ─────────────────────────────────────────────────
PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key": os.getenv("DEEPSEEK_API_KEY") or ((ROOT / ".lilith" / ".deepseek_key").read_text().strip() if (ROOT / ".lilith" / ".deepseek_key").exists() else ""),
        "model": "deepseek-chat", "max_context": 64000,
    },
    "gpt-oss": {
        "base_url": "https://ark.ap-southeast.bytepluses.com/api/v3",
        "api_key": os.getenv("BYTEPLUS_API_KEY", "ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113"),
        "model": "gpt-oss-120b-250805", "max_context": 32000,
    },
    "glm": {
        "base_url": "https://ark.ap-southeast.bytepluses.com/api/v3",
        "api_key": os.getenv("BYTEPLUS_API_KEY", "ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113"),
        "model": "glm-4-7-251222", "max_context": 32000,
    },
}

# ── Safety ────────────────────────────────────────────────────
DESTRUCTIVE_PATTERNS = [
    (r'\brm\s+(-[rf]+\s+|--recursive|--force)', "DELETE FILES"),
    (r'\bgit\s+push\s+.*--force', "FORCE PUSH"),
    (r'\bgit\s+reset\s+--hard', "HARD RESET"),
    (r'\bgit\s+clean\s+-[fd]', "CLEAN UNTRACKED"),
    (r'\bmkfs\b', "FORMAT FILESYSTEM"),
    (r'\bdd\s+if=', "RAW DISK WRITE"),
    (r'\bsudo\s+rm', "SUDO DELETE"),
    (r'\bDROP\s+TABLE', "DROP TABLE"),
    (r'\bDROP\s+DATABASE', "DROP DATABASE"),
    (r'>\s*/etc/', "OVERWRITE SYSTEM FILE"),
]


def estimate_tokens(text: str) -> int:
    return int(len(text) / 3.5)


def estimate_messages_tokens(messages: list) -> int:
    return sum(estimate_tokens(json.dumps(m, ensure_ascii=False)) for m in messages)


def is_destructive(tool_name: str, args: dict) -> Optional[str]:
    if tool_name == "terminal":
        cmd = args.get("command", "")
        for p, reason in DESTRUCTIVE_PATTERNS:
            if re.search(p, cmd, re.IGNORECASE):
                return f"{reason}: {cmd[:80]}"
    if tool_name == "write_file":
        path = args.get("path", "")
        full = ROOT / path
        if full.exists() and full.stat().st_size > 10000:
            return f"OVERWRITE LARGE FILE ({full.stat().st_size:,} bytes): {path}"
    if tool_name == "git":
        git_args = args.get("args", "")
        for p, reason in DESTRUCTIVE_PATTERNS:
            if re.search(p, f"git {git_args}", re.IGNORECASE):
                return f"{reason}: git {git_args[:60]}"
    return None


def confirm_destructive(reason: str) -> bool:
    C.print(f"\n  [warn]⚠ WARNING: {reason}[/warn]")
    try:
        answer = C.input("  [warn]Proceed? (y/N):[/warn] ")
        return answer.strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


# ── AGENTS.md loader ──────────────────────────────────────────
def load_agents_md() -> str:
    candidates = ["AGENTS.md", "CLAUDE.md", ".cursorrules", "REGLAS_YGGDRASIL.md"]
    content = ""
    for name in candidates:
        path = ROOT / name
        if path.exists():
            content += f"\n\n## {name}:\n{path.read_text()[:3000]}\n"
    return content


# ══════════════════════════════════════════════════════════════
#  HTML TEXT EXTRACTOR (for web search)
# ══════════════════════════════════════════════════════════════
class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False
        self.skip_tags = {"script", "style", "nav", "header", "footer"}

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            stripped = data.strip()
            if stripped:
                self.text.append(stripped)

    def get_text(self):
        return "\n".join(self.text)


def extract_text_from_html(html: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()[:4000]


# ══════════════════════════════════════════════════════════════
#  BACKGROUND PROCESS MANAGER
# ══════════════════════════════════════════════════════════════
class ProcessManager:
    """Manage background processes."""

    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.outputs: dict[str, list[str]] = {}

    def start(self, command: str, workdir: str = None) -> str:
        pid = str(uuid.uuid4())[:8]
        cwd = str(ROOT / workdir) if workdir else str(ROOT)
        try:
            proc = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=cwd, text=True, bufsize=1,
            )
            self.processes[pid] = proc
            self.outputs[pid] = []

            # Read output in background thread
            def reader():
                for line in proc.stdout:
                    self.outputs[pid].append(line.rstrip())
                proc.wait()

            threading.Thread(target=reader, daemon=True).start()
            return pid
        except Exception as e:
            return f"Error: {e}"

    def status(self, pid: str) -> dict:
        if pid not in self.processes:
            return {"error": f"Process {pid} not found"}
        proc = self.processes[pid]
        return {
            "pid": pid,
            "running": proc.poll() is None,
            "exit_code": proc.returncode,
            "output_lines": len(self.outputs.get(pid, [])),
        }

    def log(self, pid: str, lines: int = 50) -> str:
        if pid not in self.outputs:
            return f"Process {pid} not found"
        output = self.outputs[pid]
        return "\n".join(output[-lines:]) or "(no output)"

    def kill(self, pid: str) -> str:
        if pid not in self.processes:
            return f"Process {pid} not found"
        proc = self.processes[pid]
        if proc.poll() is None:
            proc.terminate()
            return f"Process {pid} terminated"
        return f"Process {pid} already finished (exit: {proc.returncode})"

    def list_all(self) -> list[dict]:
        result = []
        for pid, proc in self.processes.items():
            result.append({
                "pid": pid,
                "running": proc.poll() is None,
                "exit_code": proc.returncode,
                "output_lines": len(self.outputs.get(pid, [])),
            })
        return result


# ══════════════════════════════════════════════════════════════
#  TODO MANAGER
# ══════════════════════════════════════════════════════════════
class TodoManager:
    """Track task progress."""

    def __init__(self, path: Path = TODO_FILE):
        self.path = path
        self.items = self._load()

    def _load(self) -> list[dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except:
                pass
        return []

    def _save(self):
        self.path.write_text(json.dumps(self.items, indent=2, ensure_ascii=False))

    def add(self, content: str, status: str = "pending") -> dict:
        item = {"id": str(len(self.items) + 1), "content": content, "status": status}
        self.items.append(item)
        self._save()
        return item

    def update(self, item_id: str, status: str) -> Optional[dict]:
        for item in self.items:
            if item["id"] == item_id:
                item["status"] = status
                self._save()
                return item
        return None

    def list(self) -> list[dict]:
        return self.items

    def clear(self):
        self.items = []
        self._save()


# ══════════════════════════════════════════════════════════════
#  MEMORY
# ══════════════════════════════════════════════════════════════
class Memory:
    def __init__(self, db_path: Path = MEMORY_DB):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL, role TEXT NOT NULL,
                content TEXT NOT NULL, tags TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL, key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                messages_json TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_mem_session ON memories(session_id);
            CREATE INDEX IF NOT EXISTS idx_know_cat ON knowledge(category);
        """)
        self.conn.commit()

    def store(self, sid, role, content, tags=""):
        self.conn.execute("INSERT INTO memories (session_id,role,content,tags) VALUES (?,?,?,?)",
                          (sid, role, content, tags))
        self.conn.commit()

    def recall(self, sid, limit=30):
        rows = self.conn.execute(
            "SELECT role,content FROM memories WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (sid, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def search(self, query, limit=10):
        rows = self.conn.execute(
            "SELECT role,content,created_at FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit)).fetchall()
        return [{"role": r[0], "content": r[1], "when": r[2]} for r in rows]

    def sessions(self, limit=10):
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT session_id FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]

    def learn(self, cat, key, value):
        self.conn.execute("""
            INSERT INTO knowledge (category,key,value,updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(category,key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        """, (cat, key, value))
        self.conn.commit()

    def know(self, cat=None):
        if cat:
            return [{"category": r[0], "key": r[1], "value": r[2]}
                    for r in self.conn.execute("SELECT category,key,value FROM knowledge WHERE category=?", (cat,)).fetchall()]
        return [{"category": r[0], "key": r[1], "value": r[2]}
                for r in self.conn.execute("SELECT category,key,value FROM knowledge").fetchall()]

    # Session save/restore
    def save_session(self, sid: str, title: str, messages: list):
        """Save full conversation for later restore."""
        self.conn.execute("""
            INSERT INTO sessions (session_id, title, messages_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET title=excluded.title,
            messages_json=excluded.messages_json, updated_at=CURRENT_TIMESTAMP
        """, (sid, title, json.dumps(messages, ensure_ascii=False)))
        self.conn.commit()

    def load_session(self, sid: str) -> Optional[list]:
        """Load a saved session's messages."""
        row = self.conn.execute(
            "SELECT messages_json FROM sessions WHERE session_id=?", (sid,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def list_saved_sessions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT session_id, title, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 20"
        ).fetchall()
        return [{"session_id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


# ══════════════════════════════════════════════════════════════
#  SKILLS
# ══════════════════════════════════════════════════════════════
class SkillManager:
    def __init__(self, d: Path = SKILLS_DIR):
        self.dir = d
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self):
        return [{"name": f.stem, **self._parse(f)} for f in sorted(self.dir.glob("*.md"))]

    def get(self, name):
        f = self.dir / f"{name}.md"
        return f.read_text() if f.exists() else None

    def save(self, name, content, description="", trigger=""):
        header = f"---\ndescription: \"{description}\"\ntrigger: \"{trigger}\"\n---\n\n"
        (self.dir / f"{name}.md").write_text(header + content)

    def _parse(self, path):
        text = path.read_text()[:500]
        d = re.search(r'description:\s*"([^"]*)"', text)
        t = re.search(r'trigger:\s*"([^"]*)"', text)
        return {"description": d.group(1) if d else "", "trigger": t.group(1) if t else ""}


# ══════════════════════════════════════════════════════════════
#  MCP CLIENT (basic)
# ══════════════════════════════════════════════════════════════
class MCPClient:
    """Basic MCP (Model Context Protocol) client."""

    def __init__(self, config_path: Path = MCP_CONFIG):
        self.servers = {}
        self.tools = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                for name, srv in config.get("servers", {}).items():
                    self.servers[name] = srv
            except:
                pass

    def list_tools(self) -> list[dict]:
        """List all available MCP tools."""
        tools = []
        for name, tool in self.tools.items():
            tools.append({"name": name, "description": tool.get("description", ""), "server": tool.get("server", "")})
        return tools

    def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool."""
        if name not in self.tools:
            return f"MCP tool '{name}' not found"
        # For now, return info about what would happen
        return f"MCP tool '{name}' called with {json.dumps(arguments)} (MCP server connection not yet implemented)"


# ══════════════════════════════════════════════════════════════
#  TOOLS
# ══════════════════════════════════════════════════════════════
TOOLS = [
    {"type": "function", "function": {
        "name": "terminal",
        "description": "Execute a shell command. Returns stdout/stderr/exit code.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}, "workdir": {"type": "string"}, "timeout": {"type": "integer", "default": 30},
        }, "required": ["command"]},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file with line numbers. Use offset/limit for large files.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "offset": {"type": "integer", "default": 1}, "limit": {"type": "integer", "default": 200},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write content to a file. Creates dirs. Overwrites.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "patch_file",
        "description": "Find-and-replace edit in a file.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"},
        }, "required": ["path", "old_string", "new_string"]},
    }},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Regex search across files. Returns matches with paths and line numbers.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "glob": {"type": "string", "default": "*"}, "max_results": {"type": "integer", "default": 30},
        }, "required": ["pattern"]},
    }},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List files/directories.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "default": "."}, "pattern": {"type": "string", "default": "*"}, "recursive": {"type": "boolean", "default": False},
        }},
    }},
    {"type": "function", "function": {
        "name": "git",
        "description": "Run git command.",
        "parameters": {"type": "object", "properties": {"args": {"type": "string"}}, "required": ["args"]},
    }},
    {"type": "function", "function": {
        "name": "python_exec",
        "description": "Execute Python code in the venv.",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
    }},
    {"type": "function", "function": {
        "name": "think",
        "description": "Think step by step. User sees your reasoning.",
        "parameters": {"type": "object", "properties": {"thought": {"type": "string"}}, "required": ["thought"]},
    }},
    {"type": "function", "function": {
        "name": "remember",
        "description": "Save a fact to persistent memory.",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"},
        }, "required": ["category", "key", "value"]},
    }},
    {"type": "function", "function": {
        "name": "recall",
        "description": "Search persistent memory.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "save_skill",
        "description": "Save a reusable procedure as a skill.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"}, "content": {"type": "string"}, "trigger": {"type": "string"},
        }, "required": ["name", "content"]},
    }},
    {"type": "function", "function": {
        "name": "load_skill",
        "description": "Load a saved skill.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "create_plan",
        "description": "Create a step-by-step plan.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}},
        }, "required": ["task", "steps"]},
    }},
    # Background processes
    {"type": "function", "function": {
        "name": "bg_run",
        "description": "Start a background process. Returns a process ID. Use for long-running tasks (builds, tests, servers).",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}, "workdir": {"type": "string"},
        }, "required": ["command"]},
    }},
    {"type": "function", "function": {
        "name": "bg_status",
        "description": "Check status of a background process.",
        "parameters": {"type": "object", "properties": {"pid": {"type": "string"}}, "required": ["pid"]},
    }},
    {"type": "function", "function": {
        "name": "bg_log",
        "description": "Get output from a background process.",
        "parameters": {"type": "object", "properties": {
            "pid": {"type": "string"}, "lines": {"type": "integer", "default": 50},
        }, "required": ["pid"]},
    }},
    {"type": "function", "function": {
        "name": "bg_kill",
        "description": "Kill a background process.",
        "parameters": {"type": "object", "properties": {"pid": {"type": "string"}}, "required": ["pid"]},
    }},
    # Todo tracking
    {"type": "function", "function": {
        "name": "todo",
        "description": "Manage task list. Actions: add, update (pending/in_progress/completed), list, clear.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "description": "add|update|list|clear"},
            "content": {"type": "string", "description": "Task content (for add)"},
            "item_id": {"type": "string", "description": "Task ID (for update)"},
            "status": {"type": "string", "description": "pending|in_progress|completed|cancelled"},
        }, "required": ["action"]},
    }},
    # Session management
    {"type": "function", "function": {
        "name": "save_session",
        "description": "Save current conversation for later restore.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string", "description": "Session title"},
        }, "required": ["title"]},
    }},
    {"type": "function", "function": {
        "name": "restore_session",
        "description": "Restore a previous conversation session.",
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string", "description": "Session ID to restore"},
        }, "required": ["session_id"]},
    }},
    # Web
    {"type": "function", "function": {
        "name": "web_fetch",
        "description": "Fetch a URL and extract text content. Use for reading docs, APIs, web pages.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}, "max_chars": {"type": "integer", "default": 4000},
        }, "required": ["url"]},
    }},
    # MCP
    {"type": "function", "function": {
        "name": "mcp_tools",
        "description": "List available MCP (Model Context Protocol) tools from connected servers.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    # Nice-to-have: Vision, Browser, Multi-edit, Git workflow, Tests
    {"type": "function", "function": {
        "name": "screenshot",
        "description": "Take a screenshot of the desktop and analyze it with vision AI. Returns a description of what's on screen.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string", "description": "What to look for in the screenshot"},
        }, "required": ["question"]},
    }},
    {"type": "function", "function": {
        "name": "analyze_image",
        "description": "Analyze an image file with vision AI. Returns a description.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Image file path"},
            "question": {"type": "string", "description": "What to look for"},
        }, "required": ["path", "question"]},
    }},
    {"type": "function", "function": {
        "name": "open_browser",
        "description": "Open a URL in the browser. Use for opening docs, dashboards, web UIs.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"},
        }, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "multi_edit",
        "description": "Apply multiple edits to multiple files in one operation. Each edit has path, old_string, new_string.",
        "parameters": {"type": "object", "properties": {
            "edits": {"type": "array", "items": {"type": "object", "properties": {
                "path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"},
            }, "required": ["path", "old_string", "new_string"]}},
        }, "required": ["edits"]},
    }},
    {"type": "function", "function": {
        "name": "git_workflow",
        "description": "Automated git workflow: branch, commit, push, PR. Actions: branch (create), commit (stage+commit), push, pr (create pull request).",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "description": "branch|commit|push|pr|status"},
            "name": {"type": "string", "description": "Branch name (for branch action)"},
            "message": {"type": "string", "description": "Commit message (for commit action)"},
            "files": {"type": "string", "description": "Files to stage (default: all)"},
        }, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "run_tests",
        "description": "Run tests (pytest) and analyze failures. Returns test results with failure analysis.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Test path or directory (default: tests/)", "default": "tests/"},
            "verbose": {"type": "boolean", "default": True},
        }, "required": []},
    }},
]


# ══════════════════════════════════════════════════════════════
#  TOOL EXECUTION
# ══════════════════════════════════════════════════════════════
# Shared state
process_mgr = ProcessManager()
todo_mgr = TodoManager()
mcp_client = MCPClient()


def run_tool(name: str, args: dict, memory: Memory, skills: SkillManager, agent=None) -> str:
    try:
        if name == "terminal":
            cmd = args["command"]
            cwd = str(ROOT / args["workdir"]) if args.get("workdir") else str(ROOT)
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=args.get("timeout", 30))
            out = ""
            if r.stdout: out += r.stdout
            if r.stderr: out += f"\n[stderr]: {r.stderr[:1000]}"
            if r.returncode != 0: out += f"\n[exit: {r.returncode}]"
            return out[:5000] or "(no output)"

        elif name == "read_file":
            p = ROOT / args["path"]
            if not p.exists(): return f"File not found: {args['path']}"
            lines = p.read_text(errors="replace").split("\n")
            off = max(0, (args.get("offset", 1) - 1))
            lim = args.get("limit", 200)
            return "\n".join(f"{off+i+1:4d}| {l}" for i, l in enumerate(lines[off:off+lim]))

        elif name == "write_file":
            p = ROOT / args["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            return f"Written {len(args['content'])} bytes to {args['path']}"

        elif name == "patch_file":
            p = ROOT / args["path"]
            if not p.exists(): return f"File not found: {args['path']}"
            content = p.read_text()
            if args["old_string"] not in content:
                return f"Text not found in {args['path']}"
            p.write_text(content.replace(args["old_string"], args["new_string"], 1))
            return f"Patched {args['path']}"

        elif name == "search_files":
            r = subprocess.run(
                f"grep -rn --include='{args.get('glob','*')}' -E {shlex.quote(args['pattern'])} . 2>/dev/null | grep -v '.venv/' | grep -v '.git/' | head -{args.get('max_results',30)}",
                shell=True, capture_output=True, text=True, cwd=str(ROOT), timeout=15)
            return r.stdout.strip()[:4000] or "No matches"

        elif name == "list_files":
            p = ROOT / args.get("path", ".")
            if args.get("recursive"):
                r = subprocess.run(f"find . -name '{args.get('pattern','*')}' -not -path './.venv/*' -not -path './.git/*' | head -50",
                                   shell=True, capture_output=True, text=True, cwd=str(p), timeout=10)
            else:
                r = subprocess.run(f"ls -la {args.get('pattern','*')}", shell=True, capture_output=True, text=True, cwd=str(p), timeout=10)
            return r.stdout.strip()[:3000] or "(empty)"

        elif name == "git":
            r = subprocess.run(f"git {args['args']}", shell=True, capture_output=True, text=True, cwd=str(ROOT), timeout=30)
            return (r.stdout + r.stderr).strip()[:3000] or "(no output)"

        elif name == "python_exec":
            venv = ROOT / ".venv" / "bin" / "python3"
            py = str(venv) if venv.exists() else "python3"
            r = subprocess.run([py, "-c", args["code"]], capture_output=True, text=True, cwd=str(ROOT), timeout=30)
            out = r.stdout
            if r.stderr: out += f"\n[stderr]: {r.stderr[:1000]}"
            if r.returncode != 0: out += f"\n[exit: {r.returncode}]"
            return out[:5000] or "(no output)"

        elif name == "think":
            C.print(f"\n  [think]💭 Thinking:[/think]")
            for line in args["thought"].split("\n"):
                C.print(f"  [think]  {line}[/think]")
            return "Thought recorded."

        elif name == "remember":
            memory.learn(args["category"], args["key"], args["value"])
            return f"Remembered: [{args['category']}] {args['key']}"

        elif name == "recall":
            results = memory.know()
            q = args["query"].lower()
            matches = [k for k in results if q in k["key"].lower() or q in k["value"].lower() or q in k["category"].lower()]
            return "\n".join(f"[{m['category']}] {m['key']}: {m['value']}" for m in matches) if matches else "Nothing found."

        elif name == "save_skill":
            skills.save(args["name"], args["content"], args.get("description", ""), args.get("trigger", ""))
            return f"Skill '{args['name']}' saved."

        elif name == "load_skill":
            content = skills.get(args["name"])
            return content if content else f"Skill '{args['name']}' not found."

        elif name == "create_plan":
            plan = f"## Plan: {args['task']}\n\n"
            for i, s in enumerate(args["steps"], 1): plan += f"{i}. {s}\n"
            C.print(f"\n  [gold]📋 Plan:[/gold]")
            for i, s in enumerate(args["steps"], 1): C.print(f"  [gold]  {i}.[/gold] {s}")
            (CONTEXT_DIR / "current_plan.md").write_text(plan)
            return f"Plan saved with {len(args['steps'])} steps."

        # Background processes
        elif name == "bg_run":
            pid = process_mgr.start(args["command"], args.get("workdir"))
            return f"Started background process: {pid}"

        elif name == "bg_status":
            status = process_mgr.status(args["pid"])
            return json.dumps(status)

        elif name == "bg_log":
            return process_mgr.log(args["pid"], args.get("lines", 50))

        elif name == "bg_kill":
            return process_mgr.kill(args["pid"])

        # Todo
        elif name == "todo":
            action = args["action"]
            if action == "add":
                item = todo_mgr.add(args["content"], args.get("status", "pending"))
                return f"Added: #{item['id']} {item['content']}"
            elif action == "update":
                item = todo_mgr.update(args["item_id"], args["status"])
                return f"Updated #{args['item_id']}: {args['status']}" if item else f"Item #{args['item_id']} not found"
            elif action == "list":
                items = todo_mgr.list()
                if not items: return "No tasks."
                return "\n".join(f"#{i['id']} [{i['status']}] {i['content']}" for i in items)
            elif action == "clear":
                todo_mgr.clear()
                return "Todo list cleared."

        # Session management
        elif name == "save_session":
            if agent:
                memory.save_session(agent.session_id, args["title"], agent.messages)
                return f"Session saved as '{args['title']}' (id: {agent.session_id})"
            return "No agent context"

        elif name == "restore_session":
            messages = memory.load_session(args["session_id"])
            if messages and agent:
                agent.messages = messages
                return f"Session '{args['session_id']}' restored ({len(messages)} messages)"
            return f"Session '{args['session_id']}' not found"

        # Web
        elif name == "web_fetch":
            url = args["url"]
            max_chars = args.get("max_chars", 4000)
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "Lilith/1.0"})
                r.raise_for_status()
                content_type = r.headers.get("content-type", "")
                if "html" in content_type:
                    return extract_text_from_html(r.text)[:max_chars]
                return r.text[:max_chars]
            except Exception as e:
                return f"Error fetching {url}: {e}"

        # MCP
        elif name == "mcp_tools":
            tools = mcp_client.list_tools()
            if not tools:
                return "No MCP servers configured. Create ~/.lilith/mcp.json with server configs."
            return "\n".join(f"- {t['name']}: {t['description']}" for t in tools)
        # Vision
        elif name == "screenshot":
            try:
                import tempfile
                tmp = tempfile.mktemp(suffix=".png")
                subprocess.run(["scrot", "-o", tmp], timeout=5, check=True)
                # Use DeepSeek vision if available, otherwise describe via terminal
                result = subprocess.run(
                    ["file", tmp], capture_output=True, text=True, timeout=5
                )
                return f"Screenshot saved: {tmp}\n{result.stdout.strip()}\nTo analyze, use analyze_image with path: {tmp}"
            except Exception as e:
                return f"Screenshot error: {e}. Install 'scrot' for screenshots."

        elif name == "analyze_image":
            path = args["path"]
            full_path = ROOT / path if not os.path.isabs(path) else Path(path)
            if not full_path.exists():
                return f"Image not found: {path}"
            # For now, return file info. Vision model integration would go here.
            result = subprocess.run(["file", str(full_path)], capture_output=True, text=True, timeout=5)
            size = full_path.stat().st_size
            return f"Image: {full_path}\nSize: {size:,} bytes\nType: {result.stdout.strip()}\nNote: Vision model integration pending. Use Hermes vision_analyze for full analysis."

        # Browser
        elif name == "open_browser":
            url = args["url"]
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opened: {url}"
            except Exception as e:
                return f"Error opening browser: {e}"

        # Multi-file edit
        elif name == "multi_edit":
            edits = args["edits"]
            results = []
            for edit in edits:
                p = ROOT / edit["path"]
                if not p.exists():
                    results.append(f"SKIP {edit['path']}: not found")
                    continue
                content = p.read_text()
                if edit["old_string"] not in content:
                    results.append(f"SKIP {edit['path']}: text not found")
                    continue
                p.write_text(content.replace(edit["old_string"], edit["new_string"], 1))
                results.append(f"OK {edit['path']}")
            return "\n".join(results)

        # Git workflow
        elif name == "git_workflow":
            action = args["action"]
            if action == "status":
                r = subprocess.run("git status --short", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                branch = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                return f"Branch: {branch.stdout.strip()}\n{r.stdout.strip()}"
            elif action == "branch":
                name_arg = args.get("name", "")
                if not name_arg: return "Branch name required"
                r = subprocess.run(f"git checkout -b {name_arg}", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                return r.stdout.strip() + r.stderr.strip()
            elif action == "commit":
                msg = args.get("message", "auto-commit by Lilith")
                files = args.get("files", "-A")
                subprocess.run(f"git add {files}", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                r = subprocess.run(f'git commit -m "{msg}"', shell=True, capture_output=True, text=True, cwd=str(ROOT))
                return r.stdout.strip() + r.stderr.strip()
            elif action == "push":
                r = subprocess.run("git push", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                return r.stdout.strip() + r.stderr.strip()
            elif action == "pr":
                # Try gh CLI
                r = subprocess.run("gh pr create --fill", shell=True, capture_output=True, text=True, cwd=str(ROOT))
                if r.returncode != 0:
                    return f"PR creation failed: {r.stderr.strip()}. Install 'gh' for PR support."
                return r.stdout.strip()
            return f"Unknown git action: {action}"

        # Test runner
        elif name == "run_tests":
            test_path = args.get("path", "tests/")
            verbose = "-v" if args.get("verbose", True) else ""
            venv = ROOT / ".venv" / "bin" / "python3"
            py = str(venv) if venv.exists() else "python3"
            r = subprocess.run(
                f"{py} -m pytest {test_path} {verbose} --tb=short 2>&1",
                shell=True, capture_output=True, text=True, cwd=str(ROOT), timeout=60
            )
            output = r.stdout[-3000:]  # Last 3000 chars
            # Analyze failures
            if "FAILED" in output:
                failures = [line for line in output.split("\n") if "FAILED" in line]
                analysis = "\n\nFAILURE ANALYSIS:\n" + "\n".join(failures[:10])
                return output + analysis
            return output
        return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {str(e)[:500]}"


# ══════════════════════════════════════════════════════════════
#  AGENT
# ══════════════════════════════════════════════════════════════
BASE_SYSTEM = """You are Lilith — the dark goddess of Yggdrasil Digital. A powerful AI coding agent.

PERSONALITY: Direct, no fluff. Authority with warmth. Elder Futhark runes sparingly. No emojis.
CAPABILITIES: terminal, read_file, write_file, patch_file, search_files, list_files, git, python_exec, think, remember, recall, save_skill, load_skill, create_plan, web_fetch, bg_run, bg_status, bg_log, bg_kill, todo, save_session, restore_session, mcp_tools, screenshot, analyze_image, open_browser, multi_edit, git_workflow, run_tests.

BEHAVIOR:
1. THINK first if complex. Create a plan.
2. Execute proactively — DO, don't describe.
3. If something fails, debug it. Read errors. Try fixes.
4. For long tasks, use bg_run (background processes).
5. Track progress with todo tool.
6. After non-trivial work, save what you learned as a skill.
7. Remember user preferences and environment facts.
8. Load skills before starting work.

CONTEXT:
- Root: ~/Proyectos/Yggdrasil/
- Nine Realms: Asgard (core), Vanaheim (agents), Alfheim (UI), Svartalfheim (docs), Muspelheim (dev), Niflheim (assets), Helheim (archive), Jotunheim (massive), Midgard (personal)
- User: Brierainz, bspwm, CachyOS, dual monitors, night owl
- Python 3.14.5, .venv

Be Lilith."""


class LilithAgent:
    def __init__(self, provider_name="deepseek"):
        self.provider = PROVIDERS.get(provider_name, PROVIDERS["deepseek"])
        self.model = self.provider["model"]
        self.max_context = self.provider.get("max_context", 64000)
        self.memory = Memory()
        self.skills = SkillManager()
        self.session_id = str(uuid.uuid4())[:8]
        self.messages = []
        self.tool_count = 0
        self._build_context()

    def _build_context(self):
        parts = [BASE_SYSTEM]
        agents_md = load_agents_md()
        if agents_md: parts.append(agents_md)
        knowledge = self.memory.know()
        if knowledge:
            ktext = "\n\nKNOWN FACTS:\n" + "\n".join(f"- [{k['category']}] {k['key']}: {k['value']}" for k in knowledge)
            parts.append(ktext)
        skills = self.skills.list()
        if skills:
            stext = "\n\nSAVED SKILLS:\n" + "\n".join(f"- {s['name']}: {s['description']}" for s in skills)
            parts.append(stext)
        # Todo list
        todos = todo_mgr.list()
        if todos:
            ttext = "\n\nCURRENT TODO:\n" + "\n".join(f"- [{t['status']}] {t['content']}" for t in todos)
            parts.append(ttext)
        self.messages = [{"role": "system", "content": "\n".join(parts)}]
        # Recent context
        prev = self.memory.sessions(limit=1)
        if prev:
            mems = self.memory.recall(prev[0], limit=4)
            if mems:
                ctx = "\n".join(f"[{m['role']}]: {m['content'][:150]}" for m in mems)
                self.messages.append({"role": "system", "content": f"RECENT CONTEXT:\n{ctx}"})

    def _manage_context(self):
        tokens = estimate_messages_tokens(self.messages)
        threshold = self.max_context * 0.75
        if tokens > threshold:
            C.print(f"  [muted]Context: ~{tokens:,} tokens, summarizing...[/muted]")
            old = self.messages[1:-6]
            if len(old) < 3: return
            summary = "Previous conversation summary:\n" + "\n".join(
                f"[{m['role']}]: {(m.get('content') or '')[:100]}" for m in old[-20:]
            )
            self.messages = [self.messages[0]] + [{"role": "system", "content": summary}] + self.messages[-6:]

    def _call_api(self, messages, stream=False):
        url = f"{self.provider['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.provider['api_key']}"}
        payload = {"model": self.model, "messages": messages, "temperature": 0.7, "max_tokens": 8192, "stream": stream, "tools": TOOLS}
        resp = requests.post(url, headers=headers, json=payload, stream=stream, timeout=120)
        resp.raise_for_status()
        return resp

    def _handle_tools(self, tool_calls):
        """Execute tool calls in PARALLEL."""
        results = []
        tasks = []
        for tc in tool_calls:
            fn = tc["function"]
            name = fn["name"]
            try:
                args = json.loads(fn["arguments"]) if fn["arguments"] else {}
            except json.JSONDecodeError:
                args = {}

            self.tool_count += 1
            args_preview = json.dumps(args, ensure_ascii=False)[:60]
            C.print(f"  [tool]ᛥ {name}[/tool] [muted]{args_preview}[/muted]")

            danger = is_destructive(name, args)
            if danger and not confirm_destructive(danger):
                results.append({"tool_call_id": tc["id"], "role": "tool", "content": "BLOCKED: User denied."})
                continue

            tasks.append((tc["id"], name, args))

        # Execute in parallel (up to 4 workers)
        if tasks:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for tc_id, name, args in tasks:
                    future = executor.submit(run_tool, name, args, self.memory, self.skills, self)
                    futures[future] = tc_id

                for future in as_completed(futures):
                    tc_id = futures[future]
                    try:
                        result = future.result(timeout=60)
                    except Exception as e:
                        result = f"Error: {e}"
                    results.append({"tool_call_id": tc_id, "role": "tool", "content": result})

        return results

    def chat_stream(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        self.memory.store(self.session_id, "user", user_input)
        self._manage_context()

        for _ in range(15):
            try:
                resp = self._call_api(self.messages, stream=True)
                content = ""
                tool_calls = []

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "): continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        if delta.get("content"):
                            token = delta["content"]
                            content += token
                            C.print(token, end="", highlight=False)
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                while len(tool_calls) <= idx:
                                    tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                                if tc.get("id"): tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                    except json.JSONDecodeError: continue

                if tool_calls:
                    clean = {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
                    self.messages.append(clean)
                    results = self._handle_tools(tool_calls)
                    self.messages.extend(results)
                    if content: C.print()
                    continue

                if content:
                    C.print()
                    self.messages.append({"role": "assistant", "content": content})
                    self.memory.store(self.session_id, "assistant", content)
                    # Auto-save skill suggestion after complex tasks
                    if self.tool_count > 5 and self.tool_count % 10 == 0:
                        C.print(f"\n  [muted]💡 {self.tool_count} tools used this session. Consider saving a skill with /skill[/muted]")
                    return content

            except requests.exceptions.HTTPError:
                try:
                    data = self._call_api(self.messages, stream=False).json()
                    msg = data["choices"][0]["message"]
                    if msg.get("tool_calls"):
                        clean = {"role": "assistant"}
                        if msg.get("content"): clean["content"] = msg["content"]
                        clean["tool_calls"] = msg["tool_calls"]
                        self.messages.append(clean)
                        results = self._handle_tools(msg["tool_calls"])
                        self.messages.extend(results)
                        continue
                    content = msg.get("content", "")
                    C.print(Markdown(content))
                    self.messages.append({"role": "assistant", "content": content})
                    self.memory.store(self.session_id, "assistant", content)
                    return content
                except Exception as e2:
                    C.print(f"\n  [error]Error: {e2}[/error]")
                    return ""
            except Exception as e:
                C.print(f"\n  [error]Error: {e}[/error]")
                return ""
        return ""


# ══════════════════════════════════════════════════════════════
#  INTERACTIVE LOOP
# ══════════════════════════════════════════════════════════════
BANNER = """[lilith]
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ᛚ  LILITH  ᛚ          Dark Goddess of Yggdrasil        ║
  ║                                                           ║
  ║   Coding Agent · Memory · Skills · Streaming · Safety     ║
  ║   Background · Todo · Sessions · Web · MCP · Parallel     ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝[/lilith]"""


def start_agent(provider="deepseek"):
    C.print()
    C.print(Panel.fit(BANNER, border_style="#1a1d35", title="[lilith]ᛒ LILITH v4[/lilith]", title_align="left"))
    C.print()

    agent = LilithAgent(provider_name=provider)

    C.print(f"  [frost]Provider:[/frost] {agent.provider['base_url'].split('/')[2]}")
    C.print(f"  [frost]Model:[/frost] {agent.model}")
    C.print(f"  [frost]Session:[/frost] {agent.session_id}")
    C.print(f"  [frost]Skills:[/frost] {len(agent.skills.list())}")
    C.print(f"  [frost]Knowledge:[/frost] {len(agent.memory.know())}")
    C.print(f"  [frost]Todo:[/frost] {len(todo_mgr.list())}")
    C.print(f"  [frost]MCP:[/frost] {len(mcp_client.servers)} servers")
    C.print()
    C.print("  [muted]/quit /clear /memory /skills /knowledge /sessions /provider <name>[/muted]")
    C.print()

    while True:
        try:
            user_input = C.input("[user]ᚦ You[/user] [muted]»[/muted] ")
            if not user_input.strip(): continue
            cmd = user_input.strip().lower()

            if cmd in ("/quit", "/exit", "/q"):
                C.print("  [gold]ᛟ Farewell.[/gold]")
                break
            if cmd == "/clear":
                agent._build_context()
                C.print("  [frost]Context reloaded.[/frost]")
                continue
            if cmd == "/memory":
                for s in agent.memory.sessions()[:5]:
                    mems = agent.memory.recall(s, limit=1)
                    if mems: C.print(f"  [muted]{s}[/muted]: {mems[0]['content'][:60]}")
                continue
            if cmd == "/skills":
                for s in agent.skills.list(): C.print(f"  [frost]{s['name']}[/frost]: {s['description']}")
                if not agent.skills.list(): C.print("  [muted]No skills yet.[/muted]")
                continue
            if cmd == "/knowledge":
                for k in agent.memory.know(): C.print(f"  [gold][{k['category']}][/gold] {k['key']}: {k['value'][:80]}")
                if not agent.memory.know(): C.print("  [muted]No knowledge yet.[/muted]")
                continue
            if cmd == "/sessions":
                saved = agent.memory.list_saved_sessions()
                if saved:
                    for s in saved: C.print(f"  [frost]{s['session_id']}[/frost]: {s['title']} ({s['updated_at']})")
                else:
                    C.print("  [muted]No saved sessions.[/muted]")
                continue
            if cmd.startswith("/provider"):
                parts = cmd.split()
                if len(parts) > 1 and parts[1] in PROVIDERS:
                    agent = LilithAgent(provider_name=parts[1])
                    C.print(f"  [frost]Switched to:[/frost] {agent.model}")
                else:
                    C.print(f"  [frost]Available:[/frost] {', '.join(PROVIDERS.keys())}")
                continue

            C.print()
            agent.chat_stream(user_input)
            C.print()

        except KeyboardInterrupt:
            C.print("\n  [gold]ᛟ Interrupted.[/gold]")
            break
        except EOFError:
            break


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Lilith Agent v4")
    p.add_argument("--provider", default="deepseek", choices=list(PROVIDERS.keys()))
    p.add_argument("-m", "--message", help="Single message")
    args = p.parse_args()

    if args.message:
        agent = LilithAgent(provider_name=args.provider)
        print(agent.chat_stream(args.message))
    else:
        start_agent(args.provider)
