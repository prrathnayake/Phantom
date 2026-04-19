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


class TestNetworkSensor:
    """Tests for network_sensor."""

    def test_collect(self):
        """Test network collection."""
        from diagnostics import network_sensor
        context = {}
        result = network_sensor.collect(context)
        assert result is not None
        assert "connection_count" in result

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import network_sensor
        context = {}
        result = network_sensor.collect(context)
        assert isinstance(result, dict)

    def test_collect_has_established(self):
        """Test collect has established_count."""
        from diagnostics import network_sensor
        context = {}
        result = network_sensor.collect(context)
        assert "established_count" in result


class TestMemorySensor:
    """Tests for memory_sensor."""

    def test_collect(self):
        """Test memory collection."""
        from diagnostics import memory_sensor
        context = {}
        result = memory_sensor.collect(context)
        assert result is not None
        assert "percent_used" in result

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import memory_sensor
        context = {}
        result = memory_sensor.collect(context)
        assert isinstance(result, dict)

    def test_collect_has_total(self):
        """Test collect has total_mb."""
        from diagnostics import memory_sensor
        context = {}
        result = memory_sensor.collect(context)
        assert "total_mb" in result


class TestDiskIOSensor:
    """Tests for disk_io_sensor."""

    def test_collect(self):
        """Test disk I/O collection."""
        from diagnostics import disk_io_sensor
        context = {}
        result = disk_io_sensor.collect(context)
        assert result is not None
        assert "disks" in result

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import disk_io_sensor
        context = {}
        result = disk_io_sensor.collect(context)
        assert isinstance(result, dict)

    def test_collect_has_disks(self):
        """Test collect has disks list."""
        from diagnostics import disk_io_sensor
        context = {}
        result = disk_io_sensor.collect(context)
        assert isinstance(result.get("disks"), list)


class TestAuthSensor:
    """Tests for auth_sensor."""

    def test_collect(self):
        """Test auth collection."""
        from diagnostics import auth_sensor
        context = {}
        result = auth_sensor.collect(context)
        assert result is not None

    def test_collect_returns_dict(self):
        """Test collect returns dictionary."""
        from diagnostics import auth_sensor
        context = {}
        result = auth_sensor.collect(context)
        assert isinstance(result, dict)

    def test_collect_has_failed_count(self):
        """Test collect has failed_count."""
        from diagnostics import auth_sensor
        context = {}
        result = auth_sensor.collect(context)
        assert "failed_count" in result


class TestDiagnosticsImports:
    """Test diagnostics module imports."""

    def test_import_diagnostics(self):
        """Test diagnostics package imports."""
        from diagnostics import (
            process_sensor,
            port_sensor,
            file_sensor,
            network_sensor,
            memory_sensor,
            disk_io_sensor,
            auth_sensor,
        )
        assert process_sensor is not None
        assert port_sensor is not None
        assert file_sensor is not None
        assert network_sensor is not None
        assert memory_sensor is not None
        assert disk_io_sensor is not None
        assert auth_sensor is not None


class TestDiagnosticsConfig:
    """Test diagnostics configuration."""

    def test_diagnostics_registered(self):
        """Test diagnostics are registered in config."""
        import config
        assert "process_sensor" in config.POLL_INTERVALS
        assert "port_sensor" in config.POLL_INTERVALS
        assert "file_sensor" in config.POLL_INTERVALS
        assert "network_sensor" in config.POLL_INTERVALS
        assert "memory_sensor" in config.POLL_INTERVALS
        assert "disk_io_sensor" in config.POLL_INTERVALS
        assert "auth_sensor" in config.POLL_INTERVALS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])