"""TUI Dashboard for the SMA - Secure Monitoring Agent.

This application provides a real-time terminal UI that displays:
- Current sensor readings (processes, ports, files)
- Recent detections and anomalies
- Agent status and activity log
"""
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.containers import Container
from datetime import datetime
from pathlib import Path

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOG_DIR
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
    """Main TUI Dashboard Application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
    }

    .panel {
        height: 100%;
        padding: 1;
        border: solid green;
    }

    #sensor-panel { border-color: green; }
    #detections-panel { border-color: red; }
    #events-panel { border-color: blue; }
    #status-panel { border-color: yellow; }

    Static { text-style: bold; }
    DataTable { height: 100%; margin-top: 1; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.storage = Storage()
        self._refresh_count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("SENSOR STATUS", id="sensor-content"),
            Static("DETECTIONS", id="detections-content"),
            Static("ACTIVITY LOG", id="events-content"),
            Static("AGENT STATUS", id="status-content"),
            id="main-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(2.0, self.do_refresh)

    def action_refresh(self) -> None:
        self.do_refresh()

    def do_refresh(self):
        self._refresh_count += 1

        sensor_content = self.query_one("#sensor-content", Static)
        detections_content = self.query_one("#detections-content", Static)
        events_content = self.query_one("#events-content", Static)
        status_content = self.query_one("#status-content", Static)

        try:
            events = self.storage.get_recent_events(count=100)
        except Exception as e:
            events = []

        try:
            detections = self.storage.get_recent_detections(count=20)
        except Exception as e:
            detections = []

        proc_count = 0
        port_count = 0
        file_total = 0

        for event in reversed(events):
            sensor = event.get("sensor", "")
            data = event.get("data", {})
            if sensor == "process_sensor" and proc_count == 0:
                proc_count = data.get("count", 0)
            elif sensor == "port_sensor" and port_count == 0:
                port_count = data.get("count", 0)
            elif sensor == "file_sensor" and file_total == 0:
                file_total = data.get("change_count", 0)

        sensor_content.update(
            f"SENSOR STATUS\n"
            f"────────────\n"
            f"Processes: {proc_count}\n"
            f"Open Ports: {port_count}\n"
            f"Files Changed: {file_total}"
        )

        det_lines = ["DETECTIONS", "──────────"]
        if detections:
            for det in detections[:8]:
                ts = det.get("timestamp", "")[11:19]
                rule = det.get("rule", "")
                desc = det.get("description", "")[:30]
                det_lines.append(f"{ts} {rule}")
                det_lines.append(f"  {desc}")
        else:
            det_lines.append("No detections yet")
        detections_content.update("\n".join(det_lines))

        event_lines = ["ACTIVITY LOG", "───────────"]
        if events:
            for event in events[:8]:
                ts = event.get("timestamp", "")[11:19]
                sensor = event.get("sensor", "")
                data = event.get("data", {})
                if sensor == "process_sensor":
                    summary = f"{data.get('count', 0)} procs"
                elif sensor == "port_sensor":
                    summary = f"{data.get('count', 0)} ports"
                elif sensor == "file_sensor":
                    total = data.get("change_count", 0)
                    summary = f"{total} changes"
                else:
                    summary = str(list(data.keys())[:2])
                event_lines.append(f"{ts} {sensor}: {summary}")
        else:
            event_lines.append("No events yet")
        events_content.update("\n".join(event_lines))

        events_count, detections_count = get_log_counts()
        status_content.update(
            f"AGENT STATUS\n"
            f"───────────\n"
            f"Log Dir: {LOG_DIR}\n"
            f"Events: {events_count}\n"
            f"Detections: {detections_count}\n"
            f"Refresh: #{self._refresh_count}\n"
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )

    def action_quit(self) -> None:
        self.exit()


def main():
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()