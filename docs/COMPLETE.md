# Phantom - AI Agentic Harness System - Complete Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Component Details](#component-details)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Detection Engine](#detection-engine)
6. [Skills Framework](#skills-framework)
7. [Tools Framework](#tools-framework)
8. [Storage & Reports](#storage--reports)
9. [Configuration Reference](#configuration-reference)
10. [API Reference](#api-reference)
11. [Testing & Quality Assurance](#testing--quality-assurance)
12. [Deployment Guide](#deployment-guide)
13. [Troubleshooting](#troubleshooting)

---

## Executive Summary

Phantom (AI Agentic Harness System) is a comprehensive security monitoring platform designed for autonomous threat detection and response. The system combines rule-based detection, statistical anomaly detection, and ML-based anomaly detection with LLM-powered security analysis.

### Key Capabilities

- **Autonomous Monitoring**: Continuous diagnostic runs at configurable intervals
- **Multi-Layer Detection**: Rule-based, statistical, and ML-based anomaly detection
- **AI-Powered Analysis**: LLM-driven security analysis and recommendations
- **Extensible Framework**: Skills and tools for custom capabilities
- **Real-Time Notifications**: WebSocket for live updates and alerts
- **External Integrations**: Slack, Teams, PagerDuty, SIEM, CloudWatch

---

## System Architecture

### Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MONICA ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                              GATEWAY                                   │  │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────────────────┐ │  │
│  │  │ Input         │ │ Schedule      │ │ Payload                     │ │  │
│  │  │ Interfaces    │ │ Manager       │ │ Sender                     │ │  │
│  │  │ - HTTP:8000   │ │ Autonomouse    │ │ → Central Agent           │ │  │
│  │  │ - WebSocket   │ │ Runs          │ │                            │ │  │
│  │  │ - CLI        │ │ (cron-like)   │ │                            │ │  │
│  │  │ - Queue      │ │              │ │                            │ │  │
│  │  │ - File      │ │              │ │                            │ │  │
│  │  └────────────────┘ └────────────────┘ └────────────────────────────┘ │  │
│  └────────────────���─────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼ Payload                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           CENTRAL AGENT                               │  │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────────────────┐ │  │
│  │  │ System        │ │ Context       │ │ Memory                     │ │  │
│  │  │ Prompt       │ │ Manager       │ │ Manager                   │ │  │
│  │  │              │ │              │ │ - TTL                     │ │  │
│  │  │              │ │              │ │ - Search                 │ │  │
│  │  └────────────────┘ └────────────────┘ └────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    ANALYSIS LOOP                               │   │  │
│  │  │  1. Payload received                                           │   │  │
│  │  │  2. Context updated                                            │   │  │
│  │  │  3. Skills executed (if enabled)                                │   │  │
│  │  │  4. Tools executed (if requested)                              │   │  │
│  │  │  5. LLM analysis                                                │   │  │
│  │  │  6. Report generated                                            │   │  │
│  │  │  7. Memory updated                                              │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │   DIAGNOSTICS    │  │    ANALYSIS     │  │     STORAGE             │   │
│  │  - process      │  │  - detection    │  │     - events.log        │   │
│  │  - port         │  │  - statistical  │  │     - detections.log   │   │
│  │  - file         │  │  - ml_anomaly   │  │     - reports/         │   │
│  │  - network     │  │  - trends      │  │                         │   │
│  │  - memory      │  │  - correlation│  │                         │   │
│  │  - disk_io     │  │  - summariser  │  │                         │   │
│  │  - auth        │  │                 │  │                         │   │
���  │  - service    │  │                 │  │                         │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Layers

#### Layer 1: Input Gateway
- **Purpose**: Collect inputs from multiple sources
- **Components**: HTTP Handler, WebSocket Handler, CLI Handler, Queue Handler, File Trigger

#### Layer 2: Schedule Manager  
- **Purpose**: Autonomous diagnostic scheduling
- **Logic**: Timer-based checks at configured intervals
- **Features**: Enable/disable schedules, manual trigger, interval updates

#### Layer 3: Diagnostic Sensors
- **Purpose**: Collect system metrics and events
- **Sensors**: Process, Port, File, Network, Memory, Disk I/O, Auth, Service, Registry, DNS, Driver, Certificate, Hardware

#### Layer 4: Central Agent
- **Purpose**: AI-powered security analysis
- **Components**: System Prompt, Context Manager, Memory Manager, Analysis Loop
- **LLM**: OpenRouter client for GPT models

#### Layer 5: Detection Engine
- **Purpose**: Identify anomalies and threats
- **Methods**: Rule-based, Statistical, ML-based, Correlation

#### Layer 6: Storage & Reports
- **Purpose**: Persist data and generate reports
- **Formats**: JSON logs, Markdown reports

---

## Component Details

### Gateway

```
gateway/
├── __init__.py
├── server.py              # Main server entry point
├── schedule_manager.py   # Autonomous scheduler
├── payload_sender.py     # Sends payloads to Central Agent
└── interfaces/
    ├── http_handler.py       # REST API (port 8000)
    ├── websocket_handler.py   # WebSocket (port 8001)
    ├── cli_handler.py        # CLI commands
    ├── queue_handler.py      # Redis/RabbitMQ
    └── file_trigger.py      # Drop folder
```

**Schedule Manager** provides:
- Autonomous diagnostic runs
- Configurable intervals
- Enable/disable controls
- Manual trigger capability
- Result collection

### Central Agent

```
central_agent/
├── __init__.py
├── system_prompt.md       # Single system prompt
├── context.py            # Session context manager
├── memory.py            # Session memory with TTL
├── agent.py             # Central Agent with LLM loop
├── reports_storage.py   # Report storage/retrieval
├── reports/            # Generated reports (YYYY-MM-DD/)
└── skills/
    ├── __init__.py
    ├── base.py
    ├── registry.py
    ├── metadata.py
    ├── network_analysis.py
    ├── process_analysis.py
    ├── memory_analysis.py
    ├── port_analysis.py
    ├── log_analysis.py
    ├── security_analysis.py
    └── system_diagnostics.py
```

**Central Agent Features**:
- Session-based context management
- Memory with TTL and tag-based search
- Skills framework for extensible capabilities
- Tools framework for remediation
- Automatic report generation

### Diagnostics

```
diagnostics/
├── __init__.py
├── process_sensor.py    # Process monitoring
├── port_sensor.py      # Network port monitoring
├── file_sensor.py     # File system monitoring
├── network_sensor.py   # Network connections
├── memory_sensor.py   # RAM/swap usage
├── disk_io_sensor.py  # Disk I/O
├── auth_sensor.py     # Authentication events
├── service_sensor.py # Windows services
├── registry_sensor.py # Registry monitoring
├── dns_sensor.py      # DNS queries
├── driver_sensor.py  # Driver monitoring
├── certificate_sensor.py # TLS certificates
└── hardware_sensor.py   # USB/hardware
```

### Analysis

```
analysis/
├── __init__.py
├── detection.py           # Rule-based detection
├── statistical_anomaly.py # Statistical detection
├── ml_anomaly.py         # ML-based detection
├── trends.py            # Trend analysis
├── correlation.py       # Event correlation
├── summariser.py        # Report summarizer
├── alert_manager.py    # Alert management
├── approval_manager.py # Approval workflows
└── response_actions.py # Automated response
```

### Core

```
core/
├── __init__.py
├── storage.py           # File-based storage
├── openrouter_client.py # LLM client
└── tools/
    ├── __init__.py
    ├── base.py
    ├── registry.py
    ├── executor.py
    ├── shell_tool.py
    ├── file_tool.py
    ├── process_tool.py
    ├── diagnostic_tool.py
    └── diagnostic_tool.py
```

---

## Data Flow Diagrams

### Main Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MAIN DATA FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  1. SCHEDULER CYCLE
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
  │ Schedule │───▶│ Run Sensor  │───▶│ Collect   │───▶│ Send to   │
  │ Check    │    │ (if due)    │    │ Data       │    │ Central   │
  └──────────┘    └──────────────┘    └─────────────┘    └────────────┘
                                                            │
  2. ANALYSIS LOOP                                            ▼
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
  │ Receive  │───▶│ Update      │───▶│ Execute   │───▶│ Build    │
  │ Payload  │    │ Context     │    │ Skills    │    │ Prompt   │
  └──────────┘    └──────────────┘    └─────────────┘    └────────────┘
       │                                                    │
       ▼                                                    ▼
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
  │ Call LLM │◀───│ Analysis    │◀───│ Generate   │◀───│ Response │
  │          │    │             │    │ Report     │    │          │
  └──────────┘    └──────────────┘    └─────────────┘    └────────────┘
       │
       ▼
  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
  │ Extract │───▶│ Update      │───▶│ Detection  │───▶│ Store    │
  │ Findings│    │ Memory     │    │ (if threshold)│  │ Events   │
  └──────────┘    └──────────────┘    └─────────────┘    └────────────┘
```

### Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SESSION LIFECYCLE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  create_session() ──▶ update_context() ──▶ analyze() ──▶ generate_report()
         │                   │                    │                  │
         ▼                   ▼                    ▼                  ▼
  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │ Session ID  │    │ Add payload │    │ LLM call    │    │ .md report  │
  │ Context    │    │ to session │    │ Analysis   │    │ in reports/ │
  │ Memory     │    │            │    │ Skills     │    │             │
  │ cleared    │    │            │    │ Tools      │    │             │
  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
         │                                                         │
         └───────────────── clear_session() ◀───────────────────┘
```

### Detection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DETECTION FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

  Sensor Data ──▶ ─�──▶ Rule-Based Detection ──▶ Alert
                   │
                   ├──▶ Statistical Detection ──▶ Alert
                   │
                   ├──▶ ML-Based Detection ──▶ Alert
                   │
                   └──▶ Correlation Engine ──▶ Alert
```

---

## Detection Engine

### Rule-Based Detection

Evaluates simple heuristics against sensor outputs:

| Rule | Threshold | Description |
|------|-----------|-------------|
| `process_count` | 250 | Max running processes |
| `open_ports` | 50 | Max listening ports |
| `file_changes` | 100 | Max file changes per interval |
| `established_connections` | 100 | Max connections |
| `external_ips` | 10 | Max unique external IPs |
| `memory_percent` | 90% | Max memory usage |
| `disk_percent` | 90% | Max disk usage |
| `failed_logins` | 5 | Max failed logins |

### Statistical Anomaly Detection

Uses rolling statistics to detect outliers:

- **Method**: Rolling mean ± 2.5 standard deviations
- **Window**: 20 samples
- **Metrics**: process_count, open_ports, memory_percent, etc.

### ML-Based Anomaly Detection

Uses Isolation Forest for anomaly detection:

- **Algorithm**: Isolation Forest
- **Features**: Sensor metrics transformed to features
- **Threshold**: Contamination rate 0.1

### Correlation Engine

Correlates events across time windows:

- **Window**: 5 minutes
- **Min Confidence**: 0.6
- **Pattern Types**: attack_chains, lateral_movement, data_exfiltration

---

## Skills Framework

Skills extend capabilities with specialized implementations.

### Available Skills

| Skill | Category | Description |
|------|----------|-------------|
| `network_analysis` | NETWORK | Analyzes network connections |
| `process_analysis` | PROCESS | Analyzes running processes |
| `memory_analysis` | MEMORY | Analyzes memory usage |
| `port_analysis` | NETWORK | Analyzes open ports |
| `log_analysis` | LOGS | Analyzes system logs |
| `security_analysis` | SECURITY | Security posture |
| `system_diagnostics` | SYSTEM | System diagnostics |

### Skill Execution

```python
context = {"payload": payload, "source": source}
result = skill_registry.execute("network_analysis", context)
```

---

## Tools Framework

Tools enable remediation actions.

### Available Tools

| Tool | Description |
|------|-------------|
| `shell` | Execute shell commands |
| `file` | File operations (read, write, list, search) |
| `process` | Process management (list, kill, info) |
| `diagnostic` | Run diagnostic collectors |

### Tool Execution

```python
result = tool_executor.execute("shell", {"command": "ps aux"})
```

---

## Storage & Reports

### Storage Format

Events stored as JSON lines:

```json
{"timestamp": "2024-01-01T12:00:00", "sensor": "process_sensor", "data": {...}}
```

### Report Format

Markdown reports in `central_agent/reports/YYYY-MM-DD/`:

```markdown
# Security Analysis Report

**Session ID**: abc123
**Timestamp**: 2024-01-01T12:00:00
**Risk Level**: MEDIUM
**Trigger**: schedule

---

## Analysis

[LLM-generated analysis]

---

## Skill Execution Results

### network_analysis
- Status: success
- Output: {...}

---

## Raw Payload

```json
{...}
```
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | LLM API key |
| `OPENROUTER_MODEL` | openrouter-gpt-3.5-turbo | Model |
| `AGENT_LOG_DIR` | ./.logs | Log directory |
| `AGENT_WATCH_DIR` | project root | File watch |
| `AGENT_THRESHOLD_PROCESS_COUNT` | 250 | Process threshold |
| `AGENT_THRESHOLD_OPEN_PORTS` | 50 | Port threshold |
| `AGENT_THRESHOLD_FILE_CHANGES` | 100 | File threshold |

### Polling Intervals

Default intervals in seconds:

```python
POLL_INTERVALS = {
    "process_sensor": 60,
    "port_sensor": 120,
    "file_sensor": 30,
    "network_sensor": 60,
    "memory_sensor": 60,
    "disk_io_sensor": 120,
    "auth_sensor": 30,
    "service_sensor": 60,
    "registry_sensor": 300,
    "dns_sensor": 30,
    "driver_sensor": 120,
    "certificate_sensor": 3600,
    "hardware_sensor": 60,
}
```

---

## API Reference

### HTTP Endpoints (port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Submit payload |
| `/schedules` | GET | Get schedules |
| `/schedules/{name}/run` | POST | Run schedule |
| `/status` | GET | Gateway status |
| `/trigger/{skill}` | POST | Trigger skill |
| `/health` | GET | Health check |

### WebSocket (port 8001)

Real-time updates including:
- Analysis progress
- Detection alerts
- System status

---

## Testing & Quality Assurance

### Test Suites

```bash
# All tests
pytest tests/ -v

# Individual suites
pytest tests/test_central_agent.py
pytest tests/test_gateway.py
pytest tests/test_diagnostics.py
pytest tests/test_integration.py
pytest tests/test_core.py
pytest tests/test_analysis.py
```

### Test Coverage Areas

- Central Agent: Session management, LLM calls, skills
- Gateway: Scheduler, interfaces, payload sending
- Diagnostics: All sensor collectors
- Analysis: Detection rules, thresholds
- Integration: End-to-end flows

---

## Deployment Guide

### Requirements

- Python 3.9+
- psutil (optional, for rich sensors)
- OpenRouter API key (optional, for AI analysis)

### Installation

```bash
pip install -r requirements.txt
```

### Running

```bash
# CLI mode
python main.py

# Web dashboard
python apps/web/app.py

# With custom config
AGENT_LOG_DIR=/var/log/phantom python main.py
```

### Docker (optional)

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|-----------|
| No sensors responding | Check psutil installed |
| LLM analysis fails | Verify OPENROUTER_API_KEY |
| High memory usage | Adjust POLL_INTERVALS |
| Detection not triggering | Check DETECTION_THRESHOLDS |
| WebSocket not connecting | Check port 8001 not blocked |

### Logs

Check logs in `AGENT_LOG_DIR`:
- `events.log` - Sensor events
- `detections.log` - Detection alerts

---

*Last Updated: 2024*