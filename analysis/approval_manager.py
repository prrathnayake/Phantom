"""Approval Manager for Suraksha.

Manages approval requests for automated actions with human-in-the-loop workflow.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional

import config
from core.storage import Storage
from utils.debug_log import debug_logger

from integrations import SIEMClient, SlackClient, TeamsClient, PagerDutyClient, ELKClient


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"


class ActionType(Enum):
    BLOCK_IP = "block_ip"
    KILL_PROCESS = "kill_process"
    DISABLE_USER = "disable_user"
    QUARANTINE_FILE = "quarantine_file"
    ISOLATE_HOST = "isolate_host"
    ALERT_ONLY = "alert_only"
    RESET_PASSWORD = "reset_password"


@dataclass
class ActionParameter:
    name: str
    value: Any
    description: str = ""
    required: bool = True


@dataclass
class ApprovalRequest:
    approval_id: str
    action_type: str
    action_parameters: List[ActionParameter]
    reason: str
    risk_level: str
    risk_score: int
    triggered_by: str
    detection_rule: Optional[str] = None
    correlation_id: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    denied_at: Optional[str] = None
    denied_by: Optional[str] = None
    executed_at: Optional[str] = None
    execution_result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalManager:
    """Manages approval requests for automated actions."""
    
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._lock = Lock()
        
        self.timeout_minutes = getattr(config, 'ALERT_TIMEOUT_MINUTES', 30)
        
        self.siem = SIEMClient()
        self.slack = SlackClient()
        self.teams = TeamsClient()
        self.pagerduty = PagerDutyClient()
        self.elk = ELKClient()
        
        self._executed_actions: Dict[str, Any] = {}
        
        debug_logger.info("ApprovalManager initialized", {
            "timeout_minutes": self.timeout_minutes
        })
    
    def _get_expiry_time(self) -> str:
        expiry = datetime.utcnow() + timedelta(minutes=self.timeout_minutes)
        return expiry.isoformat()
    
    def is_expired(self, approval: ApprovalRequest) -> bool:
        if approval.expires_at:
            expiry = datetime.fromisoformat(approval.expires_at)
            return datetime.utcnow() > expiry
        return False
    
    def create_approval_request(
        self,
        action_type: str,
        action_parameters: List[ActionParameter],
        reason: str,
        risk_level: str,
        risk_score: int,
        triggered_by: str,
        detection_rule: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """Create a new approval request.
        
        Args:
            action_type: Type of action to perform
            action_parameters: Parameters for the action
            reason: Reason for the action
            risk_level: Risk level (critical, high, medium, low)
            risk_score: Risk score (0-100)
            triggered_by: What triggered this request
            detection_rule: Detection rule that triggered
            correlation_id: Correlation ID if part of attack chain
            metadata: Additional metadata
            
        Returns:
            Created ApprovalRequest
        """
        approval_id = str(uuid.uuid4())
        
        request = ApprovalRequest(
            approval_id=approval_id,
            action_type=action_type,
            action_parameters=action_parameters,
            reason=reason,
            risk_level=risk_level.lower(),
            risk_score=risk_score,
            triggered_by=triggered_by,
            detection_rule=detection_rule,
            correlation_id=correlation_id,
            expires_at=self._get_expiry_time(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._approvals[approval_id] = request
        
        self.storage.log_event("approval_requested", {
            "approval_id": approval_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "triggered_by": triggered_by
        })
        
        if self.elk.enabled:
            self.elk.send_approval(
                approval_id,
                action_type,
                reason,
                risk_level,
                "pending"
            )
        
        if self.slack.enabled:
            self.slack.send_approval_request(
                approval_id,
                action_type,
                reason,
                risk_level,
                f"/api/approvals/{approval_id}/"
            )
        
        if self.teams.enabled:
            self.teams.send_approval_request(
                approval_id,
                action_type,
                reason,
                risk_level,
                f"/api/approvals/{approval_id}/"
            )
        
        if self.pagerduty.enabled and risk_level.lower() in ("critical", "high"):
            self.pagerduty.send_approval_request(
                approval_id,
                action_type,
                reason,
                risk_level
            )
        
        debug_logger.info("Approval request created", {
            "approval_id": approval_id,
            "action_type": action_type,
            "risk_level": risk_level
        })
        
        return request
    
    def approve_request(
        self,
        approval_id: str,
        approved_by: str = "admin"
    ) -> Optional[ApprovalRequest]:
        """Approve an approval request.
        
        Args:
            approval_id: Approval request ID
            approved_by: Who approved the request
            
        Returns:
            Updated ApprovalRequest or None
        """
        with self._lock:
            request = self._approvals.get(approval_id)
            if not request:
                return None
            
            if request.status != "pending":
                debug_logger.warning("Approval not pending", {
                    "approval_id": approval_id,
                    "status": request.status
                })
                return None
            
            if self.is_expired(request):
                request.status = "expired"
                debug_logger.info("Approval expired", {"approval_id": approval_id})
                return request
            
            request.status = "approved"
            request.approved_at = datetime.utcnow().isoformat()
            request.approved_by = approved_by
        
        self.storage.log_event("approval_approved", {
            "approval_id": approval_id,
            "approved_by": approved_by
        })
        
        if self.elk.enabled:
            self.elk.send_approval(
                approval_id,
                request.action_type,
                request.reason,
                request.risk_level,
                "approved"
            )
        
        debug_logger.info("Approval approved", {
            "approval_id": approval_id,
            "approved_by": approved_by
        })
        
        return request
    
    def deny_request(
        self,
        approval_id: str,
        denied_by: str = "admin",
        reason: Optional[str] = None
    ) -> Optional[ApprovalRequest]:
        """Deny an approval request.
        
        Args:
            approval_id: Approval request ID
            denied_by: Who denied the request
            reason: Optional reason for denial
            
        Returns:
            Updated ApprovalRequest or None
        """
        with self._lock:
            request = self._approvals.get(approval_id)
            if not request:
                return None
            
            if request.status != "pending":
                return None
            
            request.status = "denied"
            request.denied_at = datetime.utcnow().isoformat()
            request.denied_by = denied_by
            if reason:
                request.metadata["denial_reason"] = reason
        
        self.storage.log_event("approval_denied", {
            "approval_id": approval_id,
            "denied_by": denied_by,
            "reason": reason
        })
        
        if self.elk.enabled:
            self.elk.send_approval(
                approval_id,
                request.action_type,
                request.reason,
                request.risk_level,
                "denied"
            )
        
        debug_logger.info("Approval denied", {
            "approval_id": approval_id,
            "denied_by": denied_by
        })
        
        return request
    
    def mark_executed(
        self,
        approval_id: str,
        execution_result: str
    ) -> Optional[ApprovalRequest]:
        """Mark an approval request as executed.
        
        Args:
            approval_id: Approval request ID
            execution_result: Result of execution
            
        Returns:
            Updated ApprovalRequest or None
        """
        with self._lock:
            request = self._approvals.get(approval_id)
            if not request:
                return None
            
            request.status = "executed"
            request.executed_at = datetime.utcnow().isoformat()
            request.execution_result = execution_result
        
        self._executed_actions[approval_id] = {
            "result": execution_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.storage.log_event("approval_executed", {
            "approval_id": approval_id,
            "result": execution_result
        })
        
        debug_logger.info("Approval executed", {
            "approval_id": approval_id,
            "result": execution_result
        })
        
        return request
    
    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID.
        
        Args:
            approval_id: Approval request ID
            
        Returns:
            ApprovalRequest or None
        """
        return self._approvals.get(approval_id)
    
    def get_pending_approvals(
        self,
        risk_level: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending approval requests.
        
        Args:
            risk_level: Optional filter by risk level
            
        Returns:
            List of pending ApprovalRequests
        """
        with self._lock:
            approvals = [a for a in self._approvals.values() if a.status == "pending"]
        
        if risk_level:
            approvals = [a for a in approvals if a.risk_level == risk_level.lower()]
        
        approvals.sort(key=lambda a: a.created_at, reverse=True)
        return approvals
    
    def get_approval_history(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get approval history.
        
        Args:
            limit: Maximum number to return
            status: Optional filter by status
            
        Returns:
            List of ApprovalRequests
        """
        with self._lock:
            approvals = list(self._approvals.values())
        
        if status:
            approvals = [a for a in approvals if a.status == status.lower()]
        
        approvals.sort(key=lambda a: a.created_at, reverse=True)
        return approvals[:limit]
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """Get approval statistics.
        
        Returns:
            Dictionary with approval stats
        """
        with self._lock:
            approvals = list(self._approvals.values())
        
        stats = {
            "total": len(approvals),
            "pending": 0,
            "approved": 0,
            "denied": 0,
            "expired": 0,
            "executed": 0,
            "by_risk_level": {},
            "by_action_type": {}
        }
        
        for approval in approvals:
            stats[approval.status] = stats.get(approval.status, 0) + 1
            stats["by_risk_level"][approval.risk_level] = \
                stats["by_risk_level"].get(approval.risk_level, 0) + 1
            stats["by_action_type"][approval.action_type] = \
                stats["by_action_type"].get(approval.action_type, 0) + 1
        
        stats["pending"] = len([a for a in approvals if a.status == "pending"])
        
        return stats
    
    def get_action_summary(self, request: ApprovalRequest) -> Dict[str, Any]:
        """Get summary of action for UI display.
        
        Args:
            request: ApprovalRequest
            
        Returns:
            Summary dictionary
        """
        params = {p.name: p.value for p in request.action_parameters}
        
        return {
            "approval_id": request.approval_id,
            "action_type": request.action_type,
            "action_type_display": request.action_type.replace("_", " ").title(),
            "parameters": params,
            "reason": request.reason,
            "risk_level": request.risk_level.upper(),
            "risk_score": request.risk_score,
            "status": request.status,
            "created_at": request.created_at,
            "expires_at": request.expires_at,
            "triggered_by": request.triggered_by,
            "detection_rule": request.detection_rule
        }
    
    def expire_pending(self) -> int:
        """Expire pending requests that have timed out.
        
        Returns:
            Number of requests expired
        """
        expired = 0
        
        with self._lock:
            for approval in self._approvals.values():
                if approval.status == "pending" and self.is_expired(approval):
                    approval.status = "expired"
                    expired += 1
        
        if expired > 0:
            debug_logger.info("Expired pending approvals", {"count": expired})
        
        return expired


def create_approval_manager() -> ApprovalManager:
    """Create ApprovalManager with default settings.
    
    Returns:
        Configured ApprovalManager
    """
    return ApprovalManager()