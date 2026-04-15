"""Rule‑based anomaly detection.

This module evaluates simple heuristics against sensor outputs stored in
the scheduler context.  When a rule triggers it writes a detection
record to the storage layer and returns a description of the anomaly.
"""
from typing import Dict, Any, List
import config
from core.storage import Storage


def detect(context: Dict[str, Any], storage: Storage) -> List[Dict[str, Any]]:
    """Run detection rules and return a list of anomalies.

    Each rule examines the most recent payload for a particular sensor
    stored in the context (see `main.py` for how sensor outputs are
    saved).  If the rule triggers a record is appended to the detections
    log and an entry is added to the returned list.
    """
    anomalies: List[Dict[str, Any]] = []

    # Rule: number of processes exceeds threshold
    proc_payload = context.get("process_sensor_last")
    if proc_payload:
        count = proc_payload.get("count", 0)
        threshold = config.DETECTION_THRESHOLDS["process_count"]
        if count > threshold:
            description = f"High process count: {count} processes (threshold {threshold})"
            details = {"count": count, "top_processes": proc_payload.get("top_processes", [])}
            storage.log_detection("process_count", description, details)
            anomalies.append({"rule": "process_count", "description": description})

    # Rule: number of open ports exceeds threshold
    port_payload = context.get("port_sensor_last")
    if port_payload:
        count = port_payload.get("count", 0)
        threshold = config.DETECTION_THRESHOLDS["open_ports"]
        if count > threshold:
            description = f"High number of open ports: {count} listening ports (threshold {threshold})"
            details = {"count": count, "ports": port_payload.get("listening", [])}
            storage.log_detection("open_ports", description, details)
            anomalies.append({"rule": "open_ports", "description": description})

    # Rule: number of file changes exceeds threshold
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

    return anomalies
