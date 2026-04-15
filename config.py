"""Global configuration values for the monitoring agent.

The agent reads these values at start‑up.  They may be overridden by
environment variables for convenience (see below).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path(os.environ.get("AGENT_LOG_DIR", Path(__file__).parent / ".logs"))

# Default polling intervals (in seconds) for each sensor.  You can add
# additional sensor names here and register them in `main.py`.
POLL_INTERVALS = {
    "process_sensor": 60,  # every minute
    "port_sensor": 120,    # every two minutes
    "file_sensor": 30,     # watch file changes more frequently
}

# Directory to watch for file changes.  Override via `AGENT_WATCH_DIR`.
WATCH_DIRECTORY = Path(os.environ.get("AGENT_WATCH_DIR", str(Path.home())))

# OpenRouter API configuration.  The key should be supplied via environment
# variable `OPENROUTER_API_KEY` because embedding secrets in code is unsafe.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1"
)

# Default LLM model to use.  Models available depend on your OpenRouter account.
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "openrouter-gpt-3.5-turbo"
)

# Detection thresholds used by the rule engine.  These are intentionally
# simplistic and can be tuned.  See `analysis/detection.py` for usage.
DETECTION_THRESHOLDS = {
    # If the number of running processes exceeds this threshold the rule
    # triggers.  On many systems 200+ processes is normal; adjust as needed.
    "process_count": int(os.environ.get("AGENT_THRESHOLD_PROCESS_COUNT", 250)),
    # If more than this many TCP/UDP ports are listening the rule triggers.
    "open_ports": int(os.environ.get("AGENT_THRESHOLD_OPEN_PORTS", 50)),
    # Number of file changes within the watch interval that constitutes
    # abnormal activity.
    "file_changes": int(os.environ.get("AGENT_THRESHOLD_FILE_CHANGES", 100)),
}

def ensure_log_dir():
    """Ensure that the log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


TIMELINE_MAX_EVENTS = int(os.environ.get("AGENT_TIMELINE_MAX_EVENTS", 50))

MEMORY_MAX_ENTRIES = int(os.environ.get("AGENT_MEMORY_MAX_ENTRIES", 100))

RISK_SCORE_MAX = int(os.environ.get("AGENT_RISK_SCORE_MAX", 100))

RISK_TREND_WINDOW = int(os.environ.get("AGENT_RISK_TREND_WINDOW", 5))

AGENT_MODES = ["PASSIVE", "ACTIVE", "AUTONOMOUS"]

DEFAULT_AGENT_MODE = os.environ.get("AGENT_DEFAULT_MODE", "PASSIVE")

KNOWN_SYSTEM_PATHS = [
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "/usr/bin",
    "/usr/sbin",
    "/bin",
    "/sbin",
]

PORT_CLASSIFICATIONS = {
    80: "HTTP",
    443: "HTTPS",
    22: "SSH",
    21: "FTP",
    25: "SMTP",
    3306: "MySQL",
    5432: "PostgreSQL",
    6379: "Redis",
    27017: "MongoDB",
}

DEBUG_MODE = os.environ.get("AGENT_DEBUG", "false").lower() == "true"
