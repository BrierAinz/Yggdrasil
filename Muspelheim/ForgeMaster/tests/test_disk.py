"""Tests for the disk usage and cleanup module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forgemaster.disk import (
    CleanupAction,
    CleanupReport,
    DiskScanner,
    DiskUsage,
    DuplicateFinder,
    DuplicateGroup,
)
from forgemaster.scanner import ModelInfo


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def disk_scanner():
    return DiskScanner()


@pytest.fixture
def duplicate_finder():
    return DuplicateFinder(size_tolerance=0.05)


@pytest.fixture
def exact_finder():
    return DuplicateFinder(size_tolerance=0.0)


@pytest.fixture
def tmp_model_dir():
    """Create a temporary directory with sample model files of known sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # GGUF model — 10 KB
        gguf_file = tmpdir_path / "llama-7b-Q4_0.gguf"
        gguf_file.write_bytes(b"\x00" * 10240)

        # Safetensors model — 20 KB
        safetensor_file = tmpdir_path / "mistral-7b-fp16.safetensors"
        safetensor_file.write_bytes(b"\x00" * 20480)

        # PT model — 5 KB
        pt_file = tmpdir_path / "whisper-small.pt"
        pt_file.write_bytes(b"\x00" * 5120)

        # Non-model file — should not count toward model_bytes
        txt_file = tmpdir_path / "readme.txt"
        txt_file.write_text("not a model")

        # Duplicate: same model name, same size (simulating a copy)
        dup_dir = tmpdir_path / "copies"
        dup_dir.mkdir()
        dup_file = dup_dir / "llama-7b-Q4_0.gguf"
        dup_file.write_bytes(b"\x00" * 10240)

        # A second duplicate with a slightly different quant suffix
        alt_file = tmpdir_path / "llama-7b-Q8_0.gguf"
        alt_file.write_bytes(b"\x00" * 10240)

        yield tmpdir_path


@pytest.fixture
def sample_models():
    """A list of ModelInfo objects for unit-testing without the filesystem."""
    return [
        ModelInfo(
            name="llama-7b-Q4_0",
            path="/models/llama-7b-Q4_0.gguf",
            size_bytes=4_000_000_000,
            format="gguf",
            architecture="llama",
            parameters=7_000_000_000,
            quantization="Q4_0",
        ),
        ModelInfo(
            name="llama-7b-Q8_0",
            path="/models/llama-7b-Q8_0.gguf",
            size_bytes=4_100_000_000,
            format="gguf",
            architecture="llama",
            parameters=7_000_000_000,
            quantization="Q8_0",
        ),
        ModelInfo(
            name="mistral-7b-fp16",
            path="/models/mistral-7b-fp16.safetensors",
            size_bytes=14_000_000_000,
            format="safetensors",
            architecture="mistral",
            parameters=7_000_000_000,
            quantization="FP16",
        ),
        ModelInfo(
            name="whisper-small",
            path="/models/whisper-small.pt",
            size_bytes=500_000_000,
            format="pt",
            architecture="whisper",
        ),
    ]


# ── DiskUsage dataclass ─────────────────────────────────────────────────


class TestDiskUsage:
    def test_defaults(self):
        du = DiskUsage()
        assert du.total_bytes == 0
        assert du.used_bytes == 0
        assert du.free_bytes == 0
        assert du.model_bytes == 0
        assert du.other_bytes == 0

    def test_model_percent(self):
        du = DiskUsage(
            total_bytes=100,
            used_bytes=80,
            free_bytes=20,
            model_bytes=60,
            other_bytes=20,
        )
        assert du.model_percent == pytest.approx(75.0)
        assert du.other_percent == pytest.approx(25.0)
        assert du.used_percent == pytest.approx(80.0)

    def test_model_percent_zero_used(self):
        du = DiskUsage()
        assert du.model_percent == 0.0
        assert du.other_percent == 0.0
        assert du.used_percent == 0.0

    def test_model_percent_zero_total(self):
        du = DiskUsage(total_bytes=0, used_bytes=10)
        assert du.used_percent == 0.0


# ── DuplicateGroup dataclass ────────────────────────────────────────────


class TestDuplicateGroup:
    def test_defaults(self):
        dg = DuplicateGroup()
        assert dg.name == ""
        assert dg.files == []
        assert dg.total_wasted_bytes == 0
        assert dg.size_bytes == 0

    def test_fields(self):
        dg = DuplicateGroup(
            name="llama-7b",
            files=["/a/llama-7b.gguf", "/b/llama-7b.gguf"],
            total_wasted_bytes=4_000_000_000,
            size_bytes=4_000_000_000,
        )
        assert dg.name == "llama-7b"
        assert len(dg.files) == 2
        assert dg.total_wasted_bytes == 4_000_000_000


# ── CleanupAction dataclass ─────────────────────────────────────────────


class TestCleanupAction:
    def test_defaults(self):
        action = CleanupAction()
        assert action.path == ""
        assert action.size_bytes == 0
        assert action.reason == ""
        assert action.description == ""

    def test_fields(self):
        action = CleanupAction(
            path="/models/llama-7b-Q4_0.gguf",
            size_bytes=4_000_000_000,
            reason="duplicate",
            description="Duplicate of llama-7b",
        )
        assert action.reason == "duplicate"
        assert action.size_bytes == 4_000_000_000


# ── CleanupReport dataclass ─────────────────────────────────────────────


class TestCleanupReport:
    def test_defaults(self):
        report = CleanupReport()
        assert report.actions == []
        assert report.total_reclaimable_bytes == 0
        assert report.duplicate_groups == []

    def test_total_reclaimable_gb(self):
        report = CleanupReport(total_reclaimable_bytes=2 * 1024**3)
        assert report.total_reclaimable_gb == pytest.approx(2.0)

    def test_add_action(self):
        report = CleanupReport()
        a1 = CleanupAction(path="/a", size_bytes=1000, reason="duplicate")
        a2 = CleanupAction(path="/b", size_bytes=2000, reason="duplicate")
        report.add_action(a1)
        report.add_action(a2)
        assert len(report.actions) == 2
        assert report.total_reclaimable_bytes == 3000
        assert report.total_reclaimable_gb == pytest.approx(3000 / (1024**3))


# ── DiskScanner ─────────────────────────────────────────────────────────


class TestDiskScanner:
    def test_scan_usage_finds_models(self, disk_scanner, tmp_model_dir):
        usage = disk_scanner.scan_usage([str(tmp_model_dir)])
        assert isinstance(usage, DiskUsage)
        # Model bytes should be > 0 (we created model files)
        assert usage.model_bytes > 0

    def test_scan_usage_other_bytes(self, disk_scanner, tmp_model_dir):
        usage = disk_scanner.scan_usage([str(tmp_model_dir)])
        assert usage.other_bytes >= 0
        # The .txt file is non-model, so other_bytes > 0
        assert usage.other_bytes > 0

    def test_scan_model_sizes_sorted(self, disk_scanner, tmp_model_dir):
        models = disk_scanner.scan_model_sizes([str(tmp_model_dir)])
        assert len(models) >= 3
        # Should be sorted descending by size
        for i in range(len(models) - 1):
            assert models[i].size_bytes >= models[i + 1].size_bytes

    def test_scan_directory_usage(self, disk_scanner, tmp_model_dir):
        dir_sizes = disk_scanner.scan_directory_usage([str(tmp_model_dir)])
        assert isinstance(dir_sizes, dict)
        # At least one directory should have model files
        total = sum(dir_sizes.values())
        assert total > 0

    def test_scan_usage_empty_dir(self, disk_scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            usage = disk_scanner.scan_usage([tmpdir])
            assert usage.model_bytes == 0
            assert usage.other_bytes == 0

    def test_scan_usage_nonexistent_path(self, disk_scanner):
        usage = disk_scanner.scan_usage(["/nonexistent/path/12345"])
        # Should not crash; may return 0s for filesystem stats
        assert isinstance(usage, DiskUsage)

    def test_scan_model_sizes_nonexistent(self, disk_scanner):
        models = disk_scanner.scan_model_sizes(["/nonexistent/path/12345"])
        assert models == []


# ── DuplicateFinder ─────────────────────────────────────────────────────


class TestDuplicateFinder:
    def test_find_duplicates_basic(self, duplicate_finder, tmp_model_dir):
        groups = duplicate_finder.find_duplicates([str(tmp_model_dir)])
        assert isinstance(groups, list)
        # We created llama-7b-Q4_0.gguf in two locations + llama-7b-Q8_0.gguf
        # These should group together as "llama-7b" with similar size
        assert len(groups) >= 1
        # Each group should have >= 2 files
        for group in groups:
            assert len(group.files) >= 2
            assert group.total_wasted_bytes > 0

    def test_find_duplicates_no_duplicates(self, duplicate_finder):
        """If every model is unique, no duplicate groups returned."""
        models = [
            ModelInfo(name="unique-A", path="/a/a.gguf", size_bytes=1000),
            ModelInfo(name="unique-B", path="/b/b.safetensors", size_bytes=2000),
        ]
        groups = duplicate_finder.find_duplicates_from_models(models)
        assert groups == []

    def test_find_duplicates_from_models(self, duplicate_finder):
        models = [
            ModelInfo(
                name="llama-7b-Q4_0",
                path="/m1/llama-7b-Q4_0.gguf",
                size_bytes=4_000_000_000,
            ),
            ModelInfo(
                name="llama-7b-Q8_0",
                path="/m2/llama-7b-Q8_0.gguf",
                size_bytes=4_100_000_000,
            ),
            ModelInfo(
                name="mistral-7b-fp16",
                path="/m3/mistral-7b-fp16.safetensors",
                size_bytes=14_000_000_000,
            ),
        ]
        groups = duplicate_finder.find_duplicates_from_models(models)
        # llama-7b variants should group (names normalize to same key,
        # sizes are within 5%)
        assert len(groups) >= 1
        llama_group = next((g for g in groups if "llama" in g.name.lower()), None)
        assert llama_group is not None

    def test_find_duplicates_size_tolerance_strict(self, exact_finder):
        """With tolerance 0, only exact same-size files are duplicates."""
        models = [
            ModelInfo(
                name="llama-7b-Q4_0",
                path="/a/llama-7b-Q4_0.gguf",
                size_bytes=4_000_000_000,
            ),
            ModelInfo(
                name="llama-7b-Q8_0",
                path="/b/llama-7b-Q8_0.gguf",
                size_bytes=4_100_000_000,
            ),
        ]
        groups = exact_finder.find_duplicates_from_models(models)
        # Sizes differ by 2.5%, so with 0 tolerance they should NOT group
        assert len(groups) == 0

    def test_find_duplicates_exact_size_match(self, exact_finder):
        models = [
            ModelInfo(
                name="llama-7b-Q4_0",
                path="/a/llama-7b-Q4_0.gguf",
                size_bytes=4_000_000_000,
            ),
            ModelInfo(
                name="llama-7b-Q8_0",
                path="/b/llama-7b-Q8_0.gguf",
                size_bytes=4_000_000_000,
            ),
        ]
        groups = exact_finder.find_duplicates_from_models(models)
        assert len(groups) == 1
        assert groups[0].total_wasted_bytes == 4_000_000_000

    def test_find_exact_duplicates_content_match(self):
        """Test hash-based exact duplicate detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two identical files
            content = b"\x42" * 2048
            f1 = Path(tmpdir) / "model-a.gguf"
            f2 = Path(tmpdir) / "model-b.gguf"
            f1.write_bytes(content)
            f2.write_bytes(content)

            # Create a different file (same name stem, different content)
            f3 = Path(tmpdir) / "model-c.gguf"
            f3.write_bytes(b"\x43" * 2048)

            finder = DuplicateFinder()
            groups = finder.find_exact_duplicates([str(tmpdir)])
            # Should find at least one exact duplicate group
            assert len(groups) >= 1
            # The exact duplicate group should have 2 files
            exact_group = None
            for g in groups:
                if len(g.files) == 2:
                    exact_group = g
                    break
            assert exact_group is not None
            assert exact_group.total_wasted_bytes == 2048

    def test_find_exact_duplicates_no_match(self):
        """Different content should not be considered exact duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "model-a.gguf"
            f2 = Path(tmpdir) / "model-b.gguf"
            f1.write_bytes(b"\x01" * 1024)
            f2.write_bytes(b"\x02" * 1024)

            finder = DuplicateFinder()
            groups = finder.find_exact_duplicates([str(tmpdir)])
            # Same size, different content => no exact duplicates
            assert groups == []

    def test_generate_cleanup_report(self, duplicate_finder):
        models = [
            ModelInfo(
                name="llama-7b-Q4_0",
                path="/a/llama-7b-Q4_0.gguf",
                size_bytes=4_000_000_000,
            ),
            ModelInfo(
                name="llama-7b-Q8_0",
                path="/b/llama-7b-Q8_0.gguf",
                size_bytes=4_100_000_000,
            ),
            ModelInfo(
                name="unique-model",
                path="/c/unique.safetensors",
                size_bytes=7_000_000_000,
            ),
        ]
        report = duplicate_finder.generate_cleanup_report_from_models(models)
        assert isinstance(report, CleanupReport)
        assert len(report.duplicate_groups) >= 1
        assert report.total_reclaimable_bytes > 0
        assert len(report.actions) >= 1

    def test_generate_cleanup_report_no_duplicates(self, duplicate_finder):
        models = [
            ModelInfo(name="unique-A", path="/a/a.gguf", size_bytes=1000),
            ModelInfo(name="unique-B", path="/b/b.safetensors", size_bytes=2000),
        ]
        report = duplicate_finder.generate_cleanup_report_from_models(models)
        assert len(report.actions) == 0
        assert report.total_reclaimable_bytes == 0

    def test_normalize_name(self, duplicate_finder):
        # Quantization suffixes should be stripped
        assert duplicate_finder._normalize_name("llama-7b-Q4_0") == "llama-7b"
        assert duplicate_finder._normalize_name("llama-7b-Q8_0") == "llama-7b"
        assert duplicate_finder._normalize_name("mistral-7b-fp16") == "mistral-7b"
        assert duplicate_finder._normalize_name("model-bf16") == "model"
        assert duplicate_finder._normalize_name("model-f32") == "model"
        # Case should be lowered
        assert duplicate_finder._normalize_name("LLAMA-7B") == "llama-7b"

    def test_group_by_similar_size(self, duplicate_finder):
        models = [
            ModelInfo(name="model-Q4", path="/a/Q4.gguf", size_bytes=1000),
            ModelInfo(name="model-Q8", path="/b/Q8.gguf", size_bytes=1050),  # within 5%
            ModelInfo(name="model-FP16", path="/c/FP16.safetensors", size_bytes=2000),  # too far
        ]
        groups = duplicate_finder._group_by_similar_size(models)
        # Should get two groups: [2000] and [1050, 1000]
        # (sorted desc: 2000 starts group; 1050 is 47.5% from 2000 → new group;
        #  1000 is 4.76% from 1050 → same group)
        assert len(groups) == 2
        # One group has 2 models, the other has 1
        sizes = [[m.size_bytes for m in g] for g in groups]
        flat = sorted([s for grp in sizes for s in grp])
        assert flat == [1000, 1050, 2000]

    def test_wasted_bytes_calculation(self, duplicate_finder):
        """Three copies of the same model: 2x wasted."""
        models = [
            ModelInfo(name="llama-7b-Q4_0", path="/a/llama.gguf", size_bytes=4_000_000_000),
            ModelInfo(name="llama-7b-Q8_0", path="/b/llama.gguf", size_bytes=4_000_000_000),
            ModelInfo(name="llama-7b-Q5_K_M", path="/c/llama.gguf", size_bytes=4_000_000_000),
        ]
        groups = duplicate_finder.find_duplicates_from_models(models)
        assert len(groups) == 1
        # Wasted = (n - 1) * size  → 2 * 4B = 8B
        assert groups[0].total_wasted_bytes == 8_000_000_000
        assert len(groups[0].files) == 3

    def test_duplicate_report_action_descriptions(self, duplicate_finder):
        models = [
            ModelInfo(
                name="llama-7b-Q4_0",
                path="/a/llama-7b-Q4_0.gguf",
                size_bytes=4_000_000_000,
            ),
            ModelInfo(
                name="llama-7b-Q8_0",
                path="/b/llama-7b-Q8_0.gguf",
                size_bytes=4_100_000_000,
            ),
        ]
        report = duplicate_finder.generate_cleanup_report_from_models(models)
        assert len(report.actions) >= 1
        for action in report.actions:
            assert action.reason == "duplicate"
            assert action.size_bytes > 0
            assert action.description != ""

    def test_hash_file_nonexistent(self, duplicate_finder):
        result = duplicate_finder._hash_file("/nonexistent/file.gguf")
        assert result is None
