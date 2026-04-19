"""Rule‑based anomaly detection.

This module evaluates simple heuristics against sensor outputs stored in
the scheduler context.  When a rule triggers it writes a detection
record to the storage layer and returns a description of the anomaly.
"""
from typing import Dict, Any, List
import config
from core.storage import Storage
from utils.debug_log import debug_logger


def detect(context: Dict[str, Any], storage: Storage) -> List[Dict[str, Any]]:
    """Run detection rules and return a list of anomalies.

    Each rule examines the most recent payload for a particular sensor
    stored in the context (see `main.py` for how sensor outputs are
    saved).  If the rule triggers a record is appended to the detections
    log and an entry is added to the returned list.
    """
    debug_logger.detection("detection_engine", "Running detection rules")
    anomalies: List[Dict[str, Any]] = []

    proc_payload = context.get("process_sensor_last")
    if proc_payload:
        count = proc_payload.get("count", 0)
        threshold = config.DETECTION_THRESHOLDS["process_count"]
        if count > threshold:
            description = f"High process count: {count} processes (threshold {threshold})"
            details = {"count": count, "top_processes": proc_payload.get("top_processes", [])}
            storage.log_detection("process_count", description, details)
            anomalies.append({"rule": "process_count", "description": description})
            debug_logger.detection("process_count", "Rule triggered", details)

    port_payload = context.get("port_sensor_last")
    if port_payload:
        count = port_payload.get("count", 0)
        threshold = config.DETECTION_THRESHOLDS["open_ports"]
        if count > threshold:
            description = f"High number of open ports: {count} listening ports (threshold {threshold})"
            details = {"count": count, "ports": port_payload.get("listening", [])}
            storage.log_detection("open_ports", description, details)
            anomalies.append({"rule": "open_ports", "description": description})
            debug_logger.detection("open_ports", "Rule triggered", details)

    file_payload = context.get("file_sensor_last")
    if file_payload:
        change_count = file_payload.get("change_count", 0)
        threshold = config.DETECTION_THRESHOLDS["file_changes"]
        if change_count > threshold:
            description = f"High file change volume: {change_count} modifications (threshold {threshold})"
            details = {
                "added": file_payload.get("added", []),
                "removed": file_payload.get("removed", []),
                "modified": file_payload.get("modified", []),
            }
            storage.log_detection("file_changes", description, details)
            anomalies.append({"rule": "file_changes", "description": description})
            debug_logger.detection("file_changes", "Rule triggered", details)

    network_payload = context.get("network_sensor_last")
    if network_payload:
        established = network_payload.get("established_count", 0)
        threshold = config.DETECTION_THRESHOLDS["established_connections"]
        if established > threshold:
            description = f"High established connections: {established} (threshold {threshold})"
            details = {
                "count": established,
                "external_ips": network_payload.get("external_ips", []),
            }
            storage.log_detection("established_connections", description, details)
            anomalies.append({"rule": "established_connections", "description": description})
            debug_logger.detection("established_connections", "Rule triggered", details)

        external_ips = len(network_payload.get("external_ips", []))
        ip_threshold = config.DETECTION_THRESHOLDS["external_ips"]
        if external_ips > ip_threshold:
            description = f"Many external IPs contacted: {external_ips} unique IPs"
            details = {"external_ips": network_payload.get("external_ips", [])}
            storage.log_detection("external_ips", description, details)
            anomalies.append({"rule": "external_ips", "description": description})
            debug_logger.detection("external_ips", "Rule triggered", details)

    memory_payload = context.get("memory_sensor_last")
    if memory_payload:
        percent = memory_payload.get("percent_used", 0)
        threshold = config.DETECTION_THRESHOLDS["memory_percent"]
        if percent > threshold:
            description = f"High memory usage: {percent}% (threshold {threshold}%)"
            details = {
                "percent_used": percent,
                "used_mb": memory_payload.get("used_mb", 0),
                "total_mb": memory_payload.get("total_mb", 0),
            }
            storage.log_detection("memory_percent", description, details)
            anomalies.append({"rule": "memory_percent", "description": description})
            debug_logger.detection("memory_percent", "Rule triggered", details)

        swap_percent = memory_payload.get("swap_percent", 0)
        swap_threshold = config.DETECTION_THRESHOLDS["swap_percent"]
        if swap_percent > swap_threshold:
            description = f"High swap usage: {swap_percent}% (threshold {swap_threshold}%)"
            details = {
                "swap_percent": swap_percent,
                "swap_used_mb": memory_payload.get("swap_used_mb", 0),
            }
            storage.log_detection("swap_percent", description, details)
            anomalies.append({"rule": "swap_percent", "description": description})
            debug_logger.detection("swap_percent", "Rule triggered", details)

    disk_payload = context.get("disk_io_sensor_last")
    if disk_payload:
        disks = disk_payload.get("disks", [])
        threshold = config.DETECTION_THRESHOLDS["disk_percent"]
        for disk in disks:
            percent = disk.get("percent_used", 0)
            if percent > threshold:
                device = disk.get("mount", disk.get("device", "unknown"))
                description = f"High disk usage: {device} at {percent}% (threshold {threshold}%)"
                details = {
                    "device": device,
                    "percent": percent,
                    "used_gb": disk.get("used_gb", 0),
                    "total_gb": disk.get("total_gb", 0),
                }
                storage.log_detection("disk_percent", description, details)
                anomalies.append({"rule": "disk_percent", "description": description})
                debug_logger.detection("disk_percent", "Rule triggered", details)

    auth_payload = context.get("auth_sensor_last")
    if auth_payload:
        failed_count = auth_payload.get("failed_count", 0)
        threshold = config.DETECTION_THRESHOLDS["failed_logins"]
        if failed_count > threshold:
            description = f"Failed login attempts: {failed_count} (threshold {threshold})"
            details = {
                "failed_count": failed_count,
                "failed_logins": auth_payload.get("failed_logins", [])[:10],
            }
            storage.log_detection("failed_logins", description, details)
            anomalies.append({"rule": "failed_logins", "description": description})
            debug_logger.detection("failed_logins", "Rule triggered", details)

        priv_esc = auth_payload.get("privilege_escalations", [])
        if priv_esc:
            description = f"Privilege escalation detected: {len(priv_esc)} events"
            details = {"privilege_escalations": priv_esc[:5]}
            storage.log_detection("privilege_escalation", description, details)
            anomalies.append({"rule": "privilege_escalation", "description": description})
            debug_logger.detection("privilege_escalation", "Rule triggered", details)

    debug_logger.detection("detection_engine", f"Detection complete: {len(anomalies)} anomalies found")
    return anomalies
