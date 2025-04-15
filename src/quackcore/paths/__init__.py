# src/quackcore/paths/__init__.py
"""
Path resolution and management utilities for QuackCore.

This package provides utilities for resolving paths, detecting project structure,
and inferring context from file locations in QuackCore projects.
"""

"""
NOTE: This module intentionally does NOT expose low-level path functions.
Use `quackcore.fs` for join_path, split_path, etc. to avoid API duplication.
"""


from quackcore.fs.service.standalone import join_path, split_path, get_extension
from quackcore.paths._internal.context import ContentContext, ProjectContext, ProjectDirectory
from quackcore.paths._internal.resolver import PathResolver, _resolve_project_path
from quackcore.paths._internal.utils import _find_project_root, _find_nearest_directory, \
    _resolve_relative_to_project, _normalize_path, _infer_module_from_path

# Create a global instance for convenience
resolver = PathResolver()

__all__ = [
    # Classes
    "PathResolver",
    "ProjectContext",
    "ContentContext",
    "ProjectDirectory",
    # Global instance
    "resolver",
    "_resolve_project_path",
    # Utility functions
    "_find_project_root",
    "_find_nearest_directory",
    "_resolve_relative_to_project",
    "_normalize_path",
    "join_path",
    "split_path",
    "get_extension",
    "_infer_module_from_path",
]
