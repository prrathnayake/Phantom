"""Context Manager for Agent.

Manages session context for analysis runs, providing
clean separation between analysis cycles.
"""
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

from src.utils.debug_log import debug_logger


@dataclass
class SessionContext:
    """Container for analysis session context."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    payloads: list[dict[str, Any]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def age(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at
    
    def is_expired(self, timeout: int) -> bool:
        """Check if session has expired."""
        return self.age() > timeout
    
    def add_payload(self, payload: dict[str, Any]) -> None:
        """Add diagnostic payload to session."""
        self.payloads.append(payload)
        self.updated_at = time.time()
    
    def add_finding(self, finding: str) -> None:
        """Add analysis finding to session."""
        self.findings.append(finding)
        self.updated_at = time.time()


class ContextManager:
    """Manages session context for analysis runs.
    
    Provides session lifecycle management with automatic
    cleanup of expired sessions.
    
    Attributes:
        session_timeout: Seconds before session expires (default 3600)
        max_sessions: Maximum concurrent sessions (default 100)
    """
    
    def __init__(
        self,
        session_timeout: int = 3600,
        max_sessions: int = 100
    ):
        self.session_timeout = session_timeout
        self.max_sessions = max_sessions
        self._sessions: dict[str, SessionContext] = {}
        self._lock = Lock()
        
        debug_logger.info(
            "ContextManager initialized",
            {"timeout": session_timeout, "max_sessions": max_sessions}
        )
    
    def create_session(self, session_id: Optional[str] = None) -> SessionContext:
        """Create new analysis session.
        
        Args:
            session_id: Optional session ID (generated if not provided)
            
        Returns:
            New SessionContext instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            if len(self._sessions) >= self.max_sessions:
                self._evict_oldest()
            
            session = SessionContext(session_id=session_id)
            self._sessions[session_id] = session
            
            debug_logger.info("Session created", {"session_id": session_id})
            
            return session
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Retrieve session context.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            SessionContext if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                debug_logger.info(
                    "Session not found",
                    {"session_id": session_id}
                )
                return None
            
            if session.is_expired(self.session_timeout):
                debug_logger.info(
                    "Session expired",
                    {"session_id": session_id, "age": session.age()}
                )
                del self._sessions[session_id]
                return None
            
            debug_logger.info(
                "Session retrieved",
                {"session_id": session_id, "payloads": len(session.payloads)}
            )
            
            return session
    
    def update_context(
        self,
        session_id: str,
        payload: dict[str, Any]
    ) -> bool:
        """Update session with new diagnostic payload.
        
        Args:
            session_id: Session ID to update
            payload: Diagnostic payload to add
            
        Returns:
            True if updated successfully
        """
        session = self.get_session(session_id)
        
        if session is None:
            session = self.create_session(session_id)
        
        with self._lock:
            session.add_payload(payload)
        
        debug_logger.info(
            "Context updated",
            {"session_id": session_id, "payload_count": len(session.payloads)}
        )
        
        return True
    
    def add_finding(
        self,
        session_id: str,
        finding: str
    ) -> bool:
        """Add analysis finding to session.
        
        Args:
            session_id: Session ID
            finding: Finding text to add
            
        Returns:
            True if added successfully
        """
        session = self.get_session(session_id)
        
        if session is None:
            debug_logger.warning(
                "Cannot add finding - session not found",
                {"session_id": session_id}
            )
            return False
        
        with self._lock:
            session.add_finding(finding)
        
        debug_logger.info(
            "Finding added",
            {"session_id": session_id, "finding_count": len(session.findings)}
        )
        
        return True
    
    def get_all_payloads(self, session_id: str) -> list[dict[str, Any]]:
        """Get all payloads for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of payloads (empty if session not found)
        """
        session = self.get_session(session_id)
        
        if session is None:
            return []
        
        return list(session.payloads)
    
    def get_context_summary(self, session_id: str) -> dict[str, Any]:
        """Get context summary for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Summary dict with session info
        """
        session = self.get_session(session_id)
        
        if session is None:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "age_seconds": session.age(),
            "payload_count": len(session.payloads),
            "finding_count": len(session.findings),
            "metadata": session.metadata,
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired sessions.
        
        Returns:
            Number of sessions removed
        """
        removed = 0
        
        with self._lock:
            expired = [
                sid for sid, sess in self._sessions.items()
                if sess.is_expired(self.session_timeout)
            ]
            
            for sid in expired:
                del self._sessions[sid]
                removed += 1
                debug_logger.info("Session expired", {"session_id": sid})
        
        if removed > 0:
            debug_logger.info(
                "Cleanup complete",
                {"removed": removed, "remaining": len(self._sessions)}
            )
        
        return removed
    
    def clear_all(self) -> None:
        """Clear all sessions."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
        
        debug_logger.info("All sessions cleared", {"count": count})
    
    def _evict_oldest(self) -> None:
        """Evict oldest expired session."""
        if not self._sessions:
            return
        
        oldest_sid = min(
            self._sessions.items(),
            key=lambda x: x[1].created_at
        )[0]
        
        del self._sessions[oldest_sid]
        
        debug_logger.info("Oldest session evicted", {"session_id": oldest_sid})
    
    def session_count(self) -> int:
        """Get active session count."""
        with self._lock:
            return len(self._sessions)


def create_context_manager() -> ContextManager:
    """Create ContextManager with default settings.
    
    Returns:
        Configured ContextManager instance
    """
    return ContextManager(
        session_timeout=3600,
        max_sessions=100
    )
