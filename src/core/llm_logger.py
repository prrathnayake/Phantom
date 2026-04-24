"""LLM Activity Logger.

Records every LLM call with full context including system prompts,
messages, responses, errors, and metadata for monitoring and debugging.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import config


class LLMActivityLogger:
    """Persistent logger for LLM interactions."""

    def __init__(self, log_file: Optional[Path] = None):
        config.ensure_log_dir()
        self.log_file = log_file or (config.LOG_DIR / "llm_activity.log")
        self._lock = Lock()

    def log_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: Optional[str],
        max_tokens: int,
        duration_ms: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a single LLM call with full context.

        :param model: Model name used for the call
        :param messages: Full message list sent to the API
        :param response: Response content or None if error
        :param max_tokens: Max tokens parameter
        :param duration_ms: Call duration in milliseconds
        :param error: Error message if call failed
        :param metadata: Additional metadata dict
        :param session_id: Optional session identifier
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "model": model,
            "max_tokens": max_tokens,
            "duration_ms": round(duration_ms, 2),
            "status": "error" if error else "success",
            "error": error,
            "messages": messages,
            "response": response,
            "metadata": metadata or {},
        }
        with self._lock:
            try:
                with self.log_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except OSError:
                pass

    def get_recent_calls(
        self,
        count: int = 50,
        status: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent LLM calls with optional filtering.

        :param count: Maximum number of calls to return
        :param status: Filter by status ('success' or 'error')
        :param model: Filter by model name
        :param session_id: Filter by session ID
        :return: List of call records, newest first
        """
        calls = []
        try:
            with self.log_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []

        for line in reversed(lines):
            if len(calls) >= count:
                break
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if status and record.get("status") != status:
                continue
            if model and record.get("model") != model:
                continue
            if session_id and record.get("session_id") != session_id:
                continue
            calls.append(record)

        return calls

    def get_call_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Return statistics for LLM calls in the given time window.

        :param hours: Time window in hours
        :return: Dict with total_calls, success_count, error_count, avg_duration_ms
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        total = 0
        success = 0
        errors = 0
        total_duration = 0.0

        try:
            with self.log_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {
                "total_calls": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_duration_ms": 0.0,
            }

        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_str = record.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            total += 1
            if record.get("status") == "success":
                success += 1
            else:
                errors += 1
            total_duration += record.get("duration_ms", 0) or 0

        return {
            "total_calls": total,
            "success_count": success,
            "error_count": errors,
            "avg_duration_ms": round(total_duration / total, 2) if total else 0.0,
        }

    def clear_logs(self) -> None:
        """Clear all LLM activity logs."""
        with self._lock:
            try:
                self.log_file.write_text("")
            except OSError:
                pass


# Global singleton
_llm_logger: Optional[LLMActivityLogger] = None


def get_llm_logger() -> LLMActivityLogger:
    """Get the global LLM activity logger instance."""
    global _llm_logger
    if _llm_logger is None:
        _llm_logger = LLMActivityLogger()
    return _llm_logger
