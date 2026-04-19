"""Session Memory Manager for Central Agent.

Manages session memory for run sessions, providing
temporary storage during analysis cycles with TTL support.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from utils.debug_log import debug_logger


@dataclass
class SessionMemoryEntry:
    """Single session memory entry."""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    session_id: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "tags": self.tags,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMemoryEntry":
        """Create from dictionary."""
        return cls(
            key=data.get("key", ""),
            value=data.get("value"),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl"),
            tags=data.get("tags", []),
            session_id=data.get("session_id"),
        )


class SessionMemory:
    """Memory management for run sessions.
    
    Provides session-scoped memory with TTL support and
    optional persistence. Works with ContextManager.
    
    Attributes:
        persist_path: Optional path for file persistence
        default_ttl: Default time-to-live in seconds
    """
    
    def __init__(
        self,
        persist_path: Optional[Path] = None,
        default_ttl: float = 3600.0,
        max_entries: int = 500
    ):
        self.persist_path = persist_path
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._memory: dict[str, SessionMemoryEntry] = {}
        self._lock = Lock()
        
        if persist_path:
            self._load()
        
        debug_logger.info(
            "SessionMemory initialized",
            {"persist": str(persist_path), "default_ttl": default_ttl}
        )
    
    def store(
        self,
        key: str,
        value: Any,
        session_id: Optional[str] = None,
        ttl: Optional[float] = None,
        tags: Optional[list[str]] = None
    ) -> None:
        """Store session memory entry.
        
        Args:
            key: Memory key
            value: Memory value
            session_id: Optional session ID for scoping
            ttl: Time-to-live in seconds (uses default if not specified)
            tags: Optional tags for categorization
        """
        entry = SessionMemoryEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else self.default_ttl,
            tags=tags or [],
            session_id=session_id,
        )
        
        with self._lock:
            self._memory[key] = entry
            
            if len(self._memory) > self.max_entries:
                self._evict_oldest()
        
        if self.persist_path:
            self._save()
        
        debug_logger.info(
            "Memory stored",
            {"key": key, "session_id": session_id, "tags": tags}
        )
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve session memory entry.
        
        Args:
            key: Memory key
            
        Returns:
            Memory value or None if not found/expired
        """
        with self._lock:
            entry = self._memory.get(key)
            
            if entry is None:
                debug_logger.info("Memory not found", {"key": key})
                return None
            
            if entry.is_expired():
                del self._memory[key]
                debug_logger.info("Memory expired", {"key": key})
                return None
            
            debug_logger.info("Memory retrieved", {"key": key})
            return entry.value
    
    def get_entry(self, key: str) -> Optional[SessionMemoryEntry]:
        """Get full session memory entry.
        
        Args:
            key: Memory key
            
        Returns:
            SessionMemoryEntry or None
        """
        with self._lock:
            entry = self._memory.get(key)
            
            if entry and not entry.is_expired():
                return entry
            
            return None
    
    def get_for_session(self, session_id: str) -> list[tuple[str, Any]]:
        """Get all memories for a specific session.
        
        Args:
            session_id: Session ID to filter by
            
        Returns:
            List of (key, value) tuples
        """
        results = []
        
        with self._lock:
            for key, entry in self._memory.items():
                if entry.is_expired():
                    continue
                if entry.session_id == session_id:
                    results.append((key, entry.value))
        
        return results
    
    def search(self, query: str) -> list[tuple[str, Any]]:
        """Search memories by key, tag, or value.
        
        Args:
            query: Search query string
            
        Returns:
            List of (key, value) tuples
        """
        results = []
        query_lower = query.lower()
        
        with self._lock:
            for key, entry in self._memory.items():
                if entry.is_expired():
                    continue
                
                if query_lower in key.lower():
                    results.append((key, entry.value))
                elif any(query_lower in tag.lower() for tag in entry.tags):
                    results.append((key, entry.value))
                elif query_lower in str(entry.value).lower():
                    results.append((key, entry.value))
        
        return results
    
    def get_recent(self, count: int = 10) -> list[tuple[str, Any]]:
        """Get recent memories.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of (key, value) tuples, newest first
        """
        with self._lock:
            valid = [e for e in self._memory.values() if not e.is_expired()]
            valid.sort(key=lambda e: e.timestamp, reverse=True)
            return [(e.key, e.value) for e in valid[:count]]
    
    def get_by_tag(self, tag: str) -> list[tuple[str, Any]]:
        """Get memories by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of (key, value) tuples
        """
        results = []
        tag_lower = tag.lower()
        
        with self._lock:
            for key, entry in self._memory.items():
                if entry.is_expired():
                    continue
                if tag_lower in [t.lower() for t in entry.tags]:
                    results.append((key, entry.value))
        
        return results
    
    def delete(self, key: str) -> bool:
        """Delete a memory entry.
        
        Args:
            key: Memory key
            
        Returns:
            True if deleted
        """
        with self._lock:
            if key in self._memory:
                del self._memory[key]
                
                if self.persist_path:
                    self._save()
                
                debug_logger.info("Memory deleted", {"key": key})
                return True
        
        return False
    
    def clear_session(self, session_id: str) -> int:
        """Clear memory for specific session.
        
        Args:
            session_id: Session ID to clear
            
        Returns:
            Number of entries cleared
        """
        cleared = 0
        
        with self._lock:
            to_delete = [
                k for k, e in self._memory.items()
                if e.session_id == session_id
            ]
            
            for key in to_delete:
                del self._memory[key]
                cleared += 1
        
        if cleared > 0 and self.persist_path:
            self._save()
        
        debug_logger.info("Session cleared", {"session_id": session_id, "count": cleared})
        
        return cleared
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        
        with self._lock:
            expired = [k for k, e in self._memory.items() if e.is_expired()]
            
            for key in expired:
                del self._memory[key]
                removed += 1
        
        if removed > 0 and self.persist_path:
            self._save()
        
        debug_logger.info("Expired cleaned", {"removed": removed})
        
        return removed
    
    def count(self) -> int:
        """Get total entry count (non-expired)."""
        with self._lock:
            return sum(1 for e in self._memory.values() if not e.is_expired())
    
    def get_all(self) -> dict[str, Any]:
        """Get all memory as dictionary.
        
        Returns:
            Dict of key -> value
        """
        result = {}
        
        with self._lock:
            for key, entry in self._memory.items():
                if not entry.is_expired():
                    result[key] = entry.value
        
        return result
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry to maintain max size."""
        if not self._memory:
            return
        
        oldest_key = min(
            self._memory.items(),
            key=lambda x: x[1].timestamp
        )[0]
        
        del self._memory[oldest_key]
        
        debug_logger.info("Oldest entry evicted", {"key": oldest_key})
    
    def _save(self) -> None:
        """Save memories to file."""
        if not self.persist_path:
            return
        
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persist_path.open("w", encoding="utf-8") as f:
                data = {k: e.to_dict() for k, e in self._memory.items()}
                json.dump(data, f)
        except OSError as e:
            debug_logger.error("Memory save failed", {"error": str(e)})
    
    def _load(self) -> None:
        """Load memories from file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._memory = {
                    k: SessionMemoryEntry.from_dict(v)
                    for k, v in data.items()
                }
            debug_logger.info("Memory loaded", {"count": len(self._memory)})
        except (json.JSONDecodeError, OSError) as e:
            debug_logger.warning("Memory load failed", {"error": str(e)})


def create_session_memory() -> SessionMemory:
    """Create SessionMemory with default settings.
    
    Returns:
        Configured SessionMemory instance
    """
    return SessionMemory(
        persist_path=Path("central_agent") / "reports" / "session_memory.json",
        default_ttl=3600.0,
        max_entries=500
    )