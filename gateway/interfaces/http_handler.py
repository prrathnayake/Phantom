"""HTTP Handler for Gateway.

Provides HTTP API endpoints for remote triggers.
"""
import json
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Any, Callable, Dict, Optional

from utils.debug_log import debug_logger


class HTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Gateway.
    
    Provides REST endpoints:
    - POST /analyze - Submit payload for analysis
    - GET /schedules - Get schedule status
    - POST /schedules/{name}/run - Run specific schedule
    - GET /status - Gateway status
    - POST /trigger/{skill} - Trigger skill execution
    
    Class attributes set by server:
    - gateway: Gateway instance
    - schedule_manager: ScheduleManager instance
    - central_agent: CentralAgent instance
    """
    
    gateway = None
    schedule_manager = None
    central_agent = None
    
    def do_GET(self):  # noqa: N802
        """Handle GET requests."""
        if self.path == "/status":
            self._send_json_response({
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "schedules": self._get_schedule_info()
            })
        elif self.path == "/schedules":
            self._send_json_response({
                "schedules": self._get_schedule_info()
            })
        elif self.path.startswith("/report/"):
            session_id = self.path.split("/")[-1]
            self._get_report(session_id)
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
        
        if self.central_agent:
            result = self.central_agent.analyze(
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
        if self.central_agent:
            report_path = self.central_agent.get_report(session_id)
            if report_path:
                content = report_path.read_text()
                self._send_json_response({
                    "session_id": session_id,
                    "content": content
                })
            else:
                self._send_json_response({"error": "Report not found"}, status=404)
        else:
            self._send_json_response({"error": "CentralAgent not configured"}, status=500)
    
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
        central_agent: Optional[Any] = None
    ):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
        HTTPHandler.schedule_manager = schedule_manager
        HTTPHandler.central_agent = central_agent
        
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
    central_agent: Optional[Any] = None
) -> GatewayHTTPServer:
    """Create HTTP server.
    
    Returns:
        Configured GatewayHTTPServer instance
    """
    return GatewayHTTPServer(
        host=host,
        port=port,
        schedule_manager=schedule_manager,
        central_agent=central_agent
    )