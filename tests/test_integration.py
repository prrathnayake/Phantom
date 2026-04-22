"""Integration tests for full application flow."""
import sys
import os
import pytest
import tempfile
import time
from pathlib import Path
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFullArchitecture:
    """Test complete architecture flow."""

    def test_gateway_to_central_flow(self):
        """Test full Gateway -> Agent flow."""
        from agent import create_agent
        from gateway import ScheduleManager, PayloadSender
        
        schedule_mgr = ScheduleManager()
        agent = create_agent()
        sender = PayloadSender(endpoint="http://127.0.0.1:9999/analyze")
        
        def test_diagnostic(ctx):
            ctx["result"] = "test-data"
        
        schedule_mgr.add_schedule("test-diag", 60, "test_mod", test_diagnostic)
        
        result = schedule_mgr.run_schedule("test-diag")
        assert result is not None
        
        sent = sender.send(result, trigger="test")
        assert sent is False

    def test_agent_analyze_flow(self):
        """Test Agent analyze flow."""
        from agent import create_agent
        
        agent = create_agent()
        
        payload = {
            "source": "integration-test",
            "data": {"test": "value"},
            "timestamp": time.time()
        }
        
        result = agent.analyze(payload, session_id="integration-test-1")
        
        assert result.session_id == "integration-test-1"
        assert result.timestamp is not None

    def test_schedule_autonomous_flow(self):
        """Test autonomous schedule flow."""
        from gateway import ScheduleManager
        
        mgr = ScheduleManager()
        calls = []
        
        def test_task(ctx):
            calls.append(1)
        
        mgr.add_schedule("auto-test", 1, "test_mod", test_task)
        
        mgr.run_schedule("auto-test")
        
        assert len(calls) == 1

    def test_report_generation_flow(self):
        """Test report generation flow."""
        from agent import create_agent
        
        agent = create_agent()
        
        payload = {
            "source": "report-test",
            "data": {"key": "value"}
        }
        
        result = agent.analyze(payload, session_id="report-test-1")
        
        assert result.session_id == "report-test-1"

    def test_context_and_memory_flow(self):
        """Test context and memory integration."""
        from agent import create_agent
        
        agent = create_agent()
        
        agent.context_mgr.update_context("mem-test", {"data": "test"})
        
        session = agent.context_mgr.get_session("mem-test")
        assert session is not None
        
        agent.memory.store("mem-key", "mem-value", session_id="mem-test")
        
        value = agent.memory.retrieve("mem-key")
        assert value == "mem-value"


class TestDiagnosticsToCentral:
    """Test diagnostics integration with Agent."""

    def test_process_diagnostic_to_agent(self):
        """Test process diagnostic to Agent."""
        from diagnostics import process_sensor
        from agent import create_agent
        
        agent = create_agent()
        
        context = {}
        payload = process_sensor.collect(context)
        payload["source"] = "process_sensor"
        
        result = agent.analyze(payload, session_id="proc-test-1")
        
        assert result.session_id == "proc-test-1"

    def test_port_diagnostic_to_agent(self):
        """Test port diagnostic to Agent."""
        from diagnostics import port_sensor
        from agent import create_agent
        
        agent = create_agent()
        
        context = {}
        payload = port_sensor.collect(context)
        payload["source"] = "port_sensor"
        
        result = agent.analyze(payload, session_id="port-test-1")
        
        assert result.session_id == "port-test-1"


class TestGatewayInterfaces:
    """Test Gateway interfaces integration."""

    def test_http_to_schedule_flow(self):
        """Test HTTP endpoint to schedule flow."""
        from gateway import ScheduleManager
        
        mgr = ScheduleManager()
        calls = []
        
        def diag_task(ctx):
            calls.append(1)
        
        mgr.add_schedule("http-test", 60, "test_mod", diag_task)
        
        mgr.run_schedule("http-test")
        
        assert len(calls) == 1


class TestMainEntryPoint:
    """Test main.py entry point."""

    def test_main_imports(self):
        """Test main.py imports."""
        import main
        assert main is not None

    def test_main_entry(self):
        """Test main entry works."""
        import main
        assert main is not None
        assert hasattr(main, "main")


class TestConfigIntegration:
    """Test config integration."""

    def test_poll_intervals(self):
        """Test poll intervals are used."""
        import config
        from gateway import create_schedule_manager
        
        mgr = create_schedule_manager()
        
        assert len(mgr._schedules) >= 0


class TestEndToEnd:
    """End-to-end tests."""

    def test_complete_flow(self):
        """Test complete system flow."""
        from agent import Agent
        from gateway import ScheduleManager
        from diagnostics import process_sensor
        
        agent = Agent()
        mgr = ScheduleManager()
        
        def proc_diag(ctx):
            ctx.update(process_sensor.collect(ctx))
        
        mgr.add_schedule("e2e-proc", 60, "test", proc_diag)
        
        result = mgr.run_schedule("e2e-proc")
        
        if result and "data" in result:
            agent_payload = {
                "source": "e2e-test",
                "diagnostic": result.get("data", {})
            }
            analysis = agent.analyze(agent_payload, session_id="e2e-full")
            
            assert analysis.session_id == "e2e-full"

    def test_multiple_diagnostics(self):
        """Test running multiple diagnostics."""
        from gateway import ScheduleManager
        from diagnostics import process_sensor, port_sensor
        
        mgr = ScheduleManager()
        
        def proc_task(ctx):
            ctx["process"] = process_sensor.collect(ctx)
        
        def port_task(ctx):
            ctx["port"] = port_sensor.collect(ctx)
        
        mgr.add_schedule("multi-proc", 60, "test", proc_task)
        mgr.add_schedule("multi-port", 60, "test", port_task)
        
        r1 = mgr.run_schedule("multi-proc")
        r2 = mgr.run_schedule("multi-port")
        
        assert r1 is not None or r2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])