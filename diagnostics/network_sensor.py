"""Network sensor collects information about network connections and traffic.

Collects active network connections, bandwidth usage per interface,
connection state breakdown, and external IPs contacted.
Cross-platform using psutil with fallback to netstat/ss.
"""
from typing import Dict, Any, List
import platform
import logging

from utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_with_psutil() -> Dict[str, Any]:
    import psutil
    connections: List[Dict[str, Any]] = []
    established_count = 0
    external_ips: set = set()

    conns = psutil.net_connections(kind="inet")
    for conn in conns:
        try:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
            state = conn.status or "UNKNOWN"

            conn_info = {
                "protocol": "tcp" if hasattr(conn, 'type') and conn.type == 1 else "udp",
                "local": laddr,
                "remote": raddr,
                "state": state,
                "pid": conn.pid,
            }
            connections.append(conn_info)

            if state == "ESTABLISHED":
                established_count += 1
                if conn.raddr and conn.raddr.ip:
                    external_ips.add(conn.raddr.ip)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    interface_stats: List[Dict[str, Any]] = []
    io_counters = psutil.net_io_counters(pernic=True)
    for name, counters in io_counters.items():
        interface_stats.append({
            "name": name,
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
            "errors_in": counters.errin,
            "errors_out": counters.errout,
            "drops_in": counters.dropin,
            "drops_out": counters.dropout,
        })

    state_counts: Dict[str, int] = {}
    for conn in connections:
        s = conn.get("state", "UNKNOWN")
        state_counts[s] = state_counts.get(s, 0) + 1

    return {
        "connection_count": len(connections),
        "connections": connections,
        "established_count": established_count,
        "external_ips": list(external_ips),
        "interface_stats": interface_stats,
        "state_counts": state_counts,
    }


def _parse_netstat() -> Dict[str, Any]:
    import subprocess
    connections: List[Dict[str, Any]] = []
    established_count = 0
    external_ips: List[str] = []

    system = platform.system()
    if system == "Windows":
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    else:
        result = subprocess.run(["netstat", "-tan"], capture_output=True, text=True)

    lines = result.stdout.strip().splitlines()
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            proto = parts[0]
            local_addr = parts[1] if len(parts) > 1 else ""
            remote_addr = parts[2] if len(parts) > 2 else ""
            state = parts[3] if len(parts) > 3 and proto == "tcp" else "LISTENING"

            conn_info = {
                "protocol": proto,
                "local": local_addr,
                "remote": remote_addr,
                "state": state,
                "pid": int(parts[-1]) if proto.isalpha() and remote_addr else 0,
            }
            connections.append(conn_info)

            if state == "ESTABLISHED":
                established_count += 1
                if ":" in remote_addr:
                    ip = remote_addr.rsplit(":", 1)[0]
                    if not ip.startswith(("127.", "10.", "192.168.", "172.")):
                        external_ips.append(ip)
        except (ValueError, IndexError):
            continue

    state_counts: Dict[str, int] = {}
    for conn in connections:
        s = conn.get("state", "UNKNOWN")
        state_counts[s] = state_counts.get(s, 0) + 1

    return {
        "connection_count": len(connections),
        "connections": connections,
        "established_count": established_count,
        "external_ips": list(set(external_ips)),
        "interface_stats": [],
        "state_counts": state_counts,
    }


def _get_interface_stats_fallback() -> List[Dict[str, Any]]:
    import subprocess
    interface_stats: List[Dict[str, Any]] = []

    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(["ipconfig"], capture_output=True, text=True)
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(["cat", "/proc/net/dev"], capture_output=True, text=True)
        except Exception:
            pass

    return interface_stats


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    debug_logger.sensor("network_sensor", "Collecting network data", {})

    try:
        import psutil
        result = _collect_with_psutil()
        debug_logger.sensor("network_sensor", "Collected with psutil", {
            "connections": result.get("connection_count"),
            "established": result.get("established_count"),
        })
        return result
    except ImportError:
        logger.debug("psutil not available; falling back to netstat")
        result = _parse_netstat()
        result["interface_stats"] = _get_interface_stats_fallback()
        debug_logger.sensor("network_sensor", "Collected with netstat fallback", {
            "connections": result.get("connection_count"),
            "established": result.get("established_count"),
        })
        return result