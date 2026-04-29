import pytest
from lilith_core.config import Config
from lilith_memory.store import MemoryStore
from lilith_orchestrator.engine import LilithEngine


def test_engine_process(tmp_path):
    config = Config(root_path=tmp_path)
    memory = MemoryStore(tmp_path / "mem.db")
    engine = LilithEngine(config, memory)
    result = engine.process("Hola")
    assert "prompt" in result
    assert "context" in result


def test_engine_detects_tool(tmp_path):
    config = Config(root_path=tmp_path)
    memory = MemoryStore(tmp_path / "mem.db")
    engine = LilithEngine(config, memory)
    result = engine.process("dame system info")
    assert result["tool_call"] != {}
    assert result["tool_call"]["tool"] == "system_info"
