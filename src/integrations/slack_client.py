"""Slack Integration Client.

Provides webhook integration for sending alerts and approval requests to Slack.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

import config
from src.utils.debug_log import debug_logger


@dataclass
class SlackAttachment:
    color: str
    title: str
    text: str
    fields: List[Dict[str, Any]]
    footer: str
    ts: int


class SlackClient:
    """Client for sending messages to Slack via webhooks."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.SLACK_WEBHOOK_URL
        self.session = requests.Session()
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            debug_logger.warning("Slack client not configured - no webhook URL")
    
    def _build_color(self, severity: str) -> str:
        colors = {
            "critical": "#FF0000",
            "high": "#FFA500",
            "medium": "#FFFF00",
            "low": "#00FF00",
            "info": "#0000FF"
        }
        return colors.get(severity.lower(), "#808080")
    
    def _build_fields(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        fields = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)[:100]
            fields.append({
                "title": key.replace("_", " ").title(),
                "value": str(value)[:100],
                "short": True
            })
        return fields
    
    def send_alert(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: str,
        affected_assets: List[str],
        recommended_action: str,
        approval_url: Optional[str] = None
    ) -> bool:
        """Send a security alert to Slack.
        
        Args:
            alert_id: Unique alert identifier
            title: Alert title
            description: Alert description
            severity: Alert severity
            affected_assets: List of affected assets
            recommended_action: Recommended action
            approval_url: URL for approving/denying the alert
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        fields = self._build_fields({
            "Severity": severity.upper(),
            "Assets": ", ".join(affected_assets[:3]),
            "Action": recommended_action
        })
        
        attachment = SlackAttachment(
            color=self._build_color(severity),
            title=title,
            text=description[:500],
            fields=fields,
            footer="Suraksha Security Agent",
            ts=int(datetime.utcnow().timestamp())
        )
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Security Alert: {severity.upper()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{description[:300]}"
                }
            },
            {
                "type": "section",
                "fields": fields
            }
        ]
        
        if approval_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "style": "primary",
                        "url": f"{approval_url}?action=approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Deny"
                        },
                        "style": "danger",
                        "url": f"{approval_url}?action=deny"
                    }
                ]
            })
        
        payload = {
            "attachments": [
                {
                    "color": attachment.color,
                    "title": attachment.title,
                    "text": attachment.text,
                    "fields": attachment.fields,
                    "footer": attachment.footer,
                    "ts": attachment.ts
                }
            ],
            "blocks": blocks
        }
        
        return self._send_payload(payload)
    
    def send_approval_request(
        self,
        approval_id: str,
        action: str,
        reason: str,
        risk_level: str,
        approval_url: str
    ) -> bool:
        """Send an approval request to Slack.
        
        Args:
            approval_id: Approval request ID
            action: Action being requested
            reason: Reason for the action
            risk_level: Risk level
            approval_url: URL to approve/deny
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        color = self._build_color(risk_level)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ Approval Required: {action}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Level:*\n{risk_level.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:*\n`{approval_id}`"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reason:*\n{reason[:200]}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "style": "primary",
                        "url": f"{approval_url}&action=approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Deny"
                        },
                        "style": "danger",
                        "url": f"{approval_url}&action=deny"
                    }
                ]
            }
        ]
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Action Required: {action}",
                    "text": reason[:300],
                    "footer": "Suraksha Approval System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ],
            "blocks": blocks
        }
        
        return self._send_payload(payload)
    
    def send_simple_message(
        self,
        message: str,
        channel: Optional[str] = None
    ) -> bool:
        """Send a simple message to Slack.
        
        Args:
            message: Message text
            channel: Optional channel override
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        payload = {"text": message}
        if channel:
            payload["channel"] = channel
        
        return self._send_payload(payload)
    
    def _send_payload(self, payload: Dict[str, Any]) -> bool:
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                debug_logger.info("Slack message sent successfully")
                return True
            
            debug_logger.warning("Slack send failed", {
                "status": response.status_code,
                "body": response.text[:200]
            })
            return False
            
        except Exception as e:
            debug_logger.error("Slack send error", {"error": str(e)})
            return False
    
    def send_detection_alert(
        self,
        rule: str,
        description: str,
        severity: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send a detection alert to Slack.
        
        Args:
            rule: Detection rule
            description: Description
            severity: Severity level
            details: Additional details
            
        Returns:
            True if sent successfully
        """
        fields = self._build_fields(details)
        
        attachment = {
            "color": self._build_color(severity),
            "title": f"Detection: {rule}",
            "text": description,
            "fields": fields,
            "footer": "Suraksha Detection Engine",
            "ts": int(datetime.utcnow().timestamp())
        }
        
        payload = {
            "text": f"🔍 Security Detection: {rule}",
            "attachments": [attachment]
        }
        
        return self._send_payload(payload)


def create_slack_client() -> SlackClient:
    """Create Slack client with default configuration.
    
    Returns:
        Configured SlackClient
    """
    return SlackClient()
