"""Tests for forgemaster.logging — RichHandler integration and level mapping."""

import logging

from forgemaster.logging import configure_logging, get_logger


class TestConfigureLogging:
    """Test configure_logging() behaviour."""

    def setup_method(self):
        """Reset the global _CONFIGURED flag before each test."""
        import forgemaster.logging as mod

        mod._CONFIGURED = False
        # Also clear the forgemaster logger to avoid state leaks.
        logger = logging.getLogger("forgemaster")
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    def test_default_level_is_info(self):
        """Default (no verbose, no quiet) should set INFO level."""
        configure_logging(verbose=False, quiet=False)
        logger = logging.getLogger("forgemaster")
        assert logger.level == logging.INFO

    def test_verbose_sets_debug(self):
        """--verbose should set DEBUG level."""
        configure_logging(verbose=True, quiet=False)
        logger = logging.getLogger("forgemaster")
        assert logger.level == logging.DEBUG

    def test_quiet_sets_warning(self):
        """--quiet should set WARNING level."""
        configure_logging(verbose=False, quiet=True)
        logger = logging.getLogger("forgemaster")
        assert logger.level == logging.WARNING

    def test_verbose_wins_over_quiet(self):
        """When both flags are set, verbose takes priority (DEBUG)."""
        configure_logging(verbose=True, quiet=True)
        logger = logging.getLogger("forgemaster")
        assert logger.level == logging.DEBUG

    def test_explicit_level_overrides_flags(self):
        """An explicit level parameter overrides verbose/quiet flags."""
        configure_logging(verbose=True, quiet=False, level=logging.ERROR)
        logger = logging.getLogger("forgemaster")
        assert logger.level == logging.ERROR

    def test_configures_only_once(self):
        """Subsequent calls to configure_logging should be no-ops."""
        configure_logging(verbose=True, quiet=False)
        assert logging.getLogger("forgemaster").level == logging.DEBUG

        # Second call with different flags — should NOT change the level.
        configure_logging(verbose=False, quiet=True)
        assert logging.getLogger("forgemaster").level == logging.DEBUG

    def test_adds_rich_handler(self):
        """configure_logging should add exactly one RichHandler."""
        from rich.logging import RichHandler

        configure_logging()
        logger = logging.getLogger("forgemaster")
        rich_handlers = [h for h in logger.handlers if isinstance(h, RichHandler)]
        assert len(rich_handlers) == 1

    def test_propagate_is_false(self):
        """The forgemaster logger should not propagate to the root logger."""
        configure_logging()
        logger = logging.getLogger("forgemaster")
        assert logger.propagate is False


class TestGetLogger:
    """Test get_logger() namespace behaviour."""

    def test_forgemaster_namespace_prefix(self):
        """get_logger should prefix non-forgemaster names."""
        log = get_logger("scanner")
        assert log.name == "forgemaster.scanner"

    def test_forgemaster_namespace_preserved(self):
        """get_logger should preserve names that already start with forgemaster."""
        log = get_logger("forgemaster.gpu")
        assert log.name == "forgemaster.gpu"

    def test_dunder_name_style(self):
        """Module-style __name__ should work and get prefixed."""
        log = get_logger("forgemaster.vram")
        assert log.name == "forgemaster.vram"

    def test_returns_logger_instance(self):
        """get_logger should return a logging.Logger."""
        log = get_logger("test")
        assert isinstance(log, logging.Logger)
