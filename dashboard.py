"""TUI Dashboard for the SMA - Secure Monitoring Agent.

This application provides a real-time terminal UI that displays:
- Current sensor readings (processes, ports, files) with detailed info
- Recent detections and anomalies with severity indicators
- Agent status and activity log with full details
"""
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, ProgressBar
from textual.containers import Container, Horizontal, Vertical
from datetime import datetime, timedelta
from pathlib import Path

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOG_DIR, DETECTION_THRESHOLDS
from core.storage import Storage


def get_log_counts():
    events_count = 0
    detections_count = 0
    events_file = LOG_DIR / "events.log"
    detections_file = LOG_DIR / "detections.log"

    if events_file.exists():
        try:
            with events_file.open("r", encoding="utf-8") as f:
                events_count = sum(1 for _ in f)
        except:
            pass

    if detections_file.exists():
        try:
            with detections_file.open("r", encoding="utf-8") as f:
                detections_count = sum(1 for _ in f)
        except:
            pass

    return events_count, detections_count


class DashboardApp(App):
    """Main TUI Dashboard Application with detailed status display."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
    }

    #main-container {
        layout: grid;
        grid-size: 3 2;
    }

    .panel {
        height: 100%;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        text-align: center;
        color: $text;
        background: $panel-darken-1;
    }

    #process-panel {
        border-title-color: $accent;
    }

    #port-panel {
        border-title-color: $accent;
    }

    #file-panel {
        border-title-color: $accent;
    }

    #detections-panel {
        border-title-color: $warning;
    }

    #events-panel {
        border-title-color: $primary;
    }

    #status-panel {
        border-title-color: $success;
    }

    .status-ok {
        color: $success;
    }

    .status-warn {
        color: $warning;
    }

    .status-alert {
        color: $error;
    }

    .data-value {
        color: $text;
    }

    .data-label {
        color: $text-muted;
    }

    Static {
        text-style: none;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
        ("1", "focus_panel('process')", "Processes"),
        ("2", "focus_panel('ports')", "Ports"),
        ("3", "focus_panel('files')", "Files"),
        ("4", "focus_panel('detections')", "Detections"),
        ("5", "focus_panel('events')", "Events"),
        ("6", "focus_panel('status')", "Status"),
    ]

    def __init__(self):
        super().__init__()
        self.storage = Storage()
        self._refresh_count = 0
        self._app_start_time = datetime.now()
        self._last_process_data = {}
        self._last_port_data = {}
        self._last_file_data = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Static("PROCESSES", id="process-title"),
                Static("", id="process-content"),
                id="process-panel",
                classes="panel"
            ),
            Vertical(
                Static("NETWORK PORTS", id="port-title"),
                Static("", id="port-content"),
                id="port-panel",
                classes="panel"
            ),
            Vertical(
                Static("FILE CHANGES", id="file-title"),
                Static("", id="file-content"),
                id="file-panel",
                classes="panel"
            ),
            Vertical(
                Static("DETECTIONS", id="detections-title"),
                Static("", id="detections-content"),
                id="detections-panel",
                classes="panel"
            ),
            Vertical(
                Static("ACTIVITY LOG", id="events-title"),
                Static("", id="events-content"),
                id="events-panel",
                classes="panel"
            ),
            Vertical(
                Static("AGENT STATUS", id="status-title"),
                Static("", id="status-content"),
                id="status-panel",
                classes="panel"
            ),
            id="main-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(3.0, self.do_refresh)

    def action_refresh(self) -> None:
        self.do_refresh()

    def action_focus_panel(self, panel: str) -> None:
        pass

    def do_refresh(self):
        self._refresh_count += 1

        process_content = self.query_one("#process-content", Static)
        port_content = self.query_one("#port-content", Static)
        file_content = self.query_one("#file-content", Static)
        detections_content = self.query_one("#detections-content", Static)
        events_content = self.query_one("#events-content", Static)
        status_content = self.query_one("#status-content", Static)

        try:
            events = self.storage.get_recent_events(count=200)
        except Exception:
            events = []

        try:
            detections = self.storage.get_recent_detections(count=50)
        except Exception:
            detections = []

        proc_count = 0
        port_count = 0
        file_total = 0

        for event in reversed(events):
            sensor = event.get("sensor", "")
            data = event.get("data", {})
            if sensor == "process_sensor" and proc_count == 0:
                proc_count = data.get("count", 0)
                self._last_process_data = data
            elif sensor == "port_sensor" and port_count == 0:
                port_count = data.get("count", 0)
                self._last_port_data = data
            elif sensor == "file_sensor" and file_total == 0:
                file_total = data.get("change_count", 0)
                self._last_file_data = data

        process_threshold = DETECTION_THRESHOLDS["process_count"]
        proc_pct = (proc_count / process_threshold * 100) if process_threshold > 0 else 0
        if proc_count > process_threshold:
            proc_status = "[ERROR]HIGH[ERROR]"
            proc_indicator = "(!)"
        elif proc_pct > 80:
            proc_status = "[WARNING]WARN[WARNING]"
            proc_indicator = "(~)"
        else:
            proc_status = "[SUCCESS]OK[SUCCESS]"
            proc_indicator = "(+)"

        top_procs = self._last_process_data.get("top_processes", [])
        top_procs_str = ""
        if top_procs:
            top_procs_str = "\n[Top Processes]:\n"
            for p in top_procs[:5]:
                name = p.get("name", "unknown")[:20]
                pid = p.get("pid", "?")
                cpu = p.get("cpu_percent", 0)
                mem = p.get("memory_percent", 0)
                top_procs_str += f"  {name:20s} PID:{pid:6} CPU:{cpu:5.1f}% MEM:{mem:5.1f}%\n"

        process_content.update(
            f"Count: {proc_count} {proc_indicator}\n"
            f"Threshold: {process_threshold}\n"
            f"Status: {proc_status}\n"
            f"Usage: {proc_pct:.0f}%\n"
            f"{top_procs_str}"
        )

        port_threshold = DETECTION_THRESHOLDS["open_ports"]
        port_pct = (port_count / port_threshold * 100) if port_threshold > 0 else 0
        if port_count > port_threshold:
            port_status = "[ERROR]HIGH[ERROR]"
            port_indicator = "(!)"
        elif port_pct > 80:
            port_status = "[WARNING]WARN[WARNING]"
            port_indicator = "(~)"
        else:
            port_status = "[SUCCESS]OK[SUCCESS]"
            port_indicator = "(+)"

        listening_ports = self._last_port_data.get("listening", [])
        ports_str = ""
        if listening_ports:
            ports_str = "\n[Listening Ports]:\n"
            for p in listening_ports[:10]:
                addr = p.get("address", "?")
                proto = p.get("protocol", "tcp")
                ports_str += f"  {proto:4s} {addr}\n"
            if len(listening_ports) > 10:
                ports_str += f"  ... and {len(listening_ports) - 10} more\n"

        port_content.update(
            f"Open Ports: {port_count} {port_indicator}\n"
            f"Threshold: {port_threshold}\n"
            f"Status: {port_status}\n"
            f"Usage: {port_pct:.0f}%\n"
            f"{ports_str}"
        )

        file_threshold = DETECTION_THRESHOLDS["file_changes"]
        file_pct = (file_total / file_threshold * 100) if file_threshold > 0 else 0
        if file_total > file_threshold:
            file_status = "[ERROR]HIGH[ERROR]"
            file_indicator = "(!)"
        elif file_pct > 80:
            file_status = "[WARNING]WARN[WARNING]"
            file_indicator = "(~)"
        else:
            file_status = "[SUCCESS]OK[SUCCESS]"
            file_indicator = "(+)"

        file_added = self._last_file_data.get("added", [])
        file_removed = self._last_file_data.get("removed", [])
        file_modified = self._last_file_data.get("modified", [])

        file_str = "\n[Change Summary]:\n"
        file_str += f"  Added: {len(file_added)}\n"
        file_str += f"  Modified: {len(file_modified)}\n"
        file_str += f"  Removed: {len(file_removed)}\n"

        if file_added[:3]:
            file_str += "\n[Recent Added]:\n"
            for f in file_added[:3]:
                file_str += f"  + {f[:40]}\n"
        if file_modified[:3]:
            file_str += "\n[Recent Modified]:\n"
            for f in file_modified[:3]:
                file_str += f"  ~ {f[:40]}\n"

        file_content.update(
            f"Total Changes: {file_total} {file_indicator}\n"
            f"Threshold: {file_threshold}\n"
            f"Status: {file_status}\n"
            f"Usage: {file_pct:.0f}%\n"
            f"{file_str}"
        )

        det_lines = []
        if detections:
            for i, det in enumerate(detections[:15]):
                ts = det.get("timestamp", "")[11:19]
                rule = det.get("rule", "")
                desc = det.get("description", "")
                details = det.get("details", {})
                
                severity = "?"
                if "process" in rule:
                    severity = "(!)" if details.get("count", 0) > process_threshold else "(~)"
                elif "port" in rule:
                    severity = "(!)" if details.get("count", 0) > port_threshold else "(~)"
                elif "file" in rule:
                    severity = "(!)" if details.get("added") or details.get("modified") else "(~)"
                
                det_lines.append(f"[{ts}] {severity} {rule}")
                det_lines.append(f"  {desc[:50]}")
                if i < len(detections) - 1:
                    det_lines.append("")
        else:
            det_lines.append("[No detections recorded]")
            det_lines.append("")
            det_lines.append("System operating normally.")

        detections_content.update("\n".join(det_lines))

        event_lines = []
        if events:
            for event in events[:20]:
                ts = event.get("timestamp", "")[11:19]
                sensor = event.get("sensor", "")
                data = event.get("data", {})
                
                if sensor == "process_sensor":
                    count = data.get("count", 0)
                    event_lines.append(f"[{ts}] PROCESS_SENSOR")
                    event_lines.append(f"  Running processes: {count}")
                elif sensor == "port_sensor":
                    count = data.get("count", 0)
                    ports_list = data.get("listening", [])
                    event_lines.append(f"[{ts}] PORT_SENSOR")
                    event_lines.append(f"  Listening ports: {count}")
                elif sensor == "file_sensor":
                    changes = data.get("change_count", 0)
                    added = len(data.get("added", []))
                    modified = len(data.get("modified", []))
                    event_lines.append(f"[{ts}] FILE_SENSOR")
                    event_lines.append(f"  Changes: {changes} (+{added} ~{modified})")
                else:
                    event_lines.append(f"[{ts}] {sensor}")
                    event_lines.append(f"  {str(data)[:40]}")
                event_lines.append("")
        else:
            event_lines.append("[No events recorded yet]")
            event_lines.append("")
            event_lines.append("Waiting for sensor data...")

        events_content.update("\n".join(event_lines))

        events_count, detections_count = get_log_counts()
        uptime = datetime.now() - self._app_start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status_content.update(
            f"[Agent Information]\n"
            f"  Status: [SUCCESS]RUNNING[SUCCESS]\n"
            f"  Uptime: {hours}h {minutes}m {seconds}s\n"
            f"  Refresh: #{self._refresh_count}\n"
            f"  Last Update: {datetime.now().strftime('%H:%M:%S')}\n"
            f"\n"
            f"[Log Statistics]\n"
            f"  Log Directory: {LOG_DIR}\n"
            f"  Total Events: {events_count}\n"
            f"  Total Detections: {detections_count}\n"
            f"\n"
            f"[Thresholds]\n"
            f"  Process: {process_threshold}\n"
            f"  Ports: {port_threshold}\n"
            f"  File Changes: {file_threshold}\n"
            f"\n"
            f"[Legend]\n"
            f"  (+) Normal  (~) Warning  (!) Alert"
        )


def main():
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()