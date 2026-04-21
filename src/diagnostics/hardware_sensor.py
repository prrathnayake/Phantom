"""Hardware Sensor - Monitors USB devices and hardware changes.

Cross-platform sensor for monitoring hardware connections.
"""
from typing import Any, Dict, List
import platform
import logging

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    
    usb_devices = []
    new_devices = []
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice -Class 'USB' -ErrorAction SilentlyContinue | Select-Object Status, FriendlyName, InstanceId | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.stdout.strip():
            import json
            try:
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    data = [data]
                
                for device in data:
                    name = device.get("FriendlyName", "Unknown")
                    status = device.get("Status", "Unknown")
                    instance = device.get("InstanceId", "")
                    
                    if status.lower() == "error":
                        new_devices.append({"name": name, "status": status})
                    
                    usb_devices.append({"name": name, "status": status})
            except json.JSONDecodeError:
                pass
    
    except Exception as e:
        logger.debug(f"USB collection failed: {e}")
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-WinEvent -FilterHashtable @{LogName='System'; ID=400,410} -MaxEvents 20 -ErrorAction SilentlyContinue | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
    except Exception as e:
        logger.debug(f"Hardware event log failed: {e}")
    
    return {
        "usb_count": len(usb_devices),
        "new_devices": new_devices,
        "devices": usb_devices[:20]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    from pathlib import Path
    
    devices = []
    new_devices = []
    
    try:
        result = subprocess.run(
            ["lsusb"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().splitlines()
        
        for line in lines:
            parts = line.split(":", 1)
            if len(parts) == 2:
                device_id, name = parts[0].strip(), parts[1].strip()
                devices.append({"id": device_id, "name": name})
    
    except Exception as e:
        logger.debug(f"lsusb failed: {e}")
    
    dmesg_file = "/var/log/dmesg"
    if Path(dmesg_file).exists():
        try:
            with open(dmesg_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            for line in lines[-50:]:
                if "usb" in line.lower() and "connected" in line.lower():
                    new_devices.append(line.strip()[:100])
        except Exception as e:
            logger.debug(f"dmesg read failed: {e}")
    
    return {
        "device_count": len(devices),
        "new_devices": new_devices[:10],
        "devices": devices[:20]
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect hardware information.
    
    Args:
        context: Shared context
        
    Returns:
        Hardware data
    """
    debug_logger.sensor("hardware_sensor", "Collecting hardware data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("hardware_sensor", "Collected hardware data", {
        "count": result.get("usb_count") or result.get("device_count", 0)
    })
    
    return result
