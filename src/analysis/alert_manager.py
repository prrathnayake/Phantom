"""Alert Manager for Suraksha.

Manages alert creation, routing, and dispatch to external services.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

import config
from src.core.storage import Storage
from src.utils.debug_log import debug_logger

from src.integrations import (
    SIEMClient, SlackClient, TeamsClient,
    PagerDutyClient, ELKClient, CloudWatchClient
)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    PENDING = "pending"
    ROUTED = "routed"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class Alert:
    alert_id: str
    title: str
    description: str
    severity: str
    source: str
    recommended_action: str
    affected_assets: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"
    detection_rule: Optional[str] = None
    risk_score: int = 0
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """Manages alerts and dispatch to external services."""
    
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self._alerts: Dict[str, Alert] = {}
        self._lock = Lock()
        
        self.siem = SIEMClient()
        self.slack = SlackClient()
        self.teams = TeamsClient()
        self.pagerduty = PagerDutyClient()
        self.elk = ELKClient()
        self.cloudwatch = CloudWatchClient()
        
        self.throttle_window = getattr(config, 'ALERT_THROTTLE_SECONDS', 60)
        self._throttle_cache: Dict[str, float] = {}
        
        self.auto_route = True
        
        debug_logger.info("AlertManager initialized")
    
    def _is_throttled(self, alert_key: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        if alert_key in self._throttle_cache:
            if now - self._throttle_cache[alert_key] < self.throttle_window:
                return True
        self._throttle_cache[alert_key] = now
        return False
    
    def create_alert(
        self,
        title: str,
        description: str,
        severity: str,
        source: str,
        recommended_action: str,
        affected_assets: Optional[List[str]] = None,
        detection_rule: Optional[str] = None,
        risk_score: int = 0,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert.
        
        Args:
            title: Alert title
            description: Alert description
            severity: Severity level (critical, high, medium, low, info)
            source: Source of the alert
            recommended_action: Recommended action to take
            affected_assets: List of affected assets
            detection_rule: Detection rule that triggered
            risk_score: Risk score (0-100)
            correlation_id: Correlation ID for grouped alerts
            metadata: Additional metadata
            
        Returns:
            Created Alert object
        """
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity.lower(),
            source=source,
            recommended_action=recommended_action,
            affected_assets=affected_assets or [],
            detection_rule=detection_rule,
            risk_score=risk_score,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._alerts[alert_id] = alert
        
        self.storage.log_event("alert_created", {
            "alert_id": alert_id,
            "title": title,
            "severity": severity,
            "source": source
        })
        
        debug_logger.info("Alert created", {
            "alert_id": alert_id,
            "severity": severity,
            "source": source
        })
        
        if self.auto_route:
            self.route_alert(alert)
        
        return alert
    
    def route_alert(self, alert: Alert) -> bool:
        """Route alert to all configured external services.
        
        Args:
            alert: Alert to route
            
        Returns:
            True if at least one service received the alert
        """
        alert_key = f"{alert.severity}:{alert.detection_rule or alert.source}"
        if self._is_throttled(alert_key):
            debug_logger.info("Alert throttled", {"alert_id": alert.alert_id})
            return False
        
        success = False
        
        if self.elk.enabled:
            if self.elk.send_alert(
                alert.alert_id,
                alert.title,
                alert.description,
                alert.severity,
                alert.affected_assets,
                alert.recommended_action
            ):
                success = True
        
        if self.siem.config and self.siem.config.enabled:
            if self.siem.send_alert(
                alert.alert_id,
                alert.title,
                alert.description,
                alert.severity,
                alert.affected_assets,
                alert.recommended_action
            ):
                success = True
        
        if self.slack.enabled:
            if self.slack.send_alert(
                alert.alert_id,
                alert.title,
                alert.description,
                alert.severity,
                alert.affected_assets,
                alert.recommended_action
            ):
                success = True
        
        if self.teams.enabled:
            if self.teams.send_alert(
                alert.alert_id,
                alert.title,
                alert.description,
                alert.severity,
                alert.affected_assets,
                alert.recommended_action
            ):
                success = True
        
        if self.pagerduty.enabled and alert.severity in ("critical", "high"):
            if self.pagerduty.send_alert(
                alert.alert_id,
                alert.title,
                alert.description,
                alert.severity,
                alert.affected_assets,
                alert.recommended_action
            ):
                success = True
        
        if self.cloudwatch.enabled:
            self.cloudwatch.send_alert_metric(
                alert.alert_id,
                alert.severity,
                "routed"
            )
        
        if success:
            alert.status = "routed"
            debug_logger.info("Alert routed", {"alert_id": alert.alert_id})
        
        return success
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Alert or None
        """
        return self._alerts.get(alert_id)
    
    def get_alerts(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get alerts with optional filtering.
        
        Args:
            severity: Filter by severity
            status: Filter by status
            limit: Maximum number of alerts
            
        Returns:
            List of alerts
        """
        with self._lock:
            alerts = list(self._alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity.lower()]
        if status:
            alerts = [a for a in alerts if a.status == status.lower()]
        
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]
    
    def get_pending_alerts(self) -> List[Alert]:
        """Get all pending alerts.
        
        Returns:
            List of pending alerts
        """
        return self.get_alerts(status="pending")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if acknowledged
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "acknowledged"
        
        if self.pagerduty.enabled:
            self.pagerduty.acknowledge_alert(alert_id, f"Alert {alert_id} acknowledged")
        
        self.storage.log_event("alert_acknowledged", {"alert_id": alert_id})
        
        debug_logger.info("Alert acknowledged", {"alert_id": alert_id})
        return True
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if resolved
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "resolved"
        
        if self.pagerduty.enabled:
            self.pagerduty.resolve_alert(alert_id, f"Alert {alert_id} resolved")
        
        self.storage.log_event("alert_resolved", {"alert_id": alert_id})
        
        debug_logger.info("Alert resolved", {"alert_id": alert_id})
        return True
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics.
        
        Returns:
            Dictionary with alert stats
        """
        with self._lock:
            alerts = list(self._alerts.values())
        
        stats = {
            "total": len(alerts),
            "by_severity": {},
            "by_status": {},
            "pending_count": 0,
            "critical_count": 0
        }
        
        for alert in alerts:
            stats["by_severity"][alert.severity] = stats["by_severity"].get(alert.severity, 0) + 1
            stats["by_status"][alert.status] = stats["by_status"].get(alert.status, 0) + 1
            
            if alert.status == "pending":
                stats["pending_count"] += 1
            if alert.severity == "critical" and alert.status == "pending":
                stats["critical_count"] += 1
        
        return stats
    
    def clear_expired_alerts(self, hours: int = 24) -> int:
        """Clear old resolved alerts.
        
        Args:
            hours: Hours after which to clear
            
        Returns:
            Number of alerts cleared
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cleared = 0
        
        with self._lock:
            to_remove = []
            for alert_id, alert in self._alerts.items():
                if alert.status in ("resolved", "expired"):
                    alert_time = datetime.fromisoformat(alert.timestamp)
                    if alert_time < cutoff:
                        to_remove.append(alert_id)
            
            for alert_id in to_remove:
                del self._alerts[alert_id]
                cleared += 1
        
        if cleared > 0:
            debug_logger.info("Cleared expired alerts", {"count": cleared})
        
        return cleared


def create_alert_manager() -> AlertManager:
    """Create AlertManager with default settings.
    
    Returns:
        Configured AlertManager
    """
    return AlertManager()
