"""Microsoft Teams Integration Client.

Provides webhook integration for sending alerts and approval requests to Teams.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

import config
from utils.debug_log import debug_logger


@dataclass
class TeamsSection:
    activity_title: str
    activity_subtitle: Optional[str] = None
    activity_image: Optional[str] = None
    facts: Optional[List[Dict[str, str]]] = None
    text: Optional[str] = None


class TeamsClient:
    """Client for sending messages to Microsoft Teams via webhooks."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.TEAMS_WEBHOOK_URL
        self.session = requests.Session()
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            debug_logger.warning("Teams client not configured - no webhook URL")
    
    def _get_theme_color(self, severity: str) -> str:
        colors = {
            "critical": "FF0000",
            "high": "FF6600",
            "medium": "FFCC00",
            "low": "00CC00",
            "info": "0066CC"
        }
        return colors.get(severity.lower(), "808080")
    
    def _build_facts(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        facts = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)[:100]
            facts.append({
                "name": key.replace("_", " ").title(),
                "value": str(value)[:100]
            })
        return facts
    
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
        """Send a security alert to Teams.
        
        Args:
            alert_id: Unique alert identifier
            title: Alert title
            description: Alert description
            severity: Alert severity
            affected_assets: List of affected assets
            recommended_action: Recommended action
            approval_url: URL for approving/denying
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵"
        }
        
        emoji = severity_emoji.get(severity.lower(), "⚪")
        
        potential_actions = []
        if approval_url:
            potential_actions.extend([
                {
                    "@type": "OpenUri",
                    "name": "✅ Approve",
                    "targets": [
                        {"os": "default", "uri": f"{approval_url}&action=approve"}
                    ]
                },
                {
                    "@type": "OpenUri", 
                    "name": "❌ Deny",
                    "targets": [
                        {"os": "default", "uri": f"{approval_url}&action=deny"}
                    ]
                }
            ])
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_theme_color(severity),
            "summary": f"Suraksha Alert: {title}",
            "title": f"{emoji} Security Alert: {title}",
            "sections": [
                {
                    "activityTitle": f"Severity: {severity.upper()}",
                    "facts": [
                        {"name": "Alert ID", "value": alert_id},
                        {"name": "Assets", "value": ", ".join(affected_assets[:3])},
                        {"name": "Action", "value": recommended_action}
                    ]
                },
                {
                    "text": description[:500]
                }
            ],
            "potentialAction": potential_actions if potential_actions else None
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return self._send_payload(payload)
    
    def send_approval_request(
        self,
        approval_id: str,
        action: str,
        reason: str,
        risk_level: str,
        approval_url: str
    ) -> bool:
        """Send an approval request to Teams.
        
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
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_theme_color(risk_level),
            "summary": f"Suraksha Approval: {action}",
            "title": f"⚠️ Approval Required: {action}",
            "sections": [
                {
                    "facts": [
                        {"name": "Request ID", "value": approval_id},
                        {"name": "Risk Level", "value": risk_level.upper()},
                        {"name": "Reason", "value": reason[:200]}
                    ]
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "✅ Approve",
                    "targets": [
                        {"os": "default", "uri": f"{approval_url}&action=approve"}
                    ]
                },
                {
                    "@type": "OpenUri",
                    "name": "❌ Deny",
                    "targets": [
                        {"os": "default", "uri": f"{approval_url}&action=deny"}
                    ]
                }
            ]
        }
        
        return self._send_payload(payload)
    
    def send_simple_message(self, message: str) -> bool:
        """Send a simple message to Teams.
        
        Args:
            message: Message text
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "text": message
        }
        
        return self._send_payload(payload)
    
    def _send_payload(self, payload: Dict[str, Any]) -> bool:
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code in (200, 201):
                debug_logger.info("Teams message sent successfully")
                return True
            
            debug_logger.warning("Teams send failed", {
                "status": response.status_code,
                "body": response.text[:200]
            })
            return False
            
        except Exception as e:
            debug_logger.error("Teams send error", {"error": str(e)})
            return False
    
    def send_detection_alert(
        self,
        rule: str,
        description: str,
        severity: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send a detection alert to Teams.
        
        Args:
            rule: Detection rule
            description: Description
            severity: Severity level
            details: Additional details
            
        Returns:
            True if sent successfully
        """
        facts = [{"name": k.replace("_", " ").title(), "value": str(v)[:100]} 
                 for k, v in details.items()]
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_theme_color(severity),
            "summary": f"Suraksha Detection: {rule}",
            "title": f"🔍 Detection: {rule}",
            "sections": [
                {
                    "facts": facts
                },
                {
                    "text": description
                }
            ]
        }
        
        return self._send_payload(payload)


def create_teams_client() -> TeamsClient:
    """Create Teams client with default configuration.
    
    Returns:
        Configured TeamsClient
    """
    return TeamsClient()