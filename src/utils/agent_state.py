"""Agent state manager for clean sensor state handling.

Provides a structured state manager that extracts and maintains
sensor snapshots in a clean, reusable format.
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

import config


@dataclass
class SensorState:
    """Container for sensor data."""
    process: dict[str, Any] = field(default_factory=dict)
    port: dict[str, Any] = field(default_factory=dict)
    file: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AgentState:
    """Centralized state manager for agent sensors.
    
    Manages sensor snapshots with thread-safe access.
    Provides risk calculation and state persistence.
    
    Attributes:
        threshold_process: Process count threshold
        threshold_port: Port count threshold
        threshold_file: File change threshold
    """
    
    def __init__(
        self,
        threshold_process: int = 300,
        threshold_port: int = 50,
        threshold_file: int = 100
    ):
        self.threshold_process = threshold_process
        self.threshold_port = threshold_port
        self.threshold_file = threshold_file
        
        self._state = SensorState()
        self._lock = Lock()
    
    def update_from_event(self, event: dict[str, Any]) -> None:
        """Update state from a sensor event.
        
        Args:
            event: Event dictionary with sensor and data
        """
        sensor = event.get("sensor", "")
        data = event.get("data", {})
        
        with self._lock:
            if sensor == "process_sensor":
                self._state.process = data
            elif sensor == "port_sensor":
                self._state.port = data
            elif sensor == "file_sensor":
                self._state.file = data
            
            self._state.timestamp = time.time()
    
    def update_from_events(self, events: list[dict[str, Any]]) -> None:
        """Update state from a list of events.
        
        Extracts latest snapshot from each sensor type.
        
        Args:
            events: List of event dictionaries
        """
        proc_updated = port_updated = file_updated = False
        
        for event in reversed(events):
            sensor = event.get("sensor", "")
            data = event.get("data", {})
            
            with self._lock:
                if sensor == "process_sensor" and not proc_updated:
                    self._state.process = data
                    proc_updated = True
                elif sensor == "port_sensor" and not port_updated:
                    self._state.port = data
                    port_updated = True
                elif sensor == "file_sensor" and not file_updated:
                    self._state.file = data
                    file_updated = True
                
                if proc_updated and port_updated and file_updated:
                    break
        
        with self._lock:
            self._state.timestamp = time.time()
    
    def get_process(self) -> dict[str, Any]:
        """Get current process state.
        
        Returns:
            Process sensor data
        """
        with self._lock:
            return dict(self._state.process)
    
    def get_port(self) -> dict[str, Any]:
        """Get current port state.
        
        Returns:
            Port sensor data
        """
        with self._lock:
            return dict(self._state.port)
    
    def get_file(self) -> dict[str, Any]:
        """Get current file state.
        
        Returns:
            File sensor data
        """
        with self._lock:
            return dict(self._state.file)
    
    def get_all(self) -> SensorState:
        """Get complete state snapshot.
        
        Returns:
            Current sensor state
        """
        with self._lock:
            return SensorState(
                process=dict(self._state.process),
                port=dict(self._state.port),
                file=dict(self._state.file),
                timestamp=self._state.timestamp
            )
    
    def calculate_risk(self) -> tuple[int, str]:
        """Calculate overall risk score.
        
        Returns:
            Tuple of (score, level)
            - 0-2: LOW
            - 3-5: MEDIUM
            - 6+: HIGH
        """
        score = 0
        
        with self._lock:
            process_count = self._state.process.get("count", 0)
            port_count = self._state.port.get("count", 0)
            file_count = self._state.file.get("change_count", 0)
        
        if process_count > self.threshold_process:
            score += 2
        elif process_count > self.threshold_process * 0.8:
            score += 1
        
        if port_count > self.threshold_port:
            score += 2
        elif port_count > self.threshold_port * 0.8:
            score += 1
        
        if file_count > self.threshold_file:
            score += 3
        elif file_count > self.threshold_file * 0.8:
            score += 1
        
        if score <= 2:
            level = "LOW"
        elif score <= 5:
            level = "MEDIUM"
        else:
            level = "HIGH"
        
        return (score, level)
    
    def get_risk_details(self) -> list[str]:
        """Get detailed risk breakdown.
        
        Returns:
            List of risk factor descriptions
        """
        details = []
        
        with self._lock:
            process_count = self._state.process.get("count", 0)
            port_count = self._state.port.get("count", 0)
            file_count = self._state.file.get("change_count", 0)
        
        if process_count > self.threshold_process:
            details.append(f"Process count HIGH: {process_count}")
        elif process_count > self.threshold_process * 0.8:
            details.append(f"Process count elevated: {process_count}")
        
        if port_count > self.threshold_port:
            details.append(f"Open ports HIGH: {port_count}")
        elif port_count > self.threshold_port * 0.8:
            details.append(f"Open ports elevated: {port_count}")
        
        if file_count > self.threshold_file:
            details.append(f"File changes HIGH: {file_count}")
        elif file_count > self.threshold_file * 0.8:
            details.append(f"File changes elevated: {file_count}")
        
        return details
    
    def clear(self) -> None:
        """Reset state to empty."""
        with self._lock:
            self._state = SensorState()


def create_agent_state() -> AgentState:
    """Create AgentState with config thresholds.
    
    Returns:
        AgentState configured from config
    """
    thresholds = config.DETECTION_THRESHOLDS
    return AgentState(
        threshold_process=thresholds.get("process_count", 300),
        threshold_port=thresholds.get("open_ports", 50),
        threshold_file=thresholds.get("file_changes", 100)
    )
