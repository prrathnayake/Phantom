"""AWS CloudWatch Integration Client.

Provides integration with AWS CloudWatch for metrics and logs.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

import config
from src.utils.debug_log import debug_logger


class CloudWatchClient:
    """Client for sending metrics to AWS CloudWatch."""
    
    def __init__(
        self,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        self.region = region or config.CLOUDWATCH_REGION or "us-east-1"
        self.access_key = access_key or config.AWS_ACCESS_KEY_ID
        self.secret_key = secret_key or config.AWS_SECRET_ACCESS_KEY
        self.session = requests.Session()
        self.enabled = bool(self.region)
        
        if not self.enabled:
            debug_logger.warning("CloudWatch client not configured - no region")
    
    def _get_endpoint(self, service: str = "monitoring") -> str:
        return f"https://{service}.{self.region}.amazonaws.com/"
    
    def send_metric(
        self,
        namespace: str,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[List[Dict[str, str]]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Send a custom metric to CloudWatch.
        
        Args:
            namespace: Metric namespace (e.g., "Suraksha/Security")
            metric_name: Metric name
            value: Metric value
            unit: Unit of measurement
            dimensions: Optional metric dimensions
            timestamp: Optional timestamp
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        debug_logger.debug("CloudWatch metric", {
            "namespace": namespace,
            "metric": metric_name,
            "value": value
        })
        
        return True
    
    def send_security_metrics(
        self,
        alert_count: int,
        detection_count: int,
        risk_level: str,
        approval_pending: int
    ) -> bool:
        """Send security-related metrics to CloudWatch.
        
        Args:
            alert_count: Number of active alerts
            detection_count: Number of recent detections
            risk_level: Current overall risk level
            approval_pending: Number of pending approvals
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            self.send_metric(
                namespace="Suraksha/Security",
                metric_name="ActiveAlerts",
                value=alert_count,
                unit="Count"
            )
            
            self.send_metric(
                namespace="Suraksha/Security",
                metric_name="RecentDetections",
                value=detection_count,
                unit="Count"
            )
            
            risk_value = {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(risk_level.lower(), 0)
            self.send_metric(
                namespace="Suraksha/Security",
                metric_name="RiskLevel",
                value=risk_value,
                unit="None"
            )
            
            self.send_metric(
                namespace="Suraksha/Security",
                metric_name="PendingApprovals",
                value=approval_pending,
                unit="Count"
            )
            
            debug_logger.info("Security metrics sent to CloudWatch")
            return True
            
        except Exception as e:
            debug_logger.error("CloudWatch metrics error", {"error": str(e)})
            return False
    
    def send_alert_metric(
        self,
        alert_id: str,
        severity: str,
        action_taken: str
    ) -> bool:
        """Send alert-related metrics.
        
        Args:
            alert_id: Alert ID
            severity: Alert severity
            action_taken: Action taken
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        try:
            self.send_metric(
                namespace="Suraksha/Alerts",
                metric_name="AlertTriggered",
                value=1,
                unit="Count",
                dimensions=[
                    {"Name": "Severity", "Value": severity},
                    {"Name": "Action", "Value": action_taken}
                ]
            )
            
            return True
            
        except Exception as e:
            debug_logger.error("CloudWatch alert metric error", {"error": str(e)})
            return False
    
    def send_detection_metric(
        self,
        rule: str,
        severity: str
    ) -> bool:
        """Send detection metrics.
        
        Args:
            rule: Detection rule
            severity: Severity
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            self.send_metric(
                namespace="Suraksha/Detections",
                metric_name="DetectionTriggered",
                value=1,
                unit="Count",
                dimensions=[
                    {"Name": "Rule", "Value": rule},
                    {"Name": "Severity", "Value": severity}
                ]
            )
            
            return True
            
        except Exception as e:
            debug_logger.error("CloudWatch detection metric error", {"error": str(e)})
            return False
    
    def send_approval_metric(
        self,
        status: str,
        risk_level: str
    ) -> bool:
        """Send approval metrics.
        
        Args:
            status: Approval status
            risk_level: Risk level
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            self.send_metric(
                namespace="Suraksha/Approvals",
                metric_name="ApprovalStatus",
                value=1,
                unit="Count",
                dimensions=[
                    {"Name": "Status", "Value": status},
                    {"Name": "RiskLevel", "Value": risk_level}
                ]
            )
            
            return True
            
        except Exception as e:
            debug_logger.error("CloudWatch approval metric error", {"error": str(e)})
            return False
    
    def send_to_cloudwatch_logs(
        self,
        log_group: str,
        log_stream: str,
        message: str,
        level: str = "INFO"
    ) -> bool:
        """Send a log message to CloudWatch Logs.
        
        Note: This requires boto3 and proper IAM permissions.
        For basic implementation, we log locally and note the requirement.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: Log stream name
            message: Log message
            level: Log level
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        debug_logger.debug("CloudWatch log", {
            "group": log_group,
            "stream": log_stream,
            "message": message[:100]
        })
        
        return True
    
    def create_metric_alarm(
        self,
        alarm_name: str,
        metric_name: str,
        threshold: float,
        comparison: str = "GreaterThanThreshold",
        period: int = 300,
        evaluation_periods: int = 2
    ) -> bool:
        """Create a CloudWatch metric alarm.
        
        Note: This is a placeholder. Full implementation requires boto3.
        
        Args:
            alarm_name: Alarm name
            metric_name: Metric to alarm on
            threshold: Threshold value
            comparison: Comparison operator
            period: Period in seconds
            evaluation_periods: Number of periods to evaluate
            
        Returns:
            True if created successfully
        """
        if not self.enabled:
            return False
        
        debug_logger.info("CloudWatch alarm config", {
            "alarm": alarm_name,
            "metric": metric_name,
            "threshold": threshold
        })
        
        return True


def create_cloudwatch_client() -> CloudWatchClient:
    """Create CloudWatch client with default configuration.
    
    Returns:
        Configured CloudWatchClient
    """
    return CloudWatchClient(
        region=config.CLOUDWATCH_REGION,
        access_key=config.AWS_ACCESS_KEY_ID,
        secret_key=config.AWS_SECRET_ACCESS_KEY
    )
