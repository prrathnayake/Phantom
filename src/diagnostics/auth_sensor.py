"""Auth sensor collects information about authentication events and user activity.

Collects recent login attempts (success/failed), failed authentication
counts, privilege escalation events, and account lockouts.
Cross-platform using platform-specific log parsing.
"""
from typing import Dict, Any, List
import platform
import logging
from datetime import datetime, timedelta

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_windows() -> Dict[str, Any]:
    import subprocess

    last_logins: List[Dict[str, Any]] = []
    failed_logins: List[Dict[str, Any]] = []
    failed_count = 0
    lockouts: List[str] = []
    privilege_escalations: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-LocalUser | Select-Object Name,LastLogonTime,Enabled | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            import json
            try:
                users = json.loads(result.stdout)
                if isinstance(users, dict):
                    users = [users]
                for user in users:
                    if user.get("LastLogonTime"):
                        last_logins.append({
                            "user": user.get("Name", ""),
                            "time": str(user.get("LastLogonTime", "")),
                            "source": "local",
                            "success": True,
                        })
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        logger.debug(f"Get-LocalUser failed: {e}")

    try:
        cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        ps_command = (
            "Get-WinEvent -FilterHashtable @{LogName='Security'; "
            "StartTime='" + cutoff + "'} -MaxEvents 100 | "
            "Where-Object {$_.Id -in 4624,4625,4648,4672} | "
            "Select-Object TimeCreated,Id,Message | ConvertTo-Json"
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.stdout.strip():
            import json
            try:
                events = json.loads(result.stdout)
                if isinstance(events, dict):
                    events = [events]
                for event in events:
                    event_id = event.get("Id")
                    msg = event.get("Message", "")[:100] if event.get("Message") else ""
                    ts = str(event.get("TimeCreated", ""))[:19] if event.get("TimeCreated") else ""

                    if event_id == 4624:
                        last_logins.append({
                            "user": "unknown",
                            "time": ts,
                            "source": msg[:50],
                            "success": True,
                        })
                    elif event_id == 4625:
                        failed_count += 1
                        failed_logins.append({
                            "user": "unknown",
                            "time": ts,
                            "source": msg[:50],
                        })
                    elif event_id == 4672:
                        privilege_escalations.append({
                            "user": "unknown",
                            "time": ts,
                            "privileges": msg[:100],
                        })
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        logger.debug(f"Get-WinEvent failed: {e}")

    return {
        "last_logins": last_logins[:20],
        "failed_count": failed_count,
        "failed_logins": failed_logins[:20],
        "lockouts": lockouts,
        "privilege_escalations": privilege_escalations[:10],
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    import re
    from pathlib import Path

    last_logins: List[Dict[str, Any]] = []
    failed_logins: List[Dict[str, Any]] = []
    failed_count = 0
    lockouts: List[str] = []
    privilege_escalations: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(
            ["last", "-20", "-i"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 10:
                user = parts[0]
                terminal = parts[1]
                ip = parts[2] if parts[2] != "-" else "local"
                date_str = " ".join(parts[3:8])

                is_failed = "down" in line.lower() or "crash" in line.lower()

                last_logins.append({
                    "user": user,
                    "time": date_str,
                    "source": ip,
                    "success": not is_failed,
                })
    except Exception as e:
        logger.debug(f"last failed: {e}")

    log_files = [
        "/var/log/auth.log",
        "/var/log/secure",
        "/var/log/syslog",
        "/var/log/messages",
    ]

    log_file = None
    for f in log_files:
        if Path(f).exists():
            log_file = f
            break

    if log_file:
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line in lines[-500:]:
                if "Failed password" in line or "authentication failure" in line.lower():
                    failed_count += 1
                    match = re.search(r"for (invalid user )?(\S+)", line)
                    user = match.group(2) if match else "unknown"
                    match = re.search(r"from (\S+)", line)
                    source = match.group(1) if match else "unknown"
                    match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+)", line)
                    time_str = match.group(1) if match else ""
                    failed_logins.append({
                        "user": user,
                        "time": time_str,
                        "source": source,
                    })
                elif "session opened" in line and "sudo" in line:
                    match = re.search(r"(\S+)\s+session opened", line)
                    if match:
                        match_time = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+)", line)
                        privilege_escalations.append({
                            "user": match.group(1),
                            "time": match_time.group(1) if match_time else "",
                            "privileges": "sudo session",
                        })
                elif "user acct" in line and "gid" in line:
                    match = re.search(r"(\w+\s+\d+\s+\d+:\d+:\d+)", line)
                    if match:
                        privilege_escalations.append({
                            "user": "unknown",
                            "time": match.group(1),
                            "privileges": "group changed",
                        })
        except Exception as e:
            logger.debug(f"Failed to read {log_file}: {e}")

    return {
        "last_logins": last_logins[:20],
        "failed_count": failed_count,
        "failed_logins": failed_logins[:20],
        "lockouts": lockouts,
        "privilege_escalations": privilege_escalations[:10],
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    debug_logger.sensor("auth_sensor", "Collecting auth data", {})

    system = platform.system()

    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()

    debug_logger.sensor("auth_sensor", "Collected auth data", {
        "failed_count": result.get("failed_count"),
        "last_logins": len(result.get("last_logins", [])),
        "privilege_escalations": len(result.get("privilege_escalations", [])),
    })

    return result
