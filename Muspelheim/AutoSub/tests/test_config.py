"""Tests for autosub.config module."""

import pytest
from autosub.config import AutoSubConfig


class TestAutoSubConfigDefaults:
    """Tests for default configuration."""

    def test_defaults(self):
        config = AutoSubConfig()
        assert config.model_size == "base"
        assert config.device == "auto"
        assert config.compute_type == "int8"
        assert config.default_language is None
        assert config.default_format == "srt"
        assert config.batch_recursive is False

    def test_custom_init(self):
        config = AutoSubConfig(
            model_size="large-v3",
            device="cuda",
            default_language="en",
        )
        assert config.model_size == "large-v3"
        assert config.device == "cuda"
        assert config.default_language == "en"


class TestAutoSubConfigFromToml:
    """Tests for loading config from TOML files."""

    def test_load_from_toml(self, tmp_path):
        config_path = tmp_path / "autosub.toml"
        config_path.write_text(
            '[autosub]\nmodel_size = "large-v3"\ndevice = "cuda"\ndefault_language = "en"\n'
        )
        config = AutoSubConfig.from_toml(config_path)
        assert config.model_size == "large-v3"
        assert config.device == "cuda"
        assert config.default_language == "en"

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            AutoSubConfig.from_toml("/nonexistent/autosub.toml")

    def test_load_partial_config(self, tmp_path):
        config_path = tmp_path / "autosub.toml"
        config_path.write_text('[autosub]\nmodel_size = "tiny"\n')
        config = AutoSubConfig.from_toml(config_path)
        assert config.model_size == "tiny"
        assert config.device == "auto"  # default

    def test_load_empty_config(self, tmp_path):
        config_path = tmp_path / "autosub.toml"
        config_path.write_text("")
        config = AutoSubConfig.from_toml(config_path)
        assert config.model_size == "base"  # all defaults


class TestAutoSubConfigFind:
    """Tests for config file discovery."""

    def test_find_config_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        # Change to a temp dir with no config
        monkeypatch.chdir(tmp_path)
        config = AutoSubConfig.find_config()
        assert config.model_size == "base"


class TestAutoSubConfigTomlDict:
    """Tests for TOML serialization."""

    def test_to_toml_dict(self):
        config = AutoSubConfig(model_size="tiny")
        d = config.to_toml_dict()
        assert "autosub" in d
        assert d["autosub"]["model_size"] == "tiny"
