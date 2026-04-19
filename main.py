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
import signal
from pathlib import Path

import config
from central_agent import create_central_agent
from gateway import create_gateway
from utils.debug_log import debug_logger

try:
    import psutil
except ImportError:
    psutil = None


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

web_server = None
shutdown_event = None
flask_process = None
flask_pid = None


def start_web_dashboard():
    """Start the Flask web dashboard as subprocess."""
    global flask_process, flask_pid
    import subprocess
    import os
    
    print("Starting Flask server...")
    
    flask_process = subprocess.Popen(
        [sys.executable, "-m", "flask", "--app", "apps.web.app:create_app", "run", 
         "--host", "127.0.0.1", "--port", "5000", "--no-debug", "--no-worker-guard"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    import time
    time.sleep(2)
    
    import psutil
    parent = psutil.Process(flask_process.pid)
    for child in parent.children(recursive=True):
        try:
            child.kill()
        except:
            pass
    
    print("Flask started.")


def stop_web_dashboard():
    """Stop the Flask web dashboard."""
    global flask_process, flask_pid
    print("Stopping Flask server...")
    
    if flask_process:
        try:
            parent = psutil.Process(flask_process.pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except:
                    pass
            parent.kill()
        except:
            pass
    
    import subprocess
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             f"Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | "
             f"Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ "
             f"Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True,
            timeout=3
        )
    except:
        pass
    
    print("Flask stopped.")


def main() -> None:
    """Run the Monica monitoring agent."""
    global running
    running = True
    
    def signal_handler(signum, frame):
        global running
        print("\nReceived interrupt signal...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
    
    web_thread = threading.Thread(target=start_web_dashboard, daemon=True)
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
    print("    - Reports:  http://127.0.0.1:5000/reports")
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
        
        while running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print("Stopping agent...")
    except Exception as e:
        print(f"Gateway error: {e}")
        debug_logger.error(f"Gateway error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Stopping...")
    debug_logger.info("Agent stopped by user")
    gateway.stop()
    stop_web_dashboard()
    print("Done.")


if __name__ == "__main__":
    main()