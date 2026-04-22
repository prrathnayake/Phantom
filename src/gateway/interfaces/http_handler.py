"""HTTP Handler for Gateway.

Provides HTTP API endpoints for remote triggers.
"""
import json
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Any, Callable, Dict, Optional

from src.utils.debug_log import debug_logger


class HTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Gateway.
    
    Provides REST endpoints:
    - POST /analyze - Submit payload for analysis
    - GET /schedules - Get schedule status
    - POST /schedules/{name}/run - Run specific schedule
    - GET /status - Gateway status
    - POST /trigger/{skill} - Trigger skill execution
    
    Approval endpoints:
    - GET /api/approvals - List pending approvals
    - POST /api/approvals - Create approval request
    - GET /api/approvals/{id} - Get approval details
    - POST /api/approvals/{id}/approve - Approve request
    - POST /api/approvals/{id}/deny - Deny request
    - GET /api/alerts - List alerts
    - POST /api/alerts/{id}/acknowledge - Acknowledge alert
    - POST /api/alerts/{id}/resolve - Resolve alert
    
    Class attributes set by server:
    - gateway: Gateway instance
    - schedule_manager: ScheduleManager instance
    -         agent: Agent instance
    - approval_manager: ApprovalManager instance
    - alert_manager: AlertManager instance
    """
    
    gateway = None
    schedule_manager = None
    agent = None
    approval_manager = None
    alert_manager = None
    
    def do_GET(self):  # noqa: N802
        """Handle GET requests."""
        if self.path == "/status":
            self._send_json_response({
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "schedules": self._get_schedule_info()
            })
        elif self.path == "/schedules":
            self._send_json_response({
                "schedules": self._get_schedule_info()
            })
        elif self.path.startswith("/report/"):
            session_id = self.path.split("/")[-1]
            self._get_report(session_id)
        elif self.path == "/api/approvals":
            self._handle_list_approvals({})
        elif self.path.startswith("/api/approvals/") and len(self.path) > len("/api/approvals/"):
            approval_id = self.path.split("/api/approvals/")[-1]
            self._get_approval(approval_id)
        elif self.path == "/api/alerts":
            self._handle_list_alerts({})
        else:
            self._send_json_response({"error": "Not found"}, status=404)
    
    def do_POST(self):  # noqa: N802
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json_response({"error": "Invalid JSON"}, status=400)
            return
        
        if self.path == "/analyze":
            self._handle_analyze(data)
        elif self.path == "/schedules":
            self._handle_create_schedule(data)
        elif self.path.startswith("/schedules/"):
            name = self.path.split("/")[-1]
            if name == "run":
                self._handle_run_all()
            else:
                self._handle_run_schedule(name)
        elif self.path.startswith("/trigger/"):
            skill = self.path.split("/")[-1]
            self._handle_trigger(skill, data)
        elif self.path == "/api/approvals":
            self._handle_create_approval(data)
        elif self.path.startswith("/api/approvals/"):
            parts = self.path.split("/")
            if len(parts) >= 4:
                action = parts[-1]
                approval_id = parts[3]
                if action == "approve":
                    self._handle_approve(approval_id, data)
                elif action == "deny":
                    self._handle_deny(approval_id, data)
                else:
                    self._send_json_response({"error": "Not found"}, status=404)
            else:
                self._send_json_response({"error": "Not found"}, status=404)
        elif self.path.startswith("/api/alerts/"):
            parts = self.path.split("/")
            if len(parts) >= 4:
                action = parts[-1]
                alert_id = parts[3]
                if action == "acknowledge":
                    self._handle_acknowledge_alert(alert_id)
                elif action == "resolve":
                    self._handle_resolve_alert(alert_id)
                else:
                    self._send_json_response({"error": "Not found"}, status=404)
            elif self.path == "/api/alerts":
                self._handle_list_alerts(data)
            else:
                self._send_json_response({"error": "Not found"}, status=404)
        else:
            self._send_json_response({"error": "Not found"}, status=404)
    
    def _send_json_response(
        self,
        data: Dict[str, Any],
        status: int = 200
    ) -> None:
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _handle_analyze(self, data: Dict[str, Any]) -> None:
        """Handle analysis request."""
        session_id = data.get("session_id", str(uuid.uuid4()))
        trigger = data.get("trigger", "http")
        payload = data.get("payload", data)
        
        debug_logger.info("Analysis requested", {
            "session_id": session_id,
            "trigger": trigger
        })
        
        if self.agent:
            result = self.agent.analyze(
                payload=payload,
                session_id=session_id,
                trigger=trigger
            )
            self._send_json_response({
                "status": "analyzed",
                "session_id": session_id,
                "risk_level": result.risk_level,
                "report": str(result.session_id)
            })
        else:
            self._send_json_response({
                "status": "queued",
                "session_id": session_id,
                "message": "Analysis will complete async"
            })
    
    def _handle_create_schedule(self, data: Dict[str, Any]) -> None:
        """Handle create schedule request."""
        name = data.get("name")
        interval = data.get("interval", 60)
        module = data.get("module", name)
        
        if not name:
            self._send_json_response({"error": "name required"}, status=400)
            return
        
        if self.schedule_manager:
            self.schedule_manager.add_schedule(
                name=name,
                interval=interval,
                script_module=module
            )
            self._send_json_response({
                "status": "created",
                "name": name,
                "interval": interval
            })
        else:
            self._send_json_response({"error": "ScheduleManager not configured"}, status=500)
    
    def _handle_run_schedule(self, name: str) -> None:
        """Handle run specific schedule."""
        if self.schedule_manager:
            result = self.schedule_manager.run_schedule(name)
            if result:
                self._send_json_response({
                    "status": "completed",
                    "name": name,
                    "result": result
                })
            else:
                self._send_json_response({
                    "error": "Schedule not found"
                }, status=404)
        else:
            self._send_json_response({"error": "ScheduleManager not configured"}, status=500)
    
    def _handle_run_all(self) -> None:
        """Handle run all schedules."""
        if self.schedule_manager:
            results = self.schedule_manager.run_all_due()
            self._send_json_response({
                "status": "completed",
                "count": len(results),
                "results": results
            })
        else:
            self._send_json_response({"error": "ScheduleManager not configured"}, status=500)
    
    def _handle_trigger(self, skill: str, data: Dict[str, Any]) -> None:
        """Handle skill trigger."""
        debug_logger.info("Skill triggered", {
            "skill": skill,
            "data": data
        })
        
        self._send_json_response({
            "status": "triggered",
            "skill": skill
        })
    
    def _get_schedule_info(self) -> Dict[str, Any]:
        """Get schedule information."""
        if self.schedule_manager:
            return self.schedule_manager.get_all_schedules()
        return {}
    
    def _get_report(self, session_id: str) -> None:
        """Get report for session."""
        if self.agent:
            report_path = self.agent.get_report(session_id)
            if report_path:
                content = report_path.read_text()
                self._send_json_response({
                    "session_id": session_id,
                    "content": content
                })
            else:
                self._send_json_response({"error": "Report not found"}, status=404)
        else:
            self._send_json_response({"error": "Agent not configured"}, status=500)
    
    def _handle_list_approvals(self, data: Dict[str, Any]) -> None:
        """Handle list approvals request."""
        if self.approval_manager:
            risk_level = data.get("risk_level")
            approvals = self.approval_manager.get_pending_approvals(risk_level)
            self._send_json_response({
                "approvals": [
                    self.approval_manager.get_action_summary(a) 
                    for a in approvals
                ],
                "count": len(approvals)
            })
        else:
            self._send_json_response({"error": "ApprovalManager not configured"}, status=500)
    
    def _handle_create_approval(self, data: Dict[str, Any]) -> None:
        """Handle create approval request."""
        if self.approval_manager:
            try:
                from src.analysis.approval_manager import ActionParameter
                
                action_type = data.get("action_type")
                raw_params = data.get("parameters", [])
                action_parameters = [
                    ActionParameter(
                        name=p.get("name"),
                        value=p.get("value"),
                        description=p.get("description", "")
                    ) for p in raw_params
                ]
                reason = data.get("reason", "")
                risk_level = data.get("risk_level", "medium")
                risk_score = data.get("risk_score", 50)
                triggered_by = data.get("triggered_by", "system")
                detection_rule = data.get("detection_rule")
                
                request = self.approval_manager.create_approval_request(
                    action_type=action_type,
                    action_parameters=action_parameters,
                    reason=reason,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    triggered_by=triggered_by,
                    detection_rule=detection_rule
                )
                
                self._send_json_response({
                    "status": "created",
                    "approval_id": request.approval_id,
                    "expires_at": request.expires_at
                })
            except Exception as e:
                self._send_json_response({"error": str(e)}, status=500)
        else:
            self._send_json_response({"error": "ApprovalManager not configured"}, status=500)
    
    def _handle_approve(self, approval_id: str, data: Dict[str, Any]) -> None:
        """Handle approve request."""
        if self.approval_manager:
            approved_by = data.get("approved_by", "admin")
            request = self.approval_manager.approve_request(approval_id, approved_by)
            if request:
                self._send_json_response({
                    "status": "approved",
                    "approval_id": approval_id,
                    "approved_at": request.approved_at
                })
            else:
                self._send_json_response({"error": "Approval not found"}, status=404)
        else:
            self._send_json_response({"error": "ApprovalManager not configured"}, status=500)
    
    def _handle_deny(self, approval_id: str, data: Dict[str, Any]) -> None:
        """Handle deny request."""
        if self.approval_manager:
            denied_by = data.get("denied_by", "admin")
            reason = data.get("reason")
            request = self.approval_manager.deny_request(approval_id, denied_by, reason)
            if request:
                self._send_json_response({
                    "status": "denied",
                    "approval_id": approval_id,
                    "denied_at": request.denied_at
                })
            else:
                self._send_json_response({"error": "Approval not found"}, status=404)
        else:
            self._send_json_response({"error": "ApprovalManager not configured"}, status=500)
    
    def _get_approval(self, approval_id: str) -> None:
        """Get approval details."""
        if self.approval_manager:
            request = self.approval_manager.get_approval(approval_id)
            if request:
                self._send_json_response(
                    self.approval_manager.get_action_summary(request)
                )
            else:
                self._send_json_response({"error": "Approval not found"}, status=404)
        else:
            self._send_json_response({"error": "ApprovalManager not configured"}, status=500)
    
    def _handle_list_alerts(self, data: Dict[str, Any]) -> None:
        """Handle list alerts request."""
        if self.alert_manager:
            severity = data.get("severity")
            status = data.get("status")
            alerts = self.alert_manager.get_alerts(severity, status)
            self._send_json_response({
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "title": a.title,
                        "severity": a.severity,
                        "status": a.status,
                        "created": a.timestamp,
                        "source": a.source
                    } for a in alerts
                ],
                "count": len(alerts)
            })
        else:
            self._send_json_response({"error": "AlertManager not configured"}, status=500)
    
    def _handle_acknowledge_alert(self, alert_id: str) -> None:
        """Handle acknowledge alert."""
        if self.alert_manager:
            if self.alert_manager.acknowledge_alert(alert_id):
                self._send_json_response({
                    "status": "acknowledged",
                    "alert_id": alert_id
                })
            else:
                self._send_json_response({"error": "Alert not found"}, status=404)
        else:
            self._send_json_response({"error": "AlertManager not configured"}, status=500)
    
    def _handle_resolve_alert(self, alert_id: str) -> None:
        """Handle resolve alert."""
        if self.alert_manager:
            if self.alert_manager.resolve_alert(alert_id):
                self._send_json_response({
                    "status": "resolved",
                    "alert_id": alert_id
                })
            else:
                self._send_json_response({"error": "Alert not found"}, status=404)
        else:
            self._send_json_response({"error": "AlertManager not configured"}, status=500)
    
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        """Suppress default logging."""
        return


class GatewayHTTPServer:
    """HTTP server for Gateway interfaces."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        schedule_manager: Optional[Any] = None,
        agent: Optional[Any] = None,
        approval_manager: Optional[Any] = None,
        alert_manager: Optional[Any] = None
    ):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
        HTTPHandler.schedule_manager = schedule_manager
        HTTPHandler.agent = agent
        HTTPHandler.approval_manager = approval_manager
        HTTPHandler.alert_manager = alert_manager
        
        debug_logger.info("HTTPHandler configured", {
            "host": host,
            "port": port
        })
    
    def start(self) -> None:
        """Start HTTP server."""
        self.server = HTTPServer((self.host, self.port), HTTPHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        debug_logger.info("HTTP server started", {
            "host": self.host,
            "port": self.port
        })
    
    def stop(self) -> None:
        """Stop HTTP server."""
        if self.server:
            self.server.shutdown()
            debug_logger.info("HTTP server stopped")


def create_http_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    schedule_manager: Optional[Any] = None,
    central_agent: Optional[Any] = None,
    approval_manager: Optional[Any] = None,
    alert_manager: Optional[Any] = None
) -> GatewayHTTPServer:
    """Create HTTP server.
    
    Returns:
        Configured GatewayHTTPServer instance
    """
    return GatewayHTTPServer(
        host=host,
        port=port,
        schedule_manager=schedule_manager,
        agent=agent,
        approval_manager=approval_manager,
        alert_manager=alert_manager
    )
