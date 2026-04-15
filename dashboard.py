"""Optimized TUI Dashboard for the SMA - Secure Monitoring Agent."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import os
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Static

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DETECTION_THRESHOLDS, LOG_DIR
from core.storage import Storage


def safe_tail_line_count(path: Path) -> int:
    """Cheap line count fallback.

    Still O(n), but isolated so you can later replace with cached counters
    or a storage-backed stat.
    """
    if not path.exists():
        return 0

    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


class DashboardApp(App):
    """Main TUI dashboard."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
        height: 1fr;
        padding: 1;
    }

    .panel {
        height: 100%;
        border: round $surface;
        padding: 0 1;
    }

    .panel-title {
        text-style: bold;
        text-align: center;
        background: $panel-darken-1;
        margin-bottom: 1;
    }

    #process-panel { border-title-color: $accent; }
    #port-panel { border-title-color: $accent; }
    #file-panel { border-title-color: $accent; }
    #detections-panel { border-title-color: $warning; }
    #events-panel { border-title-color: $primary; }
    #status-panel { border-title-color: $success; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.storage = Storage()
        self._refresh_count = 0
        self._app_start_time = datetime.now()

        self._last_process_data: dict[str, Any] = {}
        self._last_port_data: dict[str, Any] = {}
        self._last_file_data: dict[str, Any] = {}

        self._events_count_cache = safe_tail_line_count(LOG_DIR / "events.log")
        self._detections_count_cache = safe_tail_line_count(LOG_DIR / "detections.log")
        self._last_count_refresh = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            self._panel("PROCESSES", "process"),
            self._panel("NETWORK PORTS", "port"),
            self._panel("FILE CHANGES", "file"),
            self._panel("DETECTIONS", "detections"),
            self._panel("ACTIVITY LOG", "events"),
            self._panel("AGENT STATUS", "status"),
            id="main-container",
        )
        yield Footer()

    def _panel(self, title: str, name: str) -> Vertical:
        return Vertical(
            Static(title, classes="panel-title"),
            Static("", id=f"{name}-content", expand=True),
            id=f"{name}-panel",
            classes="panel",
        )

    def on_mount(self) -> None:
        self.process_content = self.query_one("#process-content", Static)
        self.port_content = self.query_one("#port-content", Static)
        self.file_content = self.query_one("#file-content", Static)
        self.detections_content = self.query_one("#detections-content", Static)
        self.events_content = self.query_one("#events-content", Static)
        self.status_content = self.query_one("#status-content", Static)

        self._refresh_log_counts_if_needed()
        self.set_interval(3.0, self.do_refresh)
        self.do_refresh()

    def action_refresh(self) -> None:
        self.do_refresh()

    def do_refresh(self) -> None:
        self._refresh_count += 1

        events = self._safe_get_events()
        detections = self._safe_get_detections()

        self._extract_latest_sensor_snapshots(events)
        self._refresh_log_counts_if_needed()

        self.process_content.update(self._render_process_panel())
        self.port_content.update(self._render_port_panel())
        self.file_content.update(self._render_file_panel())
        self.detections_content.update(self._render_detections_panel(detections))
        self.events_content.update(self._render_events_panel(events))
        self.status_content.update(self._render_status_panel())

    def _safe_get_events(self) -> list[dict[str, Any]]:
        try:
            return self.storage.get_recent_events(count=200) or []
        except Exception:
            return []

    def _safe_get_detections(self) -> list[dict[str, Any]]:
        try:
            return self.storage.get_recent_detections(count=50) or []
        except Exception:
            return []

    def _extract_latest_sensor_snapshots(self, events: list[dict[str, Any]]) -> None:
        proc_found = port_found = file_found = False

        for event in reversed(events):
            sensor = event.get("sensor", "")
            data = event.get("data", {})

            if sensor == "process_sensor" and not proc_found:
                self._last_process_data = data
                proc_found = True
            elif sensor == "port_sensor" and not port_found:
                self._last_port_data = data
                port_found = True
            elif sensor == "file_sensor" and not file_found:
                self._last_file_data = data
                file_found = True

            if proc_found and port_found and file_found:
                break

    def _refresh_log_counts_if_needed(self) -> None:
        """Refresh expensive log counts less often."""
        if self._refresh_count - self._last_count_refresh <= 4:
            return

        self._events_count_cache = safe_tail_line_count(LOG_DIR / "events.log")
        self._detections_count_cache = safe_tail_line_count(LOG_DIR / "detections.log")
        self._last_count_refresh = self._refresh_count

    def _status_meta(self, count: int, threshold: int) -> tuple[str, str, float]:
        pct = (count / threshold * 100) if threshold > 0 else 0.0

        if count > threshold:
            return "HIGH", "(!)", pct
        if pct > 80:
            return "WARN", "(~)", pct
        return "OK", "(+)", pct

    def _render_process_panel(self) -> str:
        threshold = DETECTION_THRESHOLDS["process_count"]
        count = self._last_process_data.get("count", 0)
        status, indicator, pct = self._status_meta(count, threshold)

        lines = [
            f"Count: {count} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
            f"Usage: {pct:.0f}%",
        ]

        top = self._last_process_data.get("top_processes", [])
        if top:
            lines.append("")
            lines.append("[Top Processes]")
            for proc in top[:5]:
                name = str(proc.get("name", "unknown"))[:20]
                pid = proc.get("pid", "?")
                cpu = proc.get("cpu_percent", 0)
                mem = proc.get("memory_percent", 0)
                lines.append(
                    f"  {name:20s} PID:{str(pid):>6} CPU:{cpu:5.1f}% MEM:{mem:5.1f}%"
                )

        return "\n".join(lines)

    def _render_port_panel(self) -> str:
        threshold = DETECTION_THRESHOLDS["open_ports"]
        count = self._last_port_data.get("count", 0)
        status, indicator, pct = self._status_meta(count, threshold)

        lines = [
            f"Open Ports: {count} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
            f"Usage: {pct:.0f}%",
        ]

        listening = self._last_port_data.get("listening", [])
        if listening:
            lines.append("")
            lines.append("[Listening Ports]")
            for port in listening[:10]:
                proto = port.get("protocol", "tcp")
                addr = port.get("address", "?")
                lines.append(f"  {proto:4s} {addr}")
            if len(listening) > 10:
                lines.append(f"  ... and {len(listening) - 10} more")

        return "\n".join(lines)

    def _render_file_panel(self) -> str:
        threshold = DETECTION_THRESHOLDS["file_changes"]
        total = self._last_file_data.get("change_count", 0)
        status, indicator, pct = self._status_meta(total, threshold)

        added = self._last_file_data.get("added", [])
        modified = self._last_file_data.get("modified", [])
        removed = self._last_file_data.get("removed", [])

        lines = [
            f"Total Changes: {total} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
            f"Usage: {pct:.0f}%",
            "",
            "[Change Summary]",
            f"  Added: {len(added)}",
            f"  Modified: {len(modified)}",
            f"  Removed: {len(removed)}",
        ]

        if added[:3]:
            lines.append("")
            lines.append("[Recent Added]")
            lines.extend(f"  + {str(path)[:60]}" for path in added[:3])

        if modified[:3]:
            lines.append("")
            lines.append("[Recent Modified]")
            lines.extend(f"  ~ {str(path)[:60]}" for path in modified[:3])

        return "\n".join(lines)

    def _render_detections_panel(self, detections: list[dict[str, Any]]) -> str:
        if not detections:
            return "[No detections recorded]\n\nSystem operating normally."

        process_threshold = DETECTION_THRESHOLDS["process_count"]
        port_threshold = DETECTION_THRESHOLDS["open_ports"]

        lines: list[str] = []
        for i, det in enumerate(detections[:15]):
            ts = str(det.get("timestamp", ""))[11:19]
            rule = str(det.get("rule", ""))
            desc = str(det.get("description", ""))
            details = det.get("details", {})

            severity = "(~)"
            if "process" in rule:
                severity = "(!)" if details.get("count", 0) > process_threshold else "(~)"
            elif "port" in rule:
                severity = "(!)" if details.get("count", 0) > port_threshold else "(~)"
            elif "file" in rule:
                severity = "(!)" if details.get("added") or details.get("modified") else "(~)"

            lines.append(f"[{ts}] {severity} {rule}")
            lines.append(f"  {desc[:70]}")

            if i < len(detections) - 1:
                lines.append("")

        return "\n".join(lines)

    def _render_events_panel(self, events: list[dict[str, Any]]) -> str:
        if not events:
            return "[No events recorded yet]\n\nWaiting for sensor data..."

        lines: list[str] = []

        for event in events[:20]:
            ts = str(event.get("timestamp", ""))[11:19]
            sensor = str(event.get("sensor", ""))
            data = event.get("data", {})

            if sensor == "process_sensor":
                lines.append(f"[{ts}] PROCESS_SENSOR")
                lines.append(f"  Running processes: {data.get('count', 0)}")
            elif sensor == "port_sensor":
                lines.append(f"[{ts}] PORT_SENSOR")
                lines.append(f"  Listening ports: {data.get('count', 0)}")
            elif sensor == "file_sensor":
                lines.append(f"[{ts}] FILE_SENSOR")
                lines.append(
                    f"  Changes: {data.get('change_count', 0)} "
                    f"(+{len(data.get('added', []))} ~{len(data.get('modified', []))})"
                )
            else:
                lines.append(f"[{ts}] {sensor}")
                lines.append(f"  {str(data)[:60]}")

            lines.append("")

        return "\n".join(lines)

    def _render_status_panel(self) -> str:
        uptime = datetime.now() - self._app_start_time
        total_seconds = int(uptime.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        latest_event_time = "N/A"
        events = self._safe_get_events()
        if events:
            latest_event_time = events[0].get("timestamp", "")[:19]

        return "\n".join(
            [
                "[Agent Information]",
                "  Status: RUNNING",
                f"  Uptime: {hours}h {minutes}m {seconds}s",
                f"  Refresh: #{self._refresh_count}",
                f"  Last Update: {datetime.now().strftime('%H:%M:%S')}",
                f"  Latest Event: {latest_event_time}",
                "",
                "[Log Statistics]",
                f"  Log Directory: {LOG_DIR}",
                f"  Total Events: {self._events_count_cache}",
                f"  Total Detections: {self._detections_count_cache}",
                "",
                "[Thresholds]",
                f"  Process: {DETECTION_THRESHOLDS['process_count']}",
                f"  Ports: {DETECTION_THRESHOLDS['open_ports']}",
                f"  File Changes: {DETECTION_THRESHOLDS['file_changes']}",
                "",
                "[Legend]",
                "  (+) Normal  (~) Warning  (!) Alert",
            ]
        )


def main() -> None:
    DashboardApp().run()


if __name__ == "__main__":
    main()