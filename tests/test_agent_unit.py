"""Tests for Agent modules."""
import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestContextManager:
    """Tests for ContextManager."""

    def test_create_session(self):
        """Test session creation."""
        from agent.context import ContextManager
        mgr = ContextManager()
        session = mgr.create_session("test-123")
        assert session is not None
        assert session.session_id == "test-123"

    def test_get_session(self):
        """Test session retrieval."""
        from agent.context import ContextManager
        mgr = ContextManager()
        mgr.create_session("test-456")
        session = mgr.get_session("test-456")
        assert session is not None

    def test_get_session_not_found(self):
        """Test session not found."""
        from agent.context import ContextManager
        mgr = ContextManager()
        session = mgr.get_session("nonexistent")
        assert session is None

    def test_update_context(self):
        """Test context update."""
        from agent.context import ContextManager
        mgr = ContextManager()
        mgr.update_context("test-789", {"key": "value"})
        session = mgr.get_session("test-789")
        assert session is not None
        assert len(session.payloads) == 1

    def test_add_finding(self):
        """Test adding finding."""
        from agent.context import ContextManager
        mgr = ContextManager()
        mgr.create_session("test-abc")
        result = mgr.add_finding("test-abc", "Test finding")
        assert result is True

    def test_cleanup_expired(self):
        """Test expired cleanup."""
        from agent.context import ContextManager
        mgr = ContextManager(session_timeout=1)
        mgr.create_session("expired-test")
        import time
        time.sleep(1.1)
        removed = mgr.cleanup_expired()
        assert removed >= 1

    def test_session_count(self):
        """Test session count."""
        from agent.context import ContextManager
        mgr = ContextManager()
        mgr.create_session("count-1")
        mgr.create_session("count-2")
        assert mgr.session_count() == 2


class TestSessionMemory:
    """Tests for SessionMemory."""

    def test_store_and_retrieve(self):
        """Test basic store/retrieve."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        mem.store("test-key", "test-value", session_id="s1")
        value = mem.retrieve("test-key")
        assert value == "test-value"

    def test_retrieve_not_found(self):
        """Test retrieve not found."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        value = mem.retrieve("nonexistent")
        assert value is None

    def test_get_for_session(self):
        """Test get for session."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        mem.store("key1", "value1", session_id="session-x")
        mem.store("key2", "value2", session_id="session-y")
        results = mem.get_for_session("session-x")
        assert len(results) == 1

    def test_search(self):
        """Test search."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        mem.store("search-key", "search-value", tags=["search", "test"])
        results = mem.search("search")
        assert len(results) >= 1

    def test_delete(self):
        """Test delete."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        mem.store("delete-key", "delete-value")
        result = mem.delete("delete-key")
        assert result is True

    def test_clear_session(self):
        """Test clear session."""
        from agent.memory import SessionMemory
        mem = SessionMemory()
        mem.store("key1", "val1", session_id="clear-sess")
        mem.store("key2", "val2", session_id="clear-sess")
        cleared = mem.clear_session("clear-sess")
        assert cleared == 2


class TestCentralAgent:
    """Tests for Agent."""

    def test_create_agent(self):
        """Test agent creation."""
        from agent.agent import Agent
        agent = Agent()
        assert agent is not None
        assert agent.context_mgr is not None
        assert agent.memory is not None

    def test_analyze_with_payload(self):
        """Test analysis with payload."""
        from agent.agent import Agent
        agent = Agent()
        payload = {
            "source": "test",
            "data": {"test": "value"}
        }
        result = agent.analyze(payload, session_id="analyze-test")
        assert result is not None
        assert result.session_id == "analyze-test"

    def test_get_recent_reports(self):
        """Test getting recent reports."""
        from agent.agent import Agent
        agent = Agent()
        reports = agent.get_recent_reports(count=5)
        assert isinstance(reports, list)

    def test_clear_session(self):
        """Test session clearing."""
        from agent.agent import Agent
        agent = Agent()
        agent.clear_session("clear-test")


class TestReportStorage:
    """Tests for ReportStorage."""

    def test_create_storage(self):
        """Test storage creation."""
        from agent.reports_storage import ReportStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = ReportStorage(reports_dir=Path(tmp))
            assert storage.reports_dir.exists()

    def test_save_report(self):
        """Test save report."""
        from agent.reports_storage import ReportStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = ReportStorage(reports_dir=Path(tmp))
            path = storage.save_report("test-session", "Test content")
            assert path.exists()

    def test_get_report(self):
        """Test get report."""
        from agent.reports_storage import ReportStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = ReportStorage(reports_dir=Path(tmp))
            storage.save_report("get-test", "Content")
            path = storage.get_report("get-test")
            assert path is not None

    def test_get_report_not_found(self):
        """Test get report not found."""
        from agent.reports_storage import ReportStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = ReportStorage(reports_dir=Path(tmp))
            path = storage.get_report("nonexistent")
            assert path is None

    def test_get_recent_reports(self):
        """Test get recent reports."""
        from agent.reports_storage import ReportStorage
        with tempfile.TemporaryDirectory() as tmp:
            storage = ReportStorage(reports_dir=Path(tmp))
            storage.save_report("recent-1", "Content 1")
            storage.save_report("recent-2", "Content 2")
            reports = storage.get_recent_reports(count=10)
            assert len(reports) == 2


class TestImports:
    """Test module imports."""

    def test_import_agent_package(self):
        """Test agent package imports."""
        from agent import (
            Agent,
            create_agent,
            ContextManager,
            create_context_manager,
            SessionMemory,
            create_session_memory,
            ReportStorage,
            create_report_storage,
        )
        assert Agent is not None
        assert ContextManager is not None
        assert SessionMemory is not None
        assert ReportStorage is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])