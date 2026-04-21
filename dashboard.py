"""SOC TUI Dashboard for the Secure Monitoring Agent.

Full AI Security Operations Center (SOC) TUI with:
- Global Top Bar (name, uptime, refresh, risk, CPU/RAM, threats)
- Left Panel (Processes, Ports, Files, Timeline, Risk Score)
- Center Panel (Detections, Incidents, Activity, Status)
- Right Panel (Chat, Commands, Tools, Memory, Actions)
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import os
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Footer, Header, Static, Button, TextArea
from textual import work
from textual.timer import Timer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from core.storage import Storage
from utils.event_cache import EventCache
from utils.log_counter import MultiLogCounter
from utils.agent_state import AgentState, create_agent_state
from utils.timeline import Timeline, create_timeline
from utils.memory import AgentMemory, create_memory
from utils.tool_executor import ToolLogger, create_tool_logger
from utils.threadpool import init_threadpool, ThreadPool


CHAT_COLORS = {
    "system": "cyan",
    "user": "yellow", 
    "assistant": "green",
}


class ChatDisplay(Static):
    """Scrollable chat display with timestamps."""

    def update_messages(self, messages: list[dict[str, str]]) -> None:
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            color = CHAT_COLORS.get(role, "white")
            
            if timestamp:
                lines.append(f"[{timestamp}] ", end="")
            
            if role == "system":
                lines.append(f"[bold {color}]Agent:[/bold {color}] {content}")
            elif role == "user":
                lines.append(f"[bold {color}]You:[/bold {color}] {content}")
            else:
                lines.append(f"[bold {color}]Assistant:[/bold {color}] {content}")
            lines.append("")
        
        self.update("\n".join(lines) if lines else "[dim]No messages yet...[/dim]")


class DashboardApp(App):
    """Full SOC TUI Dashboard."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 4 2;
        grid-gutter: 1 0;
    }

    #top-bar {
        column-span: 4;
        height: 3;
        background: $panel-darken-1;
        content-align: center middle;
    }

    #left-panel {
        column-span: 2;
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
    }

    #center-panel {
        column-span: 1;
        layout: vertical;
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

    .top-text {
        text-style: bold;
        padding: 0 2;
    }

    #chat-messages {
        height: 40%;
        border: round $accent;
        padding: 1;
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
    #ports-panel { border-title-color: $accent; }
    #files-panel { border-title-color: $accent; }
    #timeline-panel { border-title-color: $warning; }
    #risk-panel { border-title-color: $error; }
    #detections-panel { border-title-color: $warning; }
    #incidents-panel { border-title-color: $error; }
    #activity-panel { border-title-color: $primary; }
    #status-panel { border-title-color: $success; }
    #tools-panel { border-title-color: $accent; }
    #memory-panel { border-title-color: $accent; }
    #actions-panel { border-title-color: $error; }
    #background-panel { border-title-color: $warning; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("c", "focus_chat", "Chat"),
        ("m", "toggle_mode", "Mode"),
        ("Ctrl+enter", "send_message", "Send"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.storage = Storage()
        self._app_start = datetime.now()
        self._refresh_count = 0
        self._agent_mode = config.DEFAULT_AGENT_MODE
        self._last_action_time: Optional[datetime] = None
        self._last_action_desc: str = "None"
        
        self._event_cache = EventCache(
            events_file=config.LOG_DIR / "events.log",
            detections_file=config.LOG_DIR / "detections.log",
            max_events=100,
            max_detections=30,
            ttl=5.0
        )
        
        self._log_counter = MultiLogCounter()
        self._log_counter.register("events", config.LOG_DIR / "events.log")
        self._log_counter.register("detections", config.LOG_DIR / "detections.log")
        
        self._agent_state = create_agent_state()
        self._timeline = create_timeline()
        self._memory = create_memory()
        self._tool_logger = create_tool_logger()
        
        self._chat_messages: list[dict[str, str]] = []
        self._llm_client = None
        self._refresh_timer: Timer | None = None
        
        self._cpu_usage = 0
        self._mem_usage = 0
        self._risk_trend: list[int] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        
        with Vertical(id="top-bar"):
            yield Static("MONICA", id="top-title", classes="top-text")
            yield Static(id="top-stats", classes="top-text")
        
        with Container(id="left-panel"):
            yield self._panel("PROCESSES", "process")
            yield self._panel("NETWORK PORTS", "ports")
            yield self._panel("FILE CHANGES", "files")
            yield self._panel("TIMELINE", "timeline")
            yield self._panel("RISK SCORE", "risk")
            yield self._panel("AGENT STATUS", "status")
        
        with Vertical(id="center-panel"):
            yield self._panel("DETECTIONS", "detections")
            yield self._panel("INCIDENTS", "incidents")
            yield self._panel("ACTIVITY LOG", "activity")
            yield self._panel("BACKGROUND TASKS", "background")
        
        with Vertical(id="right-panel"):
            with Vertical():
                yield Static("CHAT", classes="panel-title")
                yield ChatDisplay(id="chat-messages", classes="panel")
            with Vertical():
                yield Static("COMMAND", classes="panel-title")
                yield TextArea(id="command-input", placeholder="Enter command...")
                with Horizontal(id="buttons"):
                    yield Button("Send", id="btn-send", variant="primary")
                    yield Button("Clear", id="btn-clear", variant="default")
                    yield Button("Mode: PASSIVE", id="btn-mode", variant="default")
            yield self._panel("TOOL EXECUTIONS", "tools")
            yield self._panel("MEMORY", "memory")
            yield self._panel("AUTONOMOUS ACTIONS", "actions")
        
        yield Footer()

    def _panel(self, title: str, name: str) -> Vertical:
        return Vertical(
            Static(title, classes="panel-title"),
            Static("", id=f"{name}-content", expand=True),
            id=f"{name}-panel",
            classes="panel",
        )

    def on_mount(self) -> None:
        self._init_widgets()
        self._refresh_timer = self.set_interval(3.0, self._do_background_refresh)
        self._do_background_refresh()
        self._update_system_metrics()

    def _init_widgets(self) -> None:
        self.process_content = self.query_one("#process-content", Static)
        self.ports_content = self.query_one("#ports-content", Static)
        self.files_content = self.query_one("#files-content", Static)
        self.timeline_content = self.query_one("#timeline-content", Static)
        self.risk_content = self.query_one("#risk-content", Static)
        self.status_content = self.query_one("#status-content", Static)
        self.detections_content = self.query_one("#detections-content", Static)
        self.incidents_content = self.query_one("#incidents-content", Static)
        self.activity_content = self.query_one("#activity-content", Static)
        self.background_content = self.query_one("#background-content", Static)
        self.tools_content = self.query_one("#tools-content", Static)
        self.memory_content = self.query_one("#memory-content", Static)
        self.actions_content = self.query_one("#actions-content", Static)
        self.chat_display = self.query_one("#chat-messages", ChatDisplay)
        self.command_input = self.query_one("#command-input", TextArea)
        self.top_stats = self.query_one("#top-stats", Static)
        self.btn_mode = self.query_one("#btn-mode", Button)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-send":
            self.send_message()
        elif button_id == "btn-clear":
            self.clear_chat()
        elif button_id == "btn-mode":
            self.toggle_mode()

    def action_refresh(self) -> None:
        self._do_background_refresh()

    def action_focus_chat(self) -> None:
        self.command_input.focus()

    def action_toggle_mode(self) -> None:
        self.toggle_mode()

    def toggle_mode(self) -> None:
        modes = config.AGENT_MODES
        current_idx = modes.index(self._agent_mode) if self._agent_mode in modes else 0
        self._agent_mode = modes[(current_idx + 1) % len(modes)]
        self.btn_mode.label = f"Mode: {self._agent_mode}"
        self._log_action(f"Mode changed to {self._agent_mode}")

    def send_message(self) -> None:
        text = self.command_input.text.strip()
        if not text:
            return
        
        timestamp = datetime.now().strftime("%H:%M")
        self._chat_messages.append({
            "role": "user", 
            "content": text,
            "timestamp": timestamp
        })
        self.command_input.clear()
        self.process_user_input(text)

    def clear_chat(self) -> None:
        self._chat_messages = []
        self.chat_display.update_messages(self._chat_messages)

    @work(thread=True)
    def process_user_input(self, text: str) -> None:
        text_lower = text.lower().strip()
        timestamp = datetime.now().strftime("%H:%M")
        
        if text_lower in ["scan", "system scan"]:
            self._log_action("System scan started")
            from utils.system_scanner import scan_system, format_system_info
            info = scan_system()
            report = format_system_info(info)
            self._chat_messages.append({
                "role": "system",
                "content": report,
                "timestamp": timestamp
            })
            self._tool_logger.log("scan_system", {}, report, "success")
        
        elif text_lower in ["status", "check status"]:
            from utils.system_scanner import scan_system, get_missing_packages
            info = scan_system()
            missing = get_missing_packages(info)
            status_msg = f"System: OK" if not missing else f"Missing: {', '.join(missing)}"
            self._chat_messages.append({
                "role": "system",
                "content": status_msg,
                "timestamp": timestamp
            })
        
        elif text_lower in ["clear", "clear chat"]:
            self.clear_chat()
        
        elif text_lower in ["help", "?"]:
            help_msg = "Commands: scan, status, clear, help"
            self._chat_messages.append({
                "role": "system",
                "content": help_msg,
                "timestamp": timestamp
            })
        
        else:
            self._handle_llm_chat(text, timestamp)
        
        self.chat_display.update_messages(self._chat_messages)

    @work(thread=True)
    def _handle_llm_chat(self, text: str, timestamp: str) -> None:
        try:
            from core import OpenRouterClient
            if self._llm_client is None:
                self._llm_client = OpenRouterClient()
            
            if not self._llm_client.api_key:
                self._chat_messages.append({
                    "role": "assistant",
                    "content": f"You said: {text}",
                    "timestamp": timestamp
                })
                self.chat_display.update_messages(self._chat_messages)
                return
            
            messages = self._build_context()
            messages.append({"role": "user", "content": text})
            
            response = self._llm_client.chat_completion(messages)
            
            if response:
                self._chat_messages.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": timestamp
                })
                self._log_action(f"Chat: {text[:30]}")
            else:
                self._chat_messages.append({
                    "role": "system",
                    "content": "LLM unavailable",
                    "timestamp": timestamp
                })
            
            self.chat_display.update_messages(self._chat_messages)
        except Exception as e:
            self._chat_messages.append({
                "role": "system",
                "content": f"Error: {e}",
                "timestamp": timestamp
            })
            self.chat_display.update_messages(self._chat_messages)

    def _build_context(self) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": "You are Phantom, an AI agentic harness system."}]
        
        state = self._agent_state.get_all()
        risk_score, risk_level = self._agent_state.calculate_risk()
        
        context = f"Risk: {risk_level} | Process: {state.process.get('count', 0)} | Ports: {state.port.get('count', 0)} | Files: {state.file.get('change_count', 0)}"
        messages.append({"role": "system", "content": context})
        
        for msg in self._chat_messages[-3:]:
            messages.append(msg)
        
        return messages

    def _log_action(self, action: str, reason: str = "") -> None:
        self._last_action_time = datetime.now()
        self._last_action_desc = action
        self._timeline.add_event(
            event_type="action_taken",
            source="agent",
            details={"action": action, "reason": reason},
            severity="low"
        )
        self._tool_logger.log("agent_action", {"action": action}, action, "success")

    def _update_system_metrics(self) -> None:
        try:
            import psutil
            self._cpu_usage = psutil.cpu_percent()
            self._mem_usage = psutil.virtual_memory().percent
        except ImportError:
            self._cpu_usage = 0
            self._mem_usage = 0

    def _do_background_refresh(self) -> None:
        self._refresh_count += 1
        
        try:
            events = self.storage.get_recent_events(count=30)
            detections = self.storage.get_recent_detections(count=20)
            
            self._event_cache.update(events, detections)
            self._agent_state.update_from_events(events)
            self._log_counter.update_all()
            
            for event in events[-3:]:
                self._timeline.add_event(
                    event_type=event.get("sensor", "unknown"),
                    source="sensor",
                    details=event.get("data", {}),
                    severity="low"
                )
            
            self._update_system_metrics()
            self._update_risk_trend()
        except Exception:
            pass
        
        self._render_all_panels()

    def _update_risk_trend(self) -> None:
        score, _ = self._agent_state.calculate_risk()
        self._risk_trend.append(score)
        if len(self._risk_trend) > config.RISK_TREND_WINDOW:
            self._risk_trend = self._risk_trend[-config.RISK_TREND_WINDOW:]

    def _get_risk_trend_symbol(self) -> str:
        if len(self._risk_trend) < 2:
            return "→"
        avg_old = sum(self._risk_trend[:-1]) / (len(self._risk_trend) - 1)
        avg_new = self._risk_trend[-1]
        if avg_new > avg_old + 5:
            return "↑"
        elif avg_new < avg_old - 5:
            return "↓"
        return "→"

    def _render_all_panels(self) -> None:
        self._render_top_bar()
        self.process_content.update(self._render_process_panel())
        self.ports_content.update(self._render_ports_panel())
        self.files_content.update(self._render_files_panel())
        self.timeline_content.update(self._render_timeline_panel())
        self.risk_content.update(self._render_risk_panel())
        self.status_content.update(self._render_status_panel())
        self.detections_content.update(self._render_detections_panel())
        self.incidents_content.update(self._render_incidents_panel())
        self.activity_content.update(self._render_activity_panel())
        self.background_content.update(self._render_background_panel())
        self.tools_content.update(self._render_tools_panel())
        self.memory_content.update(self._render_memory_panel())
        self.actions_content.update(self._render_actions_panel())

    def _render_top_bar(self) -> None:
        uptime = datetime.now() - self._app_start
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        risk_score, risk_level = self._agent_state.calculate_risk()
        risk_trend = self._get_risk_trend_symbol()
        
        risk_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "red bold"}[risk_level]
        
        threat_count = self._timeline.get_threat_count()
        
        self.top_stats.update(
            f"[{risk_color}]Risk: {risk_level}[/] | "
            f"Score: {risk_score}{risk_trend} | "
            f"CPU: {self._cpu_usage}% | "
            f"Mem: {self._mem_usage}% | "
            f"Threats: {threat_count} | "
            f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d} | "
            f"Refresh: #{self._refresh_count}"
        )

    def _render_process_panel(self) -> str:
        process = self._agent_state.get_process()
        threshold = config.DETECTION_THRESHOLDS["process_count"]
        count = process.get("count", 0)
        
        status = self._get_status(count, threshold)
        
        lines = [
            f"Count: {count} {status[1]}",
            f"Threshold: {threshold}",
            f"Status: {status[0]}",
        ]
        
        top = process.get("top_processes", [])
        if top:
            lines.append("")
            lines.append("[Top Processes]")
            for proc in top[:5]:
                name = str(proc.get("name", "?"))[:18]
                pid = proc.get("pid", "?")
                cpu = proc.get("cpu_percent", 0)
                mem = proc.get("memory_percent", 0)
                lines.append(f"  {name:18s} {pid:>5} CPU:{cpu:4.1f}% M:{mem:4.1f}%")
        
        return "\n".join(lines)

    def _render_ports_panel(self) -> str:
        port = self._agent_state.get_port()
        threshold = config.DETECTION_THRESHOLDS["open_ports"]
        count = port.get("count", 0)
        
        status = self._get_status(count, threshold)
        
        lines = [
            f"Open: {count} {status[1]}",
            f"Threshold: {threshold}",
            f"Status: {status[0]}",
        ]
        
        listening = port.get("listening", [])
        if listening:
            lines.append("")
            lines.append("[Listening Ports]")
            for p in listening[:8]:
                proto = p.get("protocol", "tcp")[:4]
                addr = p.get("address", "?")
                service = config.PORT_CLASSIFICATIONS.get(
                    int(addr.split(":")[-1]) if ":" in addr else 0,
                    ""
                )
                flag = " [KNOWN]" if service else ""
                lines.append(f"  {proto:4s} {addr:20s}{flag}")
        
        return "\n".join(lines)

    def _render_files_panel(self) -> str:
        file_data = self._agent_state.get_file()
        threshold = config.DETECTION_THRESHOLDS["file_changes"]
        total = file_data.get("change_count", 0)
        
        status = self._get_status(total, threshold)
        
        added = file_data.get("added", [])
        modified = file_data.get("modified", [])
        removed = file_data.get("removed", [])
        
        lines = [
            f"Changes: {total} {status[1]}",
            f"Threshold: {threshold}",
            f"Status: {status[0]}",
            "",
            f"Added: {len(added)} | Modified: {len(modified)} | Removed: {len(removed)}"
        ]
        
        return "\n".join(lines)

    def _render_timeline_panel(self) -> str:
        events = self._timeline.get_recent(6)
        if not events:
            return "[No events]\nWaiting..."
        
        lines = []
        for e in events:
            ts = datetime.fromtimestamp(e.timestamp).strftime("%H:%M")
            symbol = {"low": "○", "medium": "◐", "high": "●", "critical": "⚠"}.get(e.severity, "○")
            lines.append(f"[{ts}] {symbol} {e.event_type}")
        
        return "\n".join(lines)

    def _render_risk_panel(self) -> str:
        score, level = self._agent_state.calculate_risk()
        trend = self._get_risk_trend_symbol()
        
        level_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "red bold"}[level]
        
        lines = [
            f"[bold]{score}[/bold]/100",
            f"[{level_color}]{level}[/{level_color}] {trend}",
            ""
        ]
        
        details = self._agent_state.get_risk_details()
        if details:
            lines.extend(details[:3])
        else:
            lines.append("All normal")
        
        return "\n".join(lines)

    def _render_status_panel(self) -> str:
        uptime = datetime.now() - self._app_start
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        last_action = self._last_action_desc if self._last_action_desc != "None" else "None"
        
        return "\n".join([
            f"Mode: {self._agent_mode}",
            f"Uptime: {hours}h {minutes}m",
            f"Refresh: #{self._refresh_count}",
            f"Last: {last_action}",
        ])

    def _render_detections_panel(self) -> str:
        detections = self._event_cache.get_detections()
        if not detections:
            return "[No detections]\nSystem OK"
        
        lines = []
        for det in detections[:8]:
            ts = str(det.get("timestamp", ""))[11:19]
            rule = str(det.get("rule", ""))[:20]
            desc = str(det.get("description", ""))[:40]
            severity = "(!)" if det.get("severity") in ("high", "critical") else "(~)"
            lines.append(f"[{ts}] {severity} {rule}")
            lines.append(f"  {desc}")
        
        return "\n".join(lines)

    def _render_incidents_panel(self) -> str:
        detections = self._event_cache.get_detections()
        
        high_count = sum(1 for d in detections if d.get("severity") in ("high", "critical"))
        medium_count = sum(1 for d in detections if d.get("severity") == "medium")
        
        threat_count = self._timeline.get_threat_count()
        
        lines = [
            f"High: {high_count}",
            f"Medium: {medium_count}",
            f"Active Threats: {threat_count}",
        ]
        
        return "\n".join(lines)

    def _render_activity_panel(self) -> str:
        events = self._event_cache.get_events()
        if not events:
            return "[No events]"
        
        lines = [f"Total: {len(events)} events"]
        
        last_event = events[0] if events else {}
        if last_event:
            ts = str(last_event.get("timestamp", ""))[11:19]
            sensor = str(last_event.get("sensor", "?"))[:15]
            lines.append(f"Last: [{ts}] {sensor}")
        
        return "\n".join(lines)

    def _render_background_panel(self) -> str:
        try:
            pool = ThreadPool.get_instance()
            active = pool.get_active_tasks()
            pending = pool.get_pending_tasks()
            errors = pool.get_errors()
            
            lines = []
            lines.append(f"Active Tasks: [yellow]{active}[/yellow]")
            lines.append(f"Pending: [cyan]{pending}[/cyan]")
            
            if errors:
                lines.append(f"[red]Errors: {len(errors)}[/red]")
                for err in errors[-2:]:
                    lines.append(f"  • {str(err)[:40]}")
            
            recent_logs = []
            if config.DEBUG_MODE:
                debug_file = config.LOG_DIR / "debug.log"
                if debug_file.exists():
                    with open(debug_file, "r") as f:
                        lines_file = f.readlines()
                        for line in lines_file[-10:]:
                            if line.strip():
                                recent_logs.append(line.strip()[:60])
            
            if recent_logs:
                lines.append("")
                lines.append("[dim]Recent Debug Logs:[/dim]")
                for log in recent_logs[-5:]:
                    lines.append(f"[dim]{log}[/dim]")
            
            return "\n".join(lines) if lines else "[No background activity]"
        except Exception as e:
            return f"[Background panel error: {e}]"

    def _render_tools_panel(self) -> str:
        logs = self._tool_logger.get_logs(5)
        if not logs:
            return "[No tool executions]"
        
        lines = []
        for log in logs:
            ts = datetime.fromtimestamp(log.timestamp).strftime("%H:%M")
            status = "✓" if log.status == "success" else "✗"
            lines.append(f"[{ts}] {status} {log.tool_name}")
        
        return "\n".join(lines)

    def _render_memory_panel(self) -> str:
        recent = self._memory.get_recent(5)
        if not recent:
            return "[No memory]"
        
        lines = []
        for key, value in recent:
            display_key = key[:20] if len(key) > 20 else key
            lines.append(f"{display_key} = {str(value)[:20]}")
        
        return "\n".join(lines) if lines else "[No memory]"

    def _render_actions_panel(self) -> str:
        last_action = self._tool_logger.get_last_action()
        if not last_action:
            return "[No actions]"
        
        lines = [last_action]
        
        return "\n".join(lines)

    def _get_status(self, count: int, threshold: int) -> tuple[str, str]:
        if count > threshold:
            return "CRITICAL", "(!)"
        if count > threshold * 0.8:
            return "WARNING", "(~)"
        return "OK", "(+)"


def main() -> None:
    init_threadpool(num_threads=8)
    DashboardApp().run()


if __name__ == "__main__":
    main()