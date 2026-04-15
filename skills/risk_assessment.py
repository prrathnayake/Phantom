"""Risk assessment skill.

This skill aggregates recent detections and uses the summariser to
produce a human readable summary of the system's state.  It runs at a
slower cadence (e.g. every 10 minutes) because it calls the LLM.
"""
from typing import Dict, Any
from core.storage import Storage
from core.openrouter_client import OpenRouterClient
from analysis.summariser import summarise
from utils.debug_log import debug_logger


def run(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    """Execute the risk assessment.

    This function delegates to the summariser which collects recent
    anomalies and produces a summary.  The summary is stored in the
    context and can be used by other components (e.g. UI).
    """
    debug_logger.task("risk_assessment", "Starting risk assessment")
    summarise(context, storage, client)
    debug_logger.task("risk_assessment", "Risk assessment complete")
