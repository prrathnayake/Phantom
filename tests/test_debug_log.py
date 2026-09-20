from __future__ import annotations

from src.utils.debug_log import DebugLogger


def test_disabled_debug_logger_does_not_create_log_directory(monkeypatch, tmp_path):
    import config

    monkeypatch.setattr(config, "DEBUG_MODE", False)
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "ensure_log_dir", lambda: (_ for _ in ()).throw(AssertionError("unexpected directory setup")))

    logger = DebugLogger()
    logger.info("should be ignored")

    assert not (tmp_path / "logs").exists()


def test_enabled_debug_logger_creates_log_file(monkeypatch, tmp_path):
    import config

    monkeypatch.setattr(config, "DEBUG_MODE", True)
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "ensure_log_dir", lambda: config.LOG_DIR.mkdir(parents=True, exist_ok=True))

    logger = DebugLogger()
    logger.task("worker", "started", {"worker_id": "worker-1"})

    log_file = tmp_path / "logs" / "debug.log"
    assert log_file.exists()
    assert "worker-1" in log_file.read_text(encoding="utf-8")
