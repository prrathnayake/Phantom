"""TUI Dashboard for the Suraksha Monitoring Agent.

This application provides a real-time terminal UI that displays:
- Current sensor readings (processes, ports, files)
- Recent detections and anomalies
- Agent status and activity log
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, Log
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer
import threading
import time
from pathlib import Path
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core.storage import Storage


class DashboardData:
    """Fetches and caches data from the agent's storage."""

    def __init__(self):
        self.storage = Storage()
        self._lock = threading.Lock()

    def get_events(self, count=20):
        return self.storage.get_recent_events(count=count)

    def get_detections(self, count=20):
        return self.storage.get_recent_detections(count=count)

    def get_process_count(self):
        events = self.get_events(count=100)
        for event in reversed(events):
            if event.get("sensor") == "process_sensor":
                return event.get("data", {}).get("count", 0)
        return 0

    def get_port_count(self):
        events = self.get_events(count=100)
        for event in reversed(events):
            if event.get("sensor") == "port_sensor":
                return event.get("data", {}).get("count", 0)
        return 0

    def get_file_changes(self):
        events = self.get_events(count=50)
        for event in reversed(events):
            if event.get("sensor") == "file_sensor":
                data = event.get("data", {})
                return {
                    "added": len(data.get("added", [])),
                    "removed": len(data.get("removed", [])),
                    "modified": len(data.get("modified", [])),
                    "total": data.get("change_count", 0),
                }
        return {"added": 0, "removed": 0, "modified": 0, "total": 0}

    def get_log_files(self):
        log_dir = config.LOG_DIR
        if not log_dir.exists():
            return []
        return list(log_dir.glob("*.log"))


class SensorPanel(Static):
    """Panel displaying current sensor statistics."""

    process_count = reactive(0)
    port_count = reactive(0)
    file_changes = reactive(0)
    dashboard_data = DashboardData()

    def compose(self) -> ComposeResult:
        yield Static("📊 SENSOR STATUS", id="sensor-title")

    def watch_process_count(self, count: int) -> None:
        self.refresh_panel()

    def watch_port_count(self, count: int) -> None:
        self.refresh_panel()

    def watch_file_changes(self, count: int) -> None:
        self.refresh_panel()

    def refresh_panel(self):
        self.query_one("#sensor-title", Static).update(
            f"📊 SENSOR STATUS\n"
            f"───────────────\n"
            f"Processes: {self.process_count}\n"
            f"Open Ports: {self.port_count}\n"
            f"File Changes: {self.file_changes}"
        )

    def update_counts(self):
        self.process_count = self.dashboard_data.get_process_count()
        self.port_count = self.dashboard_data.get_port_count()
        file_data = self.dashboard_data.get_file_changes()
        self.file_changes = file_data.get("total", 0)


class DetectionsPanel(Static):
    """Panel displaying recent detections."""

    dashboard_data = DashboardData()
    detections = reactive([])

    def compose(self) -> ComposeResult:
        yield Static("🚨 RECENT DETECTIONS", id="detections-title")
        yield DataTable(id="detections-table")

    def on_mount(self) -> None:
        table = self.query_one("#detections-table", DataTable)
        table.add_columns("Time", "Rule", "Description")
        table.cursor_type = "none"

    def watch_detections(self, detections: list) -> None:
        self.update_table()

    def update_table(self):
        table = self.query_one("#detections-table", DataTable)
        table.clear()
        for det in self.detections[:15]:
            timestamp = det.get("timestamp", "")[:19]
            rule = det.get("rule", "")
            desc = det.get("description", "")[:40]
            table.add_row(timestamp, rule, desc)

    def refresh_detections(self):
        self.detections = self.dashboard_data.get_detections(count=20)


class EventsPanel(Static):
    """Panel displaying recent events log."""

    dashboard_data = DashboardData()
    events = reactive([])

    def compose(self) -> ComposeResult:
        yield Static("📋 ACTIVITY LOG", id="events-title")
        yield DataTable(id="events-table")

    def on_mount(self) -> None:
        table = self.query_one("#events-table", DataTable)
        table.add_columns("Time", "Sensor", "Summary")
        table.cursor_type = "none"

    def watch_events(self, events: list) -> None:
        self.update_table()

    def update_table(self):
        table = self.query_one("#events-table", DataTable)
        table.clear()
        for event in self.events[:15]:
            timestamp = event.get("timestamp", "")[:19]
            sensor = event.get("sensor", "")
            data = event.get("data", {})
            if sensor == "process_sensor":
                summary = f"{data.get('count', 0)} processes"
            elif sensor == "port_sensor":
                summary = f"{data.get('count', 0)} ports"
            elif sensor == "file_sensor":
                summary = f"{data.get('change_count', 0)} changes"
            else:
                summary = str(data)[:30]
            table.add_row(timestamp, sensor, summary)

    def refresh_events(self):
        self.events = self.dashboard_data.get_events(count=30)


class StatusPanel(Static):
    """Panel displaying agent status."""

    status = reactive("Running")
    last_update = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("✅ AGENT STATUS", id="status-title")

    def watch_status(self, status: str) -> None:
        self.refresh_status()

    def watch_last_update(self, last_update: str) -> None:
        self.refresh_status()

    def refresh_status(self):
        self.query_one("#status-title", Static).update(
            f"✅ AGENT STATUS\n"
            f"───────────────\n"
            f"Status: {self.status}\n"
            f"Last Update: {self.last_update}"
        )

    def update_status(self, status: str, last_update: str):
        self.status = status
        self.last_update = last_update


class DashboardApp(App):
    """Main TUI Dashboard Application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-columns: 1fr 2fr 1fr;
        grid-rows: 1fr 2fr;
    }

    #sensor-panel {
        column-span: 1;
        row-span: 1;
        border: solid green;
        padding: 1;
        margin: 1;
    }

    #detections-panel {
        column-span: 2;
        row-span: 1;
        border: solid red;
        padding: 1;
        margin: 1;
    }

    #events-panel {
        column-span: 2;
        row-span: 1;
        border: solid blue;
        padding: 1;
        margin: 1;
    }

    #status-panel {
        column-span: 1;
        row-span: 1;
        border: solid yellow;
        padding: 1;
        margin: 1;
    }

    Static {
        text-style: bold;
    }

    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.dashboard_data = DashboardData()
        self._update_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            SensorPanel(id="sensor-panel"),
            DetectionsPanel(id="detections-panel"),
            EventsPanel(id="events-panel"),
            StatusPanel(id="status-panel"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._update_timer = self.set_interval(2.0, self.refresh_data)
        self.refresh_data()

    def action_refresh(self) -> None:
        self.refresh_data()

    def refresh_data(self):
        from datetime import datetime

        sensor_panel = self.query_one("#sensor-panel", SensorPanel)
        sensor_panel.update_counts()

        detections_panel = self.query_one("#detections-panel", DetectionsPanel)
        detections_panel.refresh_detections()

        events_panel = self.query_one("#events-panel", EventsPanel)
        events_panel.refresh_events()

        status_panel = self.query_one("#status-panel", StatusPanel)
        status_panel.update_status("Running", datetime.now().strftime("%H:%M:%S"))

    def action_quit(self) -> None:
        if self._update_timer:
            self._update_timer.stop()
        self.exit()


def main():
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()