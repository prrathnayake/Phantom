"""Payload Sender for Gateway.

Sends diagnostic payloads to Central Agent for analysis.
"""
import json
import uuid
from datetime import datetime, timezone
from threading import Thread
from typing import Any, Callable, Dict, List, Optional

import requests

from src.utils.debug_log import debug_logger


class PayloadSender:
    """Sends payloads to Central Agent.
    
    Handles payload transmission to central agent endpoint
    with retry logic and async support.
    
    Attributes:
        endpoint: Central agent endpoint URL
        retry_count: Number of retries on failure
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        retry_count: int = 3,
        timeout: int = 30
    ):
        self.endpoint = endpoint or "http://127.0.0.1:8000/analyze"
        self.retry_count = retry_count
        self.timeout = timeout
        
        debug_logger.info("PayloadSender initialized", {
            "endpoint": self.endpoint,
            "retry": retry_count
        })
    
    def send(
        self,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> bool:
        """Send payload to central agent.
        
        Args:
            payload: Diagnostic payload dict
            session_id: Optional session ID
            trigger: What triggered this send
            
        Returns:
            True if sent successfully
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        message = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "payload": payload
        }
        
        debug_logger.info("Sending payload", {
            "session_id": session_id,
            "source": payload.get("source", "unknown"),
            "endpoint": self.endpoint
        })
        
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    self.endpoint,
                    data=json.dumps(message),
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                debug_logger.info("Payload sent successfully", {
                    "session_id": session_id,
                    "attempt": attempt + 1
                })
                
                return True
            
            except requests.RequestException as e:
                debug_logger.warning("Payload send failed", {
                    "session_id": session_id,
                    "attempt": attempt + 1,
                    "error": str(e)
                })
                
                if attempt == self.retry_count - 1:
                    debug_logger.error("Payload send exhausted retries", {
                        "session_id": session_id
                    })
                    return False
                
                import time
                time.sleep(1 * (attempt + 1))
        
        return False
    
    def send_batch(
        self,
        payloads: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> bool:
        """Send multiple payloads as batch.
        
        Args:
            payloads: List of payload dicts
            session_id: Optional session ID
            trigger: What triggered this send
            
        Returns:
            True if all sent successfully
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        batch_payload = {
            "source": "batch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payloads": payloads,
            "count": len(payloads)
        }
        
        return self.send(batch_payload, session_id, trigger)
    
    def send_async(
        self,
        payload: Dict[str, Any],
        callback: Optional[Callable] = None,
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> str:
        """Send payload asynchronously.
        
        Args:
            payload: Diagnostic payload dict
            callback: Optional callback on completion
            session_id: Optional session ID
            trigger: What triggered this send
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        def _send_worker():
            success = self.send(payload, session_id, trigger)
            if callback:
                try:
                    callback(success, session_id)
                except Exception as e:
                    debug_logger.error("Callback error", {"error": str(e)})
        
        thread = Thread(target=_send_worker, daemon=True)
        thread.start()
        
        debug_logger.info("Async payload queued", {
            "session_id": session_id
        })
        
        return session_id
    
    def send_and_wait(
        self,
        payloads: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        trigger: str = "schedule"
    ) -> bool:
        """Send payloads and wait for analysis result.
        
        Args:
            payloads: List of payload dicts
            session_id: Optional session ID
            trigger: What triggered this send
            
        Returns:
            True if analysis completed
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        batch_payload = {
            "source": "batch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payloads": payloads,
            "count": len(payloads)
        }
        
        return self.send(batch_payload, session_id, trigger)


def create_payload_sender() -> PayloadSender:
    """Create PayloadSender with default settings.
    
    Returns:
        Configured PayloadSender instance
    """
    return PayloadSender(
        endpoint=None,
        retry_count=3,
        timeout=30
    )
