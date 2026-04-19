"""SIEM Integration Client.

Supports multiple SIEM platforms:
- Splunk HTTP Event Collector (HEC)
- QRadar log forwarding
- Wazuh API
- Generic syslog/CEF forwarding
"""
import json
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

import config
from utils.debug_log import debug_logger


class SIEMType(Enum):
    SPLUNK = "splunk"
    QRADAR = "qradar"
    WAZUH = "wazuh"
    ELASTIC = "elastic"
    SYSLOG = "syslog"


@dataclass
class SIEMConfig:
    siem_type: SIEMType
    url: str
    api_key: Optional[str] = None
    index: Optional[str] = None
    host: str = "suraksha-agent"
    enabled: bool = True


class SIEMClient:
    """Client for sending security events to SIEM systems."""
    
    def __init__(self, config: Optional[SIEMConfig] = None):
        self.config = config or self._load_config()
        self.session = requests.Session()
        self._deduplication_cache: Dict[str, float] = {}
        self._deduplication_window = 300
    
    def _load_config(self) -> Optional[SIEMConfig]:
        if not config.SIEM_URL:
            return None
        
        siem_type = config.SIEM_TYPE.lower() if config.SIEM_TYPE else "splunk"
        
        return SIEMConfig(
            siem_type=SIEMType(siem_type),
            url=config.SIEM_URL,
            api_key=config.SIEM_API_KEY,
            index=getattr(config, 'SIEM_INDEX', None),
            enabled=True
        )
    
    def _is_duplicate(self, event_id: str) -> bool:
        now = datetime.utcnow().timestamp()
        if event_id in self._deduplication_cache:
            if now - self._deduplication_cache[event_id] < self._deduplication_window:
                return True
        self._deduplication_cache[event_id] = now
        return False
    
    def send_event(
        self,
        event: Dict[str, Any],
        event_type: str = "security",
        event_id: Optional[str] = None
    ) -> bool:
        """Send an event to the configured SIEM.
        
        Args:
            event: Event data to send
            event_type: Type of event (security, audit, system)
            event_id: Optional event ID for deduplication
            
        Returns:
            True if sent successfully
        """
        if not self.config or not self.config.enabled:
            debug_logger.debug("SIEM client disabled")
            return False
        
        if event_id and self._is_duplicate(event_id):
            debug_logger.debug("Skipping duplicate event", {"event_id": event_id})
            return False
        
        try:
            if self.config.siem_type == SIEMType.SPLUNK:
                return self._send_splunk(event, event_type)
            elif self.config.siem_type == SIEMType.WAZUH:
                return self._send_wazuh(event, event_type)
            elif self.config.siem_type == SIEMType.ELASTIC:
                return self._send_elastic(event, event_type)
            elif self.config.siem_type == SIEMType.QRADAR:
                return self._send_qradar(event, event_type)
            else:
                return self._send_syslog(event, event_type)
        except Exception as e:
            debug_logger.error("SIEM send failed", {"error": str(e), "type": self.config.siem_type.value})
            return False
    
    def _build_payload(self, event: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        return {
            "time": datetime.utcnow().isoformat(),
            "host": self.config.host,
            "source": "suraksha-agent",
            "sourcetype": f"suraksha:{event_type}",
            "event": event
        }
    
    def _send_splunk(self, event: Dict[str, Any], event_type: str) -> bool:
        payload = self._build_payload(event, event_type)
        headers = {
            "Authorization": f"Splunk {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        url = self.config.url
        if self.config.index:
            url = urljoin(self.config.url, f"services/collector/event?index={self.config.index}")
        
        response = self.session.post(
            url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in (200, 201):
            debug_logger.info("Event sent to Splunk", {"event_type": event_type})
            return True
        
        debug_logger.warning("Splunk send failed", {"status": response.status_code, "body": response.text[:200]})
        return False
    
    def _send_wazuh(self, event: Dict[str, Any], event_type: str) -> bool:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "rule": {
                "level": event.get("severity", 3),
                "description": event.get("title", "Suraksha Alert")
            },
            "agent": {
                "name": self.config.host,
                "id": "suraksha"
            },
            "full_log": json.dumps(event)
        }
        
        headers = {
            "Authorization": f"Basic {self.config.api_key}",
            "Content-Type": "application/json"
        } if self.config.api_key else {"Content-Type": "application/json"}
        
        response = self.session.post(
            self.config.url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in (200, 201):
            debug_logger.info("Event sent to Wazuh", {"event_type": event_type})
            return True
        
        debug_logger.warning("Wazuh send failed", {"status": response.status_code})
        return False
    
    def _send_elastic(self, event: Dict[str, Any], event_type: str) -> bool:
        index_name = self.config.index or f"suraksha-{event_type}-{datetime.utcnow().strftime('%Y.%m.%d')}"
        url = urljoin(self.config.url, f"/{index_name}/_doc/")
        
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"ApiKey {self.config.api_key}"
        
        response = self.session.post(
            url,
            json=event,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in (200, 201):
            debug_logger.info("Event sent to Elastic", {"event_type": event_type, "index": index_name})
            return True
        
        debug_logger.warning("Elastic send failed", {"status": response.status_code})
        return False
    
    def _send_qradar(self, event: Dict[str, Any], event_type: str) -> bool:
        payload = {
            "event_timestamp": datetime.utcnow().isoformat(),
            "log_source_name": "Suraksha Agent",
            "qid": event.get("qid", 9999999),
            "severity": self._map_severity(event.get("severity", "medium")),
            "payload": json.dumps(event)
        }
        
        headers = {"Authorization": self.config.api_key or ""} if self.config.api_key else {}
        
        response = self.session.post(
            self.config.url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in (200, 201, 202):
            debug_logger.info("Event sent to QRadar", {"event_type": event_type})
            return True
        
        debug_logger.warning("QRadar send failed", {"status": response.status_code})
        return False
    
    def _send_syslog(self, event: Dict[str, Any], event_type: str) -> bool:
        try:
            host, port = self.config.url.split(":")
            port = int(port)
        except (ValueError, AttributeError):
            host = self.config.url
            port = 514
        
        severity = self._map_severity(event.get("severity", "medium"))
        facility = 16  # local0
        
        syslog_msg = f"<{(facility * 8) + severity}>Suraksha: {json.dumps(event)}"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(syslog_msg.encode('utf-8'), (host, port))
            debug_logger.info("Event sent via syslog", {"event_type": event_type})
            return True
        except Exception as e:
            debug_logger.error("Syslog send failed", {"error": str(e)})
            return False
        finally:
            sock.close()
    
    def _map_severity(self, severity: str) -> int:
        mapping = {
            "critical": 2,
            "high": 3,
            "medium": 4,
            "low": 5,
            "info": 6
        }
        return mapping.get(severity.lower(), 4)
    
    def send_alert(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: str,
        affected_assets: List[str],
        recommended_action: str
    ) -> bool:
        """Send a security alert to SIEM.
        
        Args:
            alert_id: Unique alert identifier
            title: Alert title
            description: Alert description
            severity: Alert severity (critical, high, medium, low)
            affected_assets: List of affected system assets
            recommended_action: Recommended remediation action
            
        Returns:
            True if sent successfully
        """
        event = {
            "alert_id": alert_id,
            "title": title,
            "description": description,
            "severity": severity,
            "affected_assets": affected_assets,
            "recommended_action": recommended_action,
            "source": "suraksha-alert"
        }
        
        return self.send_event(event, "alert", alert_id)
    
    def send_detection(
        self,
        rule: str,
        description: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send a detection event to SIEM.
        
        Args:
            rule: Detection rule that triggered
            description: Human-readable description
            details: Additional details about the detection
            
        Returns:
            True if sent successfully
        """
        event = {
            "rule": rule,
            "description": description,
            "details": details,
            "source": "suraksha-detection"
        }
        
        return self.send_event(event, "detection", f"{rule}-{datetime.utcnow().timestamp()}")
    
    def send_approval(
        self,
        approval_id: str,
        action: str,
        status: str,
        risk_level: str
    ) -> bool:
        """Send an approval event to SIEM for audit trail.
        
        Args:
            approval_id: Approval request ID
            action: Action that was approved/denied
            status: Status (approved, denied, expired)
            risk_level: Risk level of the action
            
        Returns:
            True if sent successfully
        """
        event = {
            "approval_id": approval_id,
            "action": action,
            "status": status,
            "risk_level": risk_level,
            "source": "suraksha-approval"
        }
        
        return self.send_event(event, "audit", approval_id)


def create_siem_client() -> Optional[SIEMClient]:
    """Create SIEM client with default configuration.
    
    Returns:
        Configured SIEMClient or None if not configured
    """
    return SIEMClient()