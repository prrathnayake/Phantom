"""Process sensor collects information about running processes.

The payload includes the total number of processes and a sample of the
most resource intensive processes.  If `psutil` is available it will
provide rich metrics; otherwise it falls back to parsing the output of
the `ps` command.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def _collect_with_psutil() -> Dict[str, Any]:
    """Collect process info using psutil (preferred)."""
    import psutil  # type: ignore
    processes = []
    for proc in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # Sort by CPU usage descending
    processes.sort(key=lambda p: p.get("cpu_percent", 0), reverse=True)
    # Sample top 5
    top = processes[:5]
    return {
        "count": len(processes),
        "top_processes": top,
    }


def _collect_with_ps() -> Dict[str, Any]:
    """Collect process info using the `ps` shell command (Unix) or `tasklist` (Windows)."""
    import subprocess
    import platform
    
    if platform.system() == "Windows":
        result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        count = len(lines)
        processes: List[Dict[str, Any]] = []
        for line in lines:
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    processes.append({
                        "pid": int(parts[1].strip().strip('"')),
                        "name": parts[0].strip().strip('"'),
                        "username": "N/A",
                        "cpu_percent": 0.0,
                        "memory_percent": 0.0,
                    })
                except (ValueError, IndexError):
                    continue
    else:
        result = subprocess.run([
            "ps", "-eo", "pid,comm,user,pcpu,pmem", "--no-headers"
        ], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        count = len(lines)
        processes = []
        for line in lines:
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            pid, command, user, cpu, mem = parts
            try:
                processes.append({
                    "pid": int(pid),
                    "name": command,
                    "username": user,
                    "cpu_percent": float(cpu),
                    "memory_percent": float(mem),
                })
            except ValueError:
                continue
    
    processes.sort(key=lambda p: p.get("cpu_percent", 0), reverse=True)
    top = processes[:5]
    return {
        "count": count,
        "top_processes": top,
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for the scheduler.

    :param context: Shared context dictionary.
    :return: A payload describing the current process list.
    """
    try:
        import psutil  # noqa: F401
        return _collect_with_psutil()
    except ImportError:
        logger.debug("psutil not available; falling back to ps command")
        return _collect_with_ps()
