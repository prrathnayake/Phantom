"""Simple client for the OpenRouter chat completion API.

This client wraps the HTTP request/response cycle for calling OpenRouter's
chat completion API.  It expects an API key to be provided via
`config.OPENROUTER_API_KEY`.  If no key is available the `chat_completion`
method will return `None` and the caller should handle this gracefully.
"""
import json
import logging
from typing import List, Dict, Optional

import requests

from .. import config


logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = config.OPENROUTER_BASE_URL.rstrip("/")
        self.model = config.OPENROUTER_MODEL

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 256) -> Optional[str]:
        """Send a chat completion request to the OpenRouter API.

        :param messages: A list of message objects with `role` and `content`
            keys.  See OpenAI ChatGPT API for format.
        :param max_tokens: Maximum number of tokens to generate.
        :return: The generated assistant response, or None if there was an
            error or API key is missing.
        """
        if not self.api_key:
            logger.warning("OpenRouter API key not found; skipping chat completion")
            return None
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
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            logger.error(f"OpenRouter request failed: {exc}")
            return None
        try:
            data = response.json()
            # According to OpenAI compatible API spec, the top level contains
            # a list under 'choices'.
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error(f"Unexpected response from OpenRouter: {exc}")
            return None
