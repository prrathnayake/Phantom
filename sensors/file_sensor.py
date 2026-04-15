"""File sensor monitors a directory for changes.

This implementation does not rely on external dependencies.  Instead it
computes a snapshot of file modification times and compares it to the
previous snapshot stored in the scheduler context.  Added, removed and
modified files are reported.  The watch directory is configured in
`config.WATCH_DIRECTORY`.

Because it performs a full directory walk each time, it is advisable to
point it at a relatively small directory (e.g. your home config folder)
or increase the interval accordingly.
"""
import os
from typing import Dict, Any, Tuple, List
from pathlib import Path
import hashlib

from .. import config


def _snapshot(directory: Path) -> Dict[str, float]:
    """Return a mapping from file path to modification time (timestamp)."""
    snapshot: Dict[str, float] = {}
    for root, _, files in os.walk(directory):
        for fname in files:
            try:
                path = Path(root) / fname
                stat = path.stat()
                snapshot[str(path)] = stat.st_mtime
            except (FileNotFoundError, PermissionError):
                continue
    return snapshot


def _compare_snapshots(old: Dict[str, float], new: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    """Return lists of added, removed, and modified file paths."""
    old_keys = set(old)
    new_keys = set(new)
    added = list(new_keys - old_keys)
    removed = list(old_keys - new_keys)
    modified = []
    for key in old_keys & new_keys:
        if abs(old[key] - new[key]) > 1e-3:
            modified.append(key)
    return added, removed, modified


def collect(context: Dict[str, Any]) -> Dict[str, Any]:
    # Determine directory to watch
    watch_dir = config.WATCH_DIRECTORY
    # Compute current snapshot
    current = _snapshot(watch_dir)
    # Retrieve previous snapshot from context
    prev = context.get("file_sensor_snapshot", {})
    added, removed, modified = _compare_snapshots(prev, current)
    # Update context with current snapshot
    context["file_sensor_snapshot"] = current
    # Build payload
    return {
        "directory": str(watch_dir),
        "added": added,
        "removed": removed,
        "modified": modified,
        "change_count": len(added) + len(removed) + len(modified),
    }
