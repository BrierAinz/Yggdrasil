"""
GitContext - MÃ³dulo de consciencia Git para Lilith

Proporciona contexto en tiempo real del estado del repositorio git,
permitiendo a Lilith ser consciente de:
- Branch actual
- Archivos modificados/staged/untracked
- Commits pendientes de push
- Estado de merge/rebase
- Sugerencias de commits basadas en diff
"""

import logging
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GitContext")


@dataclass
class GitFileStatus:
    """Estado de un archivo en git"""

    path: str
    status: str  # M, A, D, R, C, U, ??, etc.
    status_text: str  # modified, added, deleted, untracked, etc.
    staged: bool
    worktree: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GitBranchInfo:
    """InformaciÃ³n de una branch"""

    name: str
    current: bool
    remote: Optional[str]
    ahead: int  # Commits locales no pusheados
    behind: int  # Commits remotos no pulleados

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GitContext:
    """Contexto completo del repositorio git"""

    is_git_repo: bool
    repo_path: Optional[str]
    current_branch: Optional[str]
    branches: List[GitBranchInfo]
    files: List[GitFileStatus]
    commit_message_suggestion: Optional[str]
    has_changes: bool
    last_commit_hash: Optional[str]
    last_commit_message: Optional[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_git_repo": self.is_git_repo,
            "repo_path": self.repo_path,
            "current_branch": self.current_branch,
            "branches": [b.to_dict() for b in self.branches],
            "files": [f.to_dict() for f in self.files],
            "commit_message_suggestion": self.commit_message_suggestion,
            "has_changes": self.has_changes,
            "last_commit_hash": self.last_commit_hash,
            "last_commit_message": self.last_commit_message,
            "timestamp": self.timestamp,
        }


class GitContextManager:
    """
    Manager de contexto Git para Lilith.

    Proporciona informaciÃ³n en tiempo real sobre el estado del repositorio
    y sugiere acciones basadas en el contexto.
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getcwd()
        self._cache: Optional[GitContext] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 5  # Cache de 5 segundos

    def _run_git_command(self, args: List[str], cwd: Optional[str] = None) -> tuple:
        """Ejecutar comando git de forma segura"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or self.base_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return False, "", str(e)

    def _is_git_repo(self, path: str) -> bool:
        """Verificar si un path es un repositorio git"""
        success, _, _ = self._run_git_command(["rev-parse", "--git-dir"], cwd=path)
        return success

    def _find_git_root(self, path: str) -> Optional[str]:
        """Encontrar la raÃ­z del repositorio git"""
        success, stdout, _ = self._run_git_command(
            ["rev-parse", "--show-toplevel"], cwd=path
        )
        if success:
            return stdout.strip()
        return None

    def _get_current_branch(self, path: str) -> Optional[str]:
        """Obtener la branch actual"""
        success, stdout, _ = self._run_git_command(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=path
        )
        if success:
            return stdout.strip()
        return None

    def _get_branch_info(self, path: str) -> List[GitBranchInfo]:
        """Obtener informaciÃ³n de todas las branches"""
        branches = []
        current = self._get_current_branch(path)

        # Listar branches locales con tracking info
        success, stdout, _ = self._run_git_command(["branch", "-vv"], cwd=path)
        if not success:
            return branches

        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            is_current = line.startswith("*")
            if is_current:
                line = line[1:].strip()

            parts = line.split()
            if not parts:
                continue

            branch_name = parts[0]
            remote = None
            ahead = 0
            behind = 0

            # Parsear ahead/behind si existe [ahead X, behind Y]
            for i, part in enumerate(parts):
                if "[" in part and "]" in part:
                    tracking = part.strip("[]")
                    if "ahead" in tracking:
                        try:
                            ahead = int(
                                tracking.split("ahead")[1].split(",")[0].strip()
                            )
                        except:
                            pass
                    if "behind" in tracking:
                        try:
                            behind = int(
                                tracking.split("behind")[1].split(",")[0].strip()
                            )
                        except:
                            pass
                    remote = parts[i - 1] if i > 0 else None

            branches.append(
                GitBranchInfo(
                    name=branch_name,
                    current=is_current,
                    remote=remote,
                    ahead=ahead,
                    behind=behind,
                )
            )

        return branches

    def _get_file_status(self, path: str) -> List[GitFileStatus]:
        """Obtener estado de archivos"""
        files = []

        # Status porcelain v1 (estable)
        success, stdout, _ = self._run_git_command(
            ["status", "--porcelain", "-u"], cwd=path
        )
        if not success:
            return files

        status_map = {
            "M": "modified",
            "A": "added",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "updated but unmerged",
            "?": "untracked",
            "!": "ignored",
        }

        for line in stdout.strip().split("\n"):
            if len(line) < 3:
                continue

            index_status = line[0]  # Staging area
            worktree_status = line[1]  # Working tree
            file_path = line[3:]

            # Determinar estado combinado
            if index_status != " " and index_status != "?":
                status = index_status
                staged = True
                worktree = worktree_status != " "
            else:
                status = worktree_status if worktree_status != " " else index_status
                staged = False
                worktree = worktree_status != " "

            status_text = status_map.get(status, "unknown")

            files.append(
                GitFileStatus(
                    path=file_path,
                    status=status,
                    status_text=status_text,
                    staged=staged,
                    worktree=worktree,
                )
            )

        return files

    def _get_last_commit(self, path: str) -> tuple:
        """Obtener informaciÃ³n del Ãºltimo commit"""
        success, stdout, _ = self._run_git_command(
            ["log", "-1", "--format=%H|%s"], cwd=path
        )
        if success and "|" in stdout:
            parts = stdout.strip().split("|", 1)
            return parts[0], parts[1]
        return None, None

    def _generate_commit_suggestion(
        self, files: List[GitFileStatus], last_message: Optional[str]
    ) -> Optional[str]:
        """Generar sugerencia de mensaje de commit basado en cambios"""
        if not files:
            return None

        # Categorizar cambios
        added = [f for f in files if f.status == "A"]
        modified = [f for f in files if f.status == "M"]
        deleted = [f for f in files if f.status == "D"]
        renamed = [f for f in files if f.status == "R"]
        untracked = [f for f in files if f.status == "?"]

        parts = []

        if added and not modified and not deleted:
            if len(added) == 1:
                parts.append(f"Add {added[0].path}")
            else:
                parts.append(f"Add {len(added)} new files")

        elif deleted and not modified and not added:
            if len(deleted) == 1:
                parts.append(f"Remove {deleted[0].path}")
            else:
                parts.append(f"Remove {len(deleted)} files")

        elif modified and len(modified) <= 3 and not added and not deleted:
            file_names = ", ".join([f.path for f in modified])
            parts.append(f"Update {file_names}")

        elif renamed:
            parts.append(f"Rename files")

        elif any("test" in f.path.lower() for f in files):
            parts.append("Update tests")

        elif any("fix" in f.path.lower() or "bug" in f.path.lower() for f in files):
            parts.append("Fix issues")

        elif any("doc" in f.path.lower() or "readme" in f.path.lower() for f in files):
            parts.append("Update documentation")

        elif any(f.path.endswith(".md") for f in files):
            parts.append("Update documentation")

        else:
            # Caso general
            changes = []
            if added:
                changes.append(f"{len(added)} added")
            if modified:
                changes.append(f"{len(modified)} modified")
            if deleted:
                changes.append(f"{len(deleted)} deleted")
            parts.append(f"Changes: {', '.join(changes)}")

        suggestion = " | ".join(parts) if parts else "Update files"

        # Limitar longitud
        if len(suggestion) > 72:
            suggestion = suggestion[:69] + "..."

        return suggestion

    def get_context(self, force_refresh: bool = False) -> GitContext:
        """
        Obtener contexto git completo.

        Args:
            force_refresh: Si True, ignora el cache

        Returns:
            GitContext con toda la informaciÃ³n
        """
        # Verificar cache
        if not force_refresh and self._cache is not None:
            elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
            if elapsed < self._cache_ttl_seconds:
                return self._cache

        # Verificar si es repo git
        if not self._is_git_repo(self.base_path):
            context = GitContext(
                is_git_repo=False,
                repo_path=None,
                current_branch=None,
                branches=[],
                files=[],
                commit_message_suggestion=None,
                has_changes=False,
                last_commit_hash=None,
                last_commit_message=None,
                timestamp=datetime.now().isoformat(),
            )
            self._cache = context
            self._cache_timestamp = datetime.now()
            return context

        # Obtener informaciÃ³n completa
        repo_path = self._find_git_root(self.base_path)
        current_branch = self._get_current_branch(self.base_path)
        branches = self._get_branch_info(self.base_path)
        files = self._get_file_status(self.base_path)
        last_hash, last_message = self._get_last_commit(self.base_path)

        # Generar sugerencia de commit
        staged_files = [f for f in files if f.staged]
        suggestion = self._generate_commit_suggestion(staged_files, last_message)

        context = GitContext(
            is_git_repo=True,
            repo_path=repo_path,
            current_branch=current_branch,
            branches=branches,
            files=files,
            commit_message_suggestion=suggestion,
            has_changes=len(files) > 0,
            last_commit_hash=last_hash,
            last_commit_message=last_message,
            timestamp=datetime.now().isoformat(),
        )

        # Actualizar cache
        self._cache = context
        self._cache_timestamp = datetime.now()

        return context

    def get_quick_status(self) -> Dict[str, Any]:
        """Obtener status rÃ¡pido para dashboards"""
        ctx = self.get_context()

        if not ctx.is_git_repo:
            return {"is_git_repo": False, "message": "No es un repositorio git"}

        staged = len([f for f in ctx.files if f.staged])
        modified = len([f for f in ctx.files if f.status == "M" and not f.staged])
        untracked = len([f for f in ctx.files if f.status == "?"])

        current_branch_info = next((b for b in ctx.branches if b.current), None)

        return {
            "is_git_repo": True,
            "branch": ctx.current_branch,
            "repo_path": ctx.repo_path,
            "ahead": current_branch_info.ahead if current_branch_info else 0,
            "behind": current_branch_info.behind if current_branch_info else 0,
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "has_changes": ctx.has_changes,
            "suggestion": ctx.commit_message_suggestion,
            "last_commit": ctx.last_commit_message[:50] + "..."
            if ctx.last_commit_message and len(ctx.last_commit_message) > 50
            else ctx.last_commit_message,
        }

    def suggest_actions(self) -> List[Dict[str, str]]:
        """Sugerir acciones basadas en el estado actual"""
        ctx = self.get_context()
        suggestions = []

        if not ctx.is_git_repo:
            return suggestions

        staged = [f for f in ctx.files if f.staged]
        modified = [f for f in ctx.files if f.status == "M" and not f.staged]
        untracked = [f for f in ctx.files if f.status == "?"]

        current_branch_info = next((b for b in ctx.branches if b.current), None)

        # Sugerir commit si hay archivos staged
        if staged:
            suggestions.append(
                {
                    "action": "commit",
                    "command": f'git commit -m "{ctx.commit_message_suggestion or "Update files"}"',
                    "reason": f"{len(staged)} archivos listos para commit",
                    "priority": "high",
                }
            )

        # Sugerir add si hay modified no staged
        if modified and not staged:
            suggestions.append(
                {
                    "action": "stage",
                    "command": "git add .",
                    "reason": f"{len(modified)} archivos modificados sin staging",
                    "priority": "medium",
                }
            )

        # Sugerir push si hay commits ahead
        if current_branch_info and current_branch_info.ahead > 0:
            suggestions.append(
                {
                    "action": "push",
                    "command": f"git push origin {ctx.current_branch}",
                    "reason": f"{current_branch_info.ahead} commits pendientes de push",
                    "priority": "medium",
                }
            )

        # Sugerir pull si hay commits behind
        if current_branch_info and current_branch_info.behind > 0:
            suggestions.append(
                {
                    "action": "pull",
                    "command": "git pull origin",
                    "reason": f"{current_branch_info.behind} commits en remoto sin pullear",
                    "priority": "high",
                }
            )

        # Sugerir status si hay muchos untracked
        if len(untracked) > 5:
            suggestions.append(
                {
                    "action": "status",
                    "command": "git status",
                    "reason": f"{len(untracked)} archivos sin trackear",
                    "priority": "low",
                }
            )

        return suggestions


# Singleton para uso global
_git_context_manager: Optional[GitContextManager] = None


def get_git_context_manager(base_path: Optional[str] = None) -> GitContextManager:
    """Obtener instancia singleton del GitContextManager"""
    global _git_context_manager
    if _git_context_manager is None:
        _git_context_manager = GitContextManager(base_path)
    return _git_context_manager


# === Testing ===
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("GitContext - Test Suite")
    print("=" * 60)

    # Test en directorio actual
    manager = GitContextManager()

    print("\n[Test 1] Contexto completo")
    ctx = manager.get_context()
    print(f"âœ“ Is git repo: {ctx.is_git_repo}")
    if ctx.is_git_repo:
        print(f"âœ“ Branch: {ctx.current_branch}")
        print(f"âœ“ Files changed: {len(ctx.files)}")
        print(f"âœ“ Suggestion: {ctx.commit_message_suggestion}")

    print("\n[Test 2] Quick status")
    status = manager.get_quick_status()
    print(json.dumps(status, indent=2))

    print("\n[Test 3] Sugerencias de acciones")
    suggestions = manager.suggest_actions()
    for s in suggestions:
        print(f"  [{s['priority'].upper()}] {s['action']}: {s['reason']}")

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
