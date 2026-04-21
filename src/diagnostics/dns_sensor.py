"""DNS Sensor - Monitors DNS queries and cache.

Cross-platform sensor for monitoring DNS queries and detecting suspicious domains.
"""
from typing import Any, Dict, List
import platform
import logging

from src.utils.debug_log import debug_logger

logger = logging.getLogger(__name__)

SUSPICIOUS_DOMAINS = [
    "malware-domain", "evil.com", "badsite.com"
]


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    
    dns_cache = []
    
    try:
        result = subprocess.run(
            ["ipconfig", "/displaydns"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().splitlines()
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(":"):
                if "Record Name" in line:
                    current_entry = {"name": line.split(".", 1)[-1]}
                elif "Record Type" in line:
                    current_entry["type"] = line.split(":")[-1].strip()
                elif "Time to Live" in line:
                    current_entry["ttl"] = line.split(":")[-1].strip()
                elif "Data Length" in line:
                    if current_entry:
                        dns_cache.append(current_entry)
                        current_entry = {}
        
        if current_entry:
            dns_cache.append(current_entry)
    
    except Exception as e:
        logger.debug(f"DNS cache collection failed: {e}")
    
    return {
        "cached_entries": len(dns_cache),
        "dns_cache": dns_cache[:20]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    from pathlib import Path
    
    dns_queries = []
    resolve_conf = {}
    
    try:
        result = subprocess.run(
            ["cat", "/etc/resolv.conf"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        for line in result.stdout.splitlines():
            if line.startswith("nameserver"):
                resolve_conf["nameservers"] = resolve_conf.get("nameservers", [])
                resolve_conf["nameservers"].append(line.split()[1])
    except Exception as e:
        logger.debug(f"resolv.conf read failed: {e}")
    
    log_file = "/var/log/syslog"
    if Path(log_file).exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            for line in lines[-500:]:
                if "query" in line and "DNS" in line:
                    dns_queries.append(line.strip()[:100])
        except Exception as e:
            logger.debug(f"syslog read failed: {e}")
    
    return {
        "config": resolve_conf,
        "recent_queries": dns_queries[:20]
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect DNS information.
    
    Args:
        context: Shared context
        
    Returns:
        DNS data
    """
    debug_logger.sensor("dns_sensor", "Collecting DNS data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("dns_sensor", "Collected DNS data", {})
    
    return result
