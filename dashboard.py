"""TUI Dashboard for the Suraksha Monitoring Agent.

This application provides a real-time terminal UI that displays:
- Current sensor readings (processes, ports, files)
- Recent detections and anomalies
- Agent status and activity log
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.containers import Container
from textual.reactive import reactive
from textual.timer import Timer
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LOG_DIR
from core.storage import Storage


class DashboardData:
    """Fetches and caches data from the agent's storage."""

    def __init__(self):
        self.storage = Storage()

    def get_events(self, count=20):
        return self.storage.get_recent_events(count=count)

    def get_detections(self, count=20):
        return self.storage.get_recent_detections(count=count)

    def get_process_count(self):
        events = self.get_events(count=200)
        for event in reversed(events):
            if event.get("sensor") == "process_sensor":
                return event.get("data", {}).get("count", 0)
        return 0

    def get_port_count(self):
        events = self.get_events(count=200)
        for event in reversed(events):
            if event.get("sensor") == "port_sensor":
                return event.get("data", {}).get("count", 0)
        return 0

    def get_file_changes(self):
        events = self.get_events(count=100)
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


class SensorPanel(Static):
    """Panel displaying current sensor statistics."""

    dashboard_data = DashboardData()

    def compose(self) -> ComposeResult:
        yield Static("SENSOR STATUS", id="sensor-title")

    def update_counts(self):
        proc_count = self.dashboard_data.get_process_count()
        port_count = self.dashboard_data.get_port_count()
        file_data = self.dashboard_data.get_file_changes()

        self.query_one("#sensor-title", Static).update(
            f"SENSOR STATUS\n"
            f"────────────\n"
            f"Processes: {proc_count}\n"
            f"Open Ports: {port_count}\n"
            f"Files Changed: {file_data.get('total', 0)}"
        )


class DetectionsPanel(Static):
    """Panel displaying recent detections."""

    dashboard_data = DashboardData()

    def compose(self) -> ComposeResult:
        yield Static("DETECTIONS", id="detections-title")
        yield DataTable(id="detections-table")

    def on_mount(self) -> None:
        table = self.query_one("#detections-table", DataTable)
        table.add_columns("Time", "Rule", "Description")
        table.cursor_type = "row"

    def refresh(self):
        table = self.query_one("#detections-table", DataTable)
        table.clear()
        detections = self.dashboard_data.get_detections(count=15)

        for det in detections:
            timestamp = det.get("timestamp", "")[11:19]
            rule = det.get("rule", "")
            desc = det.get("description", "")[:45]
            table.add_row(timestamp, rule, desc)


class EventsPanel(Static):
    """Panel displaying recent events log."""

    dashboard_data = DashboardData()

    def compose(self) -> ComposeResult:
        yield Static("ACTIVITY LOG", id="events-title")
        yield DataTable(id="events-table")

    def on_mount(self) -> None:
        table = self.query_one("#events-table", DataTable)
        table.add_columns("Time", "Sensor", "Data")
        table.cursor_type = "row"

    def refresh(self):
        table = self.query_one("#events-table", DataTable)
        table.clear()
        events = self.dashboard_data.get_events(count=20)

        for event in events:
            timestamp = event.get("timestamp", "")[11:19]
            sensor = event.get("sensor", "")
            data = event.get("data", {})

            if sensor == "process_sensor":
                summary = f"{data.get('count', 0)} processes"
            elif sensor == "port_sensor":
                summary = f"{data.get('count', 0)} ports"
            elif sensor == "file_sensor":
                total = data.get("change_count", 0)
                added = len(data.get("added", []))
                removed = len(data.get("removed", []))
                modified = len(data.get("modified", []))
                summary = f"+{added} -{removed} ~{modified}"
            elif sensor == "vulnerability_check":
                summary = "vulnerability check"
            else:
                summary = str(list(data.keys())[:2])

            table.add_row(timestamp, sensor, summary)


class StatusPanel(Static):
    """Panel displaying agent status."""

    def compose(self) -> ComposeResult:
        yield Static("AGENT STATUS", id="status-title")

    def update_status(self):
        log_dir = LOG_DIR
        log_exists = log_dir.exists()
        events_file = log_dir / "events.log"
        detections_file = log_dir / "detections.log"

        events_count = 0
        detections_count = 0

        if events_file.exists():
            try:
                events_count = sum(1 for _ in events_file.open())
            except:
                pass

        if detections_file.exists():
            try:
                detections_count = sum(1 for _ in detections_file.open())
            except:
                pass

        self.query_one("#status-title", Static).update(
            f"AGENT STATUS\n"
            f"───────────\n"
            f"Log Dir: {log_dir}\n"
            f"Events: {events_count}\n"
            f"Detections: {detections_count}\n"
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )


class DashboardApp(App):
    """Main TUI Dashboard Application."""

    CSS = """
    Screen { layout: grid; grid-size: 3 2; }

    #sensor-panel {
        column-span: 1; row-span: 1;
        border: solid green; padding: 1; margin: 1;
    }

    #detections-panel {
        column-span: 2; row-span: 1;
        border: solid red; padding: 1; margin: 1;
    }

    #events-panel {
        column-span: 2; row-span: 1;
        border: solid blue; padding: 1; margin: 1;
    }

    #status-panel {
        column-span: 1; row-span: 1;
        border: solid yellow; padding: 1; margin: 1;
    }

    Static { text-style: bold; }
    DataTable { height: 100%; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
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
        self.query_one("#sensor-panel", SensorPanel).update_counts()
        self.query_one("#detections-panel", DetectionsPanel).refresh()
        self.query_one("#events-panel", EventsPanel).refresh()
        self.query_one("#status-panel", StatusPanel).update_status()

    def action_quit(self) -> None:
        if self._update_timer:
            self._update_timer.stop()
        self.exit()


def main():
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()