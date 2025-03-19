# tests/test_integrations/base/test_config_provider_discovery.py
"""
Tests for the config discovery functionality in BaseConfigProvider.
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from quackcore.errors import QuackConfigurationError, QuackFileNotFoundError
from tests.test_integrations.base.config_provider_impl import MockConfigProvider


class TestBaseConfigProviderDiscovery:
    """Tests for config discovery functionality in BaseConfigProvider."""

    def test_load_config_discover(self) -> None:
        """Test loading configuration by discovering the file."""
        provider = MockConfigProvider()

        # Test with environment variable
        with patch.dict(os.environ, {"QUACK_TEST_CONFIG_CONFIG": "/env/config.yaml"}):
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = True

                with patch("quackcore.fs.service.expand_user_vars") as mock_expand:
                    mock_expand.return_value = "/env/config.yaml"

                    with patch.object(provider, "_find_config_file") as mock_find:
                        mock_find.return_value = "/env/config.yaml"

                        with patch("quackcore.fs.service.get_file_info") as mock_info:
                            mock_info.return_value.success = True
                            mock_info.return_value.exists = True

                            with patch("quackcore.fs.service.read_yaml") as mock_read:
                                mock_read.return_value.success = True
                                mock_read.return_value.data = {
                                    "test_section": {"test_key": "env_value"}
                                }

                                result = provider.load_config()
                                assert result.success is True
                                assert result.content == {"test_key": "env_value"}
                                assert result.config_path == "/env/config.yaml"

        # Test with default locations
        with patch.object(provider, "_find_config_file") as mock_find:
            mock_find.return_value = "/default/config.yaml"

            with patch("quackcore.fs.service.get_file_info") as mock_info:
                mock_info.return_value.success = True
                mock_info.return_value.exists = True

                with patch("quackcore.fs.service.read_yaml") as mock_read:
                    mock_read.return_value.success = True
                    mock_read.return_value.data = {
                        "test_section": {"test_key": "default_value"}
                    }

                    result = provider.load_config()
                    assert result.success is True
                    assert result.content == {"test_key": "default_value"}
                    assert result.config_path == "/default/config.yaml"

        # Test when no config file is found
        with patch.object(provider, "_find_config_file") as mock_find:
            mock_find.return_value = None

            with pytest.raises(QuackConfigurationError):
                provider.load_config()

    def test_find_config_file(self) -> None:
        """Test finding a configuration file in standard locations."""
        provider = MockConfigProvider()

        # Test with environment variable
        with patch.dict(os.environ, {"QUACK_TEST_CONFIG_CONFIG": "/env/config.yaml"}):
            # Mock the expand_user_vars function
            with patch(
                    "quackcore.integrations.base.fs.expand_user_vars") as mock_expand:
                mock_expand.return_value = "/env/config.yaml"

                # Mock the get_file_info function
                with patch(
                        "quackcore.integrations.base.fs.get_file_info") as mock_get_file_info:
                    # Create a mock FileInfoResult that indicates the file exists
                    mock_result = MagicMock()
                    mock_result.success = True
                    mock_result.exists = True
                    mock_get_file_info.return_value = mock_result

                    # Call the function under test
                    result = provider._find_config_file()

                    # Verify the result
                    assert result == "/env/config.yaml"

                    # Verify the mocks were called correctly
                    mock_expand.assert_called_once_with("/env/config.yaml")
                    mock_get_file_info.assert_called_once_with("/env/config.yaml")

        # Test with default locations
        with patch(
                "quackcore.integrations.base.resolver.get_project_root") as mock_get_root:
            # Mock resolver.get_project_root to avoid FileNotFoundError
            mock_get_root.side_effect = QuackFileNotFoundError("mock error")

            with patch("quackcore.integrations.base.fs.get_file_info") as mock_get_info:
                # Create responses for different paths
                def get_info_side_effect(path: str) -> MagicMock:
                    result = MagicMock()
                    result.success = True
                    result.exists = path == "/default/config.yaml"
                    return result

                mock_get_info.side_effect = get_info_side_effect

                with patch(
                        "quackcore.integrations.base.fs.expand_user_vars") as mock_expand:
                    mock_expand.side_effect = lambda path: "/default/" + Path(path).name

                    with patch.object(
                            provider,
                            "DEFAULT_CONFIG_LOCATIONS",
                            ["config.yaml", "quack_config.yaml"],
                    ):
                        result = provider._find_config_file()

                        # Verify the result
                        assert result == "/default/config.yaml"

        # Test with project root detection
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch(
                "quackcore.integrations.base.resolver.get_project_root"
            ) as mock_root:
                mock_root.return_value = Path("/project")

                with patch("os.path.join") as mock_join:
                    mock_join.return_value = "/project/quack_config.yaml"

                    with patch("os.path.exists") as mock_exists2:
                        mock_exists2.return_value = True

                        result = provider._find_config_file()
                        assert result == "/project/quack_config.yaml"

        # Test when no config file can be found
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch(
                "quackcore.integrations.base.resolver.get_project_root"
            ) as mock_root:
                mock_root.side_effect = QuackFileNotFoundError("/nonexistent")

                result = provider._find_config_file()
                assert result is None

    def test_extract_config(self) -> None:
        """Test extracting integration-specific configuration."""
        provider = MockConfigProvider()

        # Test with matching section
        config_data = {"test_section": {"test_key": "test_value"}}
        result = provider._extract_config(config_data)
        assert result == {"test_key": "test_value"}

        # Test with missing section
        config_data = {"other_section": {}}
        result = provider._extract_config(config_data)
        assert result == {}

    def test_resolve_path(self) -> None:
        """Test resolving a path relative to the project root."""
        provider = MockConfigProvider()

        # Test with project root resolver
        with patch(
            "quackcore.integrations.base.resolver.resolve_project_path"
        ) as mock_resolve:
            mock_resolve.return_value = "/resolved/path"

            result = provider._resolve_path("relative/path")
            assert result == "/resolved/path"
            mock_resolve.assert_called_once_with("relative/path")

        # Test with resolver exception
        with patch(
            "quackcore.integrations.base.resolver.resolve_project_path"
        ) as mock_resolve:
            mock_resolve.side_effect = Exception("Test error")

            with patch("quackcore.fs.service.normalize_path") as mock_normalize:
                mock_normalize.return_value = "/normalized/path"

                result = provider._resolve_path("relative/path")
                assert result == "/normalized/path"
                mock_normalize.assert_called_once_with("relative/path")
