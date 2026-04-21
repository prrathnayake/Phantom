"""Disk I/O sensor collects information about disk usage and I/O operations.

Collects disk space usage per volume/drive, I/O read/write statistics,
and identifies potential I/O bottlenecks.
Cross-platform using psutil with fallback to df/du/wmic.
"""
from typing import Dict, Any, List
import platform
import logging
import os

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_with_psutil() -> Dict[str, Any]:
    import psutil
    disks: List[Dict[str, Any]] = []
    io_stats: List[Dict[str, Any]] = []

    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({
                "device": partition.device,
                "mount": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent_used": round(usage.percent, 2),
            })
        except (PermissionError, OSError):
            continue

    disk_io = psutil.disk_io_counters()
    if disk_io:
        io_stats.append({
            "device": "total",
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_time_ms": disk_io.read_time,
            "write_time_ms": disk_io.write_time,
        })

    per_disk_io = psutil.disk_io_counters(perdisk=True)
    for device, counters in per_disk_io.items():
        io_stats.append({
            "device": device,
            "read_bytes": counters.read_bytes,
            "write_bytes": counters.write_bytes,
            "read_count": counters.read_count,
            "write_count": counters.write_count,
            "read_time_ms": counters.read_time,
            "write_time_ms": counters.write_time,
        })

    return {
        "disks": disks,
        "io_stats": io_stats,
    }


def _collect_windows() -> Dict[str, Any]:
    import subprocess

    disks: List[Dict[str, Any]] = []
    io_stats: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(
            ["wmic", "logicaldisk", "get", "DeviceID,Size,FreeSpace,FileSystem"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 3:
                device = parts[0]
                if len(parts) >= 4:
                    free_gb = int(parts[1]) / (1024 ** 3) if parts[1].isdigit() else 0
                    total_gb = int(parts[2]) / (1024 ** 3) if parts[2].isdigit() else 0
                    fs = parts[3]
                else:
                    continue
                used_gb = total_gb - free_gb
                percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
                disks.append({
                    "device": device,
                    "mount": device,
                    "fstype": fs,
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_used": round(percent, 2),
                })
    except Exception as e:
        logger.debug(f"wmic failed: {e}")

    return {
        "disks": disks,
        "io_stats": io_stats,
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess

    disks: List[Dict[str, Any]] = []
    io_stats: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(["df", "-BG"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    device = parts[0]
                    total_gb = int(parts[1].replace("G", ""))
                    used_gb = int(parts[2].replace("G", ""))
                    free_gb = int(parts[3].replace("G", ""))
                    percent = int(parts[4].replace("%", ""))
                    mount = parts[5]

                    if not device.startswith("/dev/"):
                        continue

                    disks.append({
                        "device": device,
                        "mount": mount,
                        "fstype": "unknown",
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent_used": percent,
                    })
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        logger.debug(f"df failed: {e}")

    try:
        result = subprocess.run(["df", "-i"], capture_output=True, text=True)
    except Exception:
        pass

    return {
        "disks": disks,
        "io_stats": io_stats,
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    debug_logger.sensor("disk_io_sensor", "Collecting disk I/O data", {})

    system = platform.system()

    try:
        import psutil
        result = _collect_with_psutil()
        debug_logger.sensor("disk_io_sensor", "Collected with psutil", {
            "disk_count": len(result.get("disks", [])),
        })
        return result
    except ImportError:
        logger.debug("psutil not available; falling back to system commands")
        if system == "Windows":
            result = _collect_windows()
        else:
            result = _collect_linux()
        debug_logger.sensor("disk_io_sensor", "Collected with system commands", {
            "disk_count": len(result.get("disks", [])),
        })
        return result
