"""Diagnostic modules for Phantom.

Each diagnostic exposes a single callable `collect` that accepts a `context`
dictionary and returns a payload describing the diagnostic result.
Diagnostics should not perform long blocking operations; they will
be executed by the schedule manager at a configured interval.

To add a new diagnostic simply create a new module within this package
that implements a `collect(context) -> dict` function.
"""

from src.diagnostics import (
    process_sensor,
    port_sensor,
    file_sensor,
    network_sensor,
    memory_sensor,
    disk_io_sensor,
    auth_sensor,
)

__all__ = [
    "process_sensor",
    "port_sensor",
    "file_sensor",
    "network_sensor",
    "memory_sensor",
    "disk_io_sensor",
    "auth_sensor",
]
