"""Tests for sensor modules."""
import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProcessSensor:
    """Tests for process_sensor module."""

    def test_collect_returns_dict(self, mock_context):
        """Test collect returns a dictionary."""
        from sensors import process_sensor
        result = process_sensor.collect(mock_context)
        assert isinstance(result, dict)

    def test_collect_has_required_keys(self, mock_context):
        """Test collect returns required keys."""
        from sensors import process_sensor
        result = process_sensor.collect(mock_context)
        assert "count" in result
        assert "top_processes" in result
        assert isinstance(result["top_processes"], list)

    def test_collect_count_is_int(self, mock_context):
        """Test process count is an integer."""
        from sensors import process_sensor
        result = process_sensor.collect(mock_context)
        assert isinstance(result["count"], int)
        assert result["count"] >= 0

    def test_top_processes_structure(self, mock_context):
        """Test top processes have required fields."""
        from sensors import process_sensor
        result = process_sensor.collect(mock_context)
        for proc in result["top_processes"]:
            assert "pid" in proc
            assert "name" in proc


class TestPortSensor:
    """Tests for port_sensor module."""

    def test_collect_returns_dict(self, mock_context):
        """Test collect returns a dictionary."""
        from sensors import port_sensor
        result = port_sensor.collect(mock_context)
        assert isinstance(result, dict)

    def test_collect_has_required_keys(self, mock_context):
        """Test collect returns required keys."""
        from sensors import port_sensor
        result = port_sensor.collect(mock_context)
        assert "count" in result
        assert "listening" in result

    def test_collect_count_is_int(self, mock_context):
        """Test port count is an integer."""
        from sensors import port_sensor
        result = port_sensor.collect(mock_context)
        assert isinstance(result["count"], int)
        assert result["count"] >= 0

    def test_listening_entries(self, mock_context):
        """Test listening entries have protocol and address."""
        from sensors import port_sensor
        result = port_sensor.collect(mock_context)
        for entry in result["listening"]:
            assert "protocol" in entry
            assert "address" in entry


class TestFileSensor:
    """Tests for file_sensor module."""

    def test_collect_returns_dict(self, mock_context):
        """Test collect returns a dictionary."""
        from sensors import file_sensor
        result = file_sensor.collect(mock_context)
        assert isinstance(result, dict)

    def test_collect_has_required_keys(self, mock_context):
        """Test collect returns required keys."""
        from sensors import file_sensor
        result = file_sensor.collect(mock_context)
        assert "directory" in result
        assert "added" in result
        assert "removed" in result
        assert "modified" in result
        assert "change_count" in result

    def test_collect_change_count_is_int(self, mock_context):
        """Test change_count is an integer."""
        from sensors import file_sensor
        result = file_sensor.collect(mock_context)
        assert isinstance(result["change_count"], int)
        assert result["change_count"] >= 0

    def test_collect_change_lists_are_lists(self, mock_context):
        """Test change lists are lists."""
        from sensors import file_sensor
        result = file_sensor.collect(mock_context)
        assert isinstance(result["added"], list)
        assert isinstance(result["removed"], list)
        assert isinstance(result["modified"], list)

    def test_snapshot_comparison(self, temp_dir):
        """Test snapshot comparison logic."""
        from sensors import file_sensor
        
        file1 = temp_dir / "file1.txt"
        file1.write_text("content1")
        
        prev = file_sensor._snapshot(temp_dir)
        assert str(file1) in prev
        
        file2 = temp_dir / "file2.txt"
        file2.write_text("content2")
        
        current = file_sensor._snapshot(temp_dir)
        added, removed, modified = file_sensor._compare_snapshots(prev, current)
        
        assert str(file2) in added
        assert len(removed) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])