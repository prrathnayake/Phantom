"""Tests for analysis/detection module."""
import sys
import os
import pytest
from unittest.mock import Mock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDetection:
    """Tests for detection module."""

    def test_detect_returns_list(self):
        """Test detect returns a list."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {}
        result = detection.detect(context, mock_storage)
        
        assert isinstance(result, list)

    def test_process_count_rule_triggers(self):
        """Test process count rule triggers on high count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "process_sensor_last": {"count": 500, "top_processes": []}
        }
        result = detection.detect(context, mock_storage)
        
        assert any(a["rule"] == "process_count" for a in result)

    def test_process_count_rule_no_trigger(self):
        """Test process count rule does not trigger on low count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "process_sensor_last": {"count": 10, "top_processes": []}
        }
        result = detection.detect(context, mock_storage)
        
        assert not any(a["rule"] == "process_count" for a in result)

    def test_open_ports_rule_triggers(self):
        """Test open ports rule triggers on high count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "port_sensor_last": {"count": 100, "listening": []}
        }
        result = detection.detect(context, mock_storage)
        
        assert any(a["rule"] == "open_ports" for a in result)

    def test_open_ports_rule_no_trigger(self):
        """Test open ports rule does not trigger on low count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "port_sensor_last": {"count": 5, "listening": []}
        }
        result = detection.detect(context, mock_storage)
        
        assert not any(a["rule"] == "open_ports" for a in result)

    def test_file_changes_rule_triggers(self):
        """Test file changes rule triggers on high count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "file_sensor_last": {
                "change_count": 600,
                "added": [],
                "removed": [],
                "modified": []
            }
        }
        result = detection.detect(context, mock_storage)
        
        assert any(a["rule"] == "file_changes" for a in result)

    def test_file_changes_rule_no_trigger(self):
        """Test file changes rule does not trigger on low count."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "file_sensor_last": {
                "change_count": 1,
                "added": [],
                "removed": [],
                "modified": []
            }
        }
        result = detection.detect(context, mock_storage)
        
        assert not any(a["rule"] == "file_changes" for a in result)

    def test_multiple_rules_can_trigger(self):
        """Test multiple rules can trigger simultaneously."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {
            "process_sensor_last": {"count": 500, "top_processes": []},
            "port_sensor_last": {"count": 100, "listening": []},
            "file_sensor_last": {
                "change_count": 600,
                "added": [],
                "removed": [],
                "modified": []
            }
        }
        result = detection.detect(context, mock_storage)
        
        assert len(result) == 3

    def test_detection_stores_to_storage(self):
        """Test detection writes to storage."""
        from analysis import detection
        mock_storage = Mock()
        
        context = {
            "process_sensor_last": {"count": 500, "top_processes": []}
        }
        detection.detect(context, mock_storage)
        
        mock_storage.log_detection.assert_called()

    def test_missing_payload_handled(self):
        """Test missing sensor payload is handled gracefully."""
        from analysis import detection
        mock_storage = Mock()
        mock_storage.log_detection = Mock()
        
        context = {}
        result = detection.detect(context, mock_storage)
        
        assert isinstance(result, list)
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])