# src/quackcore/teaching/core/utils.py
"""
Utility functions for the QuackCore teaching module.

This module provides functions for loading and saving user progress,
getting usernames, and other utility operations.
"""

import getpass
import os
from pathlib import Path

from quackcore.fs import service as fs
from quackcore.logging import get_logger

from .models import UserProgress

logger = get_logger(__name__)

# Default location for user progress file
DEFAULT_DATA_DIR = "~/.quack"
DEFAULT_PROGRESS_FILE = "ducktyper_user.json"


def get_user_data_dir() -> Path:
    """
    Get the directory for user data.

    Returns:
        Path to the user data directory.
    """
    # Use fs.expand_user_vars to process any shell shortcuts.
    data_dir = os.environ.get("QUACK_DATA_DIR", DEFAULT_DATA_DIR)
    path = Path(fs.expand_user_vars(data_dir))

    # Ensure the directory exists using the centralized FS service.
    fs.create_directory(path, exist_ok=True)

    return path


def get_progress_file_path() -> Path:
    """
    Get the path to the user progress file.

    Returns:
        Path to the user progress file.
    """
    data_dir = get_user_data_dir()
    file_name = os.environ.get("QUACK_PROGRESS_FILE", DEFAULT_PROGRESS_FILE)
    return data_dir / file_name


def get_github_username() -> str:
    """
    Get the user's GitHub username.

    This will check:
    1. GITHUB_USERNAME environment variable.
    2. Git configuration.
    3. Prompt the user if not found.

    Returns:
        GitHub username.
    """
    username = os.environ.get("GITHUB_USERNAME")
    if username:
        return username

    # Try to retrieve the username from git config.
    try:
        import subprocess

        result = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Prompt the user if not found.
    try:
        username = input("Enter your GitHub username: ")
        if username:
            return username
    except Exception:
        pass

    # Fall back to the system username.
    return getpass.getuser()


def load_progress() -> UserProgress:
    """
    Load user progress from the progress file.

    If the file doesn't exist or can't be loaded, returns a new UserProgress.

    Returns:
        User progress.
    """
    file_path = get_progress_file_path()

    # Check if file exists using FS function.
    result = fs.get_file_info(file_path)
    if not result.success or not result.exists:
        logger.debug(f"Progress file not found at {file_path}, creating new progress")
        return create_new_progress()

    try:
        result = fs.read_json(file_path)
        if not result.success:
            logger.warning(f"Failed to read progress file: {result.error}")
            return create_new_progress()

        data = result.data
        progress = UserProgress.model_validate(data)
        logger.debug(
            f"Loaded user progress: {progress.xp} XP, {len(progress.completed_quest_ids)} quests"
        )
        return progress

    except Exception as e:
        logger.warning(f"Error loading progress file: {str(e)}")
        return create_new_progress()


def save_progress(progress: UserProgress) -> bool:
    """
    Save user progress to the progress file.

    Args:
        progress: User progress to save.

    Returns:
        True if saved successfully, False otherwise.
    """
    file_path = get_progress_file_path()
    data = progress.model_dump()

    try:
        result = fs.write_json(file_path, data)
        if not result.success:
            logger.error(f"Failed to save progress file: {result.error}")
            return False

        logger.debug(
            f"Saved user progress: {progress.xp} XP, {len(progress.completed_quest_ids)} quests"
        )
        return True
    except Exception as e:
        logger.error(f"Error saving progress file: {str(e)}")
        return False


def create_new_progress() -> UserProgress:
    """
    Create new user progress.

    Returns:
        New user progress.
    """
    github_username = get_github_username()
    progress = UserProgress(github_username=github_username)
    save_progress(progress)
    return progress


def reset_progress() -> bool:
    """
    Reset user progress by deleting the progress file.

    Returns:
        True if reset successfully, False otherwise.
    """
    file_path = get_progress_file_path()
    result = fs.get_file_info(file_path)
    if not result.success or not result.exists:
        logger.debug(f"No progress file to reset at {file_path}")
        return True

    result = fs.delete(file_path)
    if not result.success:
        logger.error(f"Failed to delete progress file: {result.error}")
        return False

    logger.info(f"Reset user progress by deleting {file_path}")
    return True


def backup_progress(backup_name: str = None) -> bool:
    """
    Create a backup of the user progress file.

    Args:
        backup_name: Optional name for the backup file.
            If not provided, a timestamp will be used.

    Returns:
        True if backed up successfully, False otherwise.
    """
    import datetime

    file_path = get_progress_file_path()
    result = fs.get_file_info(file_path)
    if not result.success or not result.exists:
        logger.debug(f"No progress file to backup at {file_path}")
        return False

    if not backup_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"ducktyper_user_{timestamp}.json"

    backup_path = get_user_data_dir() / backup_name
    result = fs.copy(file_path, backup_path)
    if not result.success:
        logger.error(f"Failed to create backup: {result.error}")
        return False

    logger.info(f"Created backup of user progress at {backup_path}")
    return True
