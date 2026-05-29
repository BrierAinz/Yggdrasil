#!/usr/bin/env python3
"""
Lilith Agent v3 — Full coding CLI agent.
+ Streaming, context management, destructive ops safety,
  AGENTS.md loading, error recovery.
"""

import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme


# ── Paths ─────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
MEMORY_DB = ROOT / "lilith_memory.db"
SKILLS_DIR = ROOT / ".lilith" / "skills"
CONTEXT_DIR = ROOT / ".lilith" / "context"

for d in [SKILLS_DIR, CONTEXT_DIR]:
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
        "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-7d4b813cfefe443b908d46f3f25e5f39"),
        "model": "deepseek-chat",
        "max_context": 64000,
    },
    "gpt-oss": {
        "base_url": "https://ark.ap-southeast.bytepluses.com/api/v3",
        "api_key": os.getenv("BYTEPLUS_API_KEY", "ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113"),
        "model": "gpt-oss-120b-250805",
        "max_context": 32000,
    },
    "glm": {
        "base_url": "https://ark.ap-southeast.bytepluses.com/api/v3",
        "api_key": os.getenv("BYTEPLUS_API_KEY", "ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113"),
        "model": "glm-4-7-251222",
        "max_context": 32000,
    },
}

# ── Dangerous patterns ───────────────────────────────────────
DESTRUCTIVE_PATTERNS = [
    (r'\brm\s+(-[rf]+\s+|--recursive|--force)', "DELETE FILES"),
    (r'\bgit\s+push\s+.*--force', "FORCE PUSH"),
    (r'\bgit\s+reset\s+--hard', "HARD RESET"),
    (r'\bgit\s+clean\s+-[fd]', "CLEAN UNTRACKED"),
    (r'\bmkfs\b', "FORMAT FILESYSTEM"),
    (r'\bdd\s+if=', "RAW DISK WRITE"),
    (r'>\s*/dev/sd', "WRITE TO DISK"),
    (r'\bsudo\s+rm', "SUDO DELETE"),
    (r'\bDROP\s+TABLE', "DROP TABLE"),
    (r'\bDROP\s+DATABASE', "DROP DATABASE"),
    (r'\btruncate\b', "TRUNCATE"),
    (r'>\s*/etc/', "OVERWRITE SYSTEM FILE"),
]

# ── Token estimation ─────────────────────────────────────────
def estimate_tokens(text: str) -> int:
    """Rough token count (chars / 3.5 for code, / 4 for natural language)."""
    return int(len(text) / 3.5)

def estimate_messages_tokens(messages: list) -> int:
    return sum(estimate_tokens(json.dumps(m, ensure_ascii=False)) for m in messages)


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
            CREATE INDEX IF NOT EXISTS idx_mem_session ON memories(session_id);
            CREATE INDEX IF NOT EXISTS idx_know_cat ON knowledge(category);
        """)
        self.conn.commit()

    def store(self, session_id, role, content, tags=""):
        self.conn.execute("INSERT INTO memories (session_id,role,content,tags) VALUES (?,?,?,?)",
                          (session_id, role, content, tags))
        self.conn.commit()

    def recall(self, session_id, limit=30):
        rows = self.conn.execute(
            "SELECT role,content FROM memories WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)).fetchall()
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

    def learn(self, category, key, value):
        self.conn.execute("""
            INSERT INTO knowledge (category,key,value,updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(category,key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        """, (category, key, value))
        self.conn.commit()

    def know(self, category=None):
        if category:
            return [{"category": r[0], "key": r[1], "value": r[2]}
                    for r in self.conn.execute("SELECT category,key,value FROM knowledge WHERE category=?", (category,)).fetchall()]
        return [{"category": r[0], "key": r[1], "value": r[2]}
                for r in self.conn.execute("SELECT category,key,value FROM knowledge").fetchall()]

    def forget(self, category, key=None):
        if key:
            self.conn.execute("DELETE FROM knowledge WHERE category=? AND key=?", (category, key))
        else:
            self.conn.execute("DELETE FROM knowledge WHERE category=?", (category,))
        self.conn.commit()


# ══════════════════════════════════════════════════════════════
#  SKILLS
# ══════════════════════════════════════════════════════════════
class SkillManager:
    def __init__(self, d: Path = SKILLS_DIR):
        self.dir = d
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self):
        skills = []
        for f in sorted(self.dir.glob("*.md")):
            meta = self._parse(f)
            skills.append({"name": f.stem, **meta})
        return skills

    def get(self, name):
        f = self.dir / f"{name}.md"
        return f.read_text() if f.exists() else None

    def save(self, name, content, description="", trigger=""):
        header = f"---\ndescription: \"{description}\"\ntrigger: \"{trigger}\"\n---\n\n"
        (self.dir / f"{name}.md").write_text(header + content)

    def _parse(self, path):
        text = path.read_text()[:500]
        desc = re.search(r'description:\s*"([^"]*)"', text)
        trig = re.search(r'trigger:\s*"([^"]*)"', text)
        return {"description": desc.group(1) if desc else "", "trigger": trig.group(1) if trig else ""}


# ══════════════════════════════════════════════════════════════
#  SAFETY — destructive ops detection
# ══════════════════════════════════════════════════════════════
def is_destructive(tool_name: str, args: dict) -> Optional[str]:
    """Check if a tool call is destructive. Returns reason or None."""
    if tool_name == "terminal":
        cmd = args.get("command", "")
        for pattern, reason in DESTRUCTIVE_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return f"{reason}: {cmd[:80]}"

    if tool_name == "write_file":
        path = args.get("path", "")
        full = ROOT / path
        if full.exists() and full.stat().st_size > 10000:
            return f"OVERWRITE LARGE FILE ({full.stat().st_size:,} bytes): {path}"

    if tool_name == "git":
        git_args = args.get("args", "")
        for pattern, reason in DESTRUCTIVE_PATTERNS:
            if re.search(pattern, f"git {git_args}", re.IGNORECASE):
                return f"{reason}: git {git_args[:60]}"

    return None


def confirm_destructive(reason: str) -> bool:
    """Ask user for confirmation."""
    C.print(f"\n  [warn]⚠ WARNING: {reason}[/warn]")
    try:
        answer = C.input("  [warn]Proceed? (y/N):[/warn] ")
        return answer.strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


# ══════════════════════════════════════════════════════════════
#  AGENTS.md loader
# ══════════════════════════════════════════════════════════════
def load_agents_md() -> str:
    """Load AGENTS.md / CLAUDE.md / .cursorrules from project root."""
    candidates = ["AGENTS.md", "CLAUDE.md", ".cursorrules", "REGLAS_YGGDRASIL.md"]
    content = ""
    for name in candidates:
        path = ROOT / name
        if path.exists():
            text = path.read_text()[:3000]
            content += f"\n\n## {name} (project rules):\n{text}\n"
    return content


# ══════════════════════════════════════════════════════════════
#  TOOLS
# ══════════════════════════════════════════════════════════════
TOOLS = [
    {"type": "function", "function": {
        "name": "terminal",
        "description": "Execute a shell command. Returns stdout/stderr/exit code. Use for builds, git, installs, scripts.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Shell command"},
            "workdir": {"type": "string", "description": "Working dir (relative to root)"},
            "timeout": {"type": "integer", "description": "Timeout seconds (default 30)"},
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
        "description": "Write content to a file. Creates dirs. Overwrites existing. CAUTION: overwrites without asking!",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "patch_file",
        "description": "Find-and-replace edit. Targeted change without rewriting the whole file.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"},
        }, "required": ["path", "old_string", "new_string"]},
    }},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Regex search across files. Returns matches with file paths and line numbers.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}, "glob": {"type": "string", "default": "*"}, "max_results": {"type": "integer", "default": 30},
        }, "required": ["pattern"]},
    }},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List files/directories with sizes and dates.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "default": "."}, "pattern": {"type": "string", "default": "*"}, "recursive": {"type": "boolean", "default": False},
        }},
    }},
    {"type": "function", "function": {
        "name": "git",
        "description": "Run git command. Common: status, diff, log, add, commit, branch.",
        "parameters": {"type": "object", "properties": {
            "args": {"type": "string"},
        }, "required": ["args"]},
    }},
    {"type": "function", "function": {
        "name": "python_exec",
        "description": "Execute Python code in the venv. Returns stdout. For data processing, testing, calculations.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string"},
        }, "required": ["code"]},
    }},
    {"type": "function", "function": {
        "name": "think",
        "description": "Think step by step. Use for complex reasoning before acting. User sees your thoughts.",
        "parameters": {"type": "object", "properties": {
            "thought": {"type": "string"},
        }, "required": ["thought"]},
    }},
    {"type": "function", "function": {
        "name": "remember",
        "description": "Save a fact to persistent memory. Use when you learn something useful.",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "user|environment|project|preference|convention|pitfall"},
            "key": {"type": "string"}, "value": {"type": "string"},
        }, "required": ["category", "key", "value"]},
    }},
    {"type": "function", "function": {
        "name": "recall",
        "description": "Search persistent memory for previously saved facts.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "save_skill",
        "description": "Save a reusable procedure as a skill. Use after non-trivial workflows.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"},
            "content": {"type": "string"}, "trigger": {"type": "string"},
        }, "required": ["name", "content"]},
    }},
    {"type": "function", "function": {
        "name": "load_skill",
        "description": "Load a previously saved skill.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"},
        }, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "create_plan",
        "description": "Create a step-by-step plan for complex tasks.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string"}, "steps": {"type": "array", "items": {"type": "string"}},
        }, "required": ["task", "steps"]},
    }},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web for documentation, APIs, solutions. Use curl to fetch URLs.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        }, "required": ["url"]},
    }},
]


def run_tool(name: str, args: dict, memory: Memory, skills: SkillManager) -> str:
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
                return f"Text not found in {args['path']}. Maybe it changed?"
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

        elif name == "web_search":
            url = args["url"]
            r = subprocess.run(["curl", "-sL", "--max-time", "15", url], capture_output=True, text=True, timeout=20)
            return r.stdout[:4000] or "No response"

        return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s)"
    except Exception as e:
        return f"Error: {str(e)[:500]}"


# ══════════════════════════════════════════════════════════════
#  AGENT
# ══════════════════════════════════════════════════════════════
BASE_SYSTEM = """You are Lilith — the dark goddess of Yggdrasil Digital. A powerful AI coding agent.

PERSONALITY:
- Direct, no fluff. Authority with warmth.
- Elder Futhark runes for emphasis (not every message).
- When uncertain, think step by step. When confident, act.
- No emojis. Use runes (ᚦ ᛟ ᚨ ᛚ ᛒ) or text symbols.
- Concise unless detail is needed.

CAPABILITIES: terminal, read_file, write_file, patch_file, search_files, list_files, git, python_exec, think, remember, recall, save_skill, load_skill, create_plan, web_search.

BEHAVIOR:
1. THINK first if complex. Create a plan.
2. Execute proactively — don't describe, DO.
3. If something fails, debug it. Read errors. Try fixes.
4. After non-trivial work, SAVE what you learned as a skill.
5. REMEMBER user preferences, environment, conventions.
6. Load skills before starting work.
7. When you discover something useful, remember it.

CONTEXT:
- Root: ~/Proyectos/Yggdrasil/
- Nine Realms: Asgard (core), Vanaheim (agents), Alfheim (UI), Svartalfheim (docs), Muspelheim (dev), Niflheim (assets), Helheim (archive), Jotunheim (massive), Midgard (personal)
- User: Brierainz, bspwm, CachyOS, dual monitors, night owl
- Active: Horror GameMaster, Audio Auto-Switch, Yggdrasil CLI
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
        self.error_count = 0
        self._build_context()

    def _build_context(self):
        """Build system prompt with all context."""
        parts = [BASE_SYSTEM]

        # AGENTS.md / project rules
        agents_md = load_agents_md()
        if agents_md:
            parts.append(agents_md)

        # Knowledge
        knowledge = self.memory.know()
        if knowledge:
            ktext = "\n\nKNOWN FACTS:\n"
            for k in knowledge:
                ktext += f"- [{k['category']}] {k['key']}: {k['value']}\n"
            parts.append(ktext)

        # Skills list
        skills = self.skills.list()
        if skills:
            stext = "\n\nSAVED SKILLS:\n"
            for s in skills:
                stext += f"- {s['name']}: {s['description']}\n"
            parts.append(stext)

        # Current plan
        plan = CONTEXT_DIR / "current_plan.md"
        if plan.exists():
            parts.append(f"\n\nCURRENT PLAN:\n{plan.read_text()}\n")

        self.messages = [{"role": "system", "content": "\n".join(parts)}]

        # Recent session context
        prev = self.memory.sessions(limit=1)
        if prev:
            mems = self.memory.recall(prev[0], limit=4)
            if mems:
                ctx = "\n".join(f"[{m['role']}]: {m['content'][:150]}" for m in mems)
                self.messages.append({"role": "system", "content": f"RECENT CONTEXT:\n{ctx}"})

    def _manage_context(self):
        """Auto-summarize if context is getting too long."""
        tokens = estimate_messages_tokens(self.messages)
        threshold = self.max_context * 0.75

        if tokens > threshold:
            # Summarize old messages (keep system + last 6)
            C.print(f"  [muted]Context: ~{tokens:,} tokens, summarizing...[/muted]")

            old_msgs = self.messages[1:-6]  # skip system, keep last 6
            if len(old_msgs) < 3:
                return

            summary_parts = []
            for m in old_msgs:
                if m["role"] == "user":
                    summary_parts.append(f"User: {m['content'][:100]}")
                elif m["role"] == "assistant":
                    summary_parts.append(f"Lilith: {m['content'][:100]}")
                elif m["role"] == "tool":
                    summary_parts.append(f"Tool result: {m['content'][:80]}")

            summary = "Previous conversation summary:\n" + "\n".join(summary_parts[-20:])

            # Rebuild: system + summary + last 6 messages
            self.messages = [self.messages[0]] + [{"role": "system", "content": summary}] + self.messages[-6:]
            new_tokens = estimate_messages_tokens(self.messages)
            C.print(f"  [muted]Reduced to ~{new_tokens:,} tokens[/muted]")

    def _call_api(self, messages, stream=False):
        url = f"{self.provider['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.provider['api_key']}"}
        payload = {
            "model": self.model, "messages": messages,
            "temperature": 0.7, "max_tokens": 8192,
            "stream": stream, "tools": TOOLS,
        }
        resp = requests.post(url, headers=headers, json=payload, stream=stream, timeout=120)
        resp.raise_for_status()
        return resp

    def _handle_tools(self, tool_calls):
        results = []
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

            # Safety check
            danger = is_destructive(name, args)
            if danger:
                if not confirm_destructive(danger):
                    results.append({"tool_call_id": tc["id"], "role": "tool", "content": "BLOCKED: User denied this destructive operation."})
                    continue

            result = run_tool(name, args, self.memory, self.skills)

            # Error recovery: if tool failed, note it
            if result.startswith("Error:") or "[exit:" in result:
                self.error_count += 1

            results.append({"tool_call_id": tc["id"], "role": "tool", "content": result})

        return results

    def chat_stream(self, user_input: str) -> str:
        """Stream a response with tool-use loop."""
        self.messages.append({"role": "user", "content": user_input})
        self.memory.store(self.session_id, "user", user_input)

        # Context management
        self._manage_context()

        for _ in range(15):
            try:
                # Try streaming
                resp = self._call_api(self.messages, stream=True)
                content = ""
                tool_calls = []
                buffer = ""

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})

                        # Text content
                        if delta.get("content"):
                            token = delta["content"]
                            content += token
                            C.print(token, end="", highlight=False)

                        # Tool calls
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                while len(tool_calls) <= idx:
                                    tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                                if tc.get("id"):
                                    tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

                    except json.JSONDecodeError:
                        continue

                # Handle tool calls
                if tool_calls:
                    assistant_msg = {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
                    self.messages.append(assistant_msg)
                    results = self._handle_tools(tool_calls)
                    self.messages.extend(results)
                    if content:
                        C.print()
                    continue

                # Final response
                if content:
                    C.print()  # newline
                    self.messages.append({"role": "assistant", "content": content})
                    self.memory.store(self.session_id, "assistant", content)
                    return content

            except requests.exceptions.HTTPError as e:
                # Fallback to non-streaming
                try:
                    data = self._call_api(self.messages, stream=False).json()
                    msg = data["choices"][0]["message"]
                    if msg.get("tool_calls"):
                        self.messages.append(msg)
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
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝[/lilith]"""


def start_agent(provider="deepseek"):
    C.print()
    C.print(Panel.fit(BANNER, border_style="#1a1d35", title="[lilith]ᛒ LILITH v3[/lilith]", title_align="left"))
    C.print()

    agent = LilithAgent(provider_name=provider)

    C.print(f"  [frost]Provider:[/frost] {agent.provider['base_url'].split('/')[2]}")
    C.print(f"  [frost]Model:[/frost] {agent.model}")
    C.print(f"  [frost]Session:[/frost] {agent.session_id}")
    C.print(f"  [frost]Skills:[/frost] {len(agent.skills.list())} saved")
    C.print(f"  [frost]Knowledge:[/frost] {len(agent.memory.know())} facts")

    # Show loaded rules
    agents_md = load_agents_md()
    if agents_md:
        rules_count = agents_md.count("## ")
        C.print(f"  [frost]Project rules:[/frost] {rules_count} files loaded")
    C.print()
    C.print("  [muted]/quit /clear /memory /skills /knowledge /provider <name>[/muted]")
    C.print()

    while True:
        try:
            user_input = C.input("[user]ᚦ You[/user] [muted]»[/muted] ")
            if not user_input.strip():
                continue

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
                    if mems:
                        C.print(f"  [muted]{s}[/muted]: {mems[0]['content'][:60]}")
                continue
            if cmd == "/skills":
                for s in agent.skills.list():
                    C.print(f"  [frost]{s['name']}[/frost]: {s['description']}")
                if not agent.skills.list():
                    C.print("  [muted]No skills yet.[/muted]")
                continue
            if cmd == "/knowledge":
                for k in agent.memory.know():
                    C.print(f"  [gold][{k['category']}][/gold] {k['key']}: {k['value'][:80]}")
                if not agent.memory.know():
                    C.print("  [muted]No knowledge yet.[/muted]")
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
    p = argparse.ArgumentParser(description="Lilith Agent v3")
    p.add_argument("--provider", default="deepseek", choices=list(PROVIDERS.keys()))
    p.add_argument("-m", "--message", help="Single message")
    args = p.parse_args()

    if args.message:
        agent = LilithAgent(provider_name=args.provider)
        print(agent.chat_stream(args.message))
    else:
        start_agent(args.provider)
