"""Entry point for Suraksha - Secure Monitoring Agent.

Architecture:
- Gateway: Input interfaces + Schedule Manager
- Central Agent: LLM analysis loop + Reports
- Diagnostics: process, port, file sensors
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading

import config
from central_agent import create_central_agent
from gateway import ScheduleManager, create_gateway
from utils.debug_log import debug_logger


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def main() -> None:
    """Run the Suraksha monitoring agent."""
    debug_logger.info("Starting Suraksha")
    
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
    
    print()
    print("=" * 50)
    print(f"{Colors.BOLD}  Suraksha - Secure Monitoring Agent{Colors.END}")
    print(f"  Architecture: Gateway + Central Agent")
    print("=" * 50)
    print()
    print(f"  HTTP API:     http://127.0.0.1:8000")
    print(f"  WebSocket:   ws://127.0.0.1:8001")
    print(f"  Diagnostics: {len(config.POLL_INTERVALS)} configured")
    print()
    print("Press Ctrl+C to stop.")
    print()
    
    debug_logger.info("Agent started")
    
    try:
        gateway.start()
    except KeyboardInterrupt:
        print()
        print("Stopping agent...")
        debug_logger.info("Agent stopped by user")
        gateway.stop()


if __name__ == "__main__":
    main()