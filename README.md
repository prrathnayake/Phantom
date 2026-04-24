# Phantom - AI Agentic Harness System

A centralized security monitoring system with Gateway + Agent architecture.

## Architecture

```
                    ┌─────────────────────────────┐
                    │         GATEWAY              │
                    │  ┌─────────────────────┐  │
                    │  │  Input Interfaces   │  │
                    │  │ HTTP | CLI | Queue   │  │
                    │  │ File | WebSocket   │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  Schedule Manager    │  │
                    │  │  (autonomous runs)   │  │
                    │  └─────────────────────┘  │
                    └──────────────┬──────────────┘
                                   │ Payload
                                   ▼
                    ┌─────────────────────────────┐
                    │      CENTRAL AGENT           │
                    │  ┌─────────────────────┐    │
                    │  │  System Prompt      │    │
                    │  │  Context Manager   │    │
                    │  │  Memory Manager    │    │
                    │  └─────────────────────┘    │
                    │  ┌─────────────────────┐    │
                    │  │  Analysis Loop      │    │
                    │  │  (LLM powered)      │    │
                    │  └─────────────────────┘    │
                    │  ┌─────────────────────┐    │
                    │  │  Reports Storage   │    │
                    │  └─────────────────────┘    │
                    └─────────────────────────────┘
```

## Directory Layout

```
Phantom/
├── main.py              # Entry point
├── config.py           # Configuration
├── dashboard.py        # TUI dashboard (Textual)
├── cli/                # CLI tools
├── apps/web/           # Flask web dashboard
├── src/                # Backend source code
│   ├── agent/  # Intelligence
│   │   ├── system_prompt.md
│   │   ├── context.py      # Session context manager
│   │   ├── memory.py       # Session memory with TTL
│   │   ├── agent.py        # Agent with LLM loop
│   │   ├── reports_storage.py
│   │   ├── reports/        # Generated reports (YYYY-MM-DD/)
│   │   └── skills/         # Agent skills
│   ├── gateway/        # Input interfaces + scheduler
│   │   ├── server.py
│   │   ├── schedule_manager.py
│   │   ├── payload_sender.py
│   │   └── interfaces/     # HTTP, CLI, Queue, File, WebSocket
│   ├── diagnostics/    # Diagnostic collectors
│   │   ├── process_sensor.py
│   │   ├── port_sensor.py
│   │   ├── file_sensor.py
│   │   ├── network_sensor.py
│   │   ├── memory_sensor.py
│   │   ├── auth_sensor.py
│   │   └── ...
│   ├── analysis/       # Detection engine
│   │   ├── detection.py
│   │   ├── alert_manager.py
│   │   ├── correlation.py
│   │   ├── trends.py
│   │   └── summariser.py
│   ├── core/           # Framework components
│   │   ├── storage.py
│   │   ├── openrouter_client.py
│   │   └── tools/
│   ├── integrations/   # External service clients
│   └── utils/          # Utilities
├── tests/              # Test suite
└── docs/               # Documentation
```

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python main.py
```

## Docker Stack

The system can run as a full Docker Compose stack with all dependencies:

```bash
# Start all containers
./phantom start

# Check status
./phantom status

# View logs
./phantom logs agent
./phantom logs dashboard

# Stop all containers
./phantom stop
```

### Available Services

| Service | Port | Description |
|---------|------|-------------|
| `agent` | 8000 | Main Phantom AI Agent |
| `dashboard` | 5000 | Flask Web Dashboard |
| `tui` | - | Textual TUI Dashboard |
| `redis` | 6379 | Cache & Messaging |
| `postgres` | 5432 | Database |
| `elasticsearch` | 9200 | Log Storage |
| `kibana` | 5601 | Log Visualization |

### CLI Commands

```bash
./phantom start              # Start all containers
./phantom stop               # Stop all containers
./phantom status             # Show container status
./phantom restart [service]  # Restart all or specific service
./phantom logs [service]     # Show logs (default: agent)
./phantom logs-follow        # Follow logs in real-time
./phantom ps                 # Show running services
./phantom build              # Rebuild containers
./phantom clean              # Remove containers and volumes
./phantom exec service cmd # Execute command in container
./phantom help              # Show help
```

### Environment Setup

Copy `.env.docker` to `.env` and configure:
- `OPENROUTER_API_KEY` - LLM API key (required for AI features)
- `POSTGRES_PASSWORD` - Database password
- `ELASTIC_PASSWORD` - Elasticsearch password

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | LLM API key (optional) |
| `AGENT_LOG_DIR` | `./.logs` | Log directory |

## Testing

```bash
# Run the agent
python main.py

# Run the TUI dashboard
python dashboard.py
```

## Reports

Generated reports stored in:
```
src/agent/reports/YYYY-MM-DD/report_{session_id}_YYYYMMDD_HHMMSS.md
```

## Key Features

- **Context Management**: Session-based context with TTL
- **Memory Management**: Session memory with tag-based search
- **Autonomous Scheduling**: Diagnostic runs at configured intervals
- **Multiple Interfaces**: HTTP (8000), CLI, Redis/RabbitMQ, File triggers, WebSocket (8001)
- **LLM Analysis**: Single LLM loop for security analysis
- **Report Generation**: Markdown reports with metadata
- **Schedule Notifications**: Callbacks for schedule run events
- **Real-time Dashboard**: Web UI with agent reasoning panel

## Web Dashboard

The Flask web dashboard provides real-time monitoring:

```
http://localhost:5000
```

### Dashboard Features

- **Agent Workspace**: Animated orbital view with agent status
- **Info Widgets**: Events, Detections, Schedules, Sensors (bottom row)
- **Reasoning Panel**: Real-time agent reasoning messages
- **Schedules Panel**: View/manage scheduled diagnostics
- **Approvals Panel**: Pending action approvals
- **Alerts Panel**: Active security alerts

### Routes

| Route | Description |
|-------|-------------|
| `/` | Main dashboard |
| `/diagnostics` | Diagnostic collectors view |
| `/monitor` | System monitor |
| `/reports` | Generated reports |
| `/alerts` | Alert management |
| `/approvals` | Approval queue |
| `/docs` | API documentation |

## API Endpoints

### HTTP (port 8000)
- `POST /analyze` - Submit payload for analysis
- `GET /schedules` - Get schedule status
- `POST /schedules/{name}/run` - Run specific schedule
- `GET /status` - Gateway status

### WebSocket (port 8001)
Real-time analysis updates and notifications.