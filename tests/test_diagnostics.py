"""Tests for Diagnostic modules (formerly sensors)."""
import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProcessSensor:
    """Tests for process_sensor."""

    def test_collect(self):
        """Test process collection."""
        from diagnostics import process_sensor
        context = {}
        result = process_sensor.collect(context)
        assert result is not None
        assert "count" in result

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import process_sensor
        context = {}
        result = process_sensor.collect(context)
        assert isinstance(result, dict)


class TestPortSensor:
    """Tests for port_sensor."""

    def test_collect(self):
        """Test port collection."""
        from diagnostics import port_sensor
        context = {}
        result = port_sensor.collect(context)
        assert result is not None
        assert "count" in result

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import port_sensor
        context = {}
        result = port_sensor.collect(context)
        assert isinstance(result, dict)


class TestFileSensor:
    """Tests for file_sensor."""

    def test_collect(self):
        """Test file collection."""
        from diagnostics import file_sensor
        context = {}
        result = file_sensor.collect(context)
        assert result is not None

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import file_sensor
        context = {}
        result = file_sensor.collect(context)
        assert isinstance(result, dict)

    def test_collect_has_change_count(self):
        """Test collect has change_count."""
        from diagnostics import file_sensor
        context = {}
        result = file_sensor.collect(context)
        assert "change_count" in result


class TestDiagnosticsImports:
    """Test diagnostics module imports."""

    def test_import_diagnostics(self):
        """Test diagnostics package imports."""
        from diagnostics import process_sensor, port_sensor, file_sensor
        assert process_sensor is not None
        assert port_sensor is not None
        assert file_sensor is not None


class TestDiagnosticsConfig:
    """Test diagnostics configuration."""

    def test_diagnostics_registered(self):
        """Test diagnostics are registered in config."""
        import config
        assert "process_sensor" in config.POLL_INTERVALS
        assert "port_sensor" in config.POLL_INTERVALS
        assert "file_sensor" in config.POLL_INTERVALS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])