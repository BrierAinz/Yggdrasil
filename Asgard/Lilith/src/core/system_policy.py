from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Set

Risk = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class PolicyDecision:
    risk: Risk
    reason: str
    requires_approval: bool


class SystemPolicy:
    # Windows-focused; extend per OS if needed.
    HIGH_PATTERNS = [
        r"\bformat\b",
        r"\bdiskpart\b",
        r"\bbcdedit\b",
        r"\bvssadmin\b.*\bdelete\b",
        r"\bcipher\b\s+/w\b",
        r"\brm\b\s+-rf\b",
        r"\bdel\b\s+/s\b",
        r"\bdel\b\s+/q\b",
        r"\bremove-item\b.*-recurse",
        r"\bshutdown\b",
        r"\brestart-computer\b",
    ]

    LOW_ALLOW_EXE: Set[str] = {
        "echo",
        "dir",
        "type",
        "whoami",
        "ipconfig",
        "ping",
        "git",
        "python",
        "powershell",
        "cmd",
        "mkdir",
        "cd",
        "copy",
        "xcopy",
        "move",
        "ren",
        "cls",
        "ver",
    }

    # For shells, allow but do not auto-LOW; they can run anything.
    SHELL_EXE: Set[str] = {"cmd", "powershell", "pwsh"}

    def classify(self, command: str) -> PolicyDecision:
        cmd = (command or "").strip()
        if not cmd:
            return PolicyDecision("MEDIUM", "Empty command", True)

        norm = cmd.lower()

        # 1. Check HIGH patterns anywhere in string
        for pat in self.HIGH_PATTERNS:
            if re.search(pat, norm):
                return PolicyDecision("HIGH", f"Matched high-risk pattern: {pat}", True)

        # 2. Extract executable
        exe = self._extract_exe(norm)

        # 3. Shells are powerful, default MEDIUM (require approval unless specifically handled)
        # Actually shells are in LOW_ALLOW_EXE above?
        # The prompt says: "If the command is outside allowlist and not safe -> MEDIUM"
        # "Shells... allow but do not auto-LOW".

        # Let's refine logic:
        # If shell, check inner command? Too complex for V1 regex.
        # Just mark shells as LOW for "launching shell" is fine?
        # But `cmd /c del /q` is dangerous.
        # The prompt logic:
        # if exe in SHELL_EXE -> MEDIUM (can run arbitrary)
        # else if exe in LOW_ALLOW_EXE -> LOW
        # else MEDIUM

        if exe in self.SHELL_EXE:
            # Exception: simple obvious safe shell commands?
            # For now, stick to prompt: Shell -> MEDIUM
            return PolicyDecision(
                "MEDIUM", "Shell command can execute arbitrary operations", True
            )

        if exe in self.LOW_ALLOW_EXE:
            # still medium if it contains redirection to critical paths etc. (optional later)
            return PolicyDecision("LOW", f"Allowlisted executable: {exe}", False)

        return PolicyDecision("MEDIUM", f"Unknown executable: {exe or 'unknown'}", True)

    def _extract_exe(self, norm: str) -> str:
        # naive parse: first token, strip quotes and path
        # handle "cmd.exe /c ..."
        token = norm.split()[0].strip('"').strip("'")
        token = token.replace("\\", "/")
        exe = token.split("/")[-1]
        if "." in exe:
            exe = exe.rsplit(".", 1)[0]  # remove extension
        return exe
