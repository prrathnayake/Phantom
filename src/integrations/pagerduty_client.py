"""PagerDuty Integration Client.

Provides integration with PagerDuty for incident management.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

import config
from src.utils.debug_log import debug_logger


@dataclass
class PagerDutyEvent:
    event_action: str
    routing_key: str
    event_type: str = "trigger"
    dedup_key: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class PagerDutyClient:
    """Client for sending events to PagerDuty."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.PAGERDUTY_KEY
        self.session = requests.Session()
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            debug_logger.warning("PagerDuty client not configured - no API key")
    
    def _get_severity(self, severity: str) -> str:
        mapping = {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info"
        }
        return mapping.get(severity.lower(), "warning")
    
    def _send_event(
        self,
        event_action: str,
        payload: Dict[str, Any],
        dedup_key: Optional[str] = None
    ) -> bool:
        if not self.enabled:
            return False
        
        url = "https://events.pagerduty.com/v2/enqueue"
        
        data = {
            "routing_key": self.api_key,
            "event_action": event_action,
            "payload": payload,
            "client": "Suraksha Security Agent",
            "client_url": "https://github.com/phantom-agent"
        }
        
        if dedup_key:
            data["dedup_key"] = dedup_key
        
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in (200, 201, 202):
                debug_logger.info(f"PagerDuty {event_action} event sent")
                return True
            
            debug_logger.warning("PagerDuty send failed", {
                "status": response.status_code,
                "body": response.text[:200]
            })
            return False
            
        except Exception as e:
            debug_logger.error("PagerDuty send error", {"error": str(e)})
            return False
    
    def send_alert(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: str,
        affected_assets: List[str],
        recommended_action: str
    ) -> bool:
        """Send a security alert to PagerDuty as an incident.
        
        Args:
            alert_id: Unique alert identifier
            title: Alert title
            description: Alert description
            severity: Alert severity
            affected_assets: List of affected assets
            recommended_action: Recommended action
            
        Returns:
            True if sent successfully
        """
        payload = {
            "summary": f"[{severity.upper()}] {title}",
            "severity": self._get_severity(severity),
            "source": "phantom-agent",
            "timestamp": datetime.utcnow().isoformat(),
            "custom_details": {
                "alert_id": alert_id,
                "description": description,
                "affected_assets": affected_assets,
                "recommended_action": recommended_action
            }
        }
        
        return self._send_event("trigger", payload, dedup_key=alert_id)
    
    def send_approval_request(
        self,
        approval_id: str,
        action: str,
        reason: str,
        risk_level: str
    ) -> bool:
        """Send an approval request to PagerDuty.
        
        Args:
            approval_id: Approval request ID
            action: Action being requested
            reason: Reason for the action
            risk_level: Risk level
            
        Returns:
            True if sent successfully
        """
        payload = {
            "summary": f"[APPROVAL] {action} - Risk: {risk_level.upper()}",
            "severity": self._get_severity(risk_level),
            "source": "phantom-approval",
            "timestamp": datetime.utcnow().isoformat(),
            "custom_details": {
                "approval_id": approval_id,
                "action": action,
                "reason": reason,
                "risk_level": risk_level,
                "type": "approval_request"
            }
        }
        
        return self._send_event("trigger", payload, dedup_key=f"approval-{approval_id}")
    
    def acknowledge_alert(self, incident_key: str, message: str) -> bool:
        """Acknowledge an existing PagerDuty incident.
        
        Args:
            incident_key: Incident deduplication key
            message: Acknowledge message
            
        Returns:
            True if sent successfully
        """
        payload = {
            "summary": message,
            "severity": "warning",
            "source": "phantom-agent"
        }
        
        return self._send_event("acknowledge", payload, dedup_key=incident_key)
    
    def resolve_alert(self, incident_key: str, message: str) -> bool:
        """Resolve an existing PagerDuty incident.
        
        Args:
            incident_key: Incident deduplication key
            message: Resolve message
            
        Returns:
            True if sent successfully
        """
        payload = {
            "summary": message,
            "severity": "info",
            "source": "phantom-agent"
        }
        
        return self._send_event("resolve", payload, dedup_key=incident_key)
    
    def send_detection(
        self,
        rule: str,
        description: str,
        severity: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send a detection to PagerDuty.
        
        Args:
            rule: Detection rule
            description: Description
            severity: Severity
            details: Additional details
            
        Returns:
            True if sent successfully
        """
        payload = {
            "summary": f"[DETECTION] {rule}: {description[:100]}",
            "severity": self._get_severity(severity),
            "source": "phantom-detection",
            "timestamp": datetime.utcnow().isoformat(),
            "custom_details": {
                "rule": rule,
                "description": description,
                "details": details
            }
        }
        
        dedup_key = f"detection-{rule}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        return self._send_event("trigger", payload, dedup_key=dedup_key)


def create_pagerduty_client() -> PagerDutyClient:
    """Create PagerDuty client with default configuration.
    
    Returns:
        Configured PagerDutyClient
    """
    return PagerDutyClient()
