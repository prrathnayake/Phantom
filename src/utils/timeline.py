"""Timeline module for attack flow visualization.

Tracks security events in a timeline format for visualizing
attack chains and system activity.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import config


class EventType(Enum):
    """Timeline event types."""
    PORT_OPENED = "port_opened"
    PROCESS_SPAWNED = "process_spawned"
    FILE_MODIFIED = "file_modified"
    ANOMALY_DETECTED = "anomaly_detected"
    ACTION_TAKEN = "action_taken"
    THREAT_DETECTED = "threat_detected"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"


class EventSeverity(Enum):
    """Event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TimelineEvent:
    """Single timeline event."""
    timestamp: float
    event_type: str
    source: str
    details: dict[str, Any]
    severity: str = "low"
    linked_to: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
            "details": self.details,
            "severity": self.severity,
            "linked_to": self.linked_to,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimelineEvent":
        return cls(
            timestamp=data.get("timestamp", time.time()),
            event_type=data.get("event_type", ""),
            source=data.get("source", ""),
            details=data.get("details", {}),
            severity=data.get("severity", "low"),
            linked_to=data.get("linked_to"),
        )


class Timeline:
    """Timeline manager for security events.
    
    Tracks events in order and provides visualization.
    Supports file persistence across restarts.
    
    Attributes:
        max_events: Maximum events to keep
        persist_path: Optional path for file persistence
    """
    
    def __init__(
        self,
        max_events: int = 50,
        persist_path: Optional[Path] = None
    ):
        self.max_events = max_events
        self.persist_path = persist_path
        self._events: list[TimelineEvent] = []
        self._lock = Lock()
        
        if persist_path:
            self._load()
    
    def add_event(
        self,
        event_type: str,
        source: str,
        details: dict[str, Any],
        severity: str = "low",
        linked_to: Optional[str] = None
    ) -> str:
        """Add a new timeline event.
        
        Args:
            event_type: Type of event (from EventType)
            source: Source of the event (e.g., "port_sensor")
            details: Event details dictionary
            severity: Severity level
            linked_to: ID of linked event
            
        Returns:
            Event ID
        """
        event_id = f"{event_type}_{int(time.time() * 1000)}"
        
        event = TimelineEvent(
            timestamp=time.time(),
            event_type=event_type,
            source=source,
            details=details,
            severity=severity,
            linked_to=linked_to
        )
        
        with self._lock:
            self._events.append(event)
            
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events:]
        
        if self.persist_path:
            self._save()
        
        return event_id
    
    def get_recent(self, count: int = 10) -> list[TimelineEvent]:
        """Get recent events.
        
        Args:
            count: Number of events to return
            
        Returns:
            List of recent events (newest first)
        """
        with self._lock:
            return list(reversed(self._events[-count:]))
    
    def get_flow(self, count: int = 10) -> list[dict[str, Any]]:
        """Get events formatted as attack flow.
        
        Args:
            count: Number of events
            
        Returns:
            List of formatted flow strings
        """
        events = self.get_recent(count)
        flow = []
        
        for event in events:
            symbol = self._get_severity_symbol(event.severity)
            ts = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
            flow.append(f"[{ts}] {symbol} {event.event_type}")
            
            if event.details:
                detail_str = str(event.details)[:50]
                flow.append(f"    → {detail_str}")
        
        return flow
    
    def get_chain(self, start_event_id: Optional[str] = None) -> list[TimelineEvent]:
        """Get attack chain from a specific event.
        
        Args:
            start_event_id: Starting event ID
            
        Returns:
            Chain of linked events
        """
        with self._lock:
            if not start_event_id:
                return list(self._events)
            
            chain = []
            for event in reversed(self._events):
                if event.linked_to == start_event_id:
                    chain.append(event)
                    start_event_id = event.linked_to
            
            return list(reversed(chain))
    
    def get_by_severity(self, severity: str) -> list[TimelineEvent]:
        """Get events filtered by severity.
        
        Args:
            severity: Severity level to filter
            
        Returns:
            Filtered events
        """
        with self._lock:
            return [e for e in self._events if e.severity == severity]
    
    def get_by_type(self, event_type: str) -> list[TimelineEvent]:
        """Get events filtered by type.
        
        Args:
            event_type: Event type to filter
            
        Returns:
            Filtered events
        """
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]
    
    def get_threat_count(self) -> int:
        """Get count of high/critical events.
        
        Returns:
            Number of active threats
        """
        with self._lock:
            return sum(1 for e in self._events if e.severity in ("high", "critical"))
    
    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._events.clear()
        
        if self.persist_path:
            self._save()
    
    def _get_severity_symbol(self, severity: str) -> str:
        symbols = {
            "low": "○",
            "medium": "◐",
            "high": "●",
            "critical": "⚠"
        }
        return symbols.get(severity, "○")
    
    def _save(self) -> None:
        """Save events to file."""
        if not self.persist_path:
            return
        
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persist_path.open("w", encoding="utf-8") as f:
                data = [e.to_dict() for e in self._events]
                json.dump(data, f)
        except OSError:
            pass
    
    def _load(self) -> None:
        """Load events from file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._events = [TimelineEvent.from_dict(e) for e in data]
        except (json.JSONDecodeError, OSError):
            pass


def create_timeline() -> Timeline:
    """Create a timeline with config settings.
    
    Returns:
        Timeline instance
    """
    return Timeline(
        max_events=config.TIMELINE_MAX_EVENTS,
        persist_path=config.LOG_DIR / "timeline.json"
    )


def add_detection_to_timeline(
    timeline: Timeline,
    event_type: str,
    source: str,
    details: dict[str, Any],
    severity: str = "low"
) -> str:
    """Add a detection event to timeline.
    
    Convenience function for adding detection-related events.
    
    Args:
        timeline: Timeline instance
        event_type: Type of event
        source: Source sensor/module
        details: Event details
        severity: Severity level
        
    Returns:
        Event ID
    """
    return timeline.add_event(
        event_type=event_type,
        source=source,
        details=details,
        severity=severity
    )
