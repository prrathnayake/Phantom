"""Tests for installer module."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInstaller:
    """Tests for installer module."""

    def test_check_python_installation(self):
        """Test Python installation check."""
        from utils.installer import check_python_installation
        success, version = check_python_installation()
        assert success is True
        assert version

    def test_get_pip_command(self):
        """Test pip command detection."""
        from utils.installer import get_pip_command
        result = get_pip_command()
        assert result in ["py", "python", "python3"]

    def test_install_package_invalid_package(self):
        """Test installing invalid package returns failure."""
        from utils.installer import install_package
        success, message = install_package("nonexistent-package-xyz-123")
        assert success is False

    def test_install_package_formats_result(self):
        """Test install_package returns tuple."""
        from utils.installer import install_package
        result = install_package("nonexistent")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)