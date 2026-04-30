import logging
import subprocess
from typing import Literal

logger = logging.getLogger("SystemExecutor")


class SystemExecutor:
    def __init__(self):
        # Allow-list or Block-list
        self.blocked_commands = [
            "rm -rf",
            "format",
            "del /s",
            "rd /s",
            "mkfs",
            "dd if=",
        ]

    def assess_risk(self, command: str) -> Literal["low", "medium", "high"]:
        """
        Assess the risk of running a command.
        """
        cmd_lower = command.lower()

        # Check blocked
        for blocked in self.blocked_commands:
            if blocked in cmd_lower:
                return "high"

        # Heuristics
        if "del" in cmd_lower or "remove" in cmd_lower or "move" in cmd_lower:
            return "medium"

        if "pip install" in cmd_lower or "npm install" in cmd_lower:
            return "medium"

        return "low"

    def execute(self, command: str) -> str:
        """
        Executes a system command.
        """
        try:
            logger.info(f"Executing system command: {command}")
            # Use shell=True to allow complex commands, but we rely on assess_risk for safety
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            output = result.stdout.strip()
            if result.stderr:
                output += f"\n[STDERR] {result.stderr.strip()}"

            return output
        except Exception as e:
            logger.error(f"System command failed: {e}")
            return f"âŒ Execution Error: {str(e)}"
