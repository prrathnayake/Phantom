"""Global configuration values for Monica - the security monitoring agent.

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
    "network_sensor": 60,  # every minute - connections and traffic
    "memory_sensor": 60,  # every minute - RAM/swap usage
    "disk_io_sensor": 120,  # every two minutes - disk usage
    "auth_sensor": 30,     # every 30 seconds - login attempts
    # New sensors (Phase 4)
    "service_sensor": 60,     # every minute - critical services
    "registry_sensor": 300,  # every 5 minutes - registry/audit
    "dns_sensor": 30,      # every 30 seconds - DNS queries
    "driver_sensor": 120,   # every 2 minutes - drivers/modules
    "certificate_sensor": 3600,  # every hour - TLS certificates
    "hardware_sensor": 60,  # every minute - USB/hardware
}

# Directory to watch for file changes.  Override via `AGENT_WATCH_DIR`.
WATCH_DIRECTORY = Path(os.environ.get("AGENT_WATCH_DIR", str(Path(__file__).parent)))

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
    # Network sensor thresholds
    "established_connections": int(os.environ.get("AGENT_THRESHOLD_ESTABLISHED_CONNS", 100)),
    "external_ips": int(os.environ.get("AGENT_THRESHOLD_EXTERNAL_IPS", 10)),
    # Memory sensor thresholds (% usage)
    "memory_percent": int(os.environ.get("AGENT_THRESHOLD_MEMORY_PERCENT", 90)),
    "swap_percent": int(os.environ.get("AGENT_THRESHOLD_SWAP_PERCENT", 50)),
    # Disk I/O sensor thresholds
    "disk_percent": int(os.environ.get("AGENT_THRESHOLD_DISK_PERCENT", 90)),
    # Auth sensor thresholds (failed logins per interval)
    "failed_logins": int(os.environ.get("AGENT_THRESHOLD_FAILED_LOGINS", 5)),
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

# Alert Manager Configuration
ALERT_THROTTLE_SECONDS = int(os.environ.get("AGENT_ALERT_THROTTLE_SECONDS", 60))
ALERT_TIMEOUT_MINUTES = int(os.environ.get("AGENT_ALERT_TIMEOUT_MINUTES", 30))

# Risk Scoring Configuration
RISK_WEIGHTS = {
    "process_count": 10,
    "open_ports": 15,
    "file_changes": 20,
    "established_connections": 15,
    "external_ips": 20,
    "memory_percent": 10,
    "swap_percent": 10,
    "disk_percent": 10,
    "failed_logins": 25,
    "privilege_escalation": 40,
    "brute_force": 35,
    "lateral_movement": 50,
    "data_exfiltration": 45,
    "malware": 50,
    "dns_tunneling": 30,
}

# Correlation Engine Configuration
CORRELATION_WINDOW_MINUTES = int(os.environ.get("AGENT_CORRELATION_WINDOW", 5))
CORRELATION_MIN_CONFIDENCE = float(os.environ.get("AGENT_CORRELATION_MIN_CONFIDENCE", 0.6))

# Statistical Anomaly Detection
STATISTICAL_WINDOW = int(os.environ.get("AGENT_STATISTICAL_WINDOW", 20))
STATISTICAL_THRESHOLD = float(os.environ.get("AGENT_STATISTICAL_THRESHOLD", 2.5))

# External Integrations Configuration
# Slack
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# Microsoft Teams
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")

# PagerDuty
PAGERDUTY_KEY = os.environ.get("PAGERDUTY_KEY")

# SIEM Configuration
SIEM_TYPE = os.environ.get("AGENT_SIEM_TYPE", "splunk")
SIEM_URL = os.environ.get("AGENT_SIEM_URL")
SIEM_API_KEY = os.environ.get("AGENT_SIEM_API_KEY")
SIEM_INDEX = os.environ.get("AGENT_SIEM_INDEX")

# Elasticsearch
ELASTIC_URL = os.environ.get("ELASTIC_URL")
ELASTIC_API_KEY = os.environ.get("ELASTIC_API_KEY")
ELASTIC_INDEX_PREFIX = os.environ.get("ELASTIC_INDEX_PREFIX", "suraksha")

# AWS CloudWatch
CLOUDWATCH_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# Approval Settings
AUTO_APPROVE_LOW_RISK = os.environ.get("AGENT_AUTO_APPROVE_LOW_RISK", "false").lower() == "true"
APPROVAL_REQUIRED_RISK_LEVEL = int(os.environ.get("AGENT_APPROVAL_RISK_THRESHOLD", 50))

# Response Actions
ENABLE_AUTO_RESPONSE = os.environ.get("AGENT_ENABLE_AUTO_RESPONSE", "false").lower() == "true"
