"""Entry point for the monitoring agent.

This script wires together the sensors, scheduler, detection engine
and skills.  It sets up periodic tasks, starts an optional webhook
listener, and runs the scheduler loop indefinitely.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Callable
import importlib

import config
from core import Scheduler, Storage, OpenRouterClient
from analysis import detection
from skills import risk_assessment, vulnerability_check
from utils.debug_log import debug_logger


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def format_summary(text: str) -> str:
    """Format summary text for better readability."""
    lines = text.strip().split('\n')
    formatted = []
    for line in lines:
        line = line.strip()
        if not line:
            formatted.append("")
            continue
        if line.startswith('**') and line.endswith('**'):
            formatted.append(f"\n{Colors.BOLD}{line}{Colors.END}")
        elif line.startswith('###'):
            formatted.append(f"\n{Colors.YELLOW}{line}{Colors.END}")
        elif line.startswith('- ') or line.startswith('* '):
            formatted.append(f"  {Colors.CYAN}•{Colors.END} {line[2:]}")
        elif any(marker in line for marker in ['Risk', 'Concern', 'Issue', 'Critical', 'Warning']):
            formatted.append(f"\n{Colors.RED}{line}{Colors.END}")
        else:
            formatted.append(line)
    return '\n'.join(formatted)


def make_sensor_task(sensor_module_name: str, storage: Storage) -> Callable[[Dict[str, Any]], None]:
    """Return a function that collects data from the given sensor.

    :param sensor_module_name: Module name within `sensors` package.
    :param storage: Storage instance for logging events.
    """
    module = importlib.import_module(f"sensors.{sensor_module_name}")
    def task(context: Dict[str, Any]) -> None:
        payload = module.collect(context)
        storage.log_event(sensor_module_name, payload)
        debug_logger.sensor(sensor_module_name, payload)
        context[f"{sensor_module_name}_last"] = payload
    return task


def detection_task(context: Dict[str, Any], storage: Storage) -> None:
    anomalies = detection.detect(context, storage)
    if anomalies:
        debug_logger.detection("anomaly_check", f"Detected {len(anomalies)} anomalies", {"count": len(anomalies), "anomalies": anomalies})
        context.setdefault("recent_anomalies", []).extend(anomalies)
        print(f"\n{Colors.RED}{'!' * 40}")
        print(f"  {Colors.BOLD}ANOMALIES DETECTED{Colors.END}")
        print(f"{Colors.RED}{'!' * 40}{Colors.END}")
        for a in anomalies:
            rule = a.get("rule", "unknown")
            desc = a.get("description", "no description")
            print(f"  {Colors.YELLOW}*{Colors.END} {Colors.BOLD}{rule}:{Colors.END} {desc}")
        print()
    else:
        debug_logger.detection("anomaly_check", "No anomalies detected")


def print_section(title: str, content: str) -> None:
    """Print formatted section with title and colored content."""
    separator = "=" * 50
    print(f"\n{Colors.BOLD}{separator}")
    print(f"  {title}")
    print(f"{separator}{Colors.END}")
    print(format_summary(content))


def risk_assessment_task(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    debug_logger.task("risk_assessment", "Starting risk assessment")
    risk_assessment.run(context, storage, client)
    summary = context.get("last_summary")
    debug_logger.task("risk_assessment", "Risk assessment completed", {"summary": summary})
    if summary:
        print_section("RISK ASSESSMENT SUMMARY", summary)


def vulnerability_check_task(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    debug_logger.task("vulnerability_check", "Starting vulnerability check")
    vulnerability_check.run(context, storage, client)
    result = context.get("last_vulnerability_assessment")
    debug_logger.task("vulnerability_check", "Vulnerability check completed", {"result": result})
    if result:
        print_section("VULNERABILITY ASSESSMENT", result)


class WebhookHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler to trigger skills via webhooks."""
    # Use closure variables to access scheduler and tasks
    scheduler: Scheduler = None  # type: ignore
    context: Dict[str, Any] = None  # type: ignore
    storage: Storage = None  # type: ignore
    client: OpenRouterClient = None  # type: ignore

    def do_GET(self):  # noqa: N802
        path = self.path
        # Example: /trigger/vulnerability_check
        if path == "/trigger/vulnerability_check":
            vulnerability_check_task(self.context, self.storage, self.client)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"vulnerability_check triggered")
            return
        elif path == "/trigger/risk_assessment":
            risk_assessment_task(self.context, self.storage, self.client)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"risk_assessment triggered")
            return
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Suppress default logging
        return


def start_webhook_server(scheduler: Scheduler, storage: Storage, client: OpenRouterClient, port: int = 8000) -> None:
    """Start a simple HTTP server in a background thread."""
    handler_class = WebhookHandler
    handler_class.scheduler = scheduler
    handler_class.context = scheduler.context
    handler_class.storage = storage
    handler_class.client = client
    server = HTTPServer(("127.0.0.1", port), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Webhook server listening on http://127.0.0.1:{port}")


def main() -> None:
    debug_logger.info("Agent starting", {"config": "loading"})
    storage = Storage()
    scheduler = Scheduler()
    client = OpenRouterClient()

    for sensor_name, interval in config.POLL_INTERVALS.items():
        task = make_sensor_task(sensor_name, storage)
        scheduler.add_task(sensor_name, interval, task)
        debug_logger.info(f"Registered sensor: {sensor_name}", {"interval": interval})

    scheduler.add_task("detection", 30, lambda ctx: detection_task(ctx, storage))
    debug_logger.info("Registered detection task", {"interval": 30})

    scheduler.add_task("risk_assessment", 600, lambda ctx: risk_assessment_task(ctx, storage, client))
    debug_logger.info("Registered risk_assessment task", {"interval": 600})

    scheduler.add_task("vulnerability_check", 3600, lambda ctx: vulnerability_check_task(ctx, storage, client))
    debug_logger.info("Registered vulnerability_check task", {"interval": 3600})

    start_webhook_server(scheduler, storage, client, port=8000)

    print("Agent started. Press Ctrl+C to stop.")
    debug_logger.info("Agent started successfully")
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        print("Stopping agent...")
        debug_logger.info("Agent stopped by user")
        scheduler.stop()


if __name__ == "__main__":
    main()
