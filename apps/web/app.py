"""Mission Control Dashboard - Web Application.

A web-based dashboard for interacting with the Monica agent."""
import os
import sys
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from threading import Lock

import config
from core import Storage, OpenRouterClient
from central_agent import CentralAgent, create_central_agent
from gateway import ScheduleManager
from diagnostics import process_sensor, port_sensor, file_sensor

app = Flask(__name__)
app.secret_key = "monica-mission-control-key"

start_time = datetime.utcnow()
chat_history = []
chat_lock = Lock()

agent = None
schedule_manager = None
storage = None
approval_manager = None
alert_manager = None
response_engine = None


def create_app():
    """Create and return Flask app for Flask CLI."""
    init_app()
    return app


def init_app():
    """Initialize application components."""
    global agent, schedule_manager, storage, approval_manager, alert_manager, response_engine
    
    storage = Storage()
    agent = create_central_agent()
    schedule_manager = ScheduleManager()
    
    from analysis.approval_manager import create_approval_manager
    from analysis.alert_manager import create_alert_manager
    from analysis.response_actions import create_response_engine
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


@app.route("/chat")
def chat_page():
    """Chat with agent page."""
    return render_template("chat.html")


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
    """Reports viewer page."""
    reports = []
    reports_dir = Path("central_agent/reports")
    
    if reports_dir.exists():
        for date_dir in sorted(reports_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for report in sorted(date_dir.glob("*.md"), reverse=True):
                    reports.append({
                        "date": date_dir.name,
                        "name": report.name,
                        "path": str(report),
                        "modified": datetime.fromtimestamp(report.stat().st_mtime).isoformat()
                    })
    
    return render_template("reports.html", reports=reports)


@app.route("/approvals")
def approvals_page():
    """Approval requests page."""
    return render_template("approvals.html")


@app.route("/alerts")
def alerts_page():
    """Alerts page."""
    return render_template("alerts.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Chat with the agent."""
    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    
    with chat_lock:
        chat_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    context_summary = _get_recent_context()
    memory_summary = _get_recent_memory()
    
    prompt = f"""You are the Monica Security Agent. 
User wants to chat with you about security monitoring.

Recent Context:
{context_summary}

Recent Memory:
{memory_summary}

Chat History:
{chr(10).join([f"{m['role']}: {m['content']}" for m in chat_history[-5:]])}

User: {user_message}

Respond as a helpful security assistant."""

    llm_client = OpenRouterClient()
    messages = [
        {"role": "system", "content": "You are Monica, a helpful security monitoring assistant."},
        {"role": "user", "content": prompt}
    ]
    
    response = llm_client.chat_completion(messages, max_tokens=512)
    
    if not response:
        response = "I apologize, but I'm unable to process your request right now. Please ensure the OPENROUTER_API_KEY is configured."
    
    with chat_lock:
        chat_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return jsonify({
        "response": response,
        "history": chat_history[-10:]
    })
    
    return render_template("reports.html", reports=reports)


@app.route("/api/report/<path:report_path>", methods=["GET"])
def report_content_api(report_path):
    """Get report content."""
    try:
        report_file = Path(report_path)
        if report_file.exists():
            return report_file.read_text(encoding="utf-8")
        return "Report not found", 404
    except Exception as e:
        return str(e), 500


@app.route("/api/reports/count", methods=["GET"])
def reports_count_api():
    """Get total report count."""
    reports_dir = Path("central_agent/reports")
    count = 0
    if reports_dir.exists():
        count = len(list(reports_dir.glob("**/*.md")))
    return jsonify({"count": count    })


@app.route("/api/chat/history", methods=["GET"])
def chat_history_api():
    """Get chat history."""
    with chat_lock:
        return jsonify(chat_history[-20:])


@app.route("/api/chat/clear", methods=["POST"])
def chat_clear_api():
    """Clear chat history."""
    with chat_lock:
        chat_history.clear()
    return jsonify({"status": "cleared"})


@app.route("/api/diagnostics/run", methods=["POST"])
def run_diagnostic_api():
    """Run a diagnostic manually."""
    data = request.get_json()
    diagnostic = data.get("diagnostic", "")
    
    if not diagnostic:
        return jsonify({"error": "No diagnostic specified"}), 400
    
    try:
        context = {}
        
        if diagnostic == "process":
            result = process_sensor.collect(context)
        elif diagnostic == "port":
            result = port_sensor.collect(context)
        elif diagnostic == "file":
            result = file_sensor.collect(context)
        else:
            return jsonify({"error": f"Unknown diagnostic: {diagnostic}"}), 400
        
        storage.log_event(f"web_{diagnostic}", result)
        
        if agent and result:
            analysis = agent.analyze(
                payload={"source": f"web_{diagnostic}", "data": result},
                session_id=f"web-{diagnostic}-{datetime.utcnow().timestamp()}",
                trigger="manual"
            )
            
            return jsonify({
                "status": "success",
                "diagnostic": diagnostic,
                "result": result,
                "analysis": analysis.analysis,
                "risk_level": analysis.risk_level
            })
        
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


@app.route("/api/schedules/<name>/interval", methods=["POST"])
def update_schedule_interval_api(name):
    """Update schedule interval."""
    data = request.get_json()
    new_interval = data.get("interval")
    if not new_interval or new_interval < 10:
        return jsonify({"success": False, "error": "Invalid interval (min 10 seconds)"}), 400
    
    if schedule_manager:
        with schedule_manager._lock:
            schedule = schedule_manager._schedules.get(name)
            if schedule:
                schedule.interval = new_interval
                schedule.next_run = datetime.utcnow() + timedelta(seconds=new_interval)
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
        
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        events_24h = sum(1 for e in events if datetime.fromisoformat(e.get('timestamp', '2020-01-01')) > one_day_ago)
        detections_24h = sum(1 for d in detections if datetime.fromisoformat(d.get('timestamp', '2020-01-01')) > one_day_ago)
    else:
        events_24h = 0
        detections_24h = 0
    
    uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
    hrs = int(uptime_seconds // 3600)
    mins = int((uptime_seconds % 3600) // 60)
    secs = int(uptime_seconds % 60)
    uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
    
    last_activity = storage.get_recent_events(count=1)
    last_activity_time = last_activity[0].get('timestamp') if last_activity else None
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": uptime_str,
        "events_logged": event_count,
        "detections": detection_count,
        "events_24h": events_24h,
        "detections_24h": detections_24h,
        "active_sensors": 3,
        "last_activity": last_activity_time,
        "schedules": len(schedule_manager._schedules) if schedule_manager else 0
    })


@app.route("/api/system/info", methods=["GET"])
def system_info_api():
    """Get system information."""
    return jsonify({
        "platform": platform.system() + " " + platform.release(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "processor": platform.processor()
    })


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