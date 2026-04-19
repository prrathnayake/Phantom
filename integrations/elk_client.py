"""Elasticsearch Integration Client.

Provides integration with Elasticsearch for centralized logging.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

import config
from utils.debug_log import debug_logger


class ELKClient:
    """Client for sending logs to Elasticsearch."""
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        index_prefix: str = "suraksha"
    ):
        self.url = url or config.ELASTIC_URL
        self.api_key = api_key or config.ELASTIC_API_KEY
        self.index_prefix = index_prefix
        self.session = requests.Session()
        self.enabled = bool(self.url)
        
        if not self.enabled:
            debug_logger.warning("ELK client not configured - no URL")
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        return headers
    
    def _get_index(self, doc_type: str) -> str:
        date = datetime.utcnow().strftime("%Y.%m.%d")
        return f"{self.index_prefix}-{doc_type}-{date}"
    
    def _send_bulk(self, operations: List[Dict[str, Any]]) -> bool:
        if not self.enabled:
            return False
        
        url = urljoin(self.url, "/_bulk")
        
        body = "\n".join(json.dumps(op) for op in operations) + "\n"
        
        try:
            response = self.session.post(
                url,
                data=body,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code in (200, 201):
                debug_logger.info("Bulk send to Elastic succeeded", {"count": len(operations) // 2})
                return True
            
            debug_logger.warning("Elastic bulk send failed", {
                "status": response.status_code,
                "body": response.text[:200]
            })
            return False
            
        except Exception as e:
            debug_logger.error("Elastic bulk send error", {"error": str(e)})
            return False
    
    def _send_doc(self, index: str, doc: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        
        url = urljoin(self.url, f"/{index}/_doc/")
        
        try:
            response = self.session.post(
                url,
                json=doc,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code in (200, 201):
                return True
            
            debug_logger.warning("Elastic doc send failed", {"status": response.status_code})
            return False
            
        except Exception as e:
            debug_logger.error("Elastic doc send error", {"error": str(e)})
            return False
    
    def send_event(
        self,
        sensor: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> bool:
        """Send a sensor event to Elasticsearch.
        
        Args:
            sensor: Sensor name
            data: Event data
            timestamp: Optional timestamp override
            
        Returns:
            True if sent successfully
        """
        doc = {
            "@timestamp": timestamp or datetime.utcnow().isoformat(),
            "sensor": sensor,
            "data": data,
            "source": "suraksha-sensor"
        }
        
        return self._send_doc(self._get_index("events"), doc)
    
    def send_alert(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: str,
        affected_assets: List[str],
        recommended_action: str,
        status: str = "pending"
    ) -> bool:
        """Send an alert to Elasticsearch.
        
        Args:
            alert_id: Alert ID
            title: Alert title
            description: Alert description
            severity: Severity
            affected_assets: Affected assets
            recommended_action: Recommended action
            status: Alert status
            
        Returns:
            True if sent successfully
        """
        doc = {
            "@timestamp": datetime.utcnow().isoformat(),
            "alert_id": alert_id,
            "title": title,
            "description": description,
            "severity": severity,
            "affected_assets": affected_assets,
            "recommended_action": recommended_action,
            "status": status,
            "source": "suraksha-alert"
        }
        
        return self._send_doc(self._get_index("alerts"), doc)
    
    def send_detection(
        self,
        rule: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "medium"
    ) -> bool:
        """Send a detection to Elasticsearch.
        
        Args:
            rule: Detection rule
            description: Description
            details: Details
            severity: Severity
            
        Returns:
            True if sent successfully
        """
        doc = {
            "@timestamp": datetime.utcnow().isoformat(),
            "rule": rule,
            "description": description,
            "details": details,
            "severity": severity,
            "source": "suraksha-detection"
        }
        
        return self._send_doc(self._get_index("detections"), doc)
    
    def send_approval(
        self,
        approval_id: str,
        action: str,
        reason: str,
        risk_level: str,
        status: str
    ) -> bool:
        """Send an approval event to Elasticsearch.
        
        Args:
            approval_id: Approval ID
            action: Action
            reason: Reason
            risk_level: Risk level
            status: Status
            
        Returns:
            True if sent successfully
        """
        doc = {
            "@timestamp": datetime.utcnow().isoformat(),
            "approval_id": approval_id,
            "action": action,
            "reason": reason,
            "risk_level": risk_level,
            "status": status,
            "source": "suraksha-approval"
        }
        
        return self._send_doc(self._get_index("approvals"), doc)
    
    def send_batch_events(
        self,
        events: List[Dict[str, Any]]
    ) -> bool:
        """Send multiple events in a single bulk request.
        
        Args:
            events: List of event documents
            
        Returns:
            True if all sent successfully
        """
        if not self.enabled or not events:
            return False
        
        operations = []
        for event in events:
            operations.append({"index": {"_index": self._get_index("events")}})
            operations.append(event)
        
        return self._send_bulk(operations)
    
    def send_batch_alerts(
        self,
        alerts: List[Dict[str, Any]]
    ) -> bool:
        """Send multiple alerts in a single bulk request.
        
        Args:
            alerts: List of alert documents
            
        Returns:
            True if all sent successfully
        """
        if not self.enabled or not alerts:
            return False
        
        operations = []
        for alert in alerts:
            operations.append({"index": {"_index": self._get_index("alerts")}})
            operations.append(alert)
        
        return self._send_bulk(operations)
    
    def search(
        self,
        index_pattern: str,
        query: Dict[str, Any],
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """Search documents in Elasticsearch.
        
        Args:
            index_pattern: Index pattern (e.g., "suraksha-alerts-*")
            query: Elasticsearch query
            size: Number of results
            
        Returns:
            List of matching documents
        """
        if not self.enabled:
            return []
        
        url = urljoin(self.url, f"/{index_pattern}/_search")
        
        try:
            response = self.session.post(
                url,
                json={"query": query, "size": size},
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return [hit["_source"] for hit in data.get("hits", {}).get("hits", [])]
            
            return []
            
        except Exception as e:
            debug_logger.error("Elastic search error", {"error": str(e)})
            return []


def create_elk_client() -> ELKClient:
    """Create ELK client with default configuration.
    
    Returns:
        Configured ELKClient
    """
    return ELKClient(
        url=config.ELASTIC_URL,
        api_key=config.ELASTIC_API_KEY,
        index_prefix=getattr(config, 'ELASTIC_INDEX_PREFIX', 'suraksha')
    )