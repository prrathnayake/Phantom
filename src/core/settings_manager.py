"""Settings Manager.

Provides persistent runtime settings storage backed by a JSON file.
Settings changed via the web UI are persisted here and take precedence
over config.py defaults.
"""
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import config


class SettingsManager:
    """Persistent runtime settings manager."""

    _DEFAULTS: Dict[str, Any] = {
        "openrouter_model": config.OPENROUTER_MODEL,
        "openrouter_base_url": config.OPENROUTER_BASE_URL,
        "debug_mode": config.DEBUG_MODE,
        "default_agent_mode": config.DEFAULT_AGENT_MODE,
        "auto_approve_low_risk": config.AUTO_APPROVE_LOW_RISK,
        "approval_risk_threshold": config.APPROVAL_REQUIRED_RISK_LEVEL,
        "enable_auto_response": config.ENABLE_AUTO_RESPONSE,
        "alert_throttle_seconds": config.ALERT_THROTTLE_SECONDS,
        "alert_timeout_minutes": config.ALERT_TIMEOUT_MINUTES,
        "timeline_max_events": config.TIMELINE_MAX_EVENTS,
        "memory_max_entries": config.MEMORY_MAX_ENTRIES,
        "risk_score_max": config.RISK_SCORE_MAX,
        "risk_trend_window": config.RISK_TREND_WINDOW,
        "correlation_window_minutes": config.CORRELATION_WINDOW_MINUTES,
        "correlation_min_confidence": config.CORRELATION_MIN_CONFIDENCE,
        "statistical_window": config.STATISTICAL_WINDOW,
        "statistical_threshold": config.STATISTICAL_THRESHOLD,
    }

    # Threshold keys that are kept in a nested dict for cleaner UI
    _THRESHOLD_KEYS = {
        "threshold_process_count": "process_count",
        "threshold_open_ports": "open_ports",
        "threshold_file_changes": "file_changes",
        "threshold_established_connections": "established_connections",
        "threshold_external_ips": "external_ips",
        "threshold_memory_percent": "memory_percent",
        "threshold_swap_percent": "swap_percent",
        "threshold_disk_percent": "disk_percent",
        "threshold_failed_logins": "failed_logins",
    }

    # Polling interval keys
    _POLLING_KEYS = {
        "poll_process_sensor": "process_sensor",
        "poll_port_sensor": "port_sensor",
        "poll_file_sensor": "file_sensor",
        "poll_network_sensor": "network_sensor",
        "poll_memory_sensor": "memory_sensor",
        "poll_disk_io_sensor": "disk_io_sensor",
        "poll_auth_sensor": "auth_sensor",
        "poll_service_sensor": "service_sensor",
        "poll_registry_sensor": "registry_sensor",
        "poll_dns_sensor": "dns_sensor",
        "poll_driver_sensor": "driver_sensor",
        "poll_certificate_sensor": "certificate_sensor",
        "poll_hardware_sensor": "hardware_sensor",
    }

    def __init__(self, settings_file: Optional[Path] = None):
        config.ensure_log_dir()
        self.settings_file = settings_file or (config.LOG_DIR / "settings.json")
        self._lock = Lock()
        self._settings: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load settings from disk or initialize with defaults."""
        if self.settings_file.exists():
            try:
                with self.settings_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._settings = loaded
                return
            except (json.JSONDecodeError, OSError):
                pass
        self._settings = {}
        self._save()

    def _save(self) -> None:
        """Persist current settings to disk."""
        with self._lock:
            try:
                with self.settings_file.open("w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=2, ensure_ascii=False)
            except OSError:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Return all settings merged with defaults."""
        merged = dict(self._DEFAULTS)
        merged.update(self._settings)
        # Add threshold defaults from config
        for setting_key, config_key in self._THRESHOLD_KEYS.items():
            merged.setdefault(setting_key, config.DETECTION_THRESHOLDS.get(config_key, 0))
        # Add polling defaults from config
        for setting_key, config_key in self._POLLING_KEYS.items():
            merged.setdefault(setting_key, config.POLL_INTERVALS.get(config_key, 60))
        return merged

    def set(self, key: str, value: Any) -> None:
        """Set a single setting value."""
        with self._lock:
            self._settings[key] = value
            self._save()

    def set_many(self, values: Dict[str, Any]) -> Dict[str, str]:
        """Set multiple settings at once.

        Returns a dict of validation errors keyed by setting name.
        """
        errors: Dict[str, str] = {}
        with self._lock:
            for key, value in values.items():
                validated = self._validate(key, value)
                if validated is None:
                    errors[key] = f"Invalid value for {key}"
                    continue
                self._settings[key] = validated
            self._save()
        return errors

    def _validate(self, key: str, value: Any) -> Any:
        """Validate and coerce a setting value."""
        # Numeric thresholds
        if key.startswith("threshold_") or key.startswith("poll_") or key in {
            "alert_throttle_seconds",
            "alert_timeout_minutes",
            "timeline_max_events",
            "memory_max_entries",
            "risk_score_max",
            "risk_trend_window",
            "correlation_window_minutes",
            "statistical_window",
            "approval_risk_threshold",
        }:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        if key in {"correlation_min_confidence", "statistical_threshold"}:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        if key in {"debug_mode", "auto_approve_low_risk", "enable_auto_response"}:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "on")
        if key == "default_agent_mode":
            val = str(value).upper()
            if val in config.AGENT_MODES:
                return val
            return None
        if key == "openrouter_base_url":
            val = str(value).strip()
            if val.startswith(("http://", "https://")):
                return val.rstrip("/")
            return None
        if key == "openrouter_model":
            val = str(value).strip()
            if val:
                return val
            return None
        return value

    def reset_to_defaults(self) -> None:
        """Clear all custom settings and revert to defaults."""
        with self._lock:
            self._settings = {}
            self._save()

    def get_thresholds(self) -> Dict[str, int]:
        """Return detection thresholds from settings or config."""
        thresholds = dict(config.DETECTION_THRESHOLDS)
        for setting_key, config_key in self._THRESHOLD_KEYS.items():
            val = self._settings.get(setting_key)
            if val is not None:
                thresholds[config_key] = val
        return thresholds

    def get_polling_intervals(self) -> Dict[str, int]:
        """Return polling intervals from settings or config."""
        intervals = dict(config.POLL_INTERVALS)
        for setting_key, config_key in self._POLLING_KEYS.items():
            val = self._settings.get(setting_key)
            if val is not None:
                intervals[config_key] = val
        return intervals

    def get_masked_settings(self) -> Dict[str, Any]:
        """Return settings with sensitive values masked for UI display."""
        all_settings = self.get_all()
        # No API keys are stored in settings.json currently, but mask just in case
        for key in list(all_settings.keys()):
            if "api_key" in key or "secret" in key or "password" in key or "webhook" in key:
                val = all_settings[key]
                if val and isinstance(val, str) and len(val) > 4:
                    all_settings[key] = val[:4] + "****"
        return all_settings


# Global singleton
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
