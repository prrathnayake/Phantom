# System Monitoring Agent Project

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
├── README.md           – This file
├── requirements.txt     – Optional Python dependencies
├── config.py            – Central configuration values
├── main.py              – Entry point for the agent
├── dashboard.py         – TUI dashboard for real-time monitoring
├── core/                – Framework components
│   ├── __init__.py
│   ├── scheduler.py     – Simple scheduler for recurring tasks
│   ├── storage.py       – Local event logging API
│   └── openrouter_client.py – Thin wrapper around the OpenRouter API
├── sensors/             – Telemetry collection modules
│   ├── __init__.py
│   ├── process_sensor.py  – Collects the current process list
│   ├── port_sensor.py     – Collects open TCP/UDP ports
│   └── file_sensor.py     – Monitors a directory for changes
├── analysis/            – Detection and summarisation
│   ├── __init__.py
│   ├── detection.py      – Rule–based anomaly detection
│   └── summariser.py     – Uses LLM to summarise recent events
└── skills/              – Example high‑level skills
    ├── __init__.py
    ├── risk_assessment.py   – Aggregates risk signals
    └── vulnerability_check.py – Placeholder for scanning vulnerabilities
```
agent_project/
├── README.md           – This file
├── requirements.txt     – Optional Python dependencies
├── config.py            – Central configuration values
├── main.py              – Entry point for the agent
├── core/                – Framework components
│   ├── __init__.py
│   ├── scheduler.py     – Simple scheduler for recurring tasks
│   ├── storage.py       – Local event logging API
│   └── openrouter_client.py – Thin wrapper around the OpenRouter API
├── sensors/             – Telemetry collection modules
│   ├── __init__.py
│   ├── process_sensor.py  – Collects the current process list
│   ├── port_sensor.py     – Collects open TCP/UDP ports
│   └── file_sensor.py     – Monitors a directory for changes
├── analysis/            – Detection and summarisation
│   ├── __init__.py
│   ├── detection.py      – Rule–based anomaly detection
│   └── summariser.py     – Uses LLM to summarise recent events
└── skills/              – Example high‑level skills
    ├── __init__.py
    ├── risk_assessment.py   – Aggregates risk signals
    └── vulnerability_check.py – Placeholder for scanning vulnerabilities
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

## Running the Dashboard

To monitor the agent in real-time, run the TUI dashboard in a separate terminal:

```bash
python dashboard.py
```

The dashboard displays:
- **Sensor Status** - Process count, open ports, file changes
- **Recent Detections** - Anomalies triggered by detection rules
- **Activity Log** - Recent sensor events
- **Agent Status** - Running state and last update time

The dashboard auto-refreshes every 2 seconds. Press `R` to refresh manually, `Q` to quit.

Enjoy exploring and modifying this codebase!