"""Local CLI wrapper for Phantom Docker management.

Runs on the host machine to control and manage Phantom containers.
"""

import subprocess
import argparse
import sys
import os
from pathlib import Path

DOCKER_COMPOSE_FILE = "docker-compose.yml"
PROJECT_DIR = Path(__file__).parent


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT_DIR, check=check)


def cmd_status():
    print("\n[PHANTOM CONTAINERS]")
    try:
        result = run_cmd(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"], check=False)
        if result.stdout:
            print(result.stdout)
    except Exception as e:
        print(f"Error: {e}")


def cmd_logs(service: str = "agent", lines: int = 50):
    print(f"\n[LOGS: {service}]")
    try:
        run_cmd(["docker", "logs", "--tail", str(lines), f"phantom-{service}"], check=False)
    except Exception as e:
        print(f"Error: {e}")


def cmd_start():
    print("\n[STARTING CONTAINERS]")
    try:
        run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d"])
        print("Containers started. Use 'phantom-cli status' to check.")
    except Exception as e:
        print(f"Error: {e}")


def cmd_stop():
    print("\n[STOPPING CONTAINERS]")
    try:
        run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "stop"])
        print("Containers stopped.")
    except Exception as e:
        print(f"Error: {e}")


def cmd_restart(service: str = None):
    if service:
        print(f"\n[RESTARTING: {service}]")
        try:
            run_cmd(["docker", "restart", f"phantom-{service}"])
            print(f"{service} restarted.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\n[RESTARTING ALL CONTAINERS]")
        try:
            run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "restart"])
            print("All containers restarted.")
        except Exception as e:
            print(f"Error: {e}")


def cmd_build():
    print("\n[BUILDING CONTAINERS]")
    try:
        run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "build", "--no-cache"])
        print("Build complete.")
    except Exception as e:
        print(f"Error: {e}")


def cmd_ps():
    print("\n[RUNNING CONTAINERS]")
    try:
        run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "ps"], check=False)
    except Exception as e:
        print(f"Error: {e}")


def cmd_exec(service: str, command: str):
    print(f"\n[EXEC: {service}] $ {command}")
    try:
        run_cmd(["docker", "exec", "-it", f"phantom-{service}", "sh", "-c", command], check=False)
    except Exception as e:
        print(f"Error: {e}")


def cmd_clean():
    print("\n[CLEANING CONTAINERS/VOLUMES]")
    confirm = input("This will remove all containers and volumes. Continue? (y/N): ")
    if confirm.lower() == "y":
        try:
            run_cmd(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down", "-v"], check=False)
            print("Cleaned.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Cancelled.")


def cmd_logs_follow(service: str = "agent"):
    print(f"\n[FOLLOWING LOGS: {service}] (Ctrl+C to exit)")
    try:
        run_cmd(["docker", "logs", "-f", "--tail", "50", f"phantom-{service}"], check=False)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Phantom Docker Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status              Show container status
  start              Start all containers
  stop               Stop all containers
  restart [service]  Restart all or specific service
  logs [service]     Show logs (default: agent)
  logs-follow        Follow logs in real-time
  exec service cmd   Execute command in container
  ps                Show running services
  build             Rebuild containers
  clean             Remove containers and volumes
        """
    )
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Command arguments")

    args = parser.parse_args()

    if args.command == "status" or args.command == "st":
        cmd_status()
    elif args.command == "logs" or args.command == "log":
        service = args.args[0] if args.args else "agent"
        cmd_logs(service)
    elif args.command == "logs-follow":
        service = args.args[0] if args.args else "agent"
        cmd_logs_follow(service)
    elif args.command == "start" or args.command == "up":
        cmd_start()
    elif args.command == "stop" or args.command == "down":
        cmd_stop()
    elif args.command == "restart" or args.command == "re":
        service = args.args[0] if args.args else None
        cmd_restart(service)
    elif args.command == "ps":
        cmd_ps()
    elif args.command == "exec":
        if len(args.args) < 2:
            print("Usage: phantom-cli exec <service> <command>")
            return
        cmd_exec(args.args[0], " ".join(args.args[1:]))
    elif args.command == "build":
        cmd_build()
    elif args.command == "clean":
        cmd_clean()
    elif args.command == "help" or args.command == "-h" or args.command == "--help":
        parser.print_help()
    elif args.command is None:
        cmd_status()
    else:
        print(f"Unknown command: {args.command}")
        print("Run 'phantom-cli help' for available commands")


if __name__ == "__main__":
    main()