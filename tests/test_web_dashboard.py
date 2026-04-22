"""Tests for the Flask dashboard routes and APIs."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture()
def webapp():
    import apps.web.app as web_app

    web_app.create_app()
    web_app.app.config.update(TESTING=True)
    return web_app


@pytest.fixture()
def client(webapp):
    return webapp.app.test_client()


def test_dashboard_pages_load(client):
    """Test primary dashboard pages render."""
    for route in ["/", "/diagnostics", "/monitor", "/reports", "/approvals", "/alerts", "/docs"]:
        response = client.get(route)
        assert response.status_code == 200


def test_status_handles_mixed_timestamps(client, webapp, monkeypatch):
    """Test status API handles naive, aware, missing, and malformed timestamps."""
    now_aware = datetime.now(timezone.utc).isoformat()
    now_naive = datetime.now().isoformat()

    class FakeStorage:
        def get_recent_events(self, count=1000):
            return [
                {"timestamp": now_aware, "sensor": "aware", "data": {}},
                {"timestamp": now_naive, "sensor": "naive", "data": {}},
                {"timestamp": "not-a-date", "sensor": "bad", "data": {}},
                {"sensor": "missing", "data": {}},
            ]

        def get_recent_detections(self, count=1000):
            return [
                {"timestamp": now_aware, "rule": "aware"},
                {"timestamp": now_naive, "rule": "naive"},
                {"timestamp": "not-a-date", "rule": "bad"},
                {"rule": "missing"},
            ]

    monkeypatch.setattr(webapp, "storage", FakeStorage())

    response = client.get("/api/status")
    data = response.get_json()

    assert response.status_code == 200
    assert data["events_24h"] == 2
    assert data["detections_24h"] == 2
    assert "llm_health" in data


def test_create_network_schedule_via_api(client):
    """Test dashboard schedule creation supports network sensor."""
    response = client.post(
        "/api/schedules/create",
        json={"name": "network-web-test", "interval": 30, "sensor": "network"},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True

    schedules = client.get("/api/schedules").get_json()
    assert "network-web-test" in schedules


def test_report_api_restricts_paths(client, webapp, tmp_path, monkeypatch):
    """Test report API allows relative report IDs and rejects absolute paths."""
    reports_root = tmp_path / "reports"
    report_dir = reports_root / "2026-04-22"
    report_dir.mkdir(parents=True)
    report = report_dir / "sample.md"
    report.write_text("# Safe report", encoding="utf-8")

    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(webapp, "REPORTS_ROOT", reports_root)

    allowed = client.get("/api/report/2026-04-22/sample.md")
    denied = client.get("/api/report/" + quote(str(outside), safe=""))
    traversal = client.get("/api/report/" + quote("../outside.md", safe=""))

    assert allowed.status_code == 200
    assert allowed.get_data(as_text=True) == "# Safe report"
    assert denied.status_code == 404
    assert traversal.status_code == 404


def test_llm_unavailable_returns_fallback_without_secret(client, webapp, monkeypatch):
    """Test diagnostic API exposes fallback status without leaking credentials."""
    secret = "sk-should-not-leak"

    class FakeModule:
        @staticmethod
        def collect(context):
            return {"count": 3}

    fake_agent = SimpleNamespace(
        llm_client=SimpleNamespace(
            get_health=lambda: {
                "configured": True,
                "model": "test-model",
                "status": "failed",
                "error_category": "auth_error",
            }
        ),
        analyze=lambda **kwargs: SimpleNamespace(
            analysis="LLM analysis unavailable - check API configuration",
            risk_level="LOW",
        ),
    )

    monkeypatch.setattr(webapp, "agent", fake_agent)
    monkeypatch.setattr(webapp, "_load_sensor_module", lambda module: FakeModule)

    response = client.post("/api/diagnostics/run", json={"diagnostic": "process"})
    body = response.get_json()
    encoded = json.dumps(body)

    assert response.status_code == 200
    assert body["analysis_status"] == "llm_unavailable"
    assert "fallback_summary" in body
    assert secret not in encoded
    assert "api_key" not in encoded.lower()
