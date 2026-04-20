"""Monica CLI - Command-line interface for Monica Security Agent."""
import sys
import os
import argparse
from pathlib import Path

CLI_DIR = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(
        prog="agent",
        description="Monica - Secure Monitoring Agent Harness System",
        add_help=False
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["help", "onboard", "config", "start", "stop", "status", "run", "reports", "version"],
        help="Command to execute"
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for command")
    parser.add_argument("-h", "--help", dest="show_help", action="store_true", help="Show help")

    args = parser.parse_args()

    if args.show_help or not args.command:
        show_help()
        return 0

    if args.command == "help":
        show_help()
        return 0

    if args.command == "version":
        show_version()
        return 0

    if args.command == "onboard":
        return cmd_onboard(args.args)

    if args.command == "config":
        return cmd_config(args.args)

    if args.command == "start":
        return cmd_start(args.args)

    if args.command == "stop":
        return cmd_stop(args.args)

    if args.command == "status":
        return cmd_status(args.args)

    if args.command == "run":
        return cmd_run(args.args)

    if args.command == "reports":
        return cmd_reports(args.args)

    show_help()
    return 1


def show_help():
    print("""
Monica - Secure Monitoring Agent Harness System

Usage: ./agent <command> [options]

Commands:
  help                Show this help message
  version             Show version information
  onboard             Initial setup and onboarding
  config              Manage configuration
  start               Start the Monica agent
  stop                Stop the Monica agent
  status              Show agent status
  run [diagnostic]    Run diagnostics manually
  reports             View analysis reports

Examples:
  ./agent help
  ./agent onboard
  ./agent config list
  ./agent start
  ./agent status
  ./agent run process_sensor
  ./agent reports

For more information, visit the documentation.
""")


def show_version():
    print("Monica - Secure Monitoring Agent")
    print("Version: 1.0.0")
    print("Build: 2026.04")


def cmd_onboard(args):
    if args and args[0] == "check":
        return onboard_check()

    print("=== Monica Onboarding ===\n")

    print("1. Checking environment...")
    check_environment()

    print("\n2. Checking configuration...")
    check_config()

    print("\n3. Checking dependencies...")
    check_dependencies()

    print("\n4. Creating required directories...")
    create_directories()

    print("\n5. Setting up configuration...")
    setup_config()

    print("\n=== Onboarding Complete ===")
    print("Run './agent start' to start the agent.")
    print("Run './agent config list' to view configuration.")

    return 0


def onboard_check():
    issues = []

    if not os.environ.get("OPENROUTER_API_KEY"):
        issues.append("OPENROUTER_API_KEY not set")

    try:
        import flask
    except ImportError:
        issues.append("flask not installed")

    try:
        import psutil
    except ImportError:
        issues.append("psutil not installed")

    if issues:
        print("Onboarding issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All checks passed!")
        return 0


def check_environment():
    print("  Environment: OK")

    import platform
    print(f"  Platform: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")

    from pathlib import Path
    print(f"  Working dir: {Path.cwd()}")


def check_config():
    try:
        import config
        print("  Config module: OK")
        print(f"  Log dir: {config.LOG_DIR}")
    except Exception as e:
        print(f"  Config error: {e}")


def check_dependencies():
    deps = ["flask", "psutil", "requests", "openai", "python-dotenv", "websockets"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"  {dep}: OK")
        except ImportError:
            print(f"  {dep}: MISSING")


def create_directories():
    from pathlib import Path
    import config

    dirs = [
        config.LOG_DIR,
        Path("central_agent/reports"),
        Path(".codex_memories"),
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {d}")


def setup_config():
    from pathlib import Path
    import shutil

    env_file = Path(".env")
    if not env_file.exists():
        template = Path(CLI_DIR.parent, "cli", ".env.template")
        if template.exists():
            shutil.copy(template, env_file)
            print(f"  Created .env from template")
        else:
            print(f"  .env not found (create manually)")
    else:
        print(f"  .env already exists")


def cmd_config(args):
    if not args or args[0] == "list":
        return config_list(args)

    if args[0] == "get":
        return config_get(args[1:])

    if args[0] == "set":
        return config_set(args[1:])

    if args[0] == "show":
        return config_show()

    print("Usage: agent config [list|get <key>|set <key> <value>|show]")
    return 1


def config_list(args):
    import config

    print("=== Configuration ===\n")

    print("Polling Intervals:")
    for key, value in config.POLL_INTERVALS.items():
        print(f"  {key}: {value}s")

    print("\nDetection Thresholds:")
    for key, value in config.DETECTION_THRESHOLDS.items():
        print(f"  {key}: {value}")

    print("\nIntegration Status:")
    print(f"  Slack: {'configured' if config.SLACK_WEBHOOK_URL else 'not configured'}")
    print(f"  Teams: {'configured' if config.TEAMS_WEBHOOK_URL else 'not configured'}")
    print(f"  PagerDuty: {'configured' if config.PAGERDUTY_KEY else 'not configured'}")

    print(f"\nAPI Key: {'set' if config.OPENROUTER_API_KEY else 'NOT SET'}")

    return 0


def config_get(args):
    if not args:
        print("Usage: agent config get <key>")
        return 1

    key = args[0].upper()
    import config

    if hasattr(config, key):
        value = getattr(config, key)
        print(f"{key} = {value}")
        return 0
    else:
        print(f"Unknown config key: {key}")
        return 1


def config_set(args):
    if len(args) < 2:
        print("Usage: agent config set <key> <value>")
        return 1

    key, value = args[0], " ".join(args[1])

    env_file = Path(".env")
    if not env_file.exists():
        env_file.touch()

    lines = env_file.read_text().splitlines() if env_file.exists() else []
    updated = False

    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_file.write_text("\n".join(lines) + "\n")
    print(f"Set {key}={value}")
    print("Note: Restart agent for changes to take effect.")

    return 0


def config_show():
    import config as cfg

    print("=== Full Configuration ===\n")

    attrs = [a for a in dir(cfg) if not a.startswith("_")]
    for attr in attrs:
        if attr.isupper():
            val = getattr(cfg, attr)
            if not callable(val):
                print(f"{attr}: {val}")

    return 0


def cmd_start(args):
    print("Starting Monica agent...")

    if is_running():
        print("Agent is already running!")
        return 1

    import subprocess
    import sys

    pid_file = Path("monica.pid")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )

    pid_file.write_text(str(proc.pid))
    print(f"Agent started with PID: {proc.pid}")
    print("Run './agent status' to check status.")

    return 0


def cmd_stop(args):
    print("Stopping Monica agent...")

    import psutil

    ports = [5000, 8000, 8001]
    killed_any = False

    for port in ports:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == "LISTEN":
                try:
                    proc = psutil.Process(conn.pid)
                    print(f"Killing process {conn.pid} on port {port} ({proc.name()})...")
                    proc.kill()
                    killed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    pid_file = Path("monica.pid")
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            proc = psutil.Process(pid)
            proc.kill()
            killed_any = True
        except psutil.NoSuchProcess:
            pass
        pid_file.unlink()

    if not killed_any:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if "main.py" in " ".join(cmdline):
                    print(f"Stopping process {proc.pid}...")
                    proc.kill()
                    killed_any = True
            except:
                pass

    if killed_any:
        print("Agent stopped.")
        return 0
    else:
        print("Agent not running.")
        return 0


def cmd_status(args):
    print("=== Monica Status ===\n")

    if is_running():
        print("Status: RUNNING")

        pid_file = Path("monica.pid")
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            print(f"PID: {pid}")

        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if "main.py" in " ".join(cmdline):
                    cpu = proc.cpu_percent(interval=0.5)
                    mem = proc.memory_info().rss / 1024 / 1024
                    print(f"CPU: {cpu:.1f}%")
                    print(f"Memory: {mem:.1f} MB")
                    break
            except:
                pass
    else:
        print("Status: STOPPED")

    print("\nServices:")
    print("  HTTP API:    http://127.0.0.1:8000")
    print("  WebSocket:  ws://127.0.0.1:8001")
    print("  Dashboard:  http://127.0.0.1:5000")

    import config
    print(f"\nDiagnostics: {len(config.POLL_INTERVALS)} configured")

    return 0


def cmd_run(args):
    if not args:
        print("Usage: agent run <diagnostic_name>")
        print("\nAvailable diagnostics:")
        import config
        for name in config.POLL_INTERVALS.keys():
            print(f"  {name}")
        return 1

    diagnostic = args[0]

    print(f"Running diagnostic: {diagnostic}...")

    module_name = diagnostic.replace("_sensor", "")
    try:
        import importlib
        module = importlib.import_module(f"diagnostics.{module_name}_sensor")

        if hasattr(module, "collect"):
            result = module.collect()
            print(f"\nResults:")
            for key, value in result.items():
                print(f"  {key}: {value}")
            return 0
        else:
            print("Diagnostic module has no collect() function")
            return 1
    except ImportError as e:
        print(f"Diagnostic not found: {diagnostic}")
        return 1


def cmd_reports(args):
    from pathlib import Path

    reports_dir = Path("central_agent/reports")

    if not reports_dir.exists():
        print("No reports found")
        return 0

    reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not reports:
        print("No reports found")
        return 0

    if args and args[0] == "list":
        print("=== Reports ===\n")
        for r in reports:
            print(f"  {r.stem}")
        return 0

    if args:
        report_file = reports_dir / f"{args[0]}.md"
        if report_file.exists():
            print(report_file.read_text())
            return 0
        else:
            print(f"Report not found: {args[0]}")
            return 1

    print(f"Found {len(reports)} reports. Use 'agent reports list' to see all.")
    print(f"Latest: {reports[0].name}")
    return 0


def is_running():
    pid_file = Path("monica.pid")
    if not pid_file.exists():
        return False

    pid = int(pid_file.read_text().strip())

    try:
        import psutil
        return psutil.pid_exists(pid)
    except:
        return False


if __name__ == "__main__":
    sys.exit(main())
