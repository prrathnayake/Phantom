"""Incremental log counter for O(Δ) file reads.

Instead of scanning the entire file (O(N)), this tracks file size and only
counts new lines since last read (O(Δ) where Δ is new content).
"""

import os
from pathlib import Path
from threading import Lock
from typing import Optional


class LogCounter:
    """Incrementally counts lines in a log file.
    
    Tracks file size and only reads new content since last check.
    Handles log rotation by detecting size decrease.
    
    Attributes:
        path: Path to the log file
        last_size: Last known file size in bytes
        count: Current line count
    """
    
    def __init__(self, path: Path):
        self.path = path
        self.last_size: int = 0
        self.count: int = 0
        self._lock = Lock()
    
    def update(self) -> int:
        """Update count by reading only new content.
        
        Returns:
            Current line count
        """
        with self._lock:
            return self._updateUnsafe()
    
    def _updateUnsafe(self) -> int:
        if not self.path.exists():
            self.count = 0
            self.last_size = 0
            return 0
        
        try:
            current_size = self.path.stat().st_size
        except OSError:
            self.count = 0
            self.last_size = 0
            return 0
        
        if current_size < self.last_size:
            self.count = 0
        
        if current_size > self.last_size:
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    f.seek(self.last_size)
                    self.count += sum(1 for _ in f)
            except OSError:
                pass
        
        self.last_size = current_size
        return self.count
    
    def get(self) -> int:
        """Get current count without updating.
        
        Returns:
            Current line count
        """
        with self._lock:
            return self.count
    
    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self.count = 0
            self.last_size = 0


class MultiLogCounter:
    """Manages multiple LogCounter instances.
    
    Provides a unified interface for tracking multiple log files.
    """
    
    def __init__(self):
        self._counters: dict[str, LogCounter] = {}
        self._lock = Lock()
    
    def register(self, name: str, path: Path) -> None:
        """Register a new log file to track.
        
        Args:
            name: Identifier for the log file
            path: Path to the log file
        """
        with self._lock:
            self._counters[name] = LogCounter(path)
    
    def update(self, name: str) -> int:
        """Update count for a specific log.
        
        Args:
            name: Identifier for the log file
            
        Returns:
            Current line count
        """
        with self._lock:
            counter = self._counters.get(name)
            if counter:
                return counter.update()
            return 0
    
    def update_all(self) -> dict[str, int]:
        """Update all registered counters.
        
        Returns:
            Dictionary of name -> count
        """
        with self._lock:
            return {name: c.update() for name, c in self._counters.items()}
    
    def get(self, name: str) -> int:
        """Get count without updating.
        
        Args:
            name: Identifier for the log file
            
        Returns:
            Current line count
        """
        with self._lock:
            counter = self._counters.get(name)
            return counter.get() if counter else 0
    
    def get_all(self) -> dict[str, int]:
        """Get all counts without updating.
        
        Returns:
            Dictionary of name -> count
        """
        with self._lock:
            return {name: c.get() for name, c in self._counters.items()}
    
    def unregister(self, name: str) -> None:
        """Remove a log file from tracking.
        
        Args:
            name: Identifier for the log file
        """
        with self._lock:
            self._counters.pop(name, None)
