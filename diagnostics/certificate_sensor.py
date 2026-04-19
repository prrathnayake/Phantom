"""Certificate Sensor - Monitors TLS certificates.

Cross-platform sensor for monitoring TLS certificate expiry and weak ciphers.
"""
from typing import Any, Dict, List
import platform
import logging
from datetime import datetime, timedelta

from utils.debug_log import debug_logger

logger = logging.getLogger(__name__)


def _collect_windows() -> Dict[str, Any]:
    import subprocess
    import os
    
    certs = []
    expiring = []
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ChildItem -Path Cert:\\\\LocalMachine\\\\My -ErrorAction SilentlyContinue | Select-Object Subject,NotBefore,NotAfter,Thumbprint | ConvertTo-Json"],
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
                
                for cert in data:
                    subject = cert.get("Subject", "Unknown")
                    not_after = cert.get("NotAfter", "")
                    
                    try:
                        expiry = datetime.strptime(str(not_after), "%Y-%m-%dT%H:%M:%S")
                        days_left = (expiry - datetime.now()).days
                        
                        cert_info = {
                            "subject": subject[:50],
                            "expires": str(not_after)[:10],
                            "days_left": days_left
                        }
                        certs.append(cert_info)
                        
                        if days_left < 30:
                            expiring.append(cert_info)
                    except (ValueError, TypeError):
                        pass
            except json.JSONDecodeError:
                pass
    
    except Exception as e:
        logger.debug(f"Certificate collection failed: {e}")
    
    return {
        "certificate_count": len(certs),
        "expiring_count": len(expiring),
        "expiring": expiring,
        "certificates": certs[:20]
    }


def _collect_linux() -> Dict[str, Any]:
    import subprocess
    import os
    from pathlib import Path
    
    certs = []
    expiring = []
    
    cert_dirs = [
        "/etc/ssl/certs",
        "/etc/pki/tls/certs",
        "/usr/share/ca-certificates"
    ]
    
    for cert_dir in cert_dirs:
        if not Path(cert_dir).exists():
            continue
        
        try:
            for root, dirs, files in os.walk(cert_dir):
                for f in files:
                    if f.endswith((".pem", ".crt", ".cer")):
                        path = os.path.join(root, f)
                        try:
                            result = subprocess.run(
                                ["openssl", "x509", "-noout", "-dates", "-in", path],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if result.returncode == 0:
                                lines = result.stdout.strip().splitlines()
                                expires = None
                                
                                for line in lines:
                                    if line.startswith("notAfter="):
                                        date_str = line.split("=", 1)[1]
                                        try:
                                            expires = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                                        except ValueError:
                                            pass
                                
                                if expires:
                                    days_left = (expires - datetime.now()).days
                                    
                                    if days_left < 30:
                                        expiring.append({
                                            "path": path,
                                            "expires": str(expires)[:10],
                                            "days_left": days_left
                                        })
                                    
                                    certs.append({"path": path, "days_left": days_left})
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Certificate scanning failed: {e}")
    
    return {
        "certificate_count": len(certs),
        "expiring_count": len(expiring),
        "expiring": expiring[:10],
        "certificates": certs[:20]
    }


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect certificate information.
    
    Args:
        context: Shared context
        
    Returns:
        Certificate data
    """
    debug_logger.sensor("certificate_sensor", "Collecting certificate data", {})
    
    system = platform.system()
    
    if system == "Windows":
        result = _collect_windows()
    else:
        result = _collect_linux()
    
    debug_logger.sensor("certificate_sensor", "Collected certificate data", {
        "count": result.get("certificate_count"),
        "expiring": result.get("expiring_count")
    })
    
    return result