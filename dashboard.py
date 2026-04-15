"""Unified TUI Dashboard for the SMA - Secure Monitoring Agent.

Optimized architecture:
- UI only (Dashboard handles rendering)
- State Manager (AgentState for sensor snapshots)
- Data Service (EventCache for storage reads)
- Background refresh via ThreadPool
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import os
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Footer, Header, Static, Button, TextArea
from textual import work
from textual.timer import Timer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DETECTION_THRESHOLDS, LOG_DIR
from core.storage import Storage
from utils.event_cache import EventCache
from utils.log_counter import MultiLogCounter
from utils.agent_state import AgentState, create_agent_state
from utils.threadpool import init_threadpool


class ChatDisplay(Static):
    """Scrollable chat display widget."""

    def update_messages(self, messages: list[dict[str, str]]) -> None:
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lines.append(f"[bold cyan]Agent:[/bold cyan] {content}")
            elif role == "user":
                lines.append(f"[bold yellow]You:[/bold yellow] {content}")
            else:
                lines.append(f"[bold green]Assistant:[/bold green] {content}")
            lines.append("")
        self.update("\n".join(lines) if lines else "[dim]No messages yet...[/dim]")


class DashboardApp(App):
    """Main TUI dashboard with optimized data handling."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 4 2;
        grid-gutter: 1 0;
    }

    #left-panel {
        column-span: 3;
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
    }

    #right-panel {
        column-span: 1;
        layout: vertical;
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

    #chat-container {
        height: 60%;
        layout: vertical;
    }

    #chat-messages {
        height: 1fr;
        border: round $accent;
        padding: 1;
    }

    #input-container {
        height: auto;
        layout: vertical;
        margin-top: 1;
    }

    #command-input {
        height: 3;
        border: round $primary;
    }

    #buttons {
        height: auto;
        margin-top: 1;
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
        ("c", "focus_chat", "Chat"),
        ("Ctrl+enter", "send_message", "Send"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.storage = Storage()
        self._refresh_count = 0
        self._app_start_time = datetime.now()
        
        self._event_cache = EventCache(
            events_file=LOG_DIR / "events.log",
            detections_file=LOG_DIR / "detections.log",
            max_events=200,
            max_detections=50,
            ttl=5.0
        )
        
        self._log_counter = MultiLogCounter()
        self._log_counter.register("events", LOG_DIR / "events.log")
        self._log_counter.register("detections", LOG_DIR / "detections.log")
        
        self._agent_state = create_agent_state()
        
        self._chat_messages: list[dict[str, str]] = []
        
        self._llm_client = None
        self._refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="left-panel"):
            yield self._panel("PROCESSES", "process")
            yield self._panel("NETWORK PORTS", "port")
            yield self._panel("FILE CHANGES", "file")
            yield self._panel("DETECTIONS", "detections")
            yield self._panel("ACTIVITY LOG", "events")
            yield self._panel("AGENT STATUS", "status")
        with Container(id="right-panel"):
            with Vertical():
                yield Static("CHAT", classes="panel-title")
                yield ChatDisplay(id="chat-messages", classes="panel")
            with Vertical():
                yield Static("COMMAND", classes="panel-title")
                yield TextArea(id="command-input", placeholder="Enter command or message...")
                with Horizontal(id="buttons"):
                    yield Button("Send", id="btn-send", variant="primary")
                    yield Button("Clear", id="btn-clear", variant="default")
                    yield Button("Scan", id="btn-scan", variant="success")
                    yield Button("Status", id="btn-status", variant="default")
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
        self.chat_display = self.query_one("#chat-messages", ChatDisplay)
        self.command_input = self.query_one("#command-input", TextArea)
        
        self._refresh_timer = self.set_interval(3.0, self._do_background_refresh)
        
        self._do_background_refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-send":
            self.send_message()
        elif button_id == "btn-clear":
            self.clear_chat()
        elif button_id == "btn-scan":
            self.run_scan()
        elif button_id == "btn-status":
            self.run_status()

    def action_refresh(self) -> None:
        self._do_background_refresh()

    def action_focus_chat(self) -> None:
        self.command_input.focus()

    def send_message(self) -> None:
        text = self.command_input.text.strip()
        if not text:
            return
        self._chat_messages.append({"role": "user", "content": text})
        self.command_input.clear()
        self.process_user_input(text)

    def clear_chat(self) -> None:
        self._chat_messages = []
        self.chat_display.update_messages(self._chat_messages)

    @work(thread=True)
    def run_scan(self) -> None:
        self._chat_messages.append({"role": "system", "content": "Scanning system..."})
        self.chat_display.update_messages(self._chat_messages)
        
        from utils.system_scanner import scan_system, format_system_info
        info = scan_system()
        report = format_system_info(info)
        
        self._chat_messages.append({"role": "system", "content": report})
        self.chat_display.update_messages(self._chat_messages)

    @work(thread=True)
    def run_status(self) -> None:
        self._chat_messages.append({"role": "system", "content": "Checking agent status..."})
        self.chat_display.update_messages(self._chat_messages)
        
        from utils.system_scanner import scan_system, get_missing_packages
        info = scan_system()
        missing = get_missing_packages(info)
        
        if missing:
            status_msg = f"Missing: {', '.join(missing)}"
        else:
            status_msg = "All dependencies installed. Agent ready."
        
        self._chat_messages.append({"role": "system", "content": status_msg})
        self.chat_display.update_messages(self._chat_messages)

    def process_user_input(self, text: str) -> None:
        text_lower = text.lower().strip()
        
        if text_lower in ["scan", "system scan", "check"]:
            self.run_scan()
        elif text_lower in ["status", "check status"]:
            self.run_status()
        elif text_lower in ["clear", "clear chat"]:
            self.clear_chat()
        elif text_lower in ["help", "?"]:
            help_msg = (
                "Available commands:\n"
                "  scan - Scan system\n"
                "  status - Check status\n"
                "  clear - Clear chat\n"
                "  help - Show help"
            )
            self._chat_messages.append({"role": "system", "content": help_msg})
            self.chat_display.update_messages(self._chat_messages)
        else:
            self._handle_llm_chat(text)

    @work(thread=True)
    def _handle_llm_chat(self, text: str) -> None:
        try:
            from core import OpenRouterClient
            if self._llm_client is None:
                self._llm_client = OpenRouterClient()
            
            if not self._llm_client.api_key:
                self._chat_messages.append({"role": "assistant", "content": f"You said: {text}"})
                self.chat_display.update_messages(self._chat_messages)
                return
            
            messages = self._build_context()
            messages.append({"role": "user", "content": text})
            
            response = self._llm_client.chat_completion(messages)
            
            if response:
                self._chat_messages.append({"role": "assistant", "content": response})
            else:
                self._chat_messages.append({"role": "system", "content": "LLM unavailable"})
            
            self.chat_display.update_messages(self._chat_messages)
        except Exception as e:
            self._chat_messages.append({"role": "system", "content": f"Error: {e}"})
            self.chat_display.update_messages(self._chat_messages)

    def _build_context(self) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": "You are a security monitoring agent."}]
        
        state = self._agent_state.get_all()
        risk_score, risk_level = self._agent_state.calculate_risk()
        
        context = (
            f"Current risk level: {risk_level} (score: {risk_score})\n"
            f"Process count: {state.process.get('count', 0)}\n"
            f"Open ports: {state.port.get('count', 0)}\n"
            f"File changes: {state.file.get('change_count', 0)}"
        )
        messages.append({"role": "system", "content": context})
        
        for msg in self._chat_messages[-5:]:
            messages.append(msg)
        
        return messages

    def _do_background_refresh(self) -> None:
        self._refresh_count += 1
        
        try:
            events = self.storage.get_recent_events(count=50)
            detections = self.storage.get_recent_detections(count=30)
            
            self._event_cache.update(events, detections)
            self._agent_state.update_from_events(events)
            
            self._log_counter.update_all()
        except Exception:
            pass
        
        self.process_content.update(self._render_process_panel())
        self.port_content.update(self._render_port_panel())
        self.file_content.update(self._render_file_panel())
        self.detections_content.update(self._render_detections_panel())
        self.events_content.update(self._render_events_panel())
        self.status_content.update(self._render_status_panel())

    def _render_process_panel(self) -> str:
        process = self._agent_state.get_process()
        threshold = DETECTION_THRESHOLDS["process_count"]
        count = process.get("count", 0)
        status, indicator = self._get_status(count, threshold)
        
        lines = [
            f"Count: {count} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
        ]
        
        top = process.get("top_processes", [])
        if top:
            lines.append("")
            lines.append("[Top Processes]")
            for proc in top[:5]:
                name = str(proc.get("name", "unknown"))[:20]
                pid = proc.get("pid", "?")
                cpu = proc.get("cpu_percent", 0)
                mem = proc.get("memory_percent", 0)
                lines.append(f"  {name:20s} PID:{str(pid):>6} CPU:{cpu:5.1f}% MEM:{mem:5.1f}%")
        
        return "\n".join(lines)

    def _render_port_panel(self) -> str:
        port = self._agent_state.get_port()
        threshold = DETECTION_THRESHOLDS["open_ports"]
        count = port.get("count", 0)
        status, indicator = self._get_status(count, threshold)
        
        lines = [
            f"Open Ports: {count} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
        ]
        
        listening = port.get("listening", [])
        if listening:
            lines.append("")
            lines.append("[Listening Ports]")
            for p in listening[:10]:
                proto = p.get("protocol", "tcp")
                addr = p.get("address", "?")
                lines.append(f"  {proto:4s} {addr}")
            if len(listening) > 10:
                lines.append(f"  ... and {len(listening) - 10} more")
        
        return "\n".join(lines)

    def _render_file_panel(self) -> str:
        file_data = self._agent_state.get_file()
        threshold = DETECTION_THRESHOLDS["file_changes"]
        total = file_data.get("change_count", 0)
        status, indicator = self._get_status(total, threshold)
        
        added = file_data.get("added", [])
        modified = file_data.get("modified", [])
        removed = file_data.get("removed", [])
        
        lines = [
            f"Total Changes: {total} {indicator}",
            f"Threshold: {threshold}",
            f"Status: {status}",
            "",
            "[Change Summary]",
            f"  Added: {len(added)}",
            f"  Modified: {len(modified)}",
            f"  Removed: {len(removed)}",
        ]
        
        if added[:3]:
            lines.append("")
            lines.append("[Recent Added]")
            lines.extend(f"  + {str(p)[:60]}" for p in added[:3])
        
        if modified[:3]:
            lines.append("")
            lines.append("[Recent Modified]")
            lines.extend(f"  ~ {str(p)[:60]}" for p in modified[:3])
        
        return "\n".join(lines)

    def _render_detections_panel(self) -> str:
        detections = self._event_cache.get_detections()
        if not detections:
            return "[No detections]\n\nSystem operating normally."
        
        process_threshold = DETECTION_THRESHOLDS["process_count"]
        port_threshold = DETECTION_THRESHOLDS["open_ports"]
        
        lines: list[str] = []
        for i, det in enumerate(detections[:15]):
            ts = str(det.get("timestamp", ""))[11:19]
            rule = str(det.get("rule", ""))
            desc = str(det.get("description", ""))[:60]
            details = det.get("details", {})
            
            severity = "(~)"
            if "process" in rule:
                severity = "(!)" if details.get("count", 0) > process_threshold else "(~)"
            elif "port" in rule:
                severity = "(!)" if details.get("count", 0) > port_threshold else "(~)"
            
            lines.append(f"[{ts}] {severity} {rule}")
            lines.append(f"  {desc}")
            if i < len(detections) - 1:
                lines.append("")
        
        return "\n".join(lines)

    def _render_events_panel(self) -> str:
        events = self._event_cache.get_events()
        if not events:
            return "[No events]\n\nWaiting for sensor data..."
        
        lines: list[str] = []
        for event in events[:20]:
            ts = str(event.get("timestamp", ""))[11:19]
            sensor = str(event.get("sensor", ""))
            data = event.get("data", {})
            
            if sensor == "process_sensor":
                lines.append(f"[{ts}] PROCESS_SENSOR")
                lines.append(f"  Running: {data.get('count', 0)}")
            elif sensor == "port_sensor":
                lines.append(f"[{ts}] PORT_SENSOR")
                lines.append(f"  Listening: {data.get('count', 0)}")
            elif sensor == "file_sensor":
                lines.append(f"[{ts}] FILE_SENSOR")
                lines.append(f"  Changes: {data.get('change_count', 0)}")
            else:
                lines.append(f"[{ts}] {sensor}")
            lines.append("")
        
        return "\n".join(lines)

    def _render_status_panel(self) -> str:
        uptime = datetime.now() - self._app_start_time
        total_seconds = int(uptime.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        risk_score, risk_level = self._agent_state.calculate_risk()
        risk_details = self._agent_state.get_risk_details()
        
        events_count, detections_count = self._log_counter.get_all()
        
        return "\n".join([
            "[Agent Information]",
            f"  Status: RUNNING",
            f"  Uptime: {hours}h {minutes}m {seconds}s",
            f"  Refresh: #{self._refresh_count}",
            "",
            "[Risk Assessment]",
            f"  Level: {risk_level}",
            f"  Score: {risk_score}",
            *([f"  - {d}" for d in risk_details] if risk_details else ["  All normal"]),
            "",
            "[Log Statistics]",
            f"  Total Events: {events_count.get('events', 0)}",
            f"  Total Detections: {events_count.get('detections', 0)}",
            "",
            "[Thresholds]",
            f"  Process: {DETECTION_THRESHOLDS['process_count']}",
            f"  Ports: {DETECTION_THRESHOLDS['open_ports']}",
            f"  File Changes: {DETECTION_THRESHOLDS['file_changes']}",
            "",
            "[Legend]",
            "  (+) Normal  (~) Warning  (!) Alert",
        ])

    def _get_status(self, count: int, threshold: int) -> tuple[str, str]:
        if count > threshold:
            return "HIGH", "(!)"
        if count > threshold * 0.8:
            return "WARN", "(~)"
        return "OK", "(+)"


def main() -> None:
    init_threadpool(num_threads=8)
    DashboardApp().run()


if __name__ == "__main__":
    main()