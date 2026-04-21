"""Driver Sensor - Monitors kernel modules and drivers.

Cross-platform sensor for monitoring loaded drivers and kernel modules.
"""
from typing import Any, Dict, List
import platform
import logging

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    
    drivers = []
    unsigned = []
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Select-Object -First 50 | ForEach-Object { $_.Path }"],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        paths = result.stdout.strip().splitlines()
        unique_paths = list(set(p for p in paths if p.strip()))
        
        for path in unique_paths[:20]:
            if path and any(ext in path.lower() for ext in ['.sys', '.dll']):
                drivers.append({
                    "path": path,
                    "type": "driver" if '.sys' in path.lower() else "library"
                })
    
    except Exception as e:
        logger.debug(f"Driver collection failed: {e}")
    
    return {
        "driver_count": len(drivers),
        "unsigned_count": len(unsigned),
        "drivers": drivers[:20]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    
    modules = []
    suspicious = []
    
    suspicious_names = [
        "rootkit", "lkm", "hide", "keylog", "hook"
    ]
    
    try:
        result = subprocess.run(
            ["lsmod"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().splitlines()
        
        for line in lines[1:]:
            parts = line.split()
            if parts:
                name = parts[0]
                modules.append(name)
                
                if any(s in name.lower() for s in suspicious_names):
                    suspicious.append(name)
    
    except Exception as e:
        logger.debug(f"lsmod failed: {e}")
    
    return {
        "module_count": len(modules),
        "modules": modules[:20],
        "suspicious": suspicious
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect driver/module information.
    
    Args:
        context: Shared context
        
    Returns:
        Driver data
    """
    debug_logger.sensor("driver_sensor", "Collecting driver data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("driver_sensor", "Collected driver data", {
        "count": result.get("module_count") or result.get("driver_count", 0)
    })
    
    return result
