"""System scanner module to detect OS, environment, and installed tools."""
import sys
import platform
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemInfo:
    os_name: str
    os_version: str
    os_release: str
    machine_type: str
    python_version: str
    python_executable: str
    has_pip: bool
    has_git: bool
    has_textual: bool
    has_psutil: bool
    has_watchdog: bool
    has_requests: bool
    has_dotenv: bool


def get_os_info() -> tuple[str, str, str, str]:
    """Detect OS details."""
    return (
        platform.system(),
        platform.release(),
        platform.version(),
        platform.machine()
    )


def get_python_info() -> tuple[str, str]:
    """Get Python version and executable path."""
    return (
        platform.python_version(),
        sys.executable
    )


def check_command_available(cmd: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(cmd) is not None


def check_python_package(package: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def check_packages() -> dict:
    """Check which required Python packages are installed."""
    return {
        "textual": check_python_package("textual"),
        "psutil": check_python_package("psutil"),
        "watchdog": check_python_package("watchdog"),
        "requests": check_python_package("requests"),
        "dotenv": check_python_package("dotenv"),
    }


def scan_system() -> SystemInfo:
    """Perform a full system scan."""
    os_name, os_version, os_release, machine_type = get_os_info()
    python_version, python_executable = get_python_info()
    packages = check_packages()

    return SystemInfo(
        os_name=os_name,
        os_version=os_version,
        os_release=os_release,
        machine_type=machine_type,
        python_version=python_version,
        python_executable=python_executable,
        has_pip=check_command_available("pip"),
        has_git=check_command_available("git"),
        has_textual=packages["textual"],
        has_psutil=packages["psutil"],
        has_watchdog=packages["watchdog"],
        has_requests=packages["requests"],
        has_dotenv=packages["dotenv"],
    )


def format_system_info(info: SystemInfo) -> str:
    """Format system info as a readable report."""
    lines = [
        "=" * 50,
        "SYSTEM SCAN REPORT",
        "=" * 50,
        f"OS: {info.os_name}",
        f"Version: {info.os_version}",
        f"Release: {info.os_release}",
        f"Machine: {info.machine_type}",
        "-" * 50,
        f"Python: {info.python_version}",
        f"Executable: {info.python_executable}",
        "-" * 50,
        "COMMAND AVAILABILITY",
        f"  pip: {'OK' if info.has_pip else 'MISSING'}",
        f"  git: {'OK' if info.has_git else 'MISSING'}",
        "-" * 50,
        "PYTHON PACKAGES",
        f"  textual: {'OK' if info.has_textual else 'MISSING'}",
        f"  psutil: {'OK' if info.has_psutil else 'MISSING'}",
        f"  watchdog: {'OK' if info.has_watchdog else 'MISSING'}",
        f"  requests: {'OK' if info.has_requests else 'MISSING'}",
        f"  python-dotenv: {'OK' if info.has_dotenv else 'MISSING'}",
        "=" * 50,
    ]
    return "\n".join(lines)


def get_missing_packages(info: SystemInfo) -> list[str]:
    """Return list of missing required packages."""
    missing = []
    if not info.has_textual:
        missing.append("textual>=0.90.0")
    if not info.has_psutil:
        missing.append("psutil>=5.9")
    if not info.has_watchdog:
        missing.append("watchdog>=3.0")
    if not info.has_requests:
        missing.append("requests>=2.31")
    if not info.has_dotenv:
        missing.append("python-dotenv>=1.0")
    return missing


def get_system_info() -> SystemInfo:
    """Export function for scanner."""
    return scan_system()
