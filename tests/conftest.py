"""Pytest configuration for tests.

This module sets up the Python path to allow imports from the src directory.
"""

import sys
from pathlib import Path

# Add src directory to Python path so tests can import from lib modules
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


# Configure pytest-asyncio for Python 3.8 compatibility
def pytest_configure(config):
    """Configure pytest options."""
    config.option.asyncio_mode = "auto"
