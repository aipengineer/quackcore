# tests/quackcore/test_integrations/pandoc/test_operations.py
"""
Tests for Pandoc conversion operations.

This module serves as an entry point for tests of the Pandoc integration operations.
The actual tests are organized into submodules within the test_operations/ directory.
"""

# Import test classes so they get discovered by pytest
from tests.quackcore.test_integrations.pandoc.operations.test_html_to_md import (
    TestHtmlToMarkdownOperations,
)
from tests.quackcore.test_integrations.pandoc.operations.test_md_to_docx import (
    TestMarkdownToDocxOperations,
)
from tests.quackcore.test_integrations.pandoc.operations.test_utils import (
    TestPandocUtilities,
)
