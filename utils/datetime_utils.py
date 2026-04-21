"""Datetime utilities for Phantom."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime.
    
    Use this instead of deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    """Return current UTC time as ISO format string."""
    return utcnow().isoformat()