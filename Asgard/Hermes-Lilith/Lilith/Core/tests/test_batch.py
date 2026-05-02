#!/usr/bin/env python3
"""Tests for Lilith Batch Mode."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.batch import run_batch


class TestBatchRun:
    """Test run_batch function directly."""

    def test_batch_no_provider(self):
        """Returns 2 when no LLM provider available."""
        with patch("Lilith.batch.get_provider") as mock_gp:
            mock_gp.side_effect = ConnectionError("No provider")
            exit_code = run_batch("test prompt")
            assert exit_code == 2

    def test_batch_no_provider_json(self, capsys):
        """Returns 2 and JSON error when no provider + --json."""
        with patch("Lilith.batch.get_provider") as mock_gp:
            mock_gp.side_effect = ConnectionError("No provider")
            exit_code = run_batch("test", json_output=True)
            assert exit_code == 2
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["status"] == "no_provider"

    def test_batch_success(self, capsys):
        """Returns 0 and prints response on success."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Hello from Lilith"
        mock_orch.session_id = "test-session"

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Say hello")
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Hello from Lilith" in captured.out

    def test_batch_success_json(self, capsys):
        """Returns 0 and structured JSON on success."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Test response"
        mock_orch.session_id = "batch-001"

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test", json_output=True)
            assert exit_code == 0
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["status"] == "ok"
            assert result["response"] == "Test response"
            assert "kimi" in result["model"]

    def test_batch_model_override(self):
        """Model override is applied to provider."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Response"

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            run_batch("Test", model="custom-model")
            assert mock_provider.model == "custom-model"

    def test_batch_no_tools_flag(self):
        """_force_no_tools is set when no_tools=True."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Response"

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            run_batch("Test", no_tools=True)
            assert mock_orch._force_no_tools is True

    def test_batch_system_prompt(self):
        """Custom system prompt is set on orchestrator messages."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Response"
        mock_orch.messages = []

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            run_batch("Test", system_prompt="You are a poet")
            assert mock_orch.messages[0]["role"] == "system"
            assert mock_orch.messages[0]["content"] == "You are a poet"

    def test_batch_session_id(self):
        """Session ID is passed to orchestrator."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.return_value = "Response"

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            run_batch("Test", session_id="my-session")
            assert mock_orch.session_id == "my-session"

    def test_batch_stream_mode(self, capsys):
        """Stream mode collects tokens and prints them."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat_stream.return_value = iter(["Hello", " ", "World"])

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test", stream=True)
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Hello World" in captured.out

    def test_batch_stream_json(self, capsys):
        """Stream + JSON outputs full response as JSON."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat_stream.return_value = iter(["Hello", " World"])

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test", stream=True, json_output=True)
            assert exit_code == 0
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["response"] == "Hello World"
            assert result["status"] == "ok"

    def test_batch_chat_error(self, capsys):
        """Returns 1 on chat error."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.side_effect = Exception("LLM exploded")

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test")
            assert exit_code == 1

    def test_batch_chat_error_json(self, capsys):
        """Returns 1 and JSON error on chat error."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat.side_effect = Exception("LLM exploded")

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test", json_output=True)
            assert exit_code == 1
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["status"] == "error"

    def test_batch_stream_error(self, capsys):
        """Returns 1 on stream error."""
        mock_provider = MagicMock()
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-for-coding"

        mock_orch = MagicMock()
        mock_orch.chat_stream.side_effect = Exception("Stream broke")

        with patch("Lilith.batch.get_provider", return_value=mock_provider), \
             patch("Lilith.batch.LilithOrchestrator", return_value=mock_orch):
            exit_code = run_batch("Test", stream=True)
            assert exit_code == 1


class TestBatchCLI:
    """Test batch CLI argument parsing via main()."""

    def test_main_batch_flag(self):
        """main() with --batch calls run_batch and exits."""
        with patch("Lilith.batch.run_batch", return_value=0) as mock_rb, \
             patch("sys.argv", ["lilith", "--batch", "Hello"]), \
             patch("Lilith.main.llm_provider"), \
             patch("Lilith.main.orch"), \
             patch("Lilith.main.Lilith_tools"):
            from Lilith.main import main
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
            mock_rb.assert_called_once()

    def test_main_batch_json(self):
        """main() with --batch --batch-json passes json_output=True."""
        with patch("Lilith.batch.run_batch", return_value=0) as mock_rb, \
             patch("sys.argv", ["lilith", "--batch", "Hi", "--batch-json"]), \
             patch("Lilith.main.llm_provider"), \
             patch("Lilith.main.orch"), \
             patch("Lilith.main.Lilith_tools"):
            from Lilith.main import main
            try:
                main()
            except SystemExit:
                pass
            call_kwargs = mock_rb.call_args[1]
            assert call_kwargs["json_output"] is True

    def test_main_batch_no_tools(self):
        """main() with --batch --batch-no-tools passes no_tools=True."""
        with patch("Lilith.batch.run_batch", return_value=0) as mock_rb, \
             patch("sys.argv", ["lilith", "--batch", "Hi", "--batch-no-tools"]), \
             patch("Lilith.main.llm_provider"), \
             patch("Lilith.main.orch"), \
             patch("Lilith.main.Lilith_tools"):
            from Lilith.main import main
            try:
                main()
            except SystemExit:
                pass
            call_kwargs = mock_rb.call_args[1]
            assert call_kwargs["no_tools"] is True


class TestForceNoTools:
    """Test _force_no_tools integration with orchestrator."""

    def test_force_no_tools_returns_empty(self):
        """_force_no_tools=True makes _get_tools_for_llm return empty list."""
        from Lilith.Core.orchestrator import LilithOrchestrator
        orch = LilithOrchestrator()
        orch._force_no_tools = True
        tools = orch._get_tools_for_llm()
        assert tools == []

    def test_force_no_tools_default_false(self):
        """Default _force_no_tools is not set (getattr returns False)."""
        from Lilith.Core.orchestrator import LilithOrchestrator
        orch = LilithOrchestrator()
        assert getattr(orch, "_force_no_tools", False) is False