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
│                              PHANTOM ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                              GATEWAY                                   │  │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────────────────┐ │  │
│  │  │ Input         │ │ Schedule      │ │ Payload                     │ │  │
│  │  │ Interfaces    │ │ Manager       │ │ Sender                     │ │  │
│  │  │ - HTTP:8000   │ │ Autonomouse    │ │ → Agent           │ │  │
│  │  │ - WebSocket   │ │ Runs          │ │                            │ │  │
│  │  │ - CLI        │ │ (cron-like)   │ │                            │ │  │
│  │  │ - Queue      │ │              │ │                            │ │  │
│  │  │ - File      │ │              │ │                            │ │  │
│  │  └────────────────┘ └────────────────┘ └────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
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

#### Layer 4: Agent
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
src/gateway/
├── __init__.py
├── server.py              # Main server entry point
├── schedule_manager.py   # Autonomous scheduler
├── payload_sender.py     # Sends payloads to Agent
└── interfaces/
    ├── http_handler.py       # REST API (port 8000)
    ├── websocket_handler.py   # WebSocket (port 8001)
    ├── cli_handler.py        # CLI commands
    ├── queue_handler.py      # Redis/RabbitMQ
    └── file_trigger.py      # Drop folder
```

**Schedule Manager Deep Dive**:

`ScheduleManager` (`src/gateway/schedule_manager.py`) provides autonomous cron-like scheduling:

- **Schedule Dataclass**: Each schedule holds `name`, `interval` (seconds), `script_module`, `func` (the sensor's `collect()` function), `next_run` (datetime), `enabled`, and `last_result`.
- **Dynamic Loading**: `add_schedule()` dynamically imports `src.diagnostics.{script_module}` and binds `module.collect` to the schedule. If the module or function is missing, the schedule is skipped with a debug log.
- **Autonomous Loop**: `run_autonomous()` runs in a background thread, sleeping in 1-second increments. Each iteration calls `run_all_due()`, which checks `schedule.should_run()` (compares `datetime.now(timezone.utc) >= next_run`).
- **Notification System**: External components register callbacks via `on_schedule_run(callback)`. After every schedule execution, `_notify_schedule_run(result)` broadcasts the result to all subscribers. This is how the dashboard receives live updates.
- **Manual Trigger**: `run_schedule(name)` executes a specific schedule immediately, independent of its `next_run` time.
- **Interval Updates**: `update_interval(name, interval)` changes the schedule frequency and recalculates `next_run = now + timedelta(seconds=interval)`.

**Payload Sender** (`src/gateway/payload_sender.py`):
- Sends diagnostic payloads to the Agent HTTP endpoint (`/analyze`) with configurable retry logic (default 3 attempts) and exponential backoff (1s, 2s, 3s delays).
- Supports synchronous (`send()`), batch (`send_batch()`), and asynchronous (`send_async()`) transmission modes.
- Async mode spawns a daemon thread and supports an optional callback on completion.

### Agent

```
src/agent/
├── __init__.py
├── system_prompt.md       # Single system prompt
├── context.py            # Session context manager
├── memory.py            # Session memory with TTL
├── agent.py             # Agent with LLM loop
├── reports_storage.py   # Report storage/retrieval
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

Reports are stored at runtime in `src/agent/reports/YYYY-MM-DD/`.

**Agent Deep Dive**:

The Agent (`src/agent/agent.py`) implements an 8-step analysis pipeline:

1. **Receive Payload** - Accepts a diagnostic dict from Gateway via `analyze(payload, session_id, trigger)`.
2. **Update Context** - `ContextManager.update_context()` appends the payload to the session's payload history. If the session doesn't exist, it is created automatically.
3. **Fetch Memory** - `_fetch_relevant_memory()` searches `SessionMemory` by payload source and retrieves the 5 most recent entries.
4. **Execute Skills** - `_execute_relevant_skills()` maps the payload source to a list of skills (e.g., `network` → `network_analysis`). Each skill runs via `SkillRegistry.execute()` and returns a `SkillResult` with status, output, and timing.
5. **Execute Tools** - If `execute_tools=True`, `_execute_relevant_tools()` processes `tool_requests` from the payload through `ToolExecutor.execute()`.
6. **Build Prompt** - `_build_prompt()` assembles a structured Markdown prompt containing session context, memory, skill/tool results, and the raw JSON payload. The prompt instructs the LLM to return risk level, findings, recommendations, and tool requests.
7. **LLM Analysis** - `_call_llm()` sends the prompt to OpenRouter using the chat completions API. If the API is unavailable, it returns a fallback message.
8. **Extract Findings** - `_extract_findings()` parses the LLM response with regex to determine `risk_level` (LOW/MEDIUM/HIGH/CRITICAL) and extracts bullet-point recommendations.
9. **Update Memory** - `_update_memory()` stores the analysis, payload, skill results, and tool results in `SessionMemory` with tags for future retrieval.
10. **Generate Report** - `_generate_report()` redacts sensitive keys (password, token, api_key, etc.) via `_redact_value()`, then writes a Markdown report to `src/agent/reports/YYYY-MM-DD/` via `ReportStorage`.

**Thread Safety**: The `analyze()` method acquires `self._lock` for the entire duration, ensuring serialized access to context and memory.

**Session Lifecycle**:
- `create_session()` → `update_context()` → `analyze()` → `generate_report()` → optional `clear_session()`
- Sessions auto-expire after 3600 seconds (configurable in `ContextManager`).
- Max 100 concurrent sessions; oldest session is evicted when the limit is exceeded.

**Memory Model**:
- `SessionMemory` stores key-value entries with optional TTL (default 3600s), tags, and session scoping.
- Supports search by key, tag, or value substring.
- Can persist to JSON file (`session_memory.json`) and auto-load on startup.
- Max 500 entries; oldest entry evicted when limit exceeded.

### Diagnostics

```
src/diagnostics/
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
src/analysis/
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
src/core/
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
    └── diagnostic_tool.py
```

---

## Deep Dive: Core Components

### Context Manager (`src/agent/context.py`)

The `ContextManager` maintains a thread-safe registry of `SessionContext` objects:

- **SessionContext Dataclass**: Holds `session_id`, `created_at`, `updated_at`, `payloads` (list), `findings` (list), and `metadata`.
- **Expiration**: `is_expired(timeout)` checks if `time.time() - created_at > timeout`. Expired sessions are deleted on access or via `cleanup_expired()`.
- **Eviction Policy**: When `max_sessions` (default 100) is reached, `_evict_oldest()` removes the session with the smallest `created_at` timestamp.
- **Locking**: All reads and writes acquire `self._lock` to prevent race conditions during concurrent Gateway and Agent access.

### Session Memory (`src/agent/memory.py`)

`SessionMemory` provides a key-value store with TTL and optional persistence:

- **SessionMemoryEntry Dataclass**: Contains `key`, `value`, `timestamp`, `ttl` (seconds), `tags` (list), and `session_id`.
- **Expiration Logic**: `is_expired()` returns `True` if `(time.time() - timestamp) > ttl`. Expired entries are purged on read or via `cleanup_expired()`.
- **Search**: `search(query)` performs case-insensitive substring matching against keys, tags, and stringified values.
- **Persistence**: If `persist_path` is set, `_save()` writes all entries as JSON to disk after every store/delete. `_load()` reads the file on initialization.
- **Scoping**: Entries can be global (`session_id=None`) or session-scoped. `get_for_session()` filters by session ID.

### Report Storage (`src/agent/reports_storage.py`)

`ReportStorage` manages Markdown report files:

- **Directory Structure**: `src/agent/reports/YYYY-MM-DD/report_{session_id}_YYYYMMDD_HHMMSS.md`
- **Metadata**: Each report includes YAML-like frontmatter with `session_id`, `timestamp`, `risk_level`, `trigger`, and skills/tools used.
- **Retrieval**: `get_report(session_id)` finds the most recent report for a session. `get_recent_reports(count)` returns the newest N reports across all dates.

### Storage Layer (`src/core/storage.py`)

The `Storage` class implements append-only JSONL logging:

- **events.log**: Each line is a JSON object with `timestamp` (ISO-8601), `sensor`, and `data`.
- **detections.log**: Each line is a JSON object with `timestamp`, `rule`, `description`, and `details`.
- **Silent Failure**: Write failures are caught and logged to `debug.log` but never raise exceptions, ensuring sensors never crash the agent.
- **Reading**: `get_recent_events(count, sensor)` and `get_recent_detections(count)` read from the end of the file, filter by sensor if requested, and return newest-first.

### OpenRouter Client (`src/core/openrouter_client.py`)

`OpenRouterClient` wraps the OpenRouter chat completions API:

- **Configuration**: Reads `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_MODEL` from `config.py` (which loads from environment variables).
- **Health Tracking**: `get_health()` returns a sanitized dict with `configured`, `model`, `status`, and `error_category`. Never exposes the API key.
- **Error Categories**:
  - `missing_api_key` - No API key configured
  - `timeout` - Request exceeded 30-second timeout
  - `auth_error` - HTTP 401/403
  - `rate_limited` - HTTP 429
  - `http_error` - Other HTTP errors
  - `request_error` - Network-level failure
  - `invalid_response` - Malformed JSON or missing expected fields
- **Fallback**: If any error occurs, `chat_completion()` returns `None`, and callers (e.g., `Agent._call_llm()`) provide a graceful fallback message.

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

  Sensor Data ──▶ ────▶ Rule-Based Detection ──▶ Alert
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

## Deep Dive: Detection & Correlation Engine

### Rule-Based Detection (`src/analysis/detection.py`)

The detection engine evaluates sensor payloads stored in the scheduler context (e.g., `process_sensor_last`, `network_sensor_last`). For each sensor:

1. Extract the latest payload from context.
2. Compare the relevant metric against `config.DETECTION_THRESHOLDS`.
3. If the threshold is exceeded, construct a description and details dict.
4. Call `storage.log_detection(rule, description, details)` to append to `detections.log`.
5. Append an anomaly dict to the returned list.

**Rules Evaluated**:
- `process_count` - Total running processes
- `open_ports` - Listening TCP/UDP ports
- `file_changes` - Added + modified + removed files in watch window
- `established_connections` - Active network connections
- `external_ips` - Unique external IP addresses contacted
- `memory_percent` / `swap_percent` - RAM/swap usage
- `disk_percent` - Per-mount disk usage
- `failed_logins` / `privilege_escalation` - Authentication events

All thresholds are overridable via environment variables (e.g., `AGENT_THRESHOLD_PROCESS_COUNT`).

### Correlation Engine (`src/analysis/correlation.py`)

The `CorrelationEngine` detects multi-step attack patterns by requiring multiple sensors to trigger within a time window.

**Architecture**:
- **Sensor Cache**: `_sensor_cache` stores the last 100 readings per sensor. Each entry is `{timestamp, data}`.
- **Time Window**: Only data from the last 5 minutes (`config.CORRELATION_WINDOW_MINUTES`) is considered.
- **CorrelationRule**: Defines `pattern` (AttackPattern enum), `required_sensors`, `conditions`, and `severity`.
- **Condition Syntax**: Conditions use operator dicts: `{"gt": 5}`, `{"gte": 90}`, `{"eq": 0}`, `{"ne": 0}`. The engine supports `gt`, `gte`, `lt`, `lte`, `eq`, `ne`.

**Built-in Patterns**:
| Pattern | Required Sensors | Conditions |
|---------|-----------------|------------|
| BRUTE_FORCE | auth_sensor, network_sensor | failed_logins > 5 AND established_count > 10 |
| LATERAL_MOVEMENT | network_sensor, port_sensor, process_sensor | external_ips > 5 AND unusual_ports > 0 AND new_processes > 0 |
| DATA_EXFILTRATION | network_sensor, disk_io_sensor | external_ips > 3 AND bytes_sent > 1MB AND write_rate > 100 |
| PRIVILEGE_ESCALATION | auth_sensor, process_sensor | privilege_escalations > 0 AND elevated_processes > 0 |
| MALWARE | process_sensor, network_sensor | suspicious_processes > 0 AND known_malicious_ips > 0 |
| RESOURCE_EXHAUSTION | memory_sensor, process_sensor | percent_used > 90% AND count > 300 |
| DNS_TUNNELING | dns_sensor, network_sensor | suspicious_domains > 0 AND external_ips > 5 |

**Confidence Scoring**:
- Base confidence = 0.5
- +0.3 if all required sensors have matching data
- Capped at 1.0

When a correlation is detected, the engine writes to `detections.log` with `correlation_id` and returns a `CorrelationEvent`.

### Risk Scoring (`src/utils/agent_state.py`)

`AgentState` calculates a simple additive risk score from three primary sensors:

```
score = 0
if process_count > threshold_process:      score += 2
elif process_count > threshold * 0.8:      score += 1

if port_count > threshold_port:            score += 2
elif port_count > threshold * 0.8:        score += 1

if file_changes > threshold_file:          score += 3
elif file_changes > threshold * 0.8:       score += 1

level = "LOW" if score <= 2 else "MEDIUM" if score <= 5 else "HIGH"
```

This score drives the TUI dashboard top-bar risk display and can be extended with additional sensor weights.

---

## Skills Framework

Skills are **read-only analytical capabilities** that inspect system state and produce structured findings for the LLM. They do not modify the system.

### Skills vs Tools

| Aspect | Skills | Tools |
|--------|--------|-------|
| **Purpose** | Analyze and report | Act and remediate |
| **Side Effects** | None (read-only) | Yes (can kill processes, block IPs, write files) |
| **When Executed** | Automatically during `Agent.analyze()` | Only when explicitly requested (`execute_tools=True` or LLM requests) |
| **Requires Approval** | No | Often yes (see `approval_manager.py`) |
| **Base Class** | `BaseSkill` (`src/agent/skills/base.py`) | `BaseTool` (`src/core/tools/base.py`) |
| **Result Type** | `SkillResult` | `ToolResult` |

### Skill Architecture (`src/agent/skills/`)

**BaseSkill** (`base.py`):
- Abstract base class requiring `metadata` (SkillMetadata) and `execute(context)`.
- Optional hooks: `validate()`, `prepare()`, `cleanup()`, `get_dependencies()`.
- Lazy initialization: heavy imports happen only when the skill is invoked.

**SkillRegistry** (`registry.py`):
- Maintains a mapping of skill names to loader functions.
- `register_loader(name, loader)` adds a skill.
- `execute(name, context)` runs the skill and returns a `SkillResult`.
- `list_skills()` returns metadata for all registered skills.

**SkillResult** (`base.py`):
```python
@dataclass
class SkillResult:
    skill_name: str
    status: SkillStatus      # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
    output: Any              # Structured analysis output
    error: Optional[str]     # Error message if failed
    duration_ms: float       # Execution time
    metadata: dict           # Additional context
    timestamp: str           # ISO-8601 timestamp
```

### Available Skills

| Skill | Category | Description |
|------|----------|-------------|
| `network_analysis` | NETWORK | Analyzes network connections, external IPs, bytes transferred |
| `process_analysis` | PROCESS | Analyzes running processes, CPU/memory per process, suspicious names |
| `memory_analysis` | MEMORY | Analyzes RAM/swap usage, pressure indicators |
| `port_analysis` | NETWORK | Analyzes listening ports, unusual services, port classifications |
| `log_analysis` | LOGS | Analyzes auth logs, system logs for anomalies |
| `security_analysis` | SECURITY | Security posture assessment, privilege escalation detection |
| `system_diagnostics` | SYSTEM | Overall system health summary |

### Skill Execution

```python
context = {"payload": payload, "source": source}
result = skill_registry.execute("network_analysis", context)
```

**Skill Mapping** (`Agent._execute_relevant_skills()`):
The agent maps payload sources to skills automatically:
- `network` → `network_analysis`
- `process` → `process_analysis`
- `memory` → `memory_analysis`
- `port` → `port_analysis`
- `security` / `auth` → `security_analysis`, `log_analysis`
- `diagnostic` → all primary analysis skills
- Unknown source → defaults to `security_analysis`, `system_diagnostics`

---

## Tools Framework

Tools are **remediation actions** that modify system state. They require safety checks and may need human approval before execution.

### Tool Architecture (`src/core/tools/`)

**BaseTool** (`base.py`):
- Abstract base class requiring `descriptor` (ToolDescriptor) and `execute(params)`.
- Safety hooks: `validate()`, `check_safety()`, `enable()`/`disable()`.
- `SafeToolMixin` provides blocked-pattern checking for shell commands.

**ToolDescriptor** (`base.py`):
```python
@dataclass
class ToolDescriptor:
    name: str
    category: ToolCategory
    description: str
    parameters: dict              # Expected parameter schema
    timeout_seconds: int = 30
    requires_confirmation: bool   # If True, approval required
    safe_mode: bool = True        # Restricts dangerous operations
```

**ToolRegistry & Executor** (`registry.py`, `executor.py`):
- `ToolRegistry` stores tool descriptors and instances.
- `ToolExecutor` validates parameters, runs safety checks, and calls `tool.execute()`.
- Tools can be enabled/disabled at runtime.

### Available Tools

| Tool | Description | Safety Considerations |
|------|-------------|----------------------|
| `shell` | Execute shell commands | Blocked patterns prevent `rm -rf /`, `mkfs`, etc. Safe mode restricts destructive commands. |
| `file` | File operations (read, write, list, search) | Write operations require confirmation. Read operations are restricted to known paths. |
| `process` | Process management (list, kill, info) | `kill` requires confirmation and is restricted to non-system processes. |
| `diagnostic` | Run diagnostic collectors | Safe - only reads system state. |

### Tool Execution

```python
result = tool_executor.execute("shell", {"command": "ps aux"})
```

**Approval Workflow**:
1. High-risk tools (`requires_confirmation=True`) create an approval request in `approval_manager.py`.
2. The dashboard displays the request with action preview.
3. User clicks **Approve** or **Deny**.
4. If approved, the tool executes and the result is logged.
5. If denied, a `ToolResult` with status `DENIED` is returned.

**Auto-Response**:
- `config.ENABLE_AUTO_RESPONSE` controls whether approved actions execute automatically.
- `config.AUTO_APPROVE_LOW_RISK` allows low-risk actions to skip approval.
- `config.APPROVAL_REQUIRED_RISK_LEVEL` (default 50) sets the risk score threshold for requiring approval.

---

## Deep Dive: Infrastructure & Utilities

### ThreadPool (`src/utils/threadpool.py`)

`ThreadPool` is a singleton worker pool using double-checked locking for thread-safe initialization.

**Design**:
- **Singleton Pattern**: `ThreadPool.get_instance(num_threads)` ensures one shared pool across the application.
- **Bounded Queue**: Tasks are submitted to a `queue.Queue`. Worker threads block on `queue.get(timeout=0.5)`.
- **Worker Threads**: Non-daemon threads named `ThreadPool-Worker-{i}`. Each runs `_worker_loop()`, catching all exceptions and storing them in `_error_queue`.
- **Active Task Tracking**: `_active_tasks` counter is protected by `_mutex` and incremented/decremented around task execution.
- **Graceful Shutdown**: `shutdown(wait=True)` sets the shutdown flag, injects `None` sentinel values to unblock workers, and joins threads with a 5-second timeout.
- **Error Retrieval**: `get_errors()` drains the error queue for inspection by callers (e.g., the dashboard BACKGROUND TASKS panel).

**Lifecycle**:
```python
pool = init_threadpool(num_threads=8)
pool.submit(my_task)
pool.wait_completion(timeout=30.0)
errors = pool.get_errors()
pool.shutdown(wait=True)
```

### Debug Logger (`src/utils/debug_log.py`)

`DebugLogger` provides structured debug logging independent of Python's standard logging module.

**Features**:
- **Controlled by `config.DEBUG_MODE`**: When `False`, all calls are no-ops with minimal overhead.
- **Output Format**: `[DEBUG] YYYY-MM-DD HH:MM:SS.mmm | CATEGORY | message | {"optional":"json"}`
- **Specialized Methods**:
  - `info(message, data)` - General information
  - `error(message, data)` - Errors
  - `warning(message, data)` - Warnings
  - `sensor(name, message, data)` - Sensor-specific events
  - `task(name, message, data)` - Task execution events
  - `detection(rule, message, data)` - Detection rule triggers
- **File Location**: `.logs/debug.log` (configurable via `AGENT_LOG_DIR`)
- **Failure Handling**: Write failures are caught and printed to stdout but never crash the agent.

### Event Cache & Log Counter (`src/utils/event_cache.py`, `src/utils/log_counter.py`)

**EventCache**:
- In-memory TTL cache of recent events and detections.
- Reduces disk I/O for dashboard refreshes by keeping the last N records in RAM.
- `update(events, detections)` rebuilds the cache from Storage on each refresh cycle.
- TTL defaults to 5 seconds, ensuring stale data is automatically evicted.

**MultiLogCounter**:
- Tracks line counts of multiple log files (events.log, detections.log).
- `register(name, path)` adds a file to watch.
- `update_all()` refreshes counts for all registered files.
- Used by the dashboard to display event totals without reading entire files.

### AgentState (`src/utils/agent_state.py`)

Centralized thread-safe state manager for sensor snapshots:
- **State**: `SensorState` dataclass holds `process`, `port`, `file` dicts and a timestamp.
- **Update Strategy**: `update_from_events()` iterates events newest-first, taking the first match for each sensor type. This ensures the state reflects the most recent data without redundant processing.
- **Locking**: All getters and setters use `self._lock` for thread safety between the scheduler thread and dashboard refresh thread.

---

## Storage & Reports

### Storage Format

Events stored as JSON lines:

```json
{"timestamp": "2024-01-01T12:00:00", "sensor": "process_sensor", "data": {...}}
```

### Report Format

Markdown reports in `src/agent/reports/YYYY-MM-DD/`:

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

## Deep Dive: Dashboards

### TUI Dashboard (`dashboard.py`)

The Textual-based TUI dashboard provides a real-time Security Operations Center (SOC) interface in the terminal.

**Layout** (4-column grid):
- **Top Bar** (column-span 4): Agent name, risk level/color, risk score with trend arrow (↑↓→), CPU%, Mem%, threat count, uptime, refresh counter.
- **Left Panel** (column-span 2): Processes, Network Ports, File Changes, Timeline, Risk Score, Agent Status.
- **Center Panel** (column-span 1): Detections, Incidents, Activity Log, Background Tasks.
- **Right Panel** (column-span 1): Chat, Command Input, Tool Executions, Memory, Autonomous Actions.

**Key Bindings**:
- `r` - Refresh all panels
- `c` - Focus chat input
- `m` - Toggle agent mode (PASSIVE → ACTIVE → AUTONOMOUS)
- `Ctrl+Enter` - Send chat message
- `q` - Quit

**Background Refresh** (`_do_background_refresh()`, every 3 seconds):
1. Fetch recent events/detections from Storage.
2. Update `EventCache` and `AgentState`.
3. Update `MultiLogCounter`.
4. Append recent events to `Timeline`.
5. Update system metrics (CPU/Mem via psutil).
6. Update risk trend window.
7. Re-render all panels.

**Chat System**:
- Commands: `scan`, `status`, `clear`, `help`
- Falls back to LLM chat if OpenRouter API key is configured.
- Context includes last 3 chat messages + current sensor state summary.

**Risk Trend**:
- Maintains a rolling window of risk scores (`config.RISK_TREND_WINDOW`, default 5).
- Compares current score to the average of previous scores to determine trend arrow.

### Web Dashboard (`apps/web/app.py`)

The Flask web dashboard provides a browser-based monitoring interface.

**Routes**:
| Route | Description |
|-------|-------------|
| `/` | Main dashboard with agent workspace and info widgets |
| `/diagnostics` | Sensor collector status and configuration |
| `/monitor` | Real-time system monitor with charts |
| `/reports` | Browse generated Markdown reports by date |
| `/alerts` | Active security alerts with severity filters |
| `/approvals` | Pending action approval queue |
| `/chat` | Interactive chat interface |
| `/docs` | API documentation |
| `/health` | Health check endpoint for load balancers |

**Architecture**:
- **Agent Workspace**: Animated orbital visualization showing agent status and activity.
- **Info Widgets**: Bottom-row cards for Events, Detections, Schedules, and Sensors.
- **Reasoning Panel**: Displays real-time agent reasoning messages streamed from the analysis loop.
- **Schedules Panel**: View/manage scheduled diagnostics with enable/disable toggles.
- **Approvals Panel**: One-click approve/deny buttons for high-risk auto-response actions.
- **Alerts Panel**: Active security alerts with severity coloring and detail expansion.
- **Mobile Layout**: Responsive CSS grid adapts to narrow viewports.

**API Integration**:
- Polls `/api/status` for gateway health and schedule state.
- Fetches `/api/events` and `/api/detections` for live data.
- WebSocket endpoint (port 8001) pushes real-time analysis progress and detection alerts.

**Security**:
- Report paths are validated to prevent directory traversal (`..` blocked).
- LLM health endpoint returns sanitized info without exposing API keys.
- All file reads are confined to `src/agent/reports/`.

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
pytest tests/test_agent_unit.py
pytest tests/test_gateway.py
pytest tests/test_diagnostics.py
pytest tests/test_integration.py
pytest tests/test_core.py
pytest tests/test_analysis.py
```

### Test Coverage Areas

- **Agent** (`tests/test_agent_unit.py`):
  - Session creation, retrieval, and expiration
  - Context updates and payload aggregation
  - Memory store, retrieve, search, and TTL eviction
  - Skill registration and execution with mocked LLM
  - Report generation and redaction of sensitive keys
  - Tool execution and error handling

- **Gateway** (`tests/test_gateway.py`):
  - Schedule add/remove/enable/disable
  - Autonomous loop timing and `should_run()` logic
  - Payload sender retry logic and async transmission
  - HTTP handler route registration and request parsing
  - WebSocket handler connection lifecycle

- **Diagnostics** (`tests/test_diagnostics.py`):
  - Process sensor with mocked psutil and fallback to `ps`/`tasklist`
  - Port sensor connection state parsing
  - File sensor change detection
  - Network sensor external IP extraction
  - Memory sensor percentage calculations

- **Analysis** (`tests/test_analysis.py`):
  - Detection rule threshold evaluation
  - Statistical anomaly Z-score and rolling mean
  - Correlation engine pattern matching and confidence scoring
  - Risk score calculation and level assignment

- **Core** (`tests/test_core.py`):
  - Storage JSONL append and read operations
  - OpenRouter client error categorization and health reporting
  - Tool registry and executor validation

- **Integration** (`tests/test_integration.py`):
  - End-to-end flow: sensor → schedule → detection → alert → storage
  - Dashboard API endpoints and report retrieval
  - ThreadPool task submission and error capture

- **ThreadPool** (`tests/test_threadpool.py`):
  - Singleton initialization and double-checked locking
  - Task submission and completion
  - Exception capture in worker threads
  - Graceful shutdown and cleanup

- **Config** (`tests/test_config.py`):
  - Environment variable overrides
  - Threshold validation and default values
  - Log directory creation and fallback behavior

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
| No sensors responding | Check `psutil` is installed (`pip install psutil`). Without it, sensors fall back to shell commands with reduced fidelity. |
| LLM analysis fails | Verify `OPENROUTER_API_KEY` is set. Check `debug.log` for error category (`auth_error`, `rate_limited`, `timeout`). |
| High memory usage | Reduce `POLL_INTERVALS` or disable high-frequency sensors (`file_sensor`, `auth_sensor`). Reduce `AGENT_MEMORY_MAX_ENTRIES`. |
| Detection not triggering | Check `DETECTION_THRESHOLDS` in `config.py`. Verify sensors are writing to `events.log`. Check `detections.log` for existing alerts. |
| WebSocket not connecting | Verify port 8001 is not blocked by firewall. Check if another process is bound to port 8001 (`lsof -i :8001` or `netstat`). |
| Reports not generating | Ensure `src/agent/reports/` directory exists and is writable. Check `debug.log` for OSError during report generation. |
| Dashboard shows stale data | Press `r` in TUI to force refresh. For web dashboard, verify the `/api/status` endpoint is reachable. |
| ThreadPool errors | Check `debug.log` for `THREADPOOL_ERROR`. Ensure `init_threadpool()` was called before submitting tasks. |
| Schedule not running | Verify schedule is `enabled` via `/schedules` API. Check that the sensor module exists in `src/diagnostics/` and has a `collect()` function. |

### Logs

All logs are stored in `AGENT_LOG_DIR` (default `./.logs`):

- **`events.log`** - Sensor events (JSONL format, one JSON object per line)
- **`detections.log`** - Detection alerts and correlation events (JSONL format)
- **`debug.log`** - Structured debug output from all components (human-readable with timestamps)

**Reading Events with jq**:
```bash
# Get last 10 events
jq -s '.[-10:]' .logs/events.log

# Filter by sensor
jq 'select(.sensor == "process_sensor")' .logs/events.log

# Get last 5 detections
jq -s '.[-5:]' .logs/detections.log
```

**Log Rotation**: The storage layer appends indefinitely. For production deployments, configure log rotation (e.g., `logrotate` on Linux) or adjust `TIMELINE_MAX_EVENTS` to limit in-memory retention.

---

*Last Updated: 2026-04-24*