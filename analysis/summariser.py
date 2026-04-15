"""Summarisation logic using OpenRouter.

This module provides a function that builds a prompt based on recent
events and detections and asks the language model to produce a concise
summary for the user.  Summaries are optional and will be skipped
silently if no API key is provided or the API call fails.
"""
from typing import Dict, Any, List

from core.openrouter_client import OpenRouterClient
from core.storage import Storage
from utils.debug_log import debug_logger


def summarise(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    """Generate and record a summary of recent activity.

    This function retrieves a handful of recent detection events and
    passes them to the LLM.  The summary is stored in the shared
    context under `last_summary` for later access.  If no LLM is
    available or there are no new detections, nothing happens.
    """
    debug_logger.info("Summariser starting")
    detections = storage.get_recent_detections(count=5)
    if not detections:
        debug_logger.info("Summariser: no detections to summarise")
        return
    system_prompt = (
        "You are an assistant summarising security anomalies detected by a local agent. "
        "Provide a concise, user friendly summary of the anomalies described. "
        "Mention only what is necessary and avoid speculation."
    )
    events_text = []
    for det in reversed(detections):
        rule = det.get("rule")
        desc = det.get("description")
        events_text.append(f"Rule {rule}: {desc} (at {det.get('timestamp')})")
    events_str = "\n".join(events_text)
    user_prompt = (
        "The following anomalies were detected:\n" + events_str + "\n" +
        "Summarise the overall risk and suggest next actions."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat_completion(messages, max_tokens=200)
    if response:
        context["last_summary"] = response
        debug_logger.info("Summariser: summary generated")
    else:
        debug_logger.warning("Summariser: failed to generate summary")
