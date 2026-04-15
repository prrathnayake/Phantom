"""Tests for system_scanner module."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSystemScanner:
    """Tests for system_scanner module."""

    def test_scan_system_returns_info(self):
        """Test scan_system returns SystemInfo."""
        from utils.system_scanner import scan_system
        result = scan_system()
        assert result is not None
        assert hasattr(result, "os_name")
        assert hasattr(result, "python_version")

    def test_system_info_has_os_details(self):
        """Test SystemInfo has OS fields."""
        from utils.system_scanner import scan_system
        info = scan_system()
        assert info.os_name in ["Windows", "Linux", "Darwin"]
        assert info.machine_type

    def test_system_info_has_python_details(self):
        """Test SystemInfo has Python fields."""
        from utils.system_scanner import scan_system
        info = scan_system()
        assert info.python_version
        assert info.python_executable

    def test_system_info_has_package_status(self):
        """Test SystemInfo has package status fields."""
        from utils.system_scanner import scan_system
        info = scan_system()
        assert hasattr(info, "has_textual")
        assert hasattr(info, "has_psutil")
        assert hasattr(info, "has_watchdog")
        assert hasattr(info, "has_requests")
        assert hasattr(info, "has_dotenv")

    def test_check_python_package_imports_textual(self):
        """Test check_python_package works for textual."""
        from utils.system_scanner import check_python_package
        result = check_python_package("textual")
        assert isinstance(result, bool)

    def test_check_python_package_imports_psutil(self):
        """Test check_python_package works for psutil."""
        from utils.system_scanner import check_python_package
        result = check_python_package("psutil")
        assert isinstance(result, bool)

    def test_check_command_available(self):
        """Test check_command_available detects commands."""
        from utils.system_scanner import check_command_available
        result = check_command_available("python")
        assert result is True

    def test_get_missing_packages(self):
        """Test get_missing_packages returns list."""
        from utils.system_scanner import scan_system, get_missing_packages
        info = scan_system()
        missing = get_missing_packages(info)
        assert isinstance(missing, list)

    def test_format_system_info(self):
        """Test format_system_info returns string."""
        from utils.system_scanner import scan_system, format_system_info
        info = scan_system()
        result = format_system_info(info)
        assert isinstance(result, str)
        assert "OS:" in result
        assert "Python:" in result