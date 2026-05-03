"""Tests for the Typer CLI module (tui/cli.py)."""

from __future__ import annotations

from tui import __version__
from tui.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestCLIVersion:
    """Test the --version flag."""

    def test_version_flag_prints_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_flag_short(self) -> None:
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestCLIHelp:
    """Test the --help flag."""

    def test_help_shows_description(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Yggdrasil" in result.output

    def test_help_shows_install_completion_option(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "install-completion" in result.output

    def test_help_shows_show_completion_option(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "show-completion" in result.output


class TestCLIVersionValue:
    """Test that __version__ is correct."""

    def test_version_is_1_0_0(self) -> None:
        assert __version__ == "1.0.0"
