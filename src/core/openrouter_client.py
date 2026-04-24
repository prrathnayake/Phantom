"""Simple client for the OpenRouter chat completion API.

This client wraps the HTTP request/response cycle for calling OpenRouter's
chat completion API.  It expects an API key to be provided via
`config.OPENROUTER_API_KEY`.  If no key is available the `chat_completion`
method will return `None` and the caller should handle this gracefully.
"""
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

import requests

import config
from src.utils.debug_log import debug_logger
from src.core.llm_logger import get_llm_logger


logger = logging.getLogger(__name__)


@dataclass
class OpenRouterError:
    """Sanitized OpenRouter failure information."""
    category: str
    message: str


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = config.OPENROUTER_BASE_URL.rstrip("/")
        self.model = config.OPENROUTER_MODEL
        self.last_error: Optional[OpenRouterError] = None
        self.last_success = False

    def _set_error(self, category: str, message: str) -> None:
        """Store sanitized error state for callers and health endpoints."""
        self.last_error = OpenRouterError(category=category, message=message)
        self.last_success = False

    def get_health(self) -> Dict[str, object]:
        """Return safe client health details without exposing credentials."""
        if not self.api_key:
            status = "missing_api_key"
        elif self.last_error:
            status = "failed"
        elif self.last_success:
            status = "reachable"
        else:
            status = "configured"

        return {
            "configured": bool(self.api_key),
            "model": self.model,
            "status": status,
            "error_category": self.last_error.category if self.last_error else None,
        }

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 256) -> Optional[str]:
        """Send a chat completion request to the OpenRouter API.

        :param messages: A list of message objects with `role` and `content`
            keys.  See OpenAI ChatGPT API for format.
        :param max_tokens: Maximum number of tokens to generate.
        :return: The generated assistant response, or None if there was an
            error or API key is missing.
        """
        import time
        start_time = time.perf_counter()
        llm_logger = get_llm_logger()
        session_id = None
        for msg in messages:
            if msg.get("role") == "system" and "session_id" in msg.get("content", ""):
                try:
                    import re
                    m = re.search(r"Session ID:\s*([a-zA-Z0-9\-]+)", msg.get("content", ""))
                    if m:
                        session_id = m.group(1)
                except Exception:
                    pass

        debug_logger.info("OpenRouter request", {"model": self.model, "message_count": len(messages)})
        if not self.api_key:
            logger.warning("OpenRouter API key not found; skipping chat completion")
            debug_logger.warning("OpenRouter API key missing")
            self._set_error("missing_api_key", "OPENROUTER_API_KEY is not configured")
            duration_ms = (time.perf_counter() - start_time) * 1000
            llm_logger.log_call(
                model=self.model,
                messages=messages,
                response=None,
                max_tokens=max_tokens,
                duration_ms=duration_ms,
                error="missing_api_key",
                session_id=session_id,
            )
            return None
        self.last_error = None
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        error_msg = None
        response_text = None
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
            response.raise_for_status()
        except requests.Timeout:
            logger.error("OpenRouter request timed out")
            debug_logger.error("OpenRouter request failed", {"error": "timeout"})
            self._set_error("timeout", "OpenRouter request timed out")
            error_msg = "timeout"
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            category = "http_error" if status else "request_error"
            if status in (401, 403):
                category = "auth_error"
            elif status == 429:
                category = "rate_limited"
            logger.error(f"OpenRouter request failed with HTTP {status}")
            debug_logger.error("OpenRouter request failed", {"status": status, "category": category})
            self._set_error(category, f"OpenRouter returned HTTP {status}")
            error_msg = category
        except requests.RequestException as exc:
            logger.error(f"OpenRouter request failed: {exc}")
            debug_logger.error("OpenRouter request failed", {"error": type(exc).__name__})
            self._set_error("request_error", "OpenRouter request failed")
            error_msg = "request_error"
        else:
            try:
                data = response.json()
                response_text = data["choices"][0]["message"]["content"]
                self.last_success = True
            except Exception as exc:
                logger.error(f"Unexpected response from OpenRouter: {exc}")
                debug_logger.error("OpenRouter response parse failed", {"error": type(exc).__name__})
                self._set_error("invalid_response", "OpenRouter returned an unexpected response")
                error_msg = "invalid_response"

        duration_ms = (time.perf_counter() - start_time) * 1000
        llm_logger.log_call(
            model=self.model,
            messages=messages,
            response=response_text,
            max_tokens=max_tokens,
            duration_ms=duration_ms,
            error=error_msg,
            metadata={
                "api_configured": bool(self.api_key),
                "base_url": self.base_url,
            },
            session_id=session_id,
        )
        return response_text
