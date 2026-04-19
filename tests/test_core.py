"""Tests for core modules: Storage and OpenRouterClient."""
import sys
import os
import pytest
import tempfile
import shutil
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStorage:
    """Tests for Storage module."""

    def test_storage_creation(self):
        """Test storage can be created."""
        from core import Storage
        storage = Storage()
        assert storage is not None

    def test_log_event(self):
        """Test logging an event."""
        from core import Storage
        storage = Storage()
        storage.log_event("test_sensor", {"test": "data"})
        
        events = storage.get_recent_events(count=1)
        assert len(events) > 0
        assert events[0]["sensor"] == "test_sensor"

    def test_log_detection(self):
        """Test logging a detection."""
        from core import Storage
        storage = Storage()
        storage.log_detection("test_rule", "Test detection", {"detail": "value"})
        
        detections = storage.get_recent_detections(count=1)
        assert len(detections) > 0
        assert detections[0]["rule"] == "test_rule"

    def test_get_recent_events_limit(self):
        """Test event count limit works."""
        from core import Storage
        storage = Storage()
        
        for i in range(5):
            storage.log_event(f"sensor_{i}", {"index": i})
        
        events = storage.get_recent_events(count=2)
        assert len(events) == 2

    def test_get_recent_events_filter_by_sensor(self):
        """Test filtering events by sensor name."""
        from core import Storage
        storage = Storage()
        
        storage.log_event("sensor_a", {"data": "a"})
        storage.log_event("sensor_b", {"data": "b"})
        
        events = storage.get_recent_events(sensor="sensor_a")
        for event in events:
            assert event["sensor"] == "sensor_a"

    def test_event_timestamp_format(self):
        """Test event has ISO timestamp."""
        from core import Storage
        from datetime import datetime
        storage = Storage()
        storage.log_event("test_sensor", {})
        
        events = storage.get_recent_events(count=1)
        timestamp = events[0]["timestamp"]
        
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid timestamp format")


class TestOpenRouterClient:
    """Tests for OpenRouterClient module."""

    def test_client_creation(self):
        """Test client can be created."""
        from core import OpenRouterClient
        client = OpenRouterClient()
        assert client is not None

    def test_client_has_config(self):
        """Test client has required configuration."""
        from core import OpenRouterClient
        client = OpenRouterClient()
        assert hasattr(client, "api_key")
        assert hasattr(client, "base_url")
        assert hasattr(client, "model")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])