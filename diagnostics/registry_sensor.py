"""Registry/Audit Sensor - Monitors Windows registry and Linux auditd.

Cross-platform sensor for security-sensitive registry keys and audit events.
"""
from typing import Any, Dict, List
import platform
import logging

from utils.debug_log import debug_logger

logger = logging.getLogger(__name__)

CRITICAL_REGISTRY_KEYS = [
    "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
    "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    "HKLM\\System\\CurrentControlSet\\Services\\LanmanServer\\Parameters",
    "HKLM\\Security\\Policy\\Accounts",
]


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    
    modified_keys = []
    new_services = []
    startup_programs = []
    
    try:
        for key in CRITICAL_REGISTRY_KEYS[:3]:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     f"Get-ItemProperty -Path 'Registry::{key}' -ErrorAction SilentlyContinue | ConvertTo-Json"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.stdout.strip():
                    import json
                    try:
                        data = json.loads(result.stdout)
                        if data:
                            startup_programs.append({
                                "key": key,
                                "entries": list(data.keys()) if isinstance(data, dict) else []
                            })
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.debug(f"Registry key {key} failed: {e}")
    
    except Exception as e:
        logger.debug(f"Registry collection failed: {e}")
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4688} -MaxEvents 20 -ErrorAction SilentlyContinue | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.stdout.strip():
            new_services = ["process_creation_events_available"]
    except Exception as e:
        logger.debug(f"Audit log collection failed: {e}")
    
    return {
        "monitored_keys": CRITICAL_REGISTRY_KEYS,
        "startup_programs": startup_programs,
        "recent_modifications": modified_keys[:10]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    from pathlib import Path
    
    audit_events = []
    sudo_usage = []
    failed_auth = []
    
    log_files = [
        "/var/log/audit/audit.log",
        "/var/log/auth.log",
        "/var/log/secure"
    ]
    
    log_file = None
    for f in log_files:
        if Path(f).exists():
            log_file = f
            break
    
    if log_file:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            for line in lines[-500:]:
                if "type=EXECVE" in line or "type=USER_CMD" in line:
                    audit_events.append(line.strip()[:100])
                elif "sudo" in line and "COMMAND" in line:
                    sudo_usage.append(line.strip()[:100])
                elif "authentication failure" in line.lower():
                    failed_auth.append(line.strip()[:100])
        except Exception as e:
            logger.debug(f"Failed to read {log_file}: {e}")
    
    return {
        "audit_events": audit_events[:20],
        "sudo_commands": sudo_usage[:20],
        "failed_auth": failed_auth[:20]
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect registry/audit information.
    
    Args:
        context: Shared context
        
    Returns:
        Registry/audit data
    """
    debug_logger.sensor("registry_sensor", "Collecting registry/audit data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("registry_sensor", "Collected registry/audit data", {})
    
    return result