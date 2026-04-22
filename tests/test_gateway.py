"""Tests for Gateway modules."""
import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestScheduleManager:
    """Tests for ScheduleManager."""

    def test_create_manager(self):
        """Test manager creation."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        assert mgr is not None

    def test_add_schedule(self):
        """Test adding schedule."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        calls = []
        def test_func(ctx):
            calls.append(1)
        mgr.add_schedule("test-schedule", 60, "test_module", test_func)
        assert "test-schedule" in mgr._schedules

    def test_remove_schedule(self):
        """Test removing schedule."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        calls = []
        def test_func(ctx):
            calls.append(1)
        mgr.add_schedule("remove-test", 60, "test_module", test_func)
        result = mgr.remove_schedule("remove-test")
        assert result is True

    def test_enable_schedule(self):
        """Test enabling schedule."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        def test_func(ctx):
            pass
        mgr.add_schedule("enable-test", 60, "test_module", test_func)
        mgr.disable_schedule("enable-test")
        result = mgr.enable_schedule("enable-test")
        assert result is True

    def test_disable_schedule(self):
        """Test disabling schedule."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        def test_func(ctx):
            pass
        mgr.add_schedule("disable-test", 60, "test_module", test_func)
        result = mgr.disable_schedule("disable-test")
        assert result is True

    def test_run_schedule(self):
        """Test running schedule."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        calls = []
        def test_func(ctx):
            calls.append(1)
        mgr.add_schedule("run-test", 60, "test_module", test_func)
        result = mgr.run_schedule("run-test")
        assert result is not None
        assert len(calls) == 1

    def test_collect_results(self):
        """Test collecting results."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        def test_func(ctx):
            ctx["result"] = "test"
        mgr.add_schedule("collect-test", 60, "test_module", test_func)
        mgr.run_schedule("collect-test")
        results = mgr.collect_results()
        assert "collect-test" in results

    def test_get_schedule_info(self):
        """Test getting schedule info."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        def test_func(ctx):
            pass
        mgr.add_schedule("info-test", 60, "test_module", test_func)
        info = mgr.get_schedule_info("info-test")
        assert info is not None
        assert info["name"] == "info-test"

    def test_get_all_schedules(self):
        """Test getting all schedules."""
        from gateway.schedule_manager import ScheduleManager
        mgr = ScheduleManager()
        def test_func(ctx):
            pass
        mgr.add_schedule("all-1", 60, "test_module", test_func)
        mgr.add_schedule("all-2", 60, "test_module", test_func)
        schedules = mgr.get_all_schedules()
        assert len(schedules) == 2

    def test_create_schedule_manager_registers_defaults(self):
        """Test default configured schedules are registered."""
        import config
        from gateway.schedule_manager import create_schedule_manager

        mgr = create_schedule_manager()
        schedules = mgr.get_all_schedules()

        assert len(schedules) == len(config.POLL_INTERVALS)
        for name in config.POLL_INTERVALS:
            assert name in schedules

    def test_run_schedule_uses_returned_collector_payload(self):
        """Test returned collector data is captured in the run result."""
        from gateway.schedule_manager import ScheduleManager

        mgr = ScheduleManager()

        def test_func(ctx):
            ctx["shared_snapshot"] = {"old": "state"}
            return {"fresh": "payload"}

        mgr.add_schedule("returned-payload", 60, "test_module", test_func)
        result = mgr.run_schedule("returned-payload")

        assert result is not None
        assert result["data"] == {"fresh": "payload"}

    def test_update_interval(self):
        """Test schedule interval updates reset next run."""
        from gateway.schedule_manager import ScheduleManager

        mgr = ScheduleManager()

        def test_func(ctx):
            return {}

        mgr.add_schedule("interval-test", 60, "test_module", test_func)
        assert mgr.update_interval("interval-test", 120) is True
        assert mgr.get_schedule_info("interval-test")["interval"] == 120
        assert mgr.update_interval("missing", 120) is False
        assert mgr.update_interval("interval-test", 5) is False


class TestPayloadSender:
    """Tests for PayloadSender."""

    def test_create_sender(self):
        """Test sender creation."""
        from gateway.payload_sender import PayloadSender
        sender = PayloadSender()
        assert sender is not None


class TestGatewayServer:
    """Tests for Gateway server."""

    def test_create_gateway(self):
        """Test gateway creation."""
        from gateway.server import Gateway
        gw = Gateway(autonomous=False)
        assert gw is not None
        assert gw.schedule_manager is not None
        assert gw.payload_sender is not None
        assert gw.http_server is not None

    def test_get_status(self):
        """Test getting status."""
        from gateway.server import Gateway
        gw = Gateway(autonomous=False)
        status = gw.get_status()
        assert isinstance(status, dict)
        assert "running" in status


class TestInterfaces:
    """Tests for Gateway interfaces."""

    def test_http_handler_import(self):
        """Test HTTP handler import."""
        from gateway.interfaces.http_handler import HTTPHandler, GatewayHTTPServer
        assert HTTPHandler is not None
        assert GatewayHTTPServer is not None

    def test_cli_handler_import(self):
        """Test CLI handler import."""
        from gateway.interfaces.cli_handler import CLIHandler
        assert CLIHandler is not None

    def test_queue_handler_import(self):
        """Test queue handler import."""
        from gateway.interfaces.queue_handler import QueueHandler
        assert QueueHandler is not None

    def test_file_trigger_import(self):
        """Test file trigger import."""
        from gateway.interfaces.file_trigger import FileTrigger
        assert FileTrigger is not None

    def test_websocket_handler_import(self):
        """Test websocket handler import."""
        from gateway.interfaces.websocket_handler import WebSocketHandler
        assert WebSocketHandler is not None


class TestGatewayImports:
    """Test gateway module imports."""

    def test_import_gateway_package(self):
        """Test gateway package imports."""
        from gateway import (
            ScheduleManager,
            create_schedule_manager,
            PayloadSender,
        )
        assert ScheduleManager is not None
        assert PayloadSender is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
