import pytest
from lilith_core.config import Config


def test_config_defaults(tmp_path):
    c = Config(root_path=tmp_path)
    assert c.get("model") == "auto"
    assert c.get("nonexistent", "fallback") == "fallback"


def test_config_persistence(tmp_path):
    c1 = Config(root_path=tmp_path)
    c1.set("test_key", "test_value")

    c2 = Config(root_path=tmp_path)
    assert c2.get("test_key") == "test_value"
