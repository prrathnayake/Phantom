"""Mission Control Dashboard - Web Application.

A web-based dashboard for interacting with the Phantom agent."""
import os
import sys
import platform
import importlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

import json
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session
from threading import Lock

import config
from src.core import Storage, OpenRouterClient
from src.agent import create_agent
from src.gateway import create_schedule_manager

app = Flask(__name__)
app.secret_key = os.environ.get("PHANTOM_DASHBOARD_SECRET", "phantom-mission-control-key")

start_time = datetime.now(timezone.utc)
chat_lock = Lock()


class ChatStore:
    """File-backed per-session chat history."""

    def __init__(self):
        self._dir = config.LOG_DIR / "chats"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, sid: str) -> Path:
        return self._dir / f"{sid}.json"

    def load(self, sid: str) -> list:
        with self._lock:
            path = self._path(sid)
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            return []

    def save(self, sid: str, history: list) -> None:
        with self._lock:
            try:
                self._path(sid).write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    def clear(self, sid: str) -> None:
        with self._lock:
            try:
                self._path(sid).unlink(missing_ok=True)
            except OSError:
                pass


chat_store = ChatStore()


def _get_session_id() -> str:
    """Return a stable session ID for the current browser session."""
    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid.uuid4())
    return session["chat_session_id"]


def _get_chat_history() -> list:
    return chat_store.load(_get_session_id())


def _save_chat_history(history: list) -> None:
    chat_store.save(_get_session_id(), history)

agent = None
schedule_manager = None
storage = None
approval_manager = None
alert_manager = None
response_engine = None

REPORTS_ROOT = ROOT_DIR / "src" / "agent" / "reports"
SENSOR_TYPES = {
    "process": "process_sensor",
    "port": "port_sensor",
    "file": "file_sensor",
    "network": "network_sensor",
    "memory": "memory_sensor",
    "disk_io": "disk_io_sensor",
    "auth": "auth_sensor",
    "service": "service_sensor",
    "registry": "registry_sensor",
    "dns": "dns_sensor",
    "driver": "driver_sensor",
    "certificate": "certificate_sensor",
    "hardware": "hardware_sensor",
}


def create_app():
    """Create and return Flask app for Flask CLI."""
    init_app()
    return app


def init_app():
    """Initialize application components."""
    global agent, schedule_manager, storage, approval_manager, alert_manager, response_engine
    
    storage = Storage()
    agent = create_agent()
    schedule_manager = create_schedule_manager()
    
    from src.analysis.approval_manager import create_approval_manager
    from src.analysis.alert_manager import create_alert_manager
    from src.analysis.response_actions import create_response_engine
    approval_mgr = create_approval_manager()
    alert_mgr = create_alert_manager()
    resp_engine = create_response_engine()
    
    # Assign to global variables
    approval_manager = approval_mgr
    alert_manager = alert_mgr
    response_engine = resp_engine
    
    return agent, schedule_manager, storage, approval_manager, alert_manager, response_engine


@app.route("/shutdown", methods=["POST"])
def shutdown():
    """Shutdown endpoint."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    return "OK"


@app.route("/health")
def health():
    """Health check."""
    return "OK"


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html")


@app.route("/diagnostics")
def diagnostics_page():
    """Diagnostics runner page."""
    schedules = schedule_manager.get_all_schedules() if schedule_manager else {}
    return render_template("diagnostics.html", schedules=schedules)


@app.route("/monitor")
def monitor_page():
    """Activity monitor page."""
    return render_template("monitor.html")


@app.route("/reports")
def reports_page():
    """Reports viewer page with pagination."""
    reports = []
    reports_dir = REPORTS_ROOT
    
    # Pagination params
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 500))
    except ValueError:
        limit = 50
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        offset = 0
    
    if reports_dir.exists():
        all_reports = []
        for date_dir in sorted(reports_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for report in date_dir.glob("*.md"):
                    try:
                        all_reports.append((
                            report,
                            report.stat().st_mtime
                        ))
                    except OSError:
                        continue
        
        all_reports.sort(key=lambda x: x[1], reverse=True)
        total = len(all_reports)
        
        for report, _ in all_reports[offset:offset + limit]:
            rel_path = report.relative_to(reports_dir).as_posix()
            reports.append({
                "date": report.parent.name,
                "name": report.name,
                "path": rel_path,
                "size": report.stat().st_size,
                "modified": datetime.fromtimestamp(report.stat().st_mtime, timezone.utc).isoformat()
            })
    else:
        total = 0
    
    return render_template(
        "reports.html",
        reports=reports,
        total=total,
        limit=limit,
        offset=offset
    )


@app.route("/approvals")
def approvals_page():
    """Approval requests page."""
    return render_template("approvals.html")


@app.route("/alerts")
def alerts_page():
    """Alerts page."""
    return render_template("alerts.html")


@app.route("/docs")
def docs_page():
    """Documentation page."""
    return render_template("docs.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Chat with the agent."""
    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    
    history = _get_chat_history()
    history.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    _save_chat_history(history)
    
    context_summary = _get_recent_context()
    memory_summary = _get_recent_memory()
    
    history = _get_chat_history()
    prompt = f"""You are the Phantom Security Agent.
User wants to chat with you about security monitoring.

Recent Context:
{context_summary}

Recent Memory:
{memory_summary}

Chat History:
{chr(10).join([f"{m['role']}: {m['content']}" for m in history[-5:]])}

User: {user_message}

Respond as a helpful security assistant."""

    llm_client = OpenRouterClient()
    messages = [
        {"role": "system", "content": "You are Phantom, a helpful security monitoring assistant."},
        {"role": "user", "content": prompt}
    ]
    
    response = llm_client.chat_completion(messages, max_tokens=512)
    
    if not response:
        error = llm_client.last_error
        if error and error.category == "missing_api_key":
            response = "I apologize, but I'm unable to process your request right now. Please ensure the OPENROUTER_API_KEY is configured."
        elif error and error.category == "timeout":
            response = "The LLM service is taking too long to respond. Please try again in a moment."
        elif error and error.category == "rate_limited":
            response = "Rate limit exceeded. Please wait a moment before sending another message."
        elif error and error.category == "auth_error":
            response = "Authentication failed. Please check that your OPENROUTER_API_KEY is valid."
        elif error and error.category == "http_error":
            response = f"The LLM service returned an error. Please try again later."
        else:
            response = "I apologize, but I'm unable to process your request right now. The AI service may be temporarily unavailable."
    
    history = _get_chat_history()
    history.append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    _save_chat_history(history)

    return jsonify({
        "response": response,
        "history": history[-10:]
    })


@app.route("/api/report/<path:report_path>", methods=["GET"])
def report_content_api(report_path):
    """Get report content."""
    try:
        report_file = _resolve_report_path(report_path)
        if report_file and report_file.exists():
            return report_file.read_text(encoding="utf-8")
        return "Report not found", 404
    except PermissionError:
        return "Report not found", 404
    except Exception as e:
        return str(e), 500


@app.route("/api/reports/count", methods=["GET"])
def reports_count_api():
    """Get total report count."""
    reports_dir = REPORTS_ROOT
    count = 0
    if reports_dir.exists():
        count = len(list(reports_dir.glob("**/*.md")))
    return jsonify({"count": count})


@app.route("/api/chat/history", methods=["GET"])
def chat_history_api():
    """Get chat history."""
    return jsonify(_get_chat_history()[-20:])


@app.route("/api/chat/clear", methods=["POST"])
def chat_clear_api():
    """Clear chat history."""
    chat_store.clear(_get_session_id())
    return jsonify({"status": "cleared"})


@app.route("/api/diagnostics/run", methods=["POST"])
def run_diagnostic_api():
    """Run a diagnostic manually."""
    data = request.get_json() or {}
    diagnostic = data.get("diagnostic", "")
    
    if not diagnostic:
        return jsonify({"error": "No diagnostic specified"}), 400
    
    try:
        sensor_module = SENSOR_TYPES.get(diagnostic)
        if not sensor_module:
            return jsonify({"error": f"Unknown diagnostic: {diagnostic}"}), 400

        context = {}
        module = _load_sensor_module(sensor_module)
        result = module.collect(context)
        
        storage.log_event(f"web_{diagnostic}", result)
        
        if agent and result:
            analysis = agent.analyze(
                payload={"source": f"web_{diagnostic}", "data": result},
                session_id=f"web-{diagnostic}-{datetime.now(timezone.utc).timestamp()}",
                trigger="manual"
            )
            
            analysis_status = "completed"
            fallback_summary = None
            llm_health = agent.llm_client.get_health()
            if analysis.analysis.startswith("LLM analysis unavailable"):
                analysis_status = "llm_unavailable"
                fallback_summary = _build_fallback_analysis(diagnostic, result)

            response = {
                "status": "success",
                "diagnostic": diagnostic,
                "result": result,
                "analysis": analysis.analysis,
                "risk_level": analysis.risk_level,
                "analysis_status": analysis_status,
                "llm_health": llm_health,
            }
            if fallback_summary:
                response["fallback_summary"] = fallback_summary
            return jsonify(response)
        
        return jsonify({
            "status": "success",
            "diagnostic": diagnostic,
            "result": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/activity", methods=["GET"])
def activity_api():
    """Get recent activity logs."""
    count = request.args.get("count", 50, type=int)
    
    if storage:
        events = storage.get_recent_events(count=count)
        detections = storage.get_recent_detections(count=count)
    else:
        events = []
        detections = []
    
    return jsonify({
        "events": events[-count:],
        "detections": detections[-count:]
    })


@app.route("/api/schedules", methods=["GET"])
def schedules_api():
    """Get schedule status."""
    if schedule_manager:
        return jsonify(schedule_manager.get_all_schedules())
    return jsonify({})


@app.route("/api/schedules/<name>/enable", methods=["POST"])
def enable_schedule_api(name):
    """Enable a schedule."""
    if schedule_manager and schedule_manager.enable_schedule(name):
        return jsonify({"success": True, "message": f"Schedule {name} enabled"})
    return jsonify({"success": False, "error": "Schedule not found"}), 404


@app.route("/api/schedules/<name>/disable", methods=["POST"])
def disable_schedule_api(name):
    """Disable a schedule."""
    if schedule_manager and schedule_manager.disable_schedule(name):
        return jsonify({"success": True, "message": f"Schedule {name} disabled"})
    return jsonify({"success": False, "error": "Schedule not found"}), 404


@app.route("/api/schedules/<name>/remove", methods=["POST"])
def remove_schedule_api(name):
    """Remove a schedule."""
    if schedule_manager and schedule_manager.remove_schedule(name):
        return jsonify({"success": True, "message": f"Schedule {name} removed"})
    return jsonify({"success": False, "error": "Schedule not found"}), 404


@app.route("/api/schedules/<name>/run", methods=["POST"])
def run_schedule_api(name):
    """Run a schedule manually."""
    if schedule_manager:
        result = schedule_manager.run_schedule(name)
        if result:
            return jsonify({"success": True, "result": result})
        return jsonify({"success": False, "error": "Schedule not found"}), 404
    return jsonify({"success": False, "error": "No schedule manager"}), 500


@app.route("/api/schedules/create", methods=["POST"])
def create_schedule_api():
    """Create a new schedule."""
    data = request.get_json() or {}
    name = data.get("name")
    try:
        interval = int(data.get("interval", 300))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid interval (min 10 seconds)"}), 400
    sensor = data.get("sensor", "process")
    
    if not name:
        return jsonify({"success": False, "error": "Name required"}), 400
    if interval < 10:
        return jsonify({"success": False, "error": "Invalid interval (min 10 seconds)"}), 400
    
    sensor_module = SENSOR_TYPES.get(sensor)
    if not sensor_module:
        return jsonify({"success": False, "error": f"Unknown sensor: {sensor}"}), 400

    try:
        _load_sensor_module(sensor_module)
    except ImportError:
        return jsonify({"success": False, "error": f"Unknown sensor: {sensor}"}), 400

    if schedule_manager:
        schedule_manager.add_schedule(name, interval, sensor_module)
        if not schedule_manager.get_schedule_info(name):
            return jsonify({"success": False, "error": f"Unknown sensor: {sensor}"}), 400
        return jsonify({"success": True, "name": name, "interval": interval, "sensor": sensor})
    return jsonify({"success": False, "error": "No schedule manager"}), 500


@app.route("/api/schedules/<name>/interval", methods=["POST"])
def update_schedule_interval_api(name):
    """Update schedule interval."""
    data = request.get_json() or {}
    try:
        new_interval = int(data.get("interval"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid interval (min 10 seconds)"}), 400
    if not new_interval or new_interval < 10:
        return jsonify({"success": False, "error": "Invalid interval (min 10 seconds)"}), 400
    
    if schedule_manager:
        if schedule_manager.update_interval(name, new_interval):
            return jsonify({"success": True, "message": f"Interval updated to {new_interval}s"})
        return jsonify({"success": False, "error": "Schedule not found"}), 404
    return jsonify({"success": False, "error": "No schedule manager"}), 500


@app.route("/api/status", methods=["GET"])
def status_api():
    """Get system status."""
    global start_time
    
    event_count = 0
    detection_count = 0
    
    if storage:
        events = storage.get_recent_events(count=1000)
        detections = storage.get_recent_detections(count=1000)
        event_count = len(events)
        detection_count = len(detections)
        
        events_24h = _count_since(events, "timestamp", hours=24)
        detections_24h = _count_since(detections, "timestamp", hours=24)
    else:
        events_24h = 0
        detections_24h = 0
    
    uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    hrs = int(uptime_seconds // 3600)
    mins = int((uptime_seconds % 3600) // 60)
    secs = int(uptime_seconds % 60)
    uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
    
    last_activity = storage.get_recent_events(count=1) if storage else []
    last_activity_time = last_activity[0].get('timestamp') if last_activity else None
    llm_health = agent.llm_client.get_health() if agent and agent.llm_client else OpenRouterClient().get_health()
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": uptime_str,
        "events_logged": event_count,
        "detections": detection_count,
        "events_24h": events_24h,
        "detections_24h": detections_24h,
        "active_sensors": _active_sensor_count(),
        "last_activity": last_activity_time,
        "schedules": schedule_manager.schedule_count() if schedule_manager else 0,
        "memory_usage": _get_memory_usage(),
        "llm_health": llm_health,
    })


@app.route("/api/system/info", methods=["GET"])
def system_info_api():
    """Get system information."""
    return jsonify({
        "platform": platform.system() + " " + platform.release(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "processor": platform.processor(),
        "memory_usage": _get_memory_usage()
    })


@app.route("/api/llm/health", methods=["GET"])
def llm_health_api():
    """Get sanitized LLM client health."""
    llm_health = agent.llm_client.get_health() if agent and agent.llm_client else OpenRouterClient().get_health()
    return jsonify(llm_health)


@app.route("/api/approvals", methods=["GET"])
def approvals_api():
    """Get approval requests."""
    global approval_manager
    if approval_manager:
        approvals = approval_manager.get_pending_approvals()
        return jsonify({
            "approvals": [approval_manager.get_action_summary(a) for a in approvals],
            "count": len(approvals)
        })
    return jsonify({"approvals": [], "count": 0})


@app.route("/api/approvals/<approval_id>/approve", methods=["POST"])
def approve_api(approval_id):
    """Approve an action request."""
    global approval_manager
    global alert_manager
    global response_engine
    
    if approval_manager:
        request = approval_manager.approve_request(approval_id, "web-ui")
        if request:
            if response_engine:
                params = {p.name: p.value for p in request.action_parameters}
                result = response_engine.execute(request.action_type, params)
                approval_manager.mark_executed(approval_id, str(result))
            
            if alert_manager:
                alert_manager.create_alert(
                    title=f"Action Approved: {request.action_type}",
                    description=request.reason,
                    severity=request.risk_level,
                    source="approval",
                    recommended_action=request.action_type,
                    affected_assets=[p.value for p in request.action_parameters if p.name in ["ip_address", "username", "file_path"]],
                    risk_score=request.risk_score
                )
            
            return jsonify({"status": "approved", "approval_id": approval_id})
    return jsonify({"error": "Approval not found"}), 404


@app.route("/api/approvals/<approval_id>/deny", methods=["POST"])
def deny_api(approval_id):
    """Deny an action request."""
    global approval_manager
    
    if approval_manager:
        request = approval_manager.deny_request(approval_id, "web-ui")
        if request:
            return jsonify({"status": "denied", "approval_id": approval_id})
    return jsonify({"error": "Approval not found"}), 404


@app.route("/api/alerts", methods=["GET"])
def alerts_api():
    """Get alerts."""
    global alert_manager
    if alert_manager:
        alerts = alert_manager.get_alerts(limit=50)
        return jsonify({
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
    return jsonify({"alerts": [], "count": 0})


@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert_api(alert_id):
    """Acknowledge an alert."""
    global alert_manager
    if alert_manager:
        if alert_manager.acknowledge_alert(alert_id):
            return jsonify({"status": "acknowledged", "alert_id": alert_id})
    return jsonify({"error": "Alert not found"}), 404


@app.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert_api(alert_id):
    """Resolve an alert."""
    global alert_manager
    if alert_manager:
        if alert_manager.resolve_alert(alert_id):
            return jsonify({"status": "resolved", "alert_id": alert_id})
    return jsonify({"error": "Alert not found"}), 404


@app.route("/api/alert-stats", methods=["GET"])
def alert_stats_api():
    """Get alert statistics."""
    global alert_manager
    if alert_manager:
        return jsonify(alert_manager.get_alert_stats())
    return jsonify({})


@app.route("/api/approval-stats", methods=["GET"])
def approval_stats_api():
    """Get approval statistics."""
    global approval_manager
    if approval_manager:
        return jsonify(approval_manager.get_approval_stats())
    return jsonify({})


def _load_sensor_module(sensor_module: str):
    """Load a diagnostic sensor by module name."""
    return importlib.import_module(f"src.diagnostics.{sensor_module}")


def _resolve_report_path(report_path: str) -> Path | None:
    """Resolve a report path safely inside the reports root."""
    root = REPORTS_ROOT.resolve()
    candidate = (root / report_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Report path outside reports root") from exc
    if candidate.suffix.lower() != ".md":
        return None
    return candidate


def _parse_timestamp(value) -> datetime | None:
    """Parse timestamps from logs into timezone-aware UTC datetimes."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _count_since(records: list[dict], field: str, hours: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    count = 0
    for record in records:
        parsed = _parse_timestamp(record.get(field))
        if parsed and parsed > cutoff:
            count += 1
    return count


def _active_sensor_count() -> int:
    if not schedule_manager:
        return 0
    schedules = schedule_manager.get_all_schedules()
    return sum(1 for item in schedules.values() if item and item.get("enabled"))


def _get_memory_usage() -> int | None:
    try:
        import psutil
        return int(round(psutil.virtual_memory().used / (1024 * 1024)))
    except Exception:
        return None


def _build_fallback_analysis(diagnostic: str, result: dict) -> str:
    """Build a local summary when LLM analysis is unavailable."""
    if diagnostic == "process":
        return f"Local fallback: observed {result.get('count', 0)} running processes. Review top CPU consumers for unusual names or owners."
    if diagnostic == "port":
        return f"Local fallback: observed {result.get('count', 0)} listening ports. Review externally exposed or unexpected services."
    if diagnostic == "file":
        return f"Local fallback: observed {result.get('change_count', 0)} file changes in {result.get('directory', 'the watched directory')}."
    if diagnostic == "network":
        return f"Local fallback: observed {result.get('established_count', 0)} established connections and {len(result.get('external_ips', []))} external IPs."
    if diagnostic == "memory":
        return f"Local fallback: memory usage is {result.get('percent_used', result.get('memory_percent', 'unknown'))}%."
    return f"Local fallback: {diagnostic} diagnostic completed. Review the raw result for unusual values."


def _get_recent_context():
    """Get recent context from storage."""
    if not storage:
        return "No storage available"
    
    events = storage.get_recent_events(count=5)
    if not events:
        return "No recent events"
    
    return "\n".join([
        f"- {e.get('sensor', 'unknown')}: {e.get('data', {})}"
        for e in events[-5:]
    ])


def _get_recent_memory():
    """Get recent memory from agent."""
    if not agent:
        return "No agent available"
    
    recent = agent.memory.get_recent(5)
    if not recent:
        return "No recent memory"
    
    return "\n".join([
        f"- {k}: {v}"
        for k, v in recent
    ])


if __name__ == "__main__":
    init_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
