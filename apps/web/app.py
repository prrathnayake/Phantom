"""Mission Control Dashboard - Web Application.

A web-based dashboard for interacting with the Monica agent."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from threading import Lock

import config
from core import Storage, OpenRouterClient
from central_agent import CentralAgent, create_central_agent
from gateway import ScheduleManager
from diagnostics import process_sensor, port_sensor, file_sensor

app = Flask(__name__)
app.secret_key = "monica-mission-control-key"

chat_history = []
chat_lock = Lock()

agent = None
schedule_manager = None
storage = None


def init_app():
    """Initialize application components."""
    global agent, schedule_manager, storage
    
    storage = Storage()
    agent = create_central_agent()
    schedule_manager = ScheduleManager()
    
    return agent, schedule_manager, storage


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
    return jsonify({"count": count})


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


@app.route("/api/status", methods=["GET"])
def status_api():
    """Get system status."""
    event_count = 0
    detection_count = 0
    
    if storage:
        events = storage.get_recent_events(count=1000)
        detections = storage.get_recent_detections(count=1000)
        event_count = len(events)
        detection_count = len(detections)
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "events_logged": event_count,
        "detections": detection_count,
        "schedules": len(schedule_manager._schedules) if schedule_manager else 0
    })


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