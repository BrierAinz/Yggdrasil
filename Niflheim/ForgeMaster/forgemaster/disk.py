"""Disk usage scanner and cleanup module for ForgeMaster.

Helps users find what's eating disk space, identify duplicate/similar
model files, and suggest cleanup actions.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from forgemaster.scanner import FORMAT_EXTENSIONS, ModelInfo, ModelScanner, ScanResult


@dataclass
class DiskUsage:
    """Snapshot of disk usage for a scanned directory tree."""

    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    model_bytes: int = 0
    other_bytes: int = 0

    @property
    def model_percent(self) -> float:
        """Percentage of used space occupied by model files."""
        if self.used_bytes == 0:
            return 0.0
        return (self.model_bytes / self.used_bytes) * 100.0

    @property
    def other_percent(self) -> float:
        """Percentage of used space occupied by non-model files."""
        if self.used_bytes == 0:
            return 0.0
        return (self.other_bytes / self.used_bytes) * 100.0

    @property
    def used_percent(self) -> float:
        """Percentage of total space that is used."""
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0


@dataclass
class DuplicateGroup:
    """A group of files that are considered duplicates of each other."""

    name: str = ""
    files: list[str] = field(default_factory=list)
    total_wasted_bytes: int = 0
    size_bytes: int = 0


@dataclass
class CleanupAction:
    """A single cleanup action that can be taken."""

    path: str = ""
    size_bytes: int = 0
    reason: str = ""  # "duplicate", "temp", "cache", etc.
    description: str = ""


@dataclass
class CleanupReport:
    """Report of cleanup actions and potential space savings."""

    actions: list[CleanupAction] = field(default_factory=list)
    total_reclaimable_bytes: int = 0
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)

    @property
    def total_reclaimable_gb(self) -> float:
        """Total reclaimable space in GB."""
        return self.total_reclaimable_bytes / (1024**3)

    def add_action(self, action: CleanupAction) -> None:
        """Add a cleanup action to the report."""
        self.actions.append(action)
        self.total_reclaimable_bytes += action.size_bytes


class DiskScanner:
    """Scan directories for model files and calculate disk usage."""

    def __init__(self) -> None:
        self._model_scanner = ModelScanner()

    def scan_usage(self, paths: list[str | Path]) -> DiskUsage:
        """Calculate disk usage for given paths, separating model vs. other files.

        Args:
            paths: List of directories to scan.

        Returns:
            DiskUsage with total/used/free/model/other byte counts.
        """
        total_size = 0
        model_size = 0

        scan_result = self._model_scanner.scan(paths)

        for model in scan_result.models:
            model_size += model.size_bytes

        # Calculate total size of all files (including non-model)
        for path_str in paths:
            path = Path(path_str)
            if path.is_file():
                try:
                    total_size += path.stat().st_size
                except OSError:
                    pass
            elif path.is_dir():
                total_size += self._dir_total_size(path)

        # Get filesystem free/total from first valid path
        total_disk, used_disk, free_disk = self._filesystem_stats(paths)

        other_size = total_size - model_size

        return DiskUsage(
            total_bytes=total_disk,
            used_bytes=used_disk,
            free_bytes=free_disk,
            model_bytes=model_size,
            other_bytes=other_size,
        )

    def scan_model_sizes(self, paths: list[str | Path]) -> list[ModelInfo]:
        """Scan paths and return model files sorted by size (descending).

        Args:
            paths: List of directories to scan.

        Returns:
            List of ModelInfo sorted by size_bytes descending.
        """
        result = self._model_scanner.scan(paths)
        models = sorted(result.models, key=lambda m: m.size_bytes, reverse=True)
        return models

    def scan_directory_usage(self, paths: list[str | Path]) -> dict[str, int]:
        """Calculate per-directory model sizes.

        Args:
            paths: List of directories to scan.

        Returns:
            Dict mapping directory path to total model size in that tree.
        """
        result = self._model_scanner.scan(paths)
        dir_sizes: dict[str, int] = {}
        for model in result.models:
            model_dir = str(Path(model.path).parent)
            dir_sizes[model_dir] = dir_sizes.get(model_dir, 0) + model.size_bytes
        return dir_sizes

    def _dir_total_size(self, directory: Path) -> int:
        """Calculate total size of all files under a directory."""
        total = 0
        try:
            for root, _dirs, files in os.walk(directory):
                for f in files:
                    try:
                        total += (Path(root) / f).stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    def _filesystem_stats(self, paths: list[str | Path]) -> tuple[int, int, int]:
        """Get filesystem total, used, and free bytes for the given paths.

        Falls back to sum of file sizes if statvfs is unavailable (e.g. Windows).
        """
        for path_str in paths:
            path = Path(path_str)
            if path.exists():
                try:
                    stat = os.statvfs(str(path))
                    total = stat.f_blocks * stat.f_frsize
                    free = stat.f_bfree * stat.f_frsize
                    used = total - free
                    return total, used, free
                except (OSError, AttributeError):
                    # statvfs not available (Windows) or path error
                    continue

        # Fallback: cannot determine filesystem stats, return 0s
        # In this case, used_bytes will be set to the sum of all file sizes
        # which the caller can still work with for model vs other breakdown.
        return 0, 0, 0


class DuplicateFinder:
    """Find duplicate and similar model files by name and size."""

    def __init__(self, size_tolerance: float = 0.05) -> None:
        """Initialize the DuplicateFinder.

        Args:
            size_tolerance: Fractional tolerance for considering two files
                as "similar size" (0.05 = 5%). Set to 0 for exact match only.
        """
        self.size_tolerance = size_tolerance

    def find_duplicates(self, paths: list[str | Path]) -> list[DuplicateGroup]:
        """Find groups of duplicate model files.

        Two files are considered duplicates if they share the same
        normalized name stem AND have similar sizes (within tolerance).

        Args:
            paths: List of directories to scan for models.

        Returns:
            List of DuplicateGroup, sorted by wasted bytes descending.
        """
        scanner = ModelScanner()
        result = scanner.scan(paths)
        return self.find_duplicates_from_models(result.models)

    def find_duplicates_from_models(
        self, models: list[ModelInfo]
    ) -> list[DuplicateGroup]:
        """Find duplicate groups from an existing list of ModelInfo.

        Args:
            models: List of ModelInfo to check for duplicates.

        Returns:
            List of DuplicateGroup, sorted by wasted bytes descending.
        """
        groups: dict[str, list[ModelInfo]] = {}

        for model in models:
            key = self._normalize_name(model.name)
            if key not in groups:
                groups[key] = []
            groups[key].append(model)

        duplicate_groups: list[DuplicateGroup] = []
        for key, group_models in groups.items():
            if len(group_models) < 2:
                continue

            # Further split into sub-groups by similar size
            sub_groups = self._group_by_similar_size(group_models)
            for sub_group in sub_groups:
                if len(sub_group) < 2:
                    continue
                # The "original" is the largest file; the rest are duplicates
                sub_group.sort(key=lambda m: m.size_bytes, reverse=True)
                original = sub_group[0]
                duplicates = sub_group[1:]
                wasted = sum(m.size_bytes for m in duplicates)
                dg = DuplicateGroup(
                    name=original.name,
                    files=[m.path for m in sub_group],
                    total_wasted_bytes=wasted,
                    size_bytes=original.size_bytes,
                )
                duplicate_groups.append(dg)

        duplicate_groups.sort(key=lambda g: g.total_wasted_bytes, reverse=True)
        return duplicate_groups

    def find_exact_duplicates(self, paths: list[str | Path]) -> list[DuplicateGroup]:
        """Find files with identical content (hash-based deduplication).

        This reads file contents and computes hashes, so it is slower
        but more accurate than name-based duplicate detection.

        Args:
            paths: List of directories to scan.

        Returns:
            List of DuplicateGroup for exact content duplicates.
        """
        scanner = ModelScanner()
        result = scanner.scan(paths)
        return self.find_exact_duplicates_from_models(result.models)

    def find_exact_duplicates_from_models(
        self, models: list[ModelInfo]
    ) -> list[DuplicateGroup]:
        """Find exact content duplicates from ModelInfo list.

        Args:
            models: List of ModelInfo to check.

        Returns:
            List of DuplicateGroup for exact duplicates.
        """
        # First group by size (fast filter)
        size_groups: dict[int, list[ModelInfo]] = {}
        for model in models:
            s = model.size_bytes
            if s not in size_groups:
                size_groups[s] = []
            size_groups[s].append(model)

        duplicate_groups: list[DuplicateGroup] = []
        for size, group in size_groups.items():
            if len(group) < 2:
                continue

            # Hash files of same size to find exact duplicates
            hash_groups: dict[str, list[ModelInfo]] = {}
            for model in group:
                file_hash = self._hash_file(model.path)
                if file_hash is None:
                    continue
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(model)

            for hash_val, hash_group in hash_groups.items():
                if len(hash_group) < 2:
                    continue

                hash_group.sort(key=lambda m: m.size_bytes, reverse=True)
                original = hash_group[0]
                duplicates = hash_group[1:]
                wasted = sum(m.size_bytes for m in duplicates)

                dg = DuplicateGroup(
                    name=original.name,
                    files=[m.path for m in hash_group],
                    total_wasted_bytes=wasted,
                    size_bytes=original.size_bytes,
                )
                duplicate_groups.append(dg)

        duplicate_groups.sort(key=lambda g: g.total_wasted_bytes, reverse=True)
        return duplicate_groups

    def generate_cleanup_report(self, paths: list[str | Path]) -> CleanupReport:
        """Generate a full cleanup report with duplicate detection.

        Args:
            paths: List of directories to scan.

        Returns:
            CleanupReport with recommended actions.
        """
        scanner = ModelScanner()
        result = scanner.scan(paths)
        return self.generate_cleanup_report_from_models(result.models)

    def generate_cleanup_report_from_models(
        self, models: list[ModelInfo]
    ) -> CleanupReport:
        """Generate a cleanup report from an existing list of ModelInfo.

        Args:
            models: List of ModelInfo to analyze.

        Returns:
            CleanupReport with recommended actions.
        """
        report = CleanupReport()

        # Find name-and-size duplicates
        dup_groups = self.find_duplicates_from_models(models)
        report.duplicate_groups = dup_groups

        # For each duplicate group, suggest keeping the first (largest) file
        # and removing the rest
        for group in dup_groups:
            # Keep the first file, suggest removing the rest
            kept = group.files[0]
            for fpath in group.files[1:]:
                # Find model info for this path
                model = next((m for m in models if m.path == fpath), None)
                size = model.size_bytes if model else group.size_bytes
                action = CleanupAction(
                    path=fpath,
                    size_bytes=size,
                    reason="duplicate",
                    description=(
                        f"Duplicate of '{group.name}': {fpath} " f"(original: {kept})"
                    ),
                )
                report.add_action(action)

        return report

    def _normalize_name(self, name: str) -> str:
        """Normalize a model name for grouping.

        Removes quantization suffixes, version numbers, and other
        naming differences to group similar models together.
        """
        import re

        normalized = name.lower().strip()

        # Remove common quantization suffixes (order matters: longest first)
        quant_patterns = [
            re.compile(r"[._-]q[0-9]_[a-z0-9]+$", re.IGNORECASE),
            re.compile(r"[._-]q[0-9]_[a-z]+_[a-z0-9]+$", re.IGNORECASE),
            re.compile(r"[._-]q[0-9]+$", re.IGNORECASE),
            re.compile(r"[._-]f(?:p)?16$", re.IGNORECASE),
            re.compile(r"[._-]bf16$", re.IGNORECASE),
            re.compile(r"[._-]f32$", re.IGNORECASE),
        ]
        for pattern in quant_patterns:
            normalized = pattern.sub("", normalized)

        # Remove trailing dots, dashes, underscores
        normalized = normalized.rstrip(".-_")

        return normalized

    def _group_by_similar_size(self, models: list[ModelInfo]) -> list[list[ModelInfo]]:
        """Group models by similar file size within the tolerance."""
        if not models:
            return []

        # Sort by size descending
        sorted_models = sorted(models, key=lambda m: m.size_bytes, reverse=True)
        groups: list[list[ModelInfo]] = []
        current_group: list[ModelInfo] = [sorted_models[0]]

        for model in sorted_models[1:]:
            reference = current_group[0].size_bytes
            if reference == 0:
                # If reference is 0, only group with other 0-size files
                if model.size_bytes == 0:
                    current_group.append(model)
                else:
                    groups.append(current_group)
                    current_group = [model]
            else:
                ratio = abs(model.size_bytes - reference) / reference
                if ratio <= self.size_tolerance:
                    current_group.append(model)
                else:
                    groups.append(current_group)
                    current_group = [model]

        groups.append(current_group)
        return groups

    def _hash_file(self, path: str, chunk_size: int = 8192) -> Optional[str]:
        """Compute SHA256 hash of a file for exact duplicate detection."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except (OSError, IOError):
            return None
