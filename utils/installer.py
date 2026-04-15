"""Installer module to install required dependencies."""
import sys
import subprocess
import platform
from typing import Optional


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def get_pip_command() -> str:
    """Get the appropriate pip command for the current Python."""
    if platform.system() == "Windows":
        return "py"
    return "python3" if sys.executable.endswith("python3") else "python"


def install_package(package: str, upgrade: bool = False) -> tuple[bool, str]:
    """Install a package using pip."""
    cmd = [get_pip_command(), "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(package)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return True, f"Installed {package}"
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Timeout installing {package}"
    except Exception as e:
        return False, str(e)


def install_packages(packages: list[str], upgrade: bool = False) -> dict[str, bool]:
    """Install multiple packages and return results."""
    results = {}
    for package in packages:
        print(f"Installing {package}...")
        success, message = install_package(package, upgrade)
        results[package] = success
        if success:
            print(f"  {Colors.GREEN}OK{Colors.END} {message}")
        else:
            print(f"  {Colors.FAILED}FAILED{Colors.END} {message}")
    return results


def install_from_requirements(requirements_file: str = "requirements.txt") -> tuple[bool, int]:
    """Install all packages from a requirements file."""
    try:
        print(f"Installing from {requirements_file}...")
        cmd = [get_pip_command(), "-m", "pip", "install", "-r", requirements_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, 0
        else:
            return False, result.returncode
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}")
        return False, 1


def check_python_installation() -> tuple[bool, str]:
    """Verify Python is properly installed."""
    try:
        version = sys.version
        return True, version
    except Exception as e:
        return False, str(e)


def ensure_dependencies() -> dict[str, bool]:
    """Ensure all dependencies are installed, installing any missing ones."""
    from utils.system_scanner import scan_system, get_missing_packages

    print(f"{Colors.CYAN}Scanning system...{Colors.END}")
    info = scan_system()

    missing = get_missing_packages(info)
    if not missing:
        print(f"{Colors.GREEN}All dependencies already installed.{Colors.END}")
        return {}

    print(f"{Colors.YELLOW}Installing missing packages...{Colors.END}")
    return install_packages(missing)