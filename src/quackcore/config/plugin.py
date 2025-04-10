# src/quackcore/config/plugin.py
"""
Configuration loading utilities for QuackCore.

This module provides utilities for loading and merging configurations
from various sources, with support for environment-specific overrides.
"""

import os
from typing import Any, TypeVar

import yaml

from quackcore.config.models import QuackConfig
from quackcore.errors import QuackConfigurationError, wrap_io_errors

# Import FS service and helper functions.
from quackcore.fs import join_path
from quackcore.fs import service as fs
from quackcore.logging import get_logger
from quackcore.paths import resolver

T = TypeVar("T")  # Generic type for flexible typing

# Default configuration values to be merged when merge_defaults is True.
DEFAULT_CONFIG_VALUES: dict[str, Any] = {
    "logging": {
        "level": "INFO",
        "file": "logs/quackcore.log",
    },
    "paths": {
        # Using fs.expand_user_vars to get a cross‑platform, expanded path.
        "base_dir": fs.expand_user_vars("~/.quackcore"),
    },
    "general": {
        "project_name": "QuackCore",
    },
}

DEFAULT_CONFIG_LOCATIONS = [
    "./quack_config.yaml",
    "./config/quack_config.yaml",
    "~/.quack/config.yaml",
    "/etc/quack/config.yaml",
]

ENV_PREFIX = "QUACK_"

logger = get_logger(__name__)


@wrap_io_errors
def load_yaml_config(path: str) -> dict[str, Any]:
    """
    Load a YAML configuration file.

    Args:
        path: Path to YAML file.

    Returns:
        Dictionary with configuration values.

    Raises:
        QuackConfigurationError: If the file cannot be loaded.
    """
    try:
        # Use fs.read_text to read file content.
        read_result = fs.read_text(path, encoding="utf-8")
        if not read_result.success:
            raise QuackConfigurationError(
                f"Failed to load YAML config: {read_result.error}", path
            )
        config = yaml.safe_load(read_result.content)
        return config or {}
    except (yaml.YAMLError, OSError) as e:
        raise QuackConfigurationError(f"Failed to load YAML config: {e}", path) from e


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary.
        override: Override dictionary.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_float(value: str) -> bool:
    """
    Check if the string represents a float number.

    Args:
        value: The string to check.

    Returns:
        True if the string can be interpreted as a float, False otherwise.
    """
    try:
        float(value)
        return "." in value and not value.endswith(".")
    except ValueError:
        return False


def _convert_env_value(value: str) -> bool | int | float | str:
    """
    Convert an environment variable string value to an appropriate type.

    Args:
        value: The environment variable value as string.

    Returns:
        The value converted to bool, int, float, or left as string.
    """
    v_lower = value.lower()
    if v_lower == "true":
        return True
    if v_lower == "false":
        return False
    if value.startswith("-") and value[1:].isdigit():
        return int(value)
    if value.isdigit():
        return int(value)
    if _is_float(value):
        return float(value)
    return value


def _get_env_config() -> dict[str, Any]:
    """
    Get configuration from environment variables.

    Environment variables should be in the format:
    QUACK_SECTION__KEY=value

    Returns:
        Dictionary with configuration values.
    """
    config: dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIX):
            key_parts = key[len(ENV_PREFIX) :].lower().split("__")
            if len(key_parts) < 2:
                continue
            typed_value = _convert_env_value(value)
            current = config
            for i, part in enumerate(key_parts):
                if i == len(key_parts) - 1:
                    current[part] = typed_value
                else:
                    current.setdefault(part, {})
                    current = current[part]
    return config


def find_config_file() -> str | None:
    """
    Find a configuration file in standard locations.

    Returns:
        The path to the configuration file if found, or None.
    """
    # Check environment variable first.
    if config_path := os.environ.get("QUACK_CONFIG"):
        expanded = fs.expand_user_vars(config_path)
        if fs.get_file_info(expanded).success and fs.get_file_info(expanded).exists:
            return expanded

    # Check default locations.
    for location in DEFAULT_CONFIG_LOCATIONS:
        expanded = fs.expand_user_vars(location)
        if fs.get_file_info(expanded).success and fs.get_file_info(expanded).exists:
            return expanded

    # Try to find the project root and then check for config there.
    try:
        root = resolver.get_project_root()
        for name in ["quack_config.yaml", "config/quack_config.yaml"]:
            candidate = join_path(str(root), name)
            if (
                fs.get_file_info(candidate).success
                and fs.get_file_info(candidate).exists
            ):
                return str(candidate)
    except Exception as e:
        logger.debug("Failed to find project root: %s", e)

    return None


def load_config(
    config_path: str | None = None,
    merge_env: bool = True,
    merge_defaults: bool = True,
) -> QuackConfig:
    """
    Load configuration from a file and merge with environment variables and defaults.

    Args:
        config_path: Optional path to a configuration file.
        merge_env: Whether to merge environment variables into the configuration.
        merge_defaults: Whether to merge default configuration values.

    Returns:
        A QuackConfig instance built from the merged configuration.

    Raises:
        QuackConfigurationError: If no configuration could be loaded.
    """
    config_dict: dict[str, Any] = {}

    if config_path:
        expanded = fs.expand_user_vars(str(config_path))
        if not (
            fs.get_file_info(expanded).success and fs.get_file_info(expanded).exists
        ):
            raise QuackConfigurationError(
                f"Configuration file not found: {expanded}", expanded
            )
        config_dict = load_yaml_config(expanded)
    else:
        found = find_config_file()
        if found:
            config_dict = load_yaml_config(found)

    if merge_env:
        env_config = _get_env_config()
        config_dict = _deep_merge(config_dict, env_config)

    if merge_defaults:
        config_dict = _deep_merge(DEFAULT_CONFIG_VALUES, config_dict)

    return QuackConfig.model_validate(config_dict)


def merge_configs(base: QuackConfig, override: dict[str, Any]) -> QuackConfig:
    """
    Merge a base configuration with override values.

    Args:
        base: Base configuration.
        override: Override values.

    Returns:
        A merged QuackConfig instance.
    """
    base_dict = base.to_dict()
    merged = _deep_merge(base_dict, override)
    return QuackConfig.model_validate(merged)
