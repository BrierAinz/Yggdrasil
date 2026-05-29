"""
GitTools - Git repository management for Lilith
Handles git operations: status, log, diff, branch, commit, clone, pull, push
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GitTools:
    """
    Autonomous tool for git repository operations.

    Capabilities:
    - status: Check repository status (modified, staged, untracked files)
    - log: View commit history
    - diff: Show differences between commits or working directory
    - branch: List, create, switch branches
    - commit: Create commits with messages
    - clone: Clone remote repositories
    - remote: Manage remote repositories
    - pull/push: Sync with remotes (with confirmation)
    """

    def __init__(self):
        self.protected_branches = ["main", "master", "production", "release"]
        self.max_diff_lines = 500
        self.max_log_entries = 50

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute git operation

        Args:
            action: The git operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Dict with operation results
        """
        try:
            if action == "status":
                return await self._git_status(kwargs.get("repo_path", "."))
            elif action == "log":
                return await self._git_log(
                    kwargs.get("repo_path", "."),
                    kwargs.get("max_entries", self.max_log_entries),
                    kwargs.get("branch", None),
                )
            elif action == "diff":
                return await self._git_diff(
                    kwargs.get("repo_path", "."),
                    kwargs.get("target", None),
                    kwargs.get("cached", False),
                )
            elif action == "branch":
                return await self._git_branch(
                    kwargs.get("repo_path", "."),
                    kwargs.get("sub_action", "list"),
                    kwargs.get("branch_name", None),
                )
            elif action == "commit":
                return await self._git_commit(
                    kwargs.get("repo_path", "."),
                    kwargs.get("message", None),
                    kwargs.get("files", None),
                    kwargs.get("dry_run", False),
                )
            elif action == "clone":
                return await self._git_clone(
                    kwargs.get("repo_url", None),
                    kwargs.get("target_path", None),
                    kwargs.get("branch", None),
                )
            elif action == "remote":
                return await self._git_remote(
                    kwargs.get("repo_path", "."), kwargs.get("sub_action", "list")
                )
            elif action == "pull":
                return await self._git_pull_push(
                    kwargs.get("repo_path", "."), "pull", kwargs.get("dry_run", False)
                )
            elif action == "push":
                return await self._git_pull_push(
                    kwargs.get("repo_path", "."), "push", kwargs.get("dry_run", False)
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown git action: {action}",
                    "action": action,
                }
        except Exception as e:
            logger.error(f"Git operation failed: {e}")
            return {"success": False, "error": str(e), "action": action}

    async def _git_status(self, repo_path: str) -> Dict[str, Any]:
        """Get repository status"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {
                "success": False,
                "error": f"Not a git repository: {repo_path}",
                "is_git_repo": False,
            }

        try:
            # Get status in short format
            result = subprocess.run(
                ["git", "-C", str(repo_path), "status", "--porcelain", "--branch"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {"success": False, "error": result.stderr, "is_git_repo": True}

            # Parse status output
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

            staged = []
            modified = []
            untracked = []
            branch_info = {"branch": "unknown", "ahead": 0, "behind": 0}

            for line in lines:
                if line.startswith("##"):
                    # Branch info line
                    branch_line = line[3:]
                    if "..." in branch_line:
                        branch_info["branch"] = branch_line.split("...")[0]
                        if "[ahead " in branch_line:
                            ahead_match = branch_line.split("[ahead ")[1].split("]")[0]
                            branch_info["ahead"] = (
                                int(ahead_match.split(",")[0])
                                if "," in ahead_match
                                else int(ahead_match)
                            )
                        if "[behind " in branch_line:
                            behind_match = branch_line.split("[behind ")[1].split("]")[
                                0
                            ]
                            branch_info["behind"] = (
                                int(behind_match.split(",")[0])
                                if "," in behind_match
                                else int(behind_match)
                            )
                    else:
                        branch_info["branch"] = branch_line
                elif (
                    line.startswith("M ")
                    or line.startswith("A ")
                    or line.startswith("D ")
                    or line.startswith("R ")
                ):
                    staged.append({"status": line[:2].strip(), "file": line[3:]})
                elif (
                    line.startswith(" M")
                    or line.startswith(" D")
                    or line.startswith("??")
                ):
                    if line.startswith("??"):
                        untracked.append(line[3:])
                    else:
                        modified.append({"status": line[:2].strip(), "file": line[3:]})

            # Check if working tree is clean
            is_clean = len(staged) == 0 and len(modified) == 0 and len(untracked) == 0

            return {
                "success": True,
                "repo_path": str(repo_path),
                "branch": branch_info["branch"],
                "ahead": branch_info["ahead"],
                "behind": branch_info["behind"],
                "is_clean": is_clean,
                "staged": staged,
                "modified": modified,
                "untracked": untracked,
                "staged_count": len(staged),
                "modified_count": len(modified),
                "untracked_count": len(untracked),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git status timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_log(
        self, repo_path: str, max_entries: int = 50, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get commit history"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        try:
            cmd = [
                "git",
                "-C",
                str(repo_path),
                "log",
                f"-n{max_entries}",
                "--pretty=format:%H|%an|%ae|%ad|%s",
                "--date=short",
            ]
            if branch:
                cmd.append(branch)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 4)
                    if len(parts) >= 5:
                        commits.append(
                            {
                                "hash": parts[0][:7],
                                "full_hash": parts[0],
                                "author": parts[1],
                                "email": parts[2],
                                "date": parts[3],
                                "message": parts[4],
                            }
                        )

            return {
                "success": True,
                "repo_path": str(repo_path),
                "commits": commits,
                "count": len(commits),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git log timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_diff(
        self, repo_path: str, target: Optional[str] = None, cached: bool = False
    ) -> Dict[str, Any]:
        """Show differences"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        try:
            cmd = ["git", "-C", str(repo_path), "diff"]
            if cached:
                cmd.append("--cached")
            if target:
                cmd.append(target)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            diff_text = result.stdout
            lines = diff_text.split("\n")

            # Truncate if too large
            truncated = len(lines) > self.max_diff_lines
            if truncated:
                lines = lines[: self.max_diff_lines]
                lines.append(
                    f"\n... (truncated, showing {self.max_diff_lines} of {len(result.stdout.split(chr(10)))} lines)"
                )

            # Parse file changes
            files_changed = []
            for line in lines:
                if line.startswith("diff --git"):
                    file_match = line.split(" b/")[-1] if " b/" in line else None
                    if file_match:
                        files_changed.append(file_match)

            return {
                "success": True,
                "repo_path": str(repo_path),
                "diff": "\n".join(lines),
                "files_changed": list(set(files_changed)),
                "truncated": truncated,
                "line_count": len(result.stdout.split("\n")),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git diff timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_branch(
        self,
        repo_path: str,
        sub_action: str = "list",
        branch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manage branches"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        try:
            if sub_action == "list":
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "branch", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return {"success": False, "error": result.stderr}

                branches = []
                current = None
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("*"):
                        current = line[2:]
                        branches.append({"name": current, "current": True})
                    elif line:
                        branches.append(
                            {"name": line.replace("remotes/", ""), "current": False}
                        )

                return {
                    "success": True,
                    "repo_path": str(repo_path),
                    "current": current,
                    "branches": branches,
                    "count": len(branches),
                }

            elif sub_action == "create" and branch_name:
                # Check if protected branch
                if branch_name in self.protected_branches:
                    return {
                        "success": False,
                        "error": f"Cannot create protected branch: {branch_name}",
                        "protected": True,
                    }

                result = subprocess.run(
                    ["git", "-C", str(repo_path), "checkout", "-b", branch_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                return {
                    "success": result.returncode == 0,
                    "message": result.stdout
                    if result.returncode == 0
                    else result.stderr,
                    "branch": branch_name,
                }

            elif sub_action == "switch" and branch_name:
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "checkout", branch_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                return {
                    "success": result.returncode == 0,
                    "message": result.stdout
                    if result.returncode == 0
                    else result.stderr,
                    "branch": branch_name,
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown branch action: {sub_action}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git branch operation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_commit(
        self,
        repo_path: str,
        message: Optional[str],
        files: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create a commit"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        if not message:
            return {"success": False, "error": "Commit message is required"}

        try:
            # Stage files if specified
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "-C", str(repo_path), "add", file],
                        capture_output=True,
                        timeout=30,
                    )
            else:
                # Stage all changes
                subprocess.run(
                    ["git", "-C", str(repo_path), "add", "-A"],
                    capture_output=True,
                    timeout=30,
                )

            if dry_run:
                # Show what would be committed
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "diff", "--cached", "--stat"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {
                    "success": True,
                    "dry_run": True,
                    "message": message,
                    "staged_changes": result.stdout,
                }

            # Create commit
            result = subprocess.run(
                ["git", "-C", str(repo_path), "commit", "-m", message],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                commit_hash = (
                    hash_result.stdout.strip()
                    if hash_result.returncode == 0
                    else "unknown"
                )

                return {
                    "success": True,
                    "message": message,
                    "commit_hash": commit_hash,
                    "output": result.stdout,
                }
            else:
                return {"success": False, "error": result.stderr, "message": message}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git commit timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_clone(
        self,
        repo_url: Optional[str],
        target_path: Optional[str],
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone a repository"""
        if not repo_url:
            return {"success": False, "error": "Repository URL is required"}

        if not target_path:
            # Extract repo name from URL
            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
            target_path = os.path.join(".", repo_name)

        target_path = Path(target_path).resolve()

        # Safety: Don't overwrite existing directory
        if target_path.exists():
            return {
                "success": False,
                "error": f"Target directory already exists: {target_path}",
                "exists": True,
            }

        try:
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["-b", branch, "--single-branch"])
            cmd.extend([repo_url, str(target_path)])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            return {
                "success": result.returncode == 0,
                "repo_url": repo_url,
                "target_path": str(target_path),
                "branch": branch,
                "message": result.stdout if result.returncode == 0 else result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git clone timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_remote(
        self, repo_path: str, sub_action: str = "list"
    ) -> Dict[str, Any]:
        """Manage remotes"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        try:
            if sub_action == "list":
                result = subprocess.run(
                    ["git", "-C", str(repo_path), "remote", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    return {"success": False, "error": result.stderr}

                remotes = {}
                for line in result.stdout.strip().split("\n"):
                    if "\t" in line:
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            name = parts[0]
                            url = parts[1].split(" ")[0]
                            remote_type = "fetch" if "(fetch)" in line else "push"
                            if name not in remotes:
                                remotes[name] = {}
                            remotes[name][remote_type] = url

                return {
                    "success": True,
                    "repo_path": str(repo_path),
                    "remotes": remotes,
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown remote action: {sub_action}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git remote operation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _git_pull_push(
        self, repo_path: str, operation: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Pull or push changes (with safety checks)"""
        repo_path = Path(repo_path).resolve()

        if not (repo_path / ".git").exists():
            return {"success": False, "error": f"Not a git repository: {repo_path}"}

        # Get current branch
        branch_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        current_branch = (
            branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        )

        # Safety warning for protected branches
        is_protected = current_branch in self.protected_branches

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "operation": operation,
                "branch": current_branch,
                "protected": is_protected,
                "warning": f"{operation} on protected branch: {current_branch}"
                if is_protected
                else None,
            }

        try:
            cmd = ["git", "-C", str(repo_path), operation]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            return {
                "success": result.returncode == 0,
                "operation": operation,
                "branch": current_branch,
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "protected_branch": is_protected,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Git {operation} timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
