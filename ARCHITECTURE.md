# Project Architecture

## Overview

Suraksha uses a **Gateway + Central Agent** architecture for centralized security monitoring.

## Components

### 1. Gateway

Handles input interfaces and scheduled diagnostic runs.

**Location**: `gateway/`

| Module | Description |
|--------|-------------|
| `schedule_manager.py` | Autonomous diagnostic scheduling |
| `payload_sender.py` | Sends payloads to Central Agent |
| `server.py` | Main Gateway server |
| `interfaces/http_handler.py` | REST API (port 8000) |
| `interfaces/cli_handler.py` | CLI commands |
| `interfaces/queue_handler.py` | Redis/RabbitMQ consumer |
| `interfaces/file_trigger.py` | Drop folder monitoring |
| `interfaces/websocket_handler.py` | Real-time updates (port 8001) |

### 2. Central Agent

The central intelligence layer with single LLM analysis loop.

**Location**: `central_agent/`

| Module | Description |
|--------|-------------|
| `system_prompt.md` | Single system prompt |
| `context.py` | Session context manager |
| `memory.py` | Session memory with TTL |
| `agent.py` | Central Agent with LLM loop |
| `reports_storage.py` | Report storage/retrieval |
| `reports/` | Generated reports |

### 3. Diagnostics

Diagnostic collectors.

**Location**: `diagnostics/`

| Module | Description |
|--------|-------------|
| `process_sensor.py` | Process monitoring |
| `port_sensor.py` | Network port monitoring |
| `file_sensor.py` | File system monitoring |

## Data Flow

```
1. Schedule Manager runs diagnostics autonomously
   ↓
2. Results collected as payloads
   ↓
3. Payload sent to Central Agent
   ↓
4. Session context created/updated
   ↓
5. Analysis loop runs LLM with context + memory
   ↓
6. Report generated and stored
   ↓
7. Session memory updated with findings
```

## Session Lifecycle

```
create_session() → update_context() → analyze() → generate_report() → clear_session()
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | LLM API key |
| `OPENROUTER_MODEL` | `openrouter-gpt-3.5-turbo` | LLM model |
| `AGENT_LOG_DIR` | `./.logs` | Log directory |
| `AGENT_THRESHOLD_PROCESS_COUNT` | `250` | Process threshold |
| `AGENT_THRESHOLD_OPEN_PORTS` | `50` | Port threshold |
| `AGENT_THRESHOLD_FILE_CHANGES` | `100` | File threshold |

## API Endpoints

### HTTP (port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Submit payload for analysis |
| `/schedules` | GET | Get schedule status |
| `/schedules/{name}/run` | POST | Run specific schedule |
| `/status` | GET | Gateway status |
| `/trigger/{skill}` | POST | Trigger skill |

### WebSocket (port 8001)

Real-time analysis updates and notifications.

## Testing

```bash
# All tests
pytest tests/ -v

# Test suites
pytest tests/test_central_agent.py   # Central Agent tests
pytest tests/test_gateway.py       # Gateway tests
pytest tests/test_diagnostics.py # Diagnostics tests
pytest tests/test_integration.py   # Integration tests
pytest tests/test_core.py         # Core module tests
```