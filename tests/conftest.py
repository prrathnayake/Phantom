"""Pytest fixtures for common test setup."""
import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file sensor tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_context():
    """Provide an empty context dictionary."""
    return {}


@pytest.fixture
def sample_snapshot():
    """Provide a sample file snapshot for testing."""
    return {
        "/test/file1.txt": 1000.0,
        "/test/file2.txt": 2000.0,
        "/test/file3.txt": 3000.0,
    }