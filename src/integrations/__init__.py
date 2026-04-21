"""External service integrations for Suraksha.

This module provides integration clients for various external services:
- SIEM: Splunk, QRadar, Wazuh, Elastic
- Messaging: Slack, Microsoft Teams
- Incident Management: PagerDuty
- Cloud Monitoring: AWS CloudWatch
"""
from typing import Any, Dict, List, Optional

__all__ = [
    "SIEMClient",
    "SlackClient",
    "TeamsClient",
    "PagerDutyClient",
    "ELKClient",
    "CloudWatchClient",
]

from .siem_client import SIEMClient
from .slack_client import SlackClient
from .teams_client import TeamsClient
from .pagerduty_client import PagerDutyClient
from .elk_client import ELKClient
from .cloudwatch_client import CloudWatchClient
