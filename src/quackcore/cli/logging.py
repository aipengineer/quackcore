# src/quackcore/cli/logging.py
"""
Logging utilities for CLI applications.

This module provides functions for setting up logging in CLI applications,
with flexible configuration options and consistent output formatting.
"""

import atexit
import logging
from pathlib import Path
from typing import Protocol, TypeVar

from quackcore.cli.options import LogLevel
from quackcore.config.models import QuackConfig

T = TypeVar("T")  # Generic type for flexible typing


class LoggerFactory(Protocol):
    """Protocol for logger factory functions."""

    def __call__(self, name: str) -> logging.Logger:
        """
        Create or get a logger with the given name.

        Args:
            name: The name of the logger

        Returns:
            A configured logger instance
        """
        ...


def _determine_effective_level(
    cli_log_level: LogLevel | None,
    cli_debug: bool,
    cli_quiet: bool,
    cfg: QuackConfig | None,
) -> LogLevel:
    """
    Determine the effective logging level based on various inputs.

    Args:
        cli_log_level: Optional logging level override from CLI
        cli_debug: True if debug flag is set
        cli_quiet: True if quiet flag is set
        cfg: Optional configuration with logging settings

    Returns:
        The effective log level as a string
    """
    if cli_debug:
        return "DEBUG"
    if cli_quiet:
        return "ERROR"
    if cli_log_level is not None:
        return cli_log_level
    if cfg and cfg.logging.level:
        config_level = cfg.logging.level.upper()
        if config_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return config_level  # type: ignore
    return "INFO"


# Keep track of file handlers we've added
_file_handlers: list[logging.FileHandler] = []


def _add_file_handler(
    root_logger: logging.Logger,
    cfg: QuackConfig,
    level_value: int,
    console_formatter: logging.Formatter | None = None,
) -> None:
    """
    Add a file handler to the root logger if a log file is specified in the config.

    Args:
        root_logger: The root logger to configure
        cfg: The configuration containing logging settings
        level_value: The numeric logging level
        console_formatter: Optional formatter to use for consistency with console output
    """
    # Import here to avoid import at module level, making it easier to mock in tests
    from quackcore.fs.service import create_directory

    try:
        log_file = cfg.logging.file
        if not log_file:
            return

        # Ensure log_file is a Path object
        log_file = Path(log_file) if not isinstance(log_file, Path) else log_file
        log_dir = log_file.parent

        # Create the log directory
        result = create_directory(log_dir, exist_ok=True)

        # Return early if directory creation failed
        if not result.success:
            root_logger.warning(f"Failed to create log directory: {result.error}")
            return

        # Add this debug line to help with troubleshooting
        root_logger.debug(f"Log directory created: {log_dir}")

        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(level_value)

        if console_formatter:
            file_handler.setFormatter(console_formatter)
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)

        root_logger.addHandler(file_handler)
        root_logger.debug(f"Log file configured: {log_file}")

        # Add to our global list for cleanup on exit
        _file_handlers.append(file_handler)
    except Exception as e:
        root_logger.warning(f"Failed to set up log file: {e}")


# Register a cleanup function to close all file handlers on exit
@atexit.register
def _cleanup_file_handlers() -> None:
    """Close all file handlers on exit to prevent resource warnings."""
    for handler in _file_handlers:
        try:
            handler.close()
        except Exception:
            pass  # Ignore errors during cleanup
    _file_handlers.clear()


def setup_logging(
    log_level: LogLevel | None = None,
    debug: bool = False,
    quiet: bool = False,
    config: QuackConfig | None = None,
    logger_name: str = "quack",
) -> tuple[logging.Logger, LoggerFactory]:
    """
    Set up logging for CLI applications.

    This function configures logging based on CLI flags and configuration settings,
    ensuring consistent logging behavior across all QuackVerse tools.

    Args:
        log_level: Optional logging level (overrides config and other flags)
        debug: Whether debug mode is enabled (sets log level to DEBUG)
        quiet: Whether to suppress non-error output (sets log level to ERROR)
        config: Optional configuration to use for logging setup
        logger_name: Base name for the logger

    Returns:
        A tuple containing:
        - The root logger instance
        - A logger factory function to create named loggers
    """
    # Determine the effective log level
    effective_level: LogLevel = _determine_effective_level(
        log_level, debug, quiet, config
    )

    # Convert string level to numeric value
    try:
        level_value = getattr(logging, effective_level)
    except (AttributeError, TypeError):
        level_value = logging.INFO

    # Configure the root logger
    root_logger = logging.getLogger(logger_name)

    # Important: Set propagate to False for the root logger to avoid duplicate logs
    root_logger.propagate = False

    # Set the level and clear existing handlers
    root_logger.setLevel(level_value)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_value)

    # Configure formatter based on debug mode
    if effective_level == "DEBUG":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        formatter = logging.Formatter("%(levelname)s: %(message)s")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if config and config.logging.file:
        _add_file_handler(root_logger, config, level_value, formatter)

    # Factory function that creates loggers with the correct name and level
    def get_logger(name: str) -> logging.Logger:
        """Create or get a named logger with the configured settings."""
        logger = logging.getLogger(f"{logger_name}.{name}")
        # Explicitly set the level to match the root logger
        logger.setLevel(root_logger.level)
        return logger

    return root_logger, get_logger
