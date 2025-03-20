# tests/test_integrations/google/drive/test_drive_service_download.py
"""
Tests for Google Drive service download operations.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from quackcore.errors import QuackApiError
from quackcore.fs.results import FileInfoResult, OperationResult, WriteResult
from quackcore.integrations.google.drive.service import GoogleDriveService


class TestGoogleDriveServiceDownload:
    """Tests for the GoogleDriveService download operations."""

    @pytest.fixture
    def drive_service(self):
        """Set up a Google Drive service with mocked dependencies."""
        # Mock the resolver instance that's imported in the service
        with patch("quackcore.integrations.google.drive.service.resolver") as mock_resolver:
            # Setup resolver mock
            mock_resolver.resolve_project_path.side_effect = lambda p, *args: Path(f"/fake/test/dir/{Path(p).name}")

            with patch("quackcore.fs.service.get_file_info") as mock_file_info:
                # All file info checks should return that files exist
                file_info_result = FileInfoResult(
                    success=True,
                    path="/fake/test/dir/mock_credentials.json",
                    exists=True,
                    is_file=True,
                    message="File exists"
                )
                mock_file_info.return_value = file_info_result

                # Mock normalize_path to return predictable paths
                with patch("quackcore.fs.service.normalize_path") as mock_normalize:
                    mock_normalize.side_effect = lambda p: Path(f"/fake/test/dir/{Path(p).name}")

                    # Create the service with mocked configuration
                    with patch.object(GoogleDriveService, "_initialize_config") as mock_init_config:
                        # Mock the config initialization to return a valid config dictionary
                        mock_init_config.return_value = {
                            "client_secrets_file": "/fake/test/dir/mock_secrets.json",
                            "credentials_file": "/fake/test/dir/mock_credentials.json",
                        }

                        # Disable verification of the client secrets file
                        with patch("quackcore.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"):
                            # Create service instance
                            service = GoogleDriveService()
                            # Set as initialized to skip initialization logic
                            service._initialized = True
                            service.drive_service = MagicMock()

                            # Yield the service to the test
                            yield service

    @patch("googleapiclient.http.MediaIoBaseDownload")
    def test_download_file(self, mock_download_class: MagicMock, drive_service) -> None:
        """Test downloading a file."""
        # Mock API response
        mock_get = MagicMock()
        drive_service.drive_service.files().get.return_value = mock_get
        mock_get.execute.return_value = {
            "name": "test_file.txt",
            "mimeType": "text/plain",
        }

        # Mock get_media
        mock_get_media = MagicMock()
        drive_service.drive_service.files().get_media.return_value = mock_get_media

        # Mock the downloader
        mock_downloader = MagicMock()
        mock_download_class.return_value = mock_downloader
        mock_downloader.next_chunk.side_effect = [
            (MagicMock(progress=lambda: 0.5), False),
            (MagicMock(progress=lambda: 1.0), True),
        ]

        # Test successful download
        with patch(
            "quackcore.integrations.google.drive.service.io.BytesIO"
        ) as mock_bytesio:
            mock_io = MagicMock()
            mock_bytesio.return_value = mock_io
            mock_io.read.return_value = b"file content"

            with patch.object(drive_service, "_resolve_download_path") as mock_resolve:
                mock_resolve.return_value = "/tmp/test_file.txt"

                with patch("quackcore.fs.service.join_path") as mock_join:
                    mock_join.return_value = Path("/tmp/test_file.txt")

                    with patch("quackcore.fs.service.create_directory") as mock_mkdir:
                        mkdir_result = OperationResult(
                            success=True,
                            path="/tmp",
                            message="Directory created"
                        )
                        mock_mkdir.return_value = mkdir_result

                        with patch(
                            "quackcore.integrations.google.drive.service.fs.write_binary"
                        ) as mock_write:
                            write_result = WriteResult(
                                success=True,
                                path="/tmp/test_file.txt",
                                bytes_written=len(b"file content"),
                                message="File written"
                            )
                            mock_write.return_value = write_result

                            result = drive_service.download_file(
                                "file123", "/tmp/test_file.txt"
                            )

                            assert result.success is True
                            assert result.content == "/tmp/test_file.txt"
                            drive_service.drive_service.files().get.assert_called_once_with(
                                file_id="file123", fields="name, mimeType"
                            )
                            drive_service.drive_service.files().get_media.assert_called_once_with(
                                file_id="file123"
                            )
                            mock_write.assert_called_once()

        # Test API error
        drive_service.drive_service.files().get.side_effect = QuackApiError(
            "API error", service="drive"
        )
        result = drive_service.download_file("file123")
        assert result.success is False
        assert "API error" in result.error

        # Test download error
        drive_service.drive_service.files().get.side_effect = None
        mock_download_class.side_effect = Exception("Download error")
        result = drive_service.download_file("file123")
        assert result.success is False
        assert "Download error" in result.error

        # Test write error
        mock_download_class.side_effect = None
        with patch.object(drive_service, "_resolve_download_path"):
            with patch("quackcore.fs.service.join_path"):
                with patch("quackcore.fs.service.create_directory"):
                    with patch("quackcore.integrations.google.drive.service.fs.write_binary") as mock_write:
                        write_result = WriteResult(
                            success=False,
                            path="/tmp/test_file.txt",
                            error="Write error"
                        )
                        mock_write.return_value = write_result

                        result = drive_service.download_file("file123")

                        assert result.success is False
                        assert "Write error" in result.error