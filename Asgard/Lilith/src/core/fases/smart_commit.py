"""
Lilith v2.1 - SMART COMMIT MESSAGES MODULE
FASE B: Autonomia Predictiva - Intelligent Commit Message Generation

Features:
- Analyze git diff to understand changes
- Generate conventional commit messages
- Detect breaking changes automatically
- Suggest scopes based on modified files
- Learn from user commit patterns
"""

import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class ChangeType(Enum):
    ADD = "A"
    MODIFY = "M"
    DELETE = "D"
    RENAME = "R"
    COPY = "C"
    TYPE_CHANGE = "T"
    UNMERGED = "U"
    UNKNOWN = "X"


class CommitType(Enum):
    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    CHORE = "chore"
    CI = "ci"
    BUILD = "build"
    REVERT = "revert"
    WIP = "wip"


@dataclass
class FileChange:
    """Represents a single file change."""

    path: str
    change_type: ChangeType
    additions: int = 0
    deletions: int = 0
    content_diff: str = ""
    is_binary: bool = False


@dataclass
class CommitSuggestion:
    """Generated commit suggestion."""

    type: CommitType
    scope: Optional[str]
    description: str
    body: str = ""
    breaking: bool = False
    breaking_description: str = ""
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

    def format_message(self, include_body: bool = False) -> str:
        """Format as conventional commit message."""
        scope_str = f"({self.scope})" if self.scope else ""
        breaking_marker = "!" if self.breaking else ""

        message = f"{self.type.value}{scope_str}{breaking_marker}: {self.description}"

        if include_body and self.body:
            message += f"\n\n{self.body}"

        if self.breaking and self.breaking_description:
            message += f"\n\nBREAKING CHANGE: {self.breaking_description}"

        return message


class GitDiffAnalyzer:
    """Analyzes git diff to extract meaningful information."""

    FILE_PATTERNS = {
        "test": [
            r"test_.*\.py$",
            r".*_test\.py$",
            r"tests/.*",
            r"__tests__/.*",
            r"spec/.*",
        ],
        "docs": [
            r".*\.md$",
            r".*\.rst$",
            r"docs/.*",
            r"README.*",
            r"CHANGELOG.*",
            r"LICENSE.*",
        ],
        "config": [
            r".*\.json$",
            r".*\.yaml$",
            r".*\.yml$",
            r".*\.toml$",
            r"\.env.*",
            r"Makefile",
        ],
        "ci": [
            r"\.github/.*",
            r"\.gitlab-ci.*",
            r"Jenkinsfile",
            r"\.travis\.yml",
            r"azure-pipelines.*",
        ],
        "frontend": [
            r".*\.js$",
            r".*\.ts$",
            r".*\.jsx$",
            r".*\.tsx$",
            r".*\.css$",
            r".*\.html$",
            r"src/frontend/.*",
        ],
        "backend": [r".*\.py$", r"backend/.*", r"server/.*", r"api/.*"],
        "database": [r".*migration.*", r".*schema.*", r"models\.py$", r"\.sql$"],
        "security": [r"auth.*", r"security.*", r"crypto.*", r"password.*", r"token.*"],
    }

    TYPE_KEYWORDS = {
        CommitType.FEAT: [
            "add",
            "implement",
            "create",
            "introduce",
            "support",
            "enable",
            "new",
        ],
        CommitType.FIX: [
            "fix",
            "bug",
            "repair",
            "correct",
            "resolve",
            "patch",
            "hotfix",
        ],
        CommitType.DOCS: ["doc", "document", "readme", "comment", "guide", "tutorial"],
        CommitType.REFACTOR: [
            "refactor",
            "restructure",
            "cleanup",
            "clean",
            "simplify",
            "organize",
        ],
        CommitType.PERF: [
            "perf",
            "optimize",
            "speed",
            "fast",
            "improve",
            "cache",
            "lazy",
        ],
        CommitType.TEST: ["test", "spec", "coverage", "mock", "assert"],
        CommitType.CHORE: [
            "update",
            "upgrade",
            "maintain",
            "bump",
            "remove",
            "delete",
            "move",
        ],
        CommitType.CI: ["ci", "pipeline", "build", "deploy", "github", "gitlab"],
        CommitType.STYLE: ["style", "format", "lint", "whitespace", "indent"],
    }

    BREAKING_INDICATORS = [
        "BREAKING",
        "breaking change",
        "deprecated",
        "removed support",
        "no longer",
        "removed",
        "deleted",
        "dropped",
        "incompatible",
    ]

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def get_staged_changes(self) -> List[FileChange]:
        """Get staged changes from git."""
        try:
            # Get diff stats
            result = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.warning(f"Git diff failed: {result.stderr}")
                return []

            # Parse diff --cached --name-status for change types
            status_result = subprocess.run(
                ["git", "diff", "--cached", "--name-status"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )

            changes = []
            for line in status_result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 2:
                    change_code = parts[0][0]  # First character
                    file_path = parts[1]

                    change_type = self._parse_change_type(change_code)

                    # Get detailed diff for this file
                    diff_content = self._get_file_diff(file_path)
                    additions, deletions = self._count_changes(diff_content)

                    changes.append(
                        FileChange(
                            path=file_path,
                            change_type=change_type,
                            additions=additions,
                            deletions=deletions,
                            content_diff=diff_content,
                            is_binary=self._is_binary_file(file_path),
                        )
                    )

            return changes

        except Exception as e:
            logger.error(f"Error getting staged changes: {e}")
            return []

    def _parse_change_type(self, code: str) -> ChangeType:
        """Parse change type from git status code."""
        mapping = {
            "A": ChangeType.ADD,
            "M": ChangeType.MODIFY,
            "D": ChangeType.DELETE,
            "R": ChangeType.RENAME,
            "C": ChangeType.COPY,
            "T": ChangeType.TYPE_CHANGE,
            "U": ChangeType.UNMERGED,
        }
        return mapping.get(code, ChangeType.UNKNOWN)

    def _get_file_diff(self, file_path: str) -> str:
        """Get diff content for a specific file."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", file_path],
                cwd=self.project_path,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except:
            return ""

    def _count_changes(self, diff_content: str) -> Tuple[int, int]:
        """Count additions and deletions from diff."""
        additions = 0
        deletions = 0

        for line in diff_content.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        return additions, deletions

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary."""
        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".pdf",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
        }
        ext = Path(file_path).suffix.lower()
        return ext in binary_extensions

    def analyze_change_patterns(self, changes: List[FileChange]) -> Dict:
        """Analyze patterns in changes."""
        analysis = {
            "total_files": len(changes),
            "total_additions": sum(c.additions for c in changes),
            "total_deletions": sum(c.deletions for c in changes),
            "change_types": defaultdict(int),
            "affected_areas": set(),
            "main_languages": set(),
            "is_test_only": True,
            "is_docs_only": True,
            "has_new_files": False,
            "has_deletions": False,
            "breaking_indicators": [],
        }

        for change in changes:
            # Count change types
            analysis["change_types"][change.change_type.name] += 1

            # Detect affected areas
            for area, patterns in self.FILE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, change.path, re.IGNORECASE):
                        analysis["affected_areas"].add(area)
                        break

            # Detect language from extension
            ext = Path(change.path).suffix.lower()
            if ext:
                analysis["main_languages"].add(ext)

            # Check flags
            if change.change_type == ChangeType.ADD:
                analysis["has_new_files"] = True
            if change.change_type == ChangeType.DELETE:
                analysis["has_deletions"] = True

            # Check if only tests or docs
            if not any(re.search(p, change.path) for p in self.FILE_PATTERNS["test"]):
                analysis["is_test_only"] = False
            if not any(re.search(p, change.path) for p in self.FILE_PATTERNS["docs"]):
                analysis["is_docs_only"] = False

            # Check for breaking indicators in diff
            for indicator in self.BREAKING_INDICATORS:
                if indicator.lower() in change.content_diff.lower():
                    analysis["breaking_indicators"].append(indicator)

        analysis["affected_areas"] = list(analysis["affected_areas"])
        analysis["main_languages"] = list(analysis["main_languages"])

        return analysis


class CommitMessageGenerator:
    """Generates intelligent commit messages."""

    # Scope mapping based on file paths
    SCOPE_MAPPINGS = {
        "test": "test",
        "tests": "test",
        "docs": "docs",
        "documentation": "docs",
        "config": "config",
        "ci": "ci",
        "frontend": "ui",
        "backend": "api",
        "database": "db",
        "security": "auth",
    }

    # Templates for different scenarios
    DESCRIPTION_TEMPLATES = {
        "add_single": "add {what}",
        "add_multiple": "add {count} {what}s",
        "fix_single": "fix {what}",
        "update": "update {what}",
        "remove": "remove {what}",
        "refactor": "refactor {what}",
        "improve": "improve {what}",
        "implement": "implement {what}",
    }

    def __init__(self, analyzer: GitDiffAnalyzer):
        self.analyzer = analyzer

    def generate_suggestions(self, max_suggestions: int = 3) -> List[CommitSuggestion]:
        """Generate commit message suggestions."""
        changes = self.analyzer.get_staged_changes()

        if not changes:
            return []

        analysis = self.analyzer.analyze_change_patterns(changes)
        suggestions = []

        # Primary suggestion
        primary = self._generate_primary_suggestion(changes, analysis)
        if primary:
            suggestions.append(primary)

        # Alternative suggestions
        alternatives = self._generate_alternatives(changes, analysis)
        for alt in alternatives[: max_suggestions - 1]:
            if alt.description != primary.description:
                suggestions.append(alt)

        return suggestions[:max_suggestions]

    def _generate_primary_suggestion(
        self, changes: List[FileChange], analysis: Dict
    ) -> Optional[CommitSuggestion]:
        """Generate primary commit suggestion."""
        reasoning = []

        # Determine commit type
        commit_type = self._determine_commit_type(changes, analysis)
        reasoning.append(f"Detected commit type: {commit_type.value}")

        # Determine scope
        scope = self._determine_scope(analysis)
        if scope:
            reasoning.append(f"Suggested scope: {scope}")

        # Generate description
        description = self._generate_description(changes, analysis, commit_type)
        reasoning.append(
            f"Generated description based on {analysis['total_files']} files changed"
        )

        # Detect breaking changes
        is_breaking = len(analysis["breaking_indicators"]) > 0
        breaking_desc = ""
        if is_breaking:
            breaking_desc = "Changes may break backward compatibility"
            reasoning.append("Potential breaking change detected")

        # Generate body
        body = self._generate_body(changes, analysis)

        # Calculate confidence
        confidence = self._calculate_confidence(analysis, reasoning)

        return CommitSuggestion(
            type=commit_type,
            scope=scope,
            description=description,
            body=body,
            breaking=is_breaking,
            breaking_description=breaking_desc,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _generate_alternatives(
        self, changes: List[FileChange], analysis: Dict
    ) -> List[CommitSuggestion]:
        """Generate alternative suggestions."""
        alternatives = []

        # Alternative 1: Different commit type
        alt_types = [CommitType.FEAT, CommitType.CHORE, CommitType.REFACTOR]
        current_type = self._determine_commit_type(changes, analysis)

        for alt_type in alt_types:
            if alt_type != current_type:
                alt = CommitSuggestion(
                    type=alt_type,
                    scope=self._determine_scope(analysis),
                    description=self._generate_description(changes, analysis, alt_type),
                    confidence=0.6,
                )
                alternatives.append(alt)
                break

        # Alternative 2: No scope
        no_scope = CommitSuggestion(
            type=current_type,
            scope=None,
            description=self._generate_description(changes, analysis, current_type),
            confidence=0.7,
        )
        alternatives.append(no_scope)

        return alternatives

    def _determine_commit_type(
        self, changes: List[FileChange], analysis: Dict
    ) -> CommitType:
        """Determine the most appropriate commit type."""
        # Check for special cases first
        if analysis["is_test_only"]:
            return CommitType.TEST

        if analysis["is_docs_only"]:
            return CommitType.DOCS

        if analysis["change_types"].get("ADD", 0) > 0 and analysis["has_new_files"]:
            # Check if these are new features or new files
            non_test_files = [
                c
                for c in changes
                if not any(
                    re.search(p, c.path) for p in self.analyzer.FILE_PATTERNS["test"]
                )
            ]
            if non_test_files:
                return CommitType.FEAT

        if analysis["change_types"].get("DELETE", 0) > 0:
            return CommitType.CHORE

        # Analyze diff content for keywords
        all_diff = " ".join([c.content_diff for c in changes])

        type_scores = defaultdict(int)
        for commit_type, keywords in self.analyzer.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in all_diff.lower():
                    type_scores[commit_type] += 1

        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]

        # Default based on change size
        total_changes = analysis["total_additions"] + analysis["total_deletions"]
        if total_changes < 10:
            return CommitType.CHORE

        return CommitType.REFACTOR

    def _determine_scope(self, analysis: Dict) -> Optional[str]:
        """Determine the scope based on affected areas."""
        areas = analysis.get("affected_areas", [])

        if not areas:
            return None

        # Map areas to conventional commit scopes
        for area in areas:
            if area in self.SCOPE_MAPPINGS:
                return self.SCOPE_MAPPINGS[area]

        # Use first area as scope
        return areas[0]

    def _generate_description(
        self, changes: List[FileChange], analysis: Dict, commit_type: CommitType
    ) -> str:
        """Generate commit description."""
        # Get main files being changed
        main_files = [c.path for c in changes[:3]]

        # Extract meaningful name from file paths
        if len(changes) == 1:
            file_name = Path(changes[0].path).stem.replace("_", " ")
            return f"{commit_type.value} {file_name}"

        # Multiple files
        if analysis["has_new_files"] and analysis["change_types"].get("ADD", 0) > 0:
            count = analysis["change_types"]["ADD"]
            what = "module" if count == 1 else "modules"
            return f"add {count} new {what}"

        if analysis["is_test_only"]:
            count = len(changes)
            what = "test" if count == 1 else "tests"
            return f"add {count} {what}"

        # Default: describe what changed
        if analysis["affected_areas"]:
            area = analysis["affected_areas"][0]
            if commit_type == CommitType.FIX:
                return f"fix {area} issues"
            elif commit_type == CommitType.REFACTOR:
                return f"refactor {area} implementation"
            else:
                return f"update {area}"

        # Fallback: count files
        count = len(changes)
        return f"update {count} files"

    def _generate_body(self, changes: List[FileChange], analysis: Dict) -> str:
        """Generate detailed commit body."""
        lines = []

        # List changed files
        if len(changes) <= 10:
            lines.append("Changes:")
            for change in changes:
                prefix = (
                    "+"
                    if change.change_type == ChangeType.ADD
                    else "~"
                    if change.change_type == ChangeType.MODIFY
                    else "-"
                )
                lines.append(f"  {prefix} {change.path}")
        else:
            lines.append(f"Modified {len(changes)} files")

        # Add statistics
        lines.append(
            f"\nStats: +{analysis['total_additions']}/-{analysis['total_deletions']}"
        )

        return "\n".join(lines)

    def _calculate_confidence(self, analysis: Dict, reasoning: List[str]) -> float:
        """Calculate confidence score for suggestion."""
        base_confidence = 0.7

        # Boost confidence for clear patterns
        if analysis["is_test_only"] or analysis["is_docs_only"]:
            base_confidence += 0.15

        if len(reasoning) >= 3:
            base_confidence += 0.05

        # Reduce confidence for mixed changes
        if len(analysis["affected_areas"]) > 2:
            base_confidence -= 0.1

        return min(max(base_confidence, 0.0), 0.95)


class SmartCommitEngine:
    """Main engine for smart commit messages."""

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.analyzer = GitDiffAnalyzer(self.project_path)
        self.generator = CommitMessageGenerator(self.analyzer)

    async def get_suggestions(self, count: int = 3) -> List[CommitSuggestion]:
        """Get commit message suggestions."""
        return self.generator.generate_suggestions(count)

    async def analyze_staged(self) -> Dict:
        """Analyze staged changes."""
        changes = self.analyzer.get_staged_changes()
        if not changes:
            return {"has_changes": False, "message": "No staged changes found"}

        analysis = self.analyzer.analyze_change_patterns(changes)

        return {
            "has_changes": True,
            "files_changed": len(changes),
            "additions": analysis["total_additions"],
            "deletions": analysis["total_deletions"],
            "change_types": dict(analysis["change_types"]),
            "affected_areas": analysis["affected_areas"],
            "breaking_risk": len(analysis["breaking_indicators"]) > 0,
            "is_test_only": analysis["is_test_only"],
            "is_docs_only": analysis["is_docs_only"],
        }

    async def validate_message(self, message: str) -> Dict:
        """Validate a commit message."""
        issues = []
        warnings = []

        # Check length
        if len(message) > 72:
            warnings.append("Subject line exceeds 72 characters")

        if len(message) < 10:
            issues.append("Subject line too short")

        # Check conventional commit format
        conventional_pattern = r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?(!)?: .+"
        if not re.match(conventional_pattern, message):
            warnings.append("Does not follow conventional commit format")

        # Check for imperative mood
        non_imperative = ["added", "fixed", "updated", "removed", "created", "changed"]
        first_word = message.split(":")[-1].strip().split()[0].lower()
        if first_word in non_imperative:
            warnings.append(
                f"Use imperative mood (e.g., 'add' instead of '{first_word}')"
            )

        # Check for period at end
        if message.rstrip().endswith("."):
            warnings.append("Subject should not end with a period")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20) - (len(warnings) * 10),
        }

    async def commit(self, message: str, body: str = "", amend: bool = False) -> Dict:
        """Execute git commit with given message."""
        try:
            cmd = ["git", "commit"]

            if amend:
                cmd.append("--amend")
                cmd.append("--no-edit")

            full_message = message
            if body:
                full_message += f"\n\n{body}"

            cmd.extend(["-m", full_message])

            result = subprocess.run(
                cmd, cwd=self.project_path, capture_output=True, text=True
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr,
            }

        except Exception as e:
            return {"success": False, "output": str(e)}


# Global instance
_smart_commit_engine = None


def get_smart_commit_engine(project_path: Optional[Path] = None) -> SmartCommitEngine:
    global _smart_commit_engine
    if _smart_commit_engine is None:
        _smart_commit_engine = SmartCommitEngine(project_path)
    return _smart_commit_engine
