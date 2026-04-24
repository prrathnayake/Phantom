"""Memory sensor collects information about system RAM and swap usage.

Collects total/used/available RAM, swap usage, top memory-consuming
processes, and memory pressure indicators.
Cross-platform using psutil with fallback to system commands.
"""
from typing import Dict, Any, List
import platform
import logging

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_with_psutil() -> Dict[str, Any]:
    import psutil
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    processes: List[Dict[str, Any]] = []
    for proc in psutil.process_iter(attrs=["pid", "name", "username", "memory_percent", "memory_info"]):
        try:
            info = proc.info
            mem_info = info.get("memory_info")
            memory_mb = getattr(mem_info, "rss", 0) / (1024 * 1024) if mem_info else 0
            processes.append({
                "pid": info.get("pid"),
                "name": info.get("name"),
                "username": info.get("username"),
                "memory_percent": info.get("memory_percent", 0),
                "memory_mb": round(memory_mb, 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: p.get("memory_mb", 0), reverse=True)
    top_processes = processes[:10]

    return {
        "total_mb": int(vm.total / (1024 * 1024)),
        "available_mb": int(vm.available / (1024 * 1024)),
        "used_mb": int(vm.used / (1024 * 1024)),
        "free_mb": int(vm.free / (1024 * 1024)),
        "percent_used": round(vm.percent, 2),
        "swap_total_mb": int(swap.total / (1024 * 1024)),
        "swap_used_mb": int(swap.used / (1024 * 1024)),
        "swap_free_mb": int(swap.free / (1024 * 1024)),
        "swap_percent": round(swap.percent, 2),
        "swap_in": swap.sin,
        "swap_out": swap.sout,
        "top_processes": top_processes,
    }


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    import re

    top_processes: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(
            ["wmic", "process", "get", "ProcessId,Name,WorkingSetSize"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    pid = int(parts[-2])
                    working_set = int(parts[-1])
                    memory_kb = working_set / 1024
                    memory_mb = memory_kb / 1024
                    name = " ".join(parts[:-2])
                    top_processes.append({
                        "pid": pid,
                        "name": name,
                        "username": "N/A",
                        "memory_percent": 0,
                        "memory_mb": round(memory_mb, 2),
                    })
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        logger.debug(f"wmic failed: {e}")

    top_processes.sort(key=lambda p: p.get("memory_mb", 0), reverse=True)
    top_processes = top_processes[:10]

    mem_info = {}
    try:
        result = subprocess.run(["systeminfo"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Total Physical Memory:" in line:
                match = re.search(r"(\d[\d,\.]*)\s+MB", line)
                if match:
                    mem_info["total_mb"] = int(match.group(1).replace(",", ""))
            elif "Available Physical Memory:" in line:
                match = re.search(r"(\d[\d,\.]*)\s+MB", line)
                if match:
                    mem_info["available_mb"] = int(match.group(1).replace(",", ""))
    except Exception as e:
        logger.debug(f"systeminfo failed: {e}")

    total = mem_info.get("total_mb", 0)
    avail = mem_info.get("available_mb", 0)
    used = total - avail
    percent = (used / total * 100) if total > 0 else 0

    return {
        "total_mb": mem_info.get("total_mb", 0),
        "available_mb": mem_info.get("available_mb", 0),
        "used_mb": used,
        "free_mb": avail,
        "percent_used": round(percent, 2),
        "swap_total_mb": 0,
        "swap_used_mb": 0,
        "swap_free_mb": 0,
        "swap_percent": 0,
        "swap_in": 0,
        "swap_out": 0,
        "top_processes": top_processes,
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess

    top_processes: List[Dict[str, Any]] = []

    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,user,rss,comm", "--no-headers", "-m"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().splitlines()[:20]
        for line in lines:
            parts = line.split(None, 3)
            if len(parts) >= 4:
                try:
                    pid = int(parts[0])
                    user = parts[1]
                    rss_kb = int(parts[2])
                    name = parts[3]
                    memory_mb = rss_kb / 1024
                    top_processes.append({
                        "pid": pid,
                        "name": name,
                        "username": user,
                        "memory_percent": 0,
                        "memory_mb": round(memory_mb, 2),
                    })
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        logger.debug(f"ps failed: {e}")

    top_processes.sort(key=lambda p: p.get("memory_mb", 0), reverse=True)
    top_processes = top_processes[:10]

    mem_info = {"total_mb": 0, "available_mb": 0, "free_mb": 0}

    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 3:
                    mem_info["total_mb"] = int(parts[1])
                    mem_info["free_mb"] = int(parts[3])
                    mem_info["available_mb"] = int(parts[3])
            elif line.startswith("Swap:"):
                parts = line.split()
                if len(parts) >= 3:
                    mem_info["swap_total_mb"] = int(parts[1])
                    mem_info["swap_used_mb"] = int(parts[2])
                    mem_info["swap_free_mb"] = int(parts[3])
    except Exception as e:
        logger.debug(f"free failed: {e}")

    total = mem_info.get("total_mb", 0)
    avail = mem_info.get("available_mb", 0)
    used = total - avail
    percent = (used / total * 100) if total > 0 else 0

    return {
        "total_mb": mem_info.get("total_mb", 0),
        "available_mb": mem_info.get("available_mb", 0),
        "used_mb": used,
        "free_mb": mem_info.get("free_mb", 0),
        "percent_used": round(percent, 2),
        "swap_total_mb": mem_info.get("swap_total_mb", 0),
        "swap_used_mb": mem_info.get("swap_used_mb", 0),
        "swap_free_mb": mem_info.get("swap_free_mb", 0),
        "swap_percent": round((mem_info.get("swap_used_mb", 0) / mem_info.get("swap_total_mb", 1)) * 100, 2),
        "swap_in": 0,
        "swap_out": 0,
        "top_processes": top_processes,
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    debug_logger.sensor("memory_sensor", "Collecting memory data", {})

    system = platform.system()

    try:
        import psutil
        result = _collect_with_psutil()
        debug_logger.sensor("memory_sensor", "Collected with psutil", {
            "percent_used": result.get("percent_used"),
            "swap_percent": result.get("swap_percent"),
        })
        return result
    except ImportError:
        logger.debug("psutil not available; falling back to system commands")
        if system == "Windows":
            result = _collect_windows()
        else:
            result = _collect_linux()
        debug_logger.sensor("memory_sensor", "Collected with system commands", {
            "percent_used": result.get("percent_used"),
        })
        return result
