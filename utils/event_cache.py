"""Event cache for efficient storage reads.

Caches sensor events and detections to avoid repeatedly
scanning log files. Uses file-based caching with TTL.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional


@dataclass
class CacheEntry:
    """Single cache entry with timestamp."""
    data: Any
    timestamp: float = field(default_factory=time.time)


class EventCache:
    """Cache for sensor events with TTL support.
    
    Stores events in memory with optional file-based persistence.
    Only updates when stale to avoid repeated I/O.
    
    Attributes:
        storage_path: Path to storage module
        max_events: Maximum events to keep
        ttl: Time-to-live in seconds
    """
    
    def __init__(
        self,
        events_file: Path,
        detections_file: Path,
        max_events: int = 200,
        max_detections: int = 50,
        ttl: float = 5.0
    ):
        self.events_file = events_file
        self.detections_file = detections_file
        self.max_events = max_events
        self.max_detections = max_detections
        self.ttl = ttl
        
        self._events: list[dict[str, Any]] = []
        self._detections: list[dict[str, Any]] = []
        self._last_read_time = 0.0
        self._last_event_count = 0
        self._last_detection_count = 0
        self._lock = Lock()
    
    def should_update(self) -> bool:
        """Check if cache should be refreshed.
        
        Returns:
            True if TTL expired
        """
        return (time.time() - self._last_read_time) >= self.ttl
    
    def update(self, events: list[dict[str, Any]], detections: list[dict[str, Any]]) -> None:
        """Update cache with new data.
        
        Args:
            events: List of event dictionaries
            detections: List of detection dictionaries
        """
        with self._lock:
            self._events = events[:self.max_events]
            self._detections = detections[:self.max_detections]
            
            new_event_count = len(events)
            new_detection_count = len(detections)
            
            if new_event_count > self._last_event_count:
                self._last_event_count = new_event_count
            
            if new_detection_count > self._last_detection_count:
                self._last_detection_count = new_detection_count
            
            self._last_read_time = time.time()
    
    def get_events(self) -> list[dict[str, Any]]:
        """Get cached events.
        
        Returns:
            List of events (newest first)
        """
        with self._lock:
            return list(self._events)
    
    def get_detections(self) -> list[dict[str, Any]]:
        """Get cached detections.
        
        Returns:
            List of detections (newest first)
        """
        with self._lock:
            return list(self._detections)
    
    def get_counts(self) -> tuple[int, int]:
        """Get event and detection counts.
        
        Returns:
            Tuple of (event_count, detection_count)
        """
        with self._lock:
            return (len(self._events), len(self._detections))
    
    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._events.clear()
            self._detections.clear()
            self._last_read_time = 0.0


class FileCache:
    """Simple file-based cache with JSON persistence.
    
    Provides persistent caching across application restarts.
    
    Attributes:
        cache_dir: Directory for cache files
    """
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
    
    def _get_cache_path(self, name: str) -> Path:
        return self.cache_dir / f"{name}.json"
    
    def get(self, name: str) -> Optional[dict[str, Any]]:
        """Load cached data.
        
        Args:
            name: Cache identifier
            
        Returns:
            Cached data or None
        """
        path = self._get_cache_path(name)
        if not path.exists():
            return None
        
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    
    def set(self, name: str, data: dict[str, Any]) -> None:
        """Save data to cache.
        
        Args:
            name: Cache identifier
            data: Data to cache
        """
        path = self._get_cache_path(name)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass
    
    def delete(self, name: str) -> None:
        """Delete cached data.
        
        Args:
            name: Cache identifier
        """
        path = self._get_cache_path(name)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    
    def exists(self, name: str) -> bool:
        """Check if cache exists.
        
        Args:
            name: Cache identifier
            
        Returns:
            True if cache file exists
        """
        return self._get_cache_path(name).exists()


class StateCache:
    """Persistent state cache for agent state.
    
    Caches sensor snapshots for fast dashboard loading.
    """
    
    def __init__(self, cache_dir: Path):
        self._file_cache = FileCache(cache_dir)
    
    def save_state(
        self,
        process: dict[str, Any],
        port: dict[str, Any],
        file: dict[str, Any]
    ) -> None:
        """Save current sensor state."""
        state = {
            "process": process,
            "port": port,
            "file": file,
            "timestamp": time.time()
        }
        self._file_cache.set("sensor_state", state)
    
    def load_state(self) -> Optional[dict[str, Any]]:
        """Load last known sensor state."""
        return self._file_cache.get("sensor_state")
    
    def is_fresh(self, max_age: float = 60.0) -> bool:
        """Check if cached state is fresh.
        
        Args:
            max_age: Maximum age in seconds
            
        Returns:
            True if state is fresh
        """
        state = self.load_state()
        if not state:
            return False
        return (time.time() - state.get("timestamp", 0)) < max_age