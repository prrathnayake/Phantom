"""Service Sensor - Monitors critical services (Windows services / systemd).

Cross-platform sensor for monitoring critical system services.
"""
from typing import Any, Dict, List
import platform
import logging

from utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    
    services = []
    running_services = []
    stopped_critical = []
    
    critical_services = [
        "wuauserv", "WinDefend", "EventLog", "W32Time",
        "Dnscache", "LanmanServer", "LanmanWorkstation"
    ]
    
    try:
        result = subprocess.run(
            ["sc", "query", "state=", "all"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        lines = result.stdout.strip().splitlines()
        current_service = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("SERVICE_NAME:"):
                if current_service:
                    services.append(current_service)
                current_service = {"name": line.split(":", 1)[1].strip()}
            elif line.startswith("STATE:") and current_service:
                state = line.split(":", 1)[1].strip().split()[0]
                current_service["state"] = state
        
        if current_service:
            services.append(current_service)
        
        for svc in services:
            if svc.get("state") == "RUNNING":
                running_services.append(svc["name"])
            elif svc.get("name", "").lower() in [s.lower() for s in critical_services]:
                stopped_critical.append(svc)
    
    except Exception as e:
        logger.debug(f"sc query failed: {e}")
    
    return {
        "total_services": len(services),
        "running_count": len(running_services),
        "stopped_critical": stopped_critical,
        "running_services": running_services[:20]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    
    services = []
    running_services = []
    failed_services = []
    
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--all", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        lines = result.stdout.strip().splitlines()
        
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                loaded = parts[1]
                active = parts[2]
                sub = parts[3] if len(parts) > 3 else ""
                
                service = {
                    "name": name,
                    "loaded": loaded,
                    "active": active,
                    "sub": sub
                }
                services.append(service)
                
                if active == "active":
                    running_services.append(name)
                elif active == "failed":
                    failed_services.append(name)
    
    except Exception as e:
        logger.debug(f"systemctl failed: {e}")
    
    return {
        "total_services": len(services),
        "running_count": len(running_services),
        "failed_count": len(failed_services),
        "failed_services": failed_services[:10],
        "running_services": running_services[:20]
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect service status information.
    
    Args:
        context: Shared context
        
    Returns:
        Service status data
    """
    debug_logger.sensor("service_sensor", "Collecting service data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("service_sensor", "Collected service data", {
        "total": result.get("total_services"),
        "running": result.get("running_count")
    })
    
    return result