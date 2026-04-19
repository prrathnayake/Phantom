"""Entry point for Monica - Secure Monitoring Agent Harness System.

Architecture:
- Gateway: Input interfaces + Schedule Manager
- Central Agent: LLM analysis loop + Reports
- Diagnostics: process, port, file sensors
"""
import sys
import os
import time
import threading
from pathlib import Path

import config
from central_agent import create_central_agent
from gateway import create_gateway
from utils.debug_log import debug_logger


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def start_web_dashboard():
    """Start the Flask web dashboard in a background thread."""
    try:
        from apps.web.app import init_app, app
        init_app()
        print("Starting Flask server...")
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"Flask error: {e}")
        import traceback
        traceback.print_exc()


def main() -> None:
    """Run the Monica monitoring agent."""
    debug_logger.info("Starting Monica")
    
    central_agent = create_central_agent()
    gateway = create_gateway(central_agent=central_agent)
    
    for diagnostic_name, interval in config.POLL_INTERVALS.items():
        module_name = diagnostic_name.replace("_sensor", "")
        gateway.schedule_manager.add_schedule(
            name=diagnostic_name,
            interval=interval,
            script_module=module_name
        )
    
    debug_logger.info(f"Registered {len(config.POLL_INTERVALS)} diagnostic schedules")
    
    web_thread = threading.Thread(target=start_web_dashboard)
    web_thread.start()
    
    print("Web Dashboard starting on port 5000...")
    
    print()
    print("=" * 50)
    print(f"{Colors.BOLD}  MONICA{Colors.END}")
    print(f"  Secure Monitoring Agent Harness System")
    print("=" * 50)
    print()
    print(f"  HTTP API:       http://127.0.0.1:8000")
    print(f"  WebSocket:     ws://127.0.0.1:8001")
    print(f"  Web Dashboard: http://127.0.0.1:5000")
    print(f"  Diagnostics:   {len(config.POLL_INTERVALS)} configured")
    print()
    print("=" * 50)
    print("  Pages:")
    print("    - Dashboard:  http://127.0.0.1:5000/")
    print("    - Chat:      http://127.0.0.1:5000/chat")
    print("    - Diag:      http://127.0.0.1:5000/diagnostics")
    print("    - Monitor:   http://127.0.0.1:5000/monitor")
    print("    - Reports:   http://127.0.0.1:5000/reports")
    print("=" * 50)
    print()
    print("Press Ctrl+C to stop.")
    print()
    
    debug_logger.info("Agent started")
    
    try:
        print()
        print("Gateway starting on port 8000...")
        gateway.start()
        
        print("Gateway started. Waiting for scheduled diagnostics...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print("Stopping agent...")
        debug_logger.info("Agent stopped by user")
        gateway.stop()
    except Exception as e:
        print(f"Gateway error: {e}")
        debug_logger.error(f"Gateway error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()