"""CLI Management Interface for Phantom System.

Provides interactive command-line control for:
- Container management (start, stop, restart, logs, status)
- System diagnostics and monitoring
- Data query and inspection
- Configuration management
"""

import os
import sys
import json
import time
import signal
import argparse
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timedelta

try:
    import click
except ImportError:
    click = None

try:
    import redis
except ImportError:
    redis = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None


COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "white": "\033[97m",
}


def cprint(text: str, color: str = "white") -> None:
    color_code = COLORS.get(color, COLORS["white"])
    print(f"{color_code}{text}{COLORS['reset']}")


class PhantomCLI:
    def __init__(self):
        self.redis_client = None
        self.db_conn = None
        self.api_url = os.environ.get("AGENT_API_URL", "http://agent:8000")
        self.log_dir = Path(os.environ.get("AGENT_LOG_DIR", "/app/.logs"))
        
    def connect_redis(self) -> bool:
        if redis is None:
            cprint("redis package not installed", "red")
            return False
        try:
            host = os.environ.get("REDIS_HOST", "redis")
            port = int(os.environ.get("REDIS_PORT", "6379"))
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            self.redis_client.ping()
            return True
        except Exception as e:
            cprint(f"Redis connection failed: {e}", "red")
            return False

    def connect_db(self) -> bool:
        if psycopg2 is None:
            cprint("psycopg2 package not installed", "red")
            return False
        try:
            host = os.environ.get("POSTGRES_HOST", "postgres")
            port = os.environ.get("POSTGRES_PORT", "5432")
            db = os.environ.get("POSTGRES_DB", "phantom")
            user = os.environ.get("POSTGRES_USER", "phantom")
            password = os.environ.get("POSTGRES_PASSWORD", "phantom")
            self.db_conn = psycopg2.connect(
                host=host, port=port, database=db, user=user, password=password
            )
            return True
        except Exception as e:
            cprint(f"PostgreSQL connection failed: {e}", "red")
            return False

    def get_container_status(self) -> dict[str, Any]:
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
                capture_output=True, text=True, timeout=10
            )
            containers = {}
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        containers[parts[0]] = {
                            "status": parts[1],
                            "ports": parts[2] if len(parts) > 2 else ""
                        }
            return containers
        except Exception as e:
            return {"error": str(e)}

    def show_status(self) -> None:
        cprint("\n=== PHANTOM SYSTEM STATUS ===\n", "bold")
        
        containers = self.get_container_status()
        if "error" in containers:
            cprint(f"Docker error: {containers['error']}", "red")
        else:
            cprint("Containers:", "cyan")
            for name, info in containers.items():
                status_color = "green" if "Up" in info.get("status", "") else "red"
                cprint(f"  {name:20s} ", "white", end="")
                cprint(f"{info.get('status', 'unknown')}", status_color)
        
        if self.connect_redis():
            try:
                info = self.redis_client.info("memory")
                cprint("\nRedis:", "cyan")
                cprint(f"  Memory: {info.get('used_memory_human', 'N/A')}")
                cprint(f"  Keys: {self.redis_client.dbsize()}")
            except:
                pass
        
        if self.connect_db():
            try:
                cur = self.db_conn.cursor()
                cur.execute("SELECT COUNT(*) FROM events")
                count = cur.fetchone()[0]
                cprint("\nPostgreSQL:", "cyan")
                cprint(f"  Events: {count}")
                cur.close()
            except:
                pass
        
        log_file = self.log_dir / "events.log"
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                cprint(f"\nLogs: {len(lines)} events", "cyan")
            except:
                pass
        
        cprint("")

    def show_logs(self, container: str = "agent", lines: int = 50) -> None:
        import subprocess
        try:
            subprocess.run(
                ["docker", "logs", "--tail", str(lines), container],
            )
        except Exception as e:
            cprint(f"Error fetching logs: {e}", "red")

    def query_redis(self, pattern: str = "*") -> None:
        if not self.connect_redis():
            return
        
        cprint(f"Redis keys matching '{pattern}':", "cyan")
        try:
            keys = self.redis_client.keys(pattern)
            for key in keys[:20]:
                key_type = self.redis_client.type(key)
                if key_type == "string":
                    value = self.redis_client.get(key)
                    cprint(f"  {key}: {value[:100]}", "white")
                elif key_type == "list":
                    value = self.redis_client.lrange(key, 0, 5)
                    cprint(f"  {key}: {value}", "white")
                elif key_type == "hash":
                    value = self.redis_client.hgetall(key)
                    cprint(f"  {key}: {value}", "white")
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def query_db(self, table: str = "events", limit: int = 10) -> None:
        if not self.connect_db():
            return
        
        try:
            cur = self.db_conn.cursor()
            cur.execute(f"SELECT * FROM {table} LIMIT {limit}")
            columns = [desc[0] for desc in cur.description]
            cprint(f"Table: {table}", "cyan")
            cprint(f"Columns: {columns}", "white")
            
            for row in cur.fetchall():
                print(row)
            
            cur.close()
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def run_diagnostic(self, name: str = "all") -> None:
        import subprocess
        cprint(f"\nRunning diagnostic: {name}...", "cyan")
        
        try:
            result = subprocess.run(
                ["docker", "exec", "phantom-agent", "python", "-m", "diagnostics", name],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                cprint(result.stdout, "white")
            else:
                cprint(f"Error: {result.stderr}", "red")
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def exec_command(self, container: str, command: str) -> None:
        import subprocess
        cprint(f"Executing in {container}: {command}", "cyan")
        
        try:
            result = subprocess.run(
                ["docker", "exec", container, "sh", "-c", command],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                cprint(result.stdout, "white")
            if result.stderr:
                cprint(result.stderr, "red")
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def restart_container(self, container: str) -> None:
        import subprocess
        cprint(f"Restarting {container}...", "yellow")
        
        try:
            subprocess.run(["docker", "restart", container], check=True)
            cprint(f"{container} restarted", "green")
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def stop_container(self, container: str) -> None:
        import subprocess
        cprint(f"Stopping {container}...", "yellow")
        
        try:
            subprocess.run(["docker", "stop", container], check=True)
            cprint(f"{container} stopped", "green")
        except Exception as e:
            cprint(f"Error: {e}", "red")

    def start_container(self, container: str) -> None:
        import subprocess
        cprint(f"Starting {container}...", "cyan")
        
        try:
            subprocess.run(["docker", "start", container], check=True)
            cprint(f"{container} started", "green")
        except Exception as e:
            cprint(f"Error: {e}", "red")


def ansi_main():
    parser = argparse.ArgumentParser(
        description="Phantom CLI Management Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  phantom-cli status              Show system status
  phantom-cli logs agent       Show agent logs
  phantom-cli redis keys "*"   Query Redis keys
  phantom-cli db events        Query events table
  phantom-cli restart agent   Restart agent container
  phantom-cli exec agent "ls -la" Run command in container
        """
    )
    parser.add_argument("command", nargs="?", default="status", help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of log lines")
    
    args = parser.parse_args()
    
    cli = PhantomCLI()
    
    if args.command == "status" or args.command == "st":
        cli.show_status()
    
    elif args.command == "logs":
        container = args.args[0] if args.args else "agent"
        cli.show_logs(container, args.lines)
    
    elif args.command == "redis" or args.command == "r":
        pattern = args.args[0] if args.args else "*"
        cli.query_redis(pattern)
    
    elif args.command == "db":
        table = args.args[0] if args.args else "events"
        cli.query_db(table)
    
    elif args.command == "diag":
        name = args.args[0] if args.args else "all"
        cli.run_diagnostic(name)
    
    elif args.command == "exec":
        if len(args.args) < 2:
            print("Usage: phantom-cli exec <container> <command>")
            return
        cli.exec_command(args.args[0], " ".join(args.args[1:]))
    
    elif args.command == "restart":
        if not args.args:
            print("Usage: phantom-cli restart <container>")
            return
        cli.restart_container(args.args[0])
    
    elif args.command == "stop":
        if not args.args:
            print("Usage: phantom-cli stop <container>")
            return
        cli.stop_container(args.args[0])
    
    elif args.command == "start":
        if not args.args:
            print("Usage: phantom-cli start <container>")
            return
        cli.start_container(args.args[0])
    
    elif args.command == "help" or args.command == "?":
        parser.print_help()
    
    else:
        cprint(f"Unknown command: {args.command}", "red")
        cprint("Run 'phantom-cli help' for available commands", "yellow")


if __name__ == "__main__":
    ansi_main()