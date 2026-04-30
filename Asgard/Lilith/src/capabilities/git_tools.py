import logging
import os
import subprocess
from typing import List, Tuple

logger = logging.getLogger("GitTools")


class GitTools:
    def __init__(self, repo_path: str = None):
        # By default, use current working directory or find a git root
        self.repo_path = repo_path or os.getcwd()

    def execute(self, commands: List[str]) -> str:
        """
        Executes a git command.
        Example: commands=["status"] -> "git status"
        """
        full_command = ["git"] + commands

        try:
            logger.info(
                f"Executing git command: {' '.join(full_command)} in {self.repo_path}"
            )
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,  # Raise CalledProcessError on non-zero exit code
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or str(e)
            logger.error(f"Git command failed: {error_msg}")
            return f"âŒ Git Error: {error_msg}"
        except FileNotFoundError:
            return "âŒ Error: Git is not installed or not in PATH."
        except Exception as e:
            logger.error(f"Unexpected error executing git: {e}")
            return f"âŒ Error executing git command: {str(e)}"

    def get_status(self) -> str:
        return self.execute(["status"])

    def get_diff(self) -> str:
        return self.execute(["diff"])
