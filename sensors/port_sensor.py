"""Port sensor collects information about open TCP and UDP ports.

The payload includes the total number of listening sockets and a list of
the ports and protocols in use.  It uses psutil when available and
falls back to parsing the output of `netstat`.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def _collect_with_psutil() -> Dict[str, Any]:
    import psutil  # type: ignore
    ports: List[Dict[str, Any]] = []
    connections = psutil.net_connections(kind="inet")
    for conn in connections:
        # Only interested in listening sockets
        if conn.status == psutil.CONN_LISTEN:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
            proto = "tcp" if conn.type == psutil.SOCK_STREAM else "udp"
            ports.append({"protocol": proto, "address": laddr})
    return {
        "count": len(ports),
        "listening": ports,
    }


def _collect_with_netstat() -> Dict[str, Any]:
    import subprocess
    ports: List[Dict[str, Any]] = []
    # Use -tuln to list both TCP and UDP listening ports
    result = subprocess.run(["netstat", "-tuln"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    for line in lines:
        # Lines start with protocol (tcp, udp) followed by recv-q, send-q, local address
        if line.startswith("tcp") or line.startswith("udp"):
            parts = line.split()
            if len(parts) >= 4:
                proto = parts[0]
                laddr = parts[3]
                # Only include lines with state 'LISTEN' for TCP.  UDP lines may not have a state column.
                if proto.startswith("tcp"):
                    if "LISTEN" not in line and "ESTABLISHED" in line:
                        continue
                ports.append({"protocol": proto, "address": laddr})
    return {
        "count": len(ports),
        "listening": ports,
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import psutil  # noqa: F401
        return _collect_with_psutil()
    except ImportError:
        logger.debug("psutil not available; falling back to netstat")
        return _collect_with_netstat()
