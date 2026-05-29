"""Tests for autosub.cli module."""

from typer.testing import CliRunner

from autosub.cli import app


runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help and info commands."""

    def test_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AutoSub" in result.output

    def test_transcribe_help(self):
        result = runner.invoke(app, ["transcribe", "--help"])
        assert result.exit_code == 0
        assert "model" in result.output.lower()

    def test_translate_help(self):
        result = runner.invoke(app, ["translate", "--help"])
        assert result.exit_code == 0
        assert "target" in result.output.lower() or "lang" in result.output.lower()

    def test_info_command(self):
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "AutoSub" in result.output

    def test_transcribe_missing_file(self):
        result = runner.invoke(app, ["transcribe", "/nonexistent/file.wav"])
        assert result.exit_code == 1

    def test_translate_missing_file(self):
        result = runner.invoke(app, ["translate", "/nonexistent/file.srt"])
        assert result.exit_code == 1
