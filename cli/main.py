"""Phantom CLI - Command-line interface for Phantom Security Agent."""
import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

CLI_DIR = Path(__file__).parent

_IS_WINDOWS = platform.system() == "Windows"
_IS_MACOS = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"


def _docker_available() -> bool:
    """Check if Docker daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, check=False, timeout=10
        )
        return result.returncode == 0 and result.stdout.strip()
    except Exception:
        return False


def _start_docker() -> bool:
    """Attempt to start Docker if it is not running."""
    if _docker_available():
        return True

    print("Docker does not appear to be running. Attempting to start it...")

    try:
        if _IS_WINDOWS:
            possible_paths = [
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe",
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Docker" / "Docker" / "Docker Desktop.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Docker" / "Docker" / "Docker Desktop.exe",
            ]
            for docker_path in possible_paths:
                if docker_path.exists():
                    subprocess.Popen([str(docker_path)], shell=False)
                    break
            else:
                print("  Could not find Docker Desktop executable.")
                return False
        elif _IS_MACOS:
            mac_paths = [
                Path("/Applications/Docker.app/Contents/MacOS/Docker"),
                Path("/usr/local/bin/docker"),
                Path("/opt/homebrew/bin/docker"),
            ]
            for docker_path in mac_paths:
                if docker_path.exists():
                    if "MacOS" in str(docker_path):
                        subprocess.Popen([str(docker_path)], shell=False)
                    else:
                        subprocess.run(["open", "-a", "Docker"], check=False)
                    break
            else:
                print("  Could not find Docker application.")
                return False
        elif _IS_LINUX:
            result = subprocess.run(["systemctl", "is-active", "--quiet", "docker"], capture_output=True, check=False)
            if result.returncode != 0:
                result = subprocess.run(["sudo", "systemctl", "start", "docker"], capture_output=True, check=False)
                if result.returncode != 0:
                    result = subprocess.run(["sudo", "service", "docker", "start"], capture_output=True, check=False)
            if result.returncode != 0:
                print("  Failed to start Docker service. You may need to start it manually.")
                return False
        else:
            print(f"  Auto-start not implemented for {platform.system()}.")
            return False
    except Exception as exc:
        print(f"  Error starting Docker: {exc}")
        return False

    # Wait up to 60 seconds for Docker to become available
    print("  Waiting for Docker daemon...")
    for _ in range(30):
        time.sleep(2)
        if _docker_available():
            print("  Docker is now running!")
            return True

    print("  Docker did not become available in time.")
    return False


def _ensure_docker() -> bool:
    """Ensure Docker is running, attempting to start it if necessary."""
    if _docker_available():
        return True
    return _start_docker()


def main():
    parser = argparse.ArgumentParser(
        prog="agent",
        description="Phantom - Secure Monitoring Agent Harness System",
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
    parser.add_argument("--docker", action="store_true", help="Ensure Docker is running (for start/stop/status)")

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

    # Ensure Docker if requested via --docker flag
    if args.docker and args.command in ("start", "stop", "status"):
        if not _ensure_docker():
            print("Error: Docker is not running or could not be started.")
            return 1

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
Phantom - Secure Monitoring Agent Harness System

Usage: ./agent <command> [options]

Commands:
  help                Show this help message
  version             Show version information
  onboard             Initial setup and onboarding
  config              Manage configuration
  start               Start the Phantom agent
  stop                Stop the Phantom agent
  status              Show agent status
  run [diagnostic]    Run diagnostics manually
  reports             View analysis reports

Options:
  --docker            Ensure Docker is running (for start/stop/status)

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
    print("Phantom - Secure Monitoring Agent")
    print("Version: 1.0.0")
    print("Build: 2026.04")


def cmd_onboard(args):
    if args and args[0] == "check":
        return onboard_check()

    print("=== Phantom Onboarding ===\n")

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
        import flask  # noqa: F401
    except ImportError:
        issues.append("flask not installed")

    try:
        import psutil  # noqa: F401
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

    import platform as plat
    print(f"  Platform: {plat.system()} {plat.release()}")
    print(f"  Python: {sys.version.split()[0]}")

    print(f"  Working dir: {Path.cwd()}")


def check_config():
    try:
        import config
        print("  Config module: OK")
        print(f"  Log dir: {config.LOG_DIR}")
    except Exception as e:
        print(f"  Config error: {e}")


def check_dependencies():
    deps = ["flask", "psutil", "requests", "openai", "dotenv", "websockets"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"  {dep}: OK")
        except ImportError:
            print(f"  {dep}: MISSING")


def create_directories():
    import config

    dirs = [
        config.LOG_DIR,
        Path("src/agent/reports"),
        Path(".codex_memories"),
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {d}")


def setup_config():
    env_file = Path(".env")
    if not env_file.exists():
        template = CLI_DIR / ".env.template"
        if template.exists():
            import shutil
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

    key, value = args[0], " ".join(args[1:])

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
    print("Starting Phantom agent...")

    if is_running():
        print("Agent is already running!")
        return 1

    pid_file = Path("phantom.pid")
    project_root = Path(__file__).parent.parent
    devnull = open(os.devnull, "w")

    try:
        if _IS_WINDOWS:
            proc = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=project_root,
                stdout=devnull,
                stderr=devnull,
                stdin=devnull,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=project_root,
                stdout=devnull,
                stderr=devnull,
                stdin=devnull,
                start_new_session=True,
            )
    except Exception as exc:
        print(f"Failed to start agent: {exc}")
        devnull.close()
        return 1

    # Don't wait for the process; just record the PID and return.
    # Note: we intentionally do NOT close devnull here because the child
    # process inherits it. On Windows, closing it could cause errors.
    pid_file.write_text(str(proc.pid))
    print(f"Agent started with PID: {proc.pid}")
    print("Run './agent status' to check status.")

    return 0


def cmd_stop(args):
    print("Stopping Phantom agent...")

    import psutil

    ports = [5000, 8000, 8001]
    killed_any = False

    for port in ports:
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port and conn.status == "LISTEN":
                    try:
                        proc = psutil.Process(conn.pid)
                        print(f"Stopping process {conn.pid} on port {port} ({proc.name()})...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed_any = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except (psutil.AccessDenied, psutil.Error):
            pass

    pid_file = Path("phantom.pid")
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
                killed_any = True
            except psutil.NoSuchProcess:
                pass
        except ValueError:
            pass
        finally:
            if pid_file.exists():
                pid_file.unlink()

    if not killed_any:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if any("main.py" in part for part in cmdline):
                    print(f"Stopping process {proc.pid}...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if killed_any:
        print("Agent stopped.")
        return 0
    else:
        print("Agent not running.")
        return 0


def cmd_status(args):
    print("=== Phantom Status ===\n")

    if is_running():
        print("Status: RUNNING")

        pid_file = Path("phantom.pid")
        if pid_file.exists():
            try:
                pid = pid_file.read_text().strip()
                print(f"PID: {pid}")
            except Exception:
                pass

        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if any("main.py" in part for part in cmdline):
                    cpu = proc.cpu_percent(interval=0.5)
                    mem = proc.memory_info().rss / 1024 / 1024
                    print(f"CPU: {cpu:.1f}%")
                    print(f"Memory: {mem:.1f} MB")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
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

    # Normalize module name: accept both "process" and "process_sensor"
    module_name = diagnostic
    if not module_name.endswith("_sensor"):
        module_name = f"{module_name}_sensor"

    try:
        import importlib
        module = importlib.import_module(f"src.diagnostics.{module_name}")

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
        print(f"  Error: {e}")
        return 1


def cmd_reports(args):
    reports_dir = Path("src/agent/reports")

    if not reports_dir.exists():
        print("No reports found")
        return 0

    # Recurse into date subdirectories
    reports = sorted(reports_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not reports:
        print("No reports found")
        return 0

    if args and args[0] == "list":
        print("=== Reports ===\n")
        for r in reports:
            print(f"  {r.stem}")
        return 0

    if args:
        # Search by stem across all date dirs
        target_stem = args[0]
        for r in reports:
            if r.stem == target_stem:
                print(r.read_text(encoding="utf-8"))
                return 0
        print(f"Report not found: {target_stem}")
        return 1

    print(f"Found {len(reports)} reports. Use 'agent reports list' to see all.")
    print(f"Latest: {reports[0].name}")
    return 0


def is_running():
    pid_file = Path("phantom.pid")
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return False

    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
