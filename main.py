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


def make_sensor_task(sensor_module_name: str, storage: Storage) -> Callable[[Dict[str, Any]], None]:
    """Return a function that collects data from the given sensor.

    :param sensor_module_name: Module name within `sensors` package.
    :param storage: Storage instance for logging events.
    """
    module = importlib.import_module(f"sensors.{sensor_module_name}")
    def task(context: Dict[str, Any]) -> None:
        payload = module.collect(context)
        storage.log_event(sensor_module_name, payload)
        # Store last payload in context so detection rules can access it
        context[f"{sensor_module_name}_last"] = payload
    return task


def detection_task(context: Dict[str, Any], storage: Storage) -> None:
    # Run rule based detection; anomalies are logged to storage
    anomalies = detection.detect(context, storage)
    if anomalies:
        # Store last anomalies in context for UI or summarisation
        context.setdefault("recent_anomalies", []).extend(anomalies)


def risk_assessment_task(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    risk_assessment.run(context, storage, client)
    # Optionally print summary to console
    summary = context.get("last_summary")
    if summary:
        print("[Risk Assessment Summary]")
        print(summary)


def vulnerability_check_task(context: Dict[str, Any], storage: Storage, client: OpenRouterClient) -> None:
    vulnerability_check.run(context, storage, client)
    result = context.get("last_vulnerability_assessment")
    if result:
        print("[Vulnerability Assessment]")
        print(result)


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
    storage = Storage()
    scheduler = Scheduler()
    client = OpenRouterClient()

    # Register sensor tasks based on configuration
    for sensor_name, interval in config.POLL_INTERVALS.items():
        task = make_sensor_task(sensor_name, storage)
        scheduler.add_task(sensor_name, interval, task)

    # Detection task runs every 30 seconds
    scheduler.add_task("detection", 30, lambda ctx: detection_task(ctx, storage))

    # Risk assessment summary every 10 minutes (600 seconds)
    scheduler.add_task("risk_assessment", 600, lambda ctx: risk_assessment_task(ctx, storage, client))

    # Optionally run vulnerability check every hour
    scheduler.add_task("vulnerability_check", 3600, lambda ctx: vulnerability_check_task(ctx, storage, client))

    # Start webhook server
    start_webhook_server(scheduler, storage, client, port=8000)

    print("Agent started. Press Ctrl+C to stop.")
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        print("Stopping agent...")
        scheduler.stop()


if __name__ == "__main__":
    main()
