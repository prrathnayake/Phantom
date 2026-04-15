"""Tests for config module."""
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Tests for config module."""

    def test_log_dir_defined(self):
        """Test LOG_DIR is defined."""
        import config
        assert hasattr(config, "LOG_DIR")
        assert isinstance(config.LOG_DIR, Path)

    def test_poll_intervals_defined(self):
        """Test POLL_INTERVALS is defined."""
        import config
        assert hasattr(config, "POLL_INTERVALS")
        assert isinstance(config.POLL_INTERVALS, dict)
        assert "process_sensor" in config.POLL_INTERVALS

    def test_poll_intervals_values_are_integers(self):
        """Test poll interval values are integers."""
        import config
        for sensor, interval in config.POLL_INTERVALS.items():
            assert isinstance(interval, int)
            assert interval > 0

    def test_watch_directory_defined(self):
        """Test WATCH_DIRECTORY is defined."""
        import config
        assert hasattr(config, "WATCH_DIRECTORY")
        assert isinstance(config.WATCH_DIRECTORY, Path)

    def test_detection_thresholds_defined(self):
        """Test DETECTION_THRESHOLDS is defined."""
        import config
        assert hasattr(config, "DETECTION_THRESHOLDS")
        assert isinstance(config.DETECTION_THRESHOLDS, dict)

    def test_detection_threshold_values_are_integers(self):
        """Test threshold values are integers."""
        import config
        for rule, value in config.DETECTION_THRESHOLDS.items():
            assert isinstance(value, int)
            assert value >= 0

    def test_openrouter_api_key_configured(self):
        """Test OpenRouter API key is configurable."""
        import config
        assert hasattr(config, "OPENROUTER_API_KEY")

    def test_openrouter_base_url_configured(self):
        """Test OpenRouter base URL is configured."""
        import config
        assert hasattr(config, "OPENROUTER_BASE_URL")
        assert isinstance(config.OPENROUTER_BASE_URL, str)

    def test_openrouter_model_configured(self):
        """Test OpenRouter model is configured."""
        import config
        assert hasattr(config, "OPENROUTER_MODEL")
        assert isinstance(config.OPENROUTER_MODEL, str)

    def test_ensure_log_dir_creates_directory(self, tmp_path):
        """Test ensure_log_dir creates directory."""
        import config as config_module
        
        test_log_dir = tmp_path / "test_logs"
        with patch.object(config_module, "LOG_DIR", test_log_dir):
            config_module.ensure_log_dir()
            assert test_log_dir.exists()


class TestConfigEnvOverrides:
    """Tests for environment variable overrides."""

    def test_log_dir_from_env(self, tmp_path):
        """Test LOG_DIR can be overridden via environment."""
        import config as config_module
        
        with patch.dict(os.environ, {"AGENT_LOG_DIR": str(tmp_path)}):
            # Need to reimport to pick up the env var
            from importlib import reload
            reload(config_module)
            
            assert str(config_module.LOG_DIR) == str(tmp_path)

    def test_watch_directory_from_env(self, tmp_path):
        """Test WATCH_DIRECTORY can be overridden via environment."""
        import config as config_module
        
        with patch.dict(os.environ, {"AGENT_WATCH_DIR": str(tmp_path)}):
            from importlib import reload
            reload(config_module)
            
            assert str(config_module.WATCH_DIRECTORY) == str(tmp_path)

    def test_threshold_from_env(self):
        """Test thresholds can be overridden via environment."""
        import config as config_module
        
        with patch.dict(os.environ, {"AGENT_THRESHOLD_PROCESS_COUNT": "500"}):
            from importlib import reload
            reload(config_module)
            
            assert config_module.DETECTION_THRESHOLDS["process_count"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])