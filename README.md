# Monica - System Monitoring Agent

This project implements a lightweight, local security and monitoring agent.  It is **not** intended
to completely secure a machine, but instead serves as a template and reference for building
a self‑contained monitoring system.  The agent collects telemetry about the host, applies
simple detection rules, and can call out to a language model (via OpenRouter) to
summarise or explain detected anomalies.

## Design Goals

* **Local execution** – The agent is designed to run as a long‑lived process on your
  machine.  It should not require a cloud control plane and does not attempt to
  update or rewrite itself.
* **Modular** – Each sensor, analysis routine, and skill lives in its own module under
  the `sensors/`, `analysis/` and `skills/` packages.  This makes it easy to add
  new capabilities without editing core logic.
* **Safe boundaries** – The agent never executes arbitrary code from the language
  model.  The only connection to the LLM is via the `OpenRouterClient` which
  performs inference on your behalf.  New plugins must be explicitly added to
  the codebase.
* **Minimal dependencies** – The core depends only on the Python standard library.
  Optional extras (like `psutil` or `watchdog`) can be installed via the
  provided `requirements.txt`.  If they are unavailable the agent falls back
  to slower, shell–based queries.

## Directory Layout

```
agent_project/
├── README.md             – This file
├── requirements.txt     – Python dependencies
├── config.py            – Central configuration
├── main.py              – Agent entry point
├── dashboard.py         – Unified TUI dashboard (monitoring + chat + commands)
├── init_agent.py        – CLI initialization tool
├── core/              – Framework components
│   ├── __init__.py
│   ├── scheduler.py     – Task scheduler
│   ├── storage.py       – Event logging
│   └── openrouter_client.py – OpenRouter API wrapper
├── sensors/            – Telemetry collection
│   ├── __init__.py
│   ├── process_sensor.py
│   ├── port_sensor.py
│   └── file_sensor.py
├── analysis/           – Detection engine
│   ├── __init__.py
│   ├── detection.py
│   └── summariser.py
├── skills/             – Agent skills
│   ├── __init__.py
│   ├── risk_assessment.py
│   └── vulnerability_check.py
├── utils/              – Utility modules
│   ├── __init__.py
│   ├── system_scanner.py – OS and dependency scanner
│   ├── installer.py    – Package installer
│   └── threadpool.py  – Thread pool singleton
└── .logs/            – Event and detection logs
## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the agent (scans OS, checks requirements, installs missing packages)
python init_agent.py check

# Run the agent
python main.py

# Or run the unified TUI dashboard (in separate terminal)
python dashboard.py
```

## Initialization CLI

The `init_agent.py` tool handles system setup:

```bash
python init_agent.py scan     # Scan system for OS and requirements
python init_agent.py install # Install missing dependencies
python init_agent.py check   # Full system check (scan + install)
python init_agent.py status  # Show agent status
```

To start the agent, run:

```
pip install -r requirements.txt
python3 -m agent_project.main
```

If you want to utilise OpenRouter for summarisation or other LLM calls, set the
`OPENROUTER_API_KEY` environment variable to your API key.  Without the key the
agent will still run but will skip LLM calls.

## Important Notes

* **Not self‑modifying** – This agent does **not** rewrite its own code or download
  new modules from the internet.  This is by design; autonomous self‑modifying
  code is extremely risky.  Extensions must be added manually under the
  `skills/` or `sensors/` directories.
* **Analysis pipeline** – The built‑in detection engine is intentionally simple.
  Serious deployments should integrate mature security tools like Wazuh or
  OSQuery and treat the LLM as a summariser rather than an authoritative
  decision maker.

## Unified Dashboard

The dashboard provides real-time monitoring + chat + command interface:

```bash
python dashboard.py
```

### Left Panel (Monitoring)
- **Processes** - Running process count and top consumers
- **Network Ports** - Listening TCP/UDP ports
- **File Changes** - Directory change tracking
- **Detections** - Anomaly alerts
- **Activity Log** - Recent sensor events
- **Agent Status** - Uptime, stats, thresholds

### Right Panel (Chat + Commands)
- **Chat Display** - Shows messages and system responses
- **Command Input** - Text field for commands
- **Buttons** - Send, Clear, Scan, Status

### Available Commands
- `scan` - Run system scan
- `status` - Check agent readiness
- `clear` - Clear chat history
- `help` - Show help

### Keybindings
- `R` - Refresh data
- `C` - Focus chat input
- `Ctrl+Enter` - Send message
- `Q` - Quit

Enjoy exploring and modifying this codebase!