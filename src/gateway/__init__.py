"""Gateway package for Phantom.

Handles input interfaces and scheduled diagnostic runs.
Sends payloads to Agent for analysis.
"""
from .schedule_manager import (
    ScheduleManager,
    create_schedule_manager,
    on_schedule_run,
    _notify_schedule_run,
)
from .payload_sender import PayloadSender
from .server import Gateway, create_gateway

__all__ = [
    "ScheduleManager",
    "create_schedule_manager",
    "on_schedule_run",
    "_notify_schedule_run",
    "PayloadSender",
    "Gateway",
    "create_gateway",
]
