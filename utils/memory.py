"""Agent memory module for knowledge storage.

Provides key-value storage with TTL, tag-based search,
and persistent backup for agent knowledge.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import config


@dataclass
class MemoryEntry:
    """Single memory entry."""
    key: str
    value: Any
    timestamp: float
    tags: list[str] = field(default_factory=list)
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        return cls(
            key=data.get("key", ""),
            value=data.get("value"),
            timestamp=data.get("timestamp", time.time()),
            tags=data.get("tags", []),
            ttl=data.get("ttl"),
        )


class AgentMemory:
    """Agent knowledge memory storage.
    
    Provides persistent storage for agent knowledge
    with TTL support and tag-based retrieval.
    
    Attributes:
        max_entries: Maximum entries to keep
        persist_path: Optional path for file persistence
    """
    
    def __init__(
        self,
        max_entries: int = 100,
        persist_path: Optional[Path] = None
    ):
        self.max_entries = max_entries
        self.persist_path = persist_path
        self._entries: dict[str, MemoryEntry] = {}
        self._lock = Lock()
        
        if persist_path:
            self._load()
    
    def set(
        self,
        key: str,
        value: Any,
        tags: Optional[list[str]] = None,
        ttl: Optional[float] = None
    ) -> None:
        """Store a memory entry.
        
        Args:
            key: Memory key
            value: Memory value
            tags: Optional tags for categorization
            ttl: Time-to-live in seconds (None = no expiry)
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            tags=tags or [],
            ttl=ttl
        )
        
        with self._lock:
            self._entries[key] = entry
            
            if len(self._entries) > self.max_entries:
                oldest = min(self._entries.values(), key=lambda e: e.timestamp)
                del self._entries[oldest.key]
        
        if self.persist_path:
            self._save()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a memory entry.
        
        Args:
            key: Memory key
            
        Returns:
            Memory value or None
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:
                del self._entries[key]
            return None
    
    def get_entry(self, key: str) -> Optional[MemoryEntry]:
        """Get full memory entry.
        
        Args:
            key: Memory key
            
        Returns:
            MemoryEntry or None
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry and not entry.is_expired():
                return entry
            elif entry:
                del self._entries[key]
            return None
    
    def search(self, query: str) -> list[tuple[str, Any]]:
        """Search memories by key or tag.
        
        Args:
            query: Search query
            
        Returns:
            List of (key, value) tuples
        """
        results = []
        query_lower = query.lower()
        
        with self._lock:
            for key, entry in self._entries.items():
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
            count: Number of entries
            
        Returns:
            List of (key, value) tuples (newest first)
        """
        with self._lock:
            valid = [e for e in self._entries.values() if not e.is_expired()]
            valid.sort(key=lambda e: e.timestamp, reverse=True)
            return [(e.key, e.value) for e in valid[:count]]
    
    def get_by_tag(self, tag: str) -> list[tuple[str, Any]]:
        """Get memories by tag.
        
        Args:
            tag: Tag to filter
            
        Returns:
            List of (key, value) tuples
        """
        results = []
        tag_lower = tag.lower()
        
        with self._lock:
            for key, entry in self._entries.items():
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
            if key in self._entries:
                del self._entries[key]
                if self.persist_path:
                    self._save()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all memories."""
        with self._lock:
            self._entries.clear()
        
        if self.persist_path:
            self._save()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        
        with self._lock:
            expired = [k for k, e in self._entries.items() if e.is_expired()]
            for key in expired:
                del self._entries[key]
                removed += 1
        
        if removed and self.persist_path:
            self._save()
        
        return removed
    
    def count(self) -> int:
        """Get total entry count.
        
        Returns:
            Number of stored entries
        """
        with self._lock:
            return sum(1 for e in self._entries.values() if not e.is_expired())
    
    def _save(self) -> None:
        """Save memories to file."""
        if not self.persist_path:
            return
        
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persist_path.open("w", encoding="utf-8") as f:
                data = {k: e.to_dict() for k, e in self._entries.items()}
                json.dump(data, f)
        except OSError:
            pass
    
    def _load(self) -> None:
        """Load memories from file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with self.persist_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._entries = {k: MemoryEntry.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            pass


class KnowledgeBase:
    """Structured knowledge base for common patterns.
    
    Predefined knowledge categories with helpers.
    """
    
    def __init__(self, memory: AgentMemory):
        self.memory = memory
    
    def add_anomaly(self, anomaly: str, details: dict[str, Any]) -> None:
        """Store anomaly knowledge.
        
        Args:
            anomaly: Anomaly description
            details: Anomaly details
        """
        self.memory.set(
            key=f"anomaly:{anomaly}",
            value=details,
            tags=["anomaly", "detection"],
            ttl=3600
        )
    
    def add_threat(self, threat: str, details: dict[str, Any]) -> None:
        """Store threat intelligence.
        
        Args:
            threat: Threat description
            details: Threat details
        """
        self.memory.set(
            key=f"threat:{threat}",
            value=details,
            tags=["threat", "security"],
            ttl=None
        )
    
    def add_system_knowledge(self, key: str, value: Any) -> None:
        """Store system knowledge.
        
        Args:
            key: Knowledge key
            value: Knowledge value
        """
        self.memory.set(
            key=f"system:{key}",
            value=value,
            tags=["system", "knowledge"]
        )
    
    def get_anomalies(self) -> list[tuple[str, Any]]:
        """Get stored anomalies.
        
        Returns:
            List of (key, value) tuples
        """
        return self.memory.get_by_tag("anomaly")
    
    def get_threats(self) -> list[tuple[str, Any]]:
        """Get stored threats.
        
        Returns:
            List of (key, value) tuples
        """
        return self.memory.get_by_tag("threat")


def create_memory() -> AgentMemory:
    """Create agent memory with config settings.
    
    Returns:
        AgentMemory instance
    """
    return AgentMemory(
        max_entries=config.MEMORY_MAX_ENTRIES,
        persist_path=config.LOG_DIR / "memory.json"
    )


def create_knowledge_base() -> KnowledgeBase:
    """Create knowledge base with config settings.
    
    Returns:
        KnowledgeBase instance
    """
    return KnowledgeBase(create_memory())