"""Tests for the ForgeMaster configuration module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from forgemaster.config import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_CONFIG_FILE,
    DEFAULT_GPU_PROFILE,
    DEFAULT_SCAN_DIRS,
    Config,
    load_config,
    save_config,
    set_config_value,
)


class TestConfigDefaults:
    def test_default_scan_dirs(self):
        cfg = Config()
        assert cfg.scan_dirs == DEFAULT_SCAN_DIRS

    def test_default_gpu_profile(self):
        cfg = Config()
        assert cfg.gpu_profile == DEFAULT_GPU_PROFILE

    def test_default_catalog_path(self):
        cfg = Config()
        assert cfg.catalog_path == str(DEFAULT_CATALOG_PATH)

    def test_default_yggdrasil_root(self):
        cfg = Config()
        assert cfg.yggdrasil_root is None


class TestConfigResolveScanDirs:
    def test_resolve_existing_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(scan_dirs=[tmp])
            resolved = cfg.resolve_scan_dirs()
            assert len(resolved) == 1
            assert str(resolved[0]) == tmp

    def test_resolve_nonexistent_dirs_filtered(self):
        cfg = Config(scan_dirs=["/nonexistent/path/12345"])
        resolved = cfg.resolve_scan_dirs()
        assert resolved == []

    def test_resolve_tilde_expansion(self):
        cfg = Config(scan_dirs=["~/nonexistent_test_path_xyz"])
        resolved = cfg.resolve_scan_dirs()
        # Path doesn't exist, so it's filtered out
        assert resolved == []


class TestConfigResolveCatalogPath:
    def test_resolve_catalog_path(self):
        cfg = Config(catalog_path="~/.forgemaster/catalog.db")
        resolved = cfg.resolve_catalog_path()
        assert str(resolved).startswith(str(Path.home()))

    def test_resolve_absolute_path(self):
        cfg = Config(catalog_path="/tmp/test.db")
        resolved = cfg.resolve_catalog_path()
        assert str(resolved) == "/tmp/test.db"


class TestLoadConfig:
    def test_load_config_no_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "nonexistent_config.yaml"
            cfg = load_config(cfg_path)
            assert cfg.scan_dirs == DEFAULT_SCAN_DIRS
            assert cfg.gpu_profile == DEFAULT_GPU_PROFILE
            assert cfg.catalog_path == str(DEFAULT_CATALOG_PATH)

    def test_load_config_from_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            data = {
                "scan_dirs": ["/custom/path1", "/custom/path2"],
                "gpu_profile": "RTX 4090",
                "catalog_path": str(Path(tmp) / "custom.db"),
            }
            cfg_path.write_text(yaml.dump(data))
            cfg = load_config(cfg_path)
            assert cfg.scan_dirs == ["/custom/path1", "/custom/path2"]
            assert cfg.gpu_profile == "RTX 4090"
            assert cfg.catalog_path == str(Path(tmp) / "custom.db")

    def test_load_config_partial_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            # Only gpu_profile specified - others should use defaults
            data = {"gpu_profile": "RTX 3090"}
            cfg_path.write_text(yaml.dump(data))
            cfg = load_config(cfg_path)
            assert cfg.gpu_profile == "RTX 3090"
            assert cfg.scan_dirs == DEFAULT_SCAN_DIRS  # default preserved

    def test_load_config_empty_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            cfg_path.write_text("")
            cfg = load_config(cfg_path)
            assert cfg.scan_dirs == DEFAULT_SCAN_DIRS

    def test_load_config_with_yggdrasil_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            # Set the env var
            old_env = os.environ.get("YGGDRASIL_ROOT")
            try:
                os.environ["YGGDRASIL_ROOT"] = tmp
                cfg = load_config(cfg_path)
                assert cfg.yggdrasil_root == tmp
                # Should prepend tmp/models to scan_dirs
                assert str(Path(tmp) / "models") in cfg.scan_dirs
                # catalog_path should be inside yggdrasil_root
                assert tmp in cfg.catalog_path
            finally:
                if old_env is not None:
                    os.environ["YGGDRASIL_ROOT"] = old_env
                else:
                    os.environ.pop("YGGDRASIL_ROOT", None)

    def test_load_config_yggdrasil_root_no_duplicate_scan_dirs(self):
        """If YGGDRASIL_ROOT/models is already in scan_dirs, don't add it twice."""
        with tempfile.TemporaryDirectory() as tmp:
            models_dir = str(Path(tmp) / "models")
            cfg_path = Path(tmp) / "config.yaml"
            data = {"scan_dirs": [models_dir]}
            cfg_path.write_text(yaml.dump(data))

            old_env = os.environ.get("YGGDRASIL_ROOT")
            try:
                os.environ["YGGDRASIL_ROOT"] = tmp
                cfg = load_config(cfg_path)
                # Should not duplicate the models dir
                assert cfg.scan_dirs.count(models_dir) == 1
            finally:
                if old_env is not None:
                    os.environ["YGGDRASIL_ROOT"] = old_env
                else:
                    os.environ.pop("YGGDRASIL_ROOT", None)


class TestSaveConfig:
    def test_save_config_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "subdir" / "config.yaml"
            cfg = Config(
                scan_dirs=["/a", "/b"],
                gpu_profile="RTX 4090",
                catalog_path="/tmp/test.db",
                yggdrasil_root=None,
            )
            result = save_config(cfg, cfg_path)
            assert result.exists()
            # Read it back
            with open(result) as f:
                loaded = yaml.safe_load(f)
            assert loaded["scan_dirs"] == ["/a", "/b"]
            assert loaded["gpu_profile"] == "RTX 4090"
            assert loaded["catalog_path"] == "/tmp/test.db"

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            original = Config(
                scan_dirs=["/path/one", "/path/two"],
                gpu_profile="RTX 3060",
                catalog_path=str(Path(tmp) / "catalog.db"),
            )
            save_config(original, cfg_path)
            loaded = load_config(cfg_path)
            assert loaded.scan_dirs == original.scan_dirs
            assert loaded.gpu_profile == original.gpu_profile
            assert loaded.catalog_path == original.catalog_path

    def test_save_config_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "deep" / "nested" / "config.yaml"
            cfg = Config()
            result = save_config(cfg, cfg_path)
            assert result.exists()


class TestSetConfigValue:
    def test_set_gpu_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            cfg = set_config_value("gpu_profile", "RTX 4090", config_path=cfg_path)
            assert cfg.gpu_profile == "RTX 4090"
            # Verify persisted
            loaded = load_config(cfg_path)
            assert loaded.gpu_profile == "RTX 4090"

    def test_set_scan_dirs_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            cfg = set_config_value("scan_dirs", "/a,/b,/c", config_path=cfg_path)
            assert cfg.scan_dirs == ["/a", "/b", "/c"]

    def test_set_scan_dirs_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            # First, save a config with known scan_dirs
            save_config(Config(scan_dirs=["/old/path"]), cfg_path)
            # Then set index 0
            cfg = set_config_value("scan_dirs.0", "/new/path", config_path=cfg_path)
            assert cfg.scan_dirs[0] == "/new/path"

    def test_set_unsupported_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            with pytest.raises(ValueError, match="Unsupported config key"):
                set_config_value("invalid.deep.key", "val", config_path=cfg_path)

    def test_set_catalog_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.yaml"
            cfg = set_config_value(
                "catalog_path", "/custom/catalog.db", config_path=cfg_path
            )
            assert cfg.catalog_path == "/custom/catalog.db"


class TestConfigIsolated:
    """Tests using isolated env for YGGDRASIL_ROOT configuration."""

    @pytest.fixture
    def isolated(self, tmp_path):
        """Provide an isolated config environment."""
        config_file = tmp_path / "config.yaml"
        catalog_dir = tmp_path / ".forgemaster"
        catalog_dir.mkdir(parents=True, exist_ok=True)

        old_ygg_root = os.environ.pop("YGGDRASIL_ROOT", None)
        os.environ["YGGDRASIL_ROOT"] = str(tmp_path)

        yield {
            "config_file": config_file,
            "catalog_dir": catalog_dir,
            "yggdrasil_root": str(tmp_path),
        }

        if old_ygg_root is not None:
            os.environ["YGGDRASIL_ROOT"] = old_ygg_root
        else:
            os.environ.pop("YGGDRASIL_ROOT", None)

    def test_yggdrasil_root_overrides_scan_dirs(self, isolated):
        cfg = load_config(isolated["config_file"])
        models_dir = str(Path(isolated["yggdrasil_root"]) / "models")
        assert models_dir in cfg.scan_dirs

    def test_yggdrasil_root_overrides_catalog_path(self, isolated):
        cfg = load_config(isolated["config_file"])
        assert isolated["yggdrasil_root"] in cfg.catalog_path
