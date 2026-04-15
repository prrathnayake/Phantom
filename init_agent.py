"""Initialization CLI for Monica - the security monitoring agent.

Usage:
    python init_agent.py scan       - Scan system for OS and requirements
    python init_agent.py install    - Install missing dependencies
    python init_agent.py check     - Run full check (scan + install)
    python init_agent.py status     - Show current status
    python init_agent.py -h, --help - Show this help
"""
import sys
import os
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def cmd_scan(args) -> int:
    """Scan system and display info."""
    from utils.system_scanner import scan_system, format_system_info

    print(f"\n{Colors.CYAN}Scanning system...{Colors.END}\n")
    info = scan_system()
    print(format_system_info(info))
    return 0


def cmd_install(args) -> int:
    """Install missing dependencies."""
    from utils.system_scanner import scan_system, get_missing_packages
    from utils.installer import install_packages

    print(f"\n{Colors.CYAN}Scanning for missing packages...{Colors.END}\n")
    info = scan_system()
    missing = get_missing_packages(info)

    if not missing:
        print(f"{Colors.GREEN}All dependencies already installed.{Colors.END}")
        return 0

    print(f"\n{Colors.YELLOW}Missing packages: {', '.join(missing)}{Colors.END}\n")
    results = install_packages(missing, upgrade=args.upgrade)

    failed = [p for p, success in results.items() if not success]
    if failed:
        print(f"\n{Colors.RED}Failed to install: {', '.join(failed)}{Colors.END}")
        return 1

    print(f"\n{Colors.GREEN}All packages installed successfully!{Colors.END}")
    return 0


def cmd_check(args) -> int:
    """Run full check: scan and install."""
    from utils.system_scanner import scan_system, format_system_info, get_missing_packages
    from utils.installer import install_packages

    print(f"\n{Colors.CYAN}=== SYSTEM CHECK ==={Colors.END}\n")
    info = scan_system()
    print(format_system_info(info))

    missing = get_missing_packages(info)
    if not missing:
        print(f"\n{Colors.GREEN}All dependencies are satisfied.{Colors.END}")
        return 0

    results = install_packages(missing, upgrade=args.upgrade)

    failed = [p for p, success in results.items() if not success]
    if failed:
        print(f"\n{Colors.RED}Installation failed for: {', '.join(failed)}{Colors.END}")
        return 1

    print(f"\n{Colors.GREEN}System ready for agent execution!{Colors.END}")
    return 0


def cmd_status(args) -> int:
    """Show current agent status."""
    from utils.system_scanner import scan_system, format_system_info, get_missing_packages
    from pathlib import Path

    print(f"\n{Colors.CYAN}=== AGENT STATUS ==={Colors.END}\n")
    info = scan_system()
    print(format_system_info(info))

    logs_dir = SCRIPT_DIR / ".logs"
    logs_exist = logs_dir.is_dir()
    print(f"\n{Colors.BOLD}Agent Directories:{Colors.END}")
    print(f"  Logs directory: {logs_dir} ({Colors.GREEN if logs_exist else Colors.RED}{'exists' if logs_exist else 'missing'}{Colors.END})")

    env_file = SCRIPT_DIR / ".env"
    has_env = env_file.is_file()
    print(f"  .env file: {env_file} ({Colors.GREEN if has_env else Colors.YELLOW}{'exists' if has_env else 'not found'}{Colors.END})")

    missing = get_missing_packages(info)
    if missing:
        print(f"\n{Colors.RED}Warning: Missing packages - {', '.join(missing)}{Colors.END}")
        return 1
    else:
        print(f"\n{Colors.GREEN}Agent status: READY{Colors.END}")
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize and configure the monitoring agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scan_parser = subparsers.add_parser("scan", help="Scan system for OS and requirements")
    scan_parser.set_defaults(func=cmd_scan)

    install_parser = subparsers.add_parser("install", help="Install missing dependencies")
    install_parser.add_argument("--upgrade", "-u", action="store_true", help="Upgrade existing packages")
    install_parser.set_defaults(func=cmd_install)

    check_parser = subparsers.add_parser("check", help="Run full system check")
    check_parser.add_argument("--upgrade", "-u", action="store_true", help="Upgrade existing packages")
    check_parser.add_argument("--check", action="store_true", help="Only check, don't install")
    check_parser.set_defaults(func=cmd_check)

    status_parser = subparsers.add_parser("status", help="Show current agent status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())