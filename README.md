# Phantom - AI Agentic Harness System

A centralized security monitoring system with Gateway + Central Agent architecture.

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
suraksha/
├── main.py              # Entry point
├── config.py           # Configuration
├── central_agent/      # Central intelligence
│   ├── __init__.py
│   ├── system_prompt.md
│   ├── context.py     # Session context manager
│   ├── memory.py     # Session memory with TTL
│   ├── agent.py      # Central Agent with LLM loop
│   ├── reports_storage.py
│   └── reports/      # Generated reports
├── gateway/           # Input interfaces + scheduler
│   ├── __init__.py
│   ├── server.py
│   ├── schedule_manager.py
│   ├── payload_sender.py
│   └── interfaces/  # HTTP, CLI, Queue, File, WebSocket
├── diagnostics/      # Diagnostic collectors
│   ├── __init__.py
│   ├── process_sensor.py
│   ├── port_sensor.py
│   └── file_sensor.py
├── analysis/         # Detection engine
│   ├── __init__.py
│   ├── detection.py
│   └── summariser.py
├── skills/           # Agent skills
│   ├── __init__.py
│   ├── risk_assessment.py
│   └── vulnerability_check.py
├── core/            # Framework components
│   ├── __init__.py
│   ├── storage.py
│   └── openrouter_client.py
└── utils/          # Utilities
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python main.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | LLM API key (optional) |
| `AGENT_LOG_DIR` | `./.logs` | Log directory |

## Testing

```bash
# Run all tests
pytest tests/
```

## Reports

Generated reports stored in:
```
central_agent/reports/YYYY-MM-DD/report_{session_id}_{timestamp}.md
```

## Key Features

- **Context Management**: Session-based context with TTL
- **Memory Management**: Session memory with tag-based search
- **Autonomous Scheduling**: Diagnostic runs at configured intervals
- **Multiple Interfaces**: HTTP (8000), CLI, Redis/RabbitMQ, File triggers, WebSocket (8001)
- **LLM Analysis**: Single LLM loop for security analysis
- **Report Generation**: Markdown reports with metadata

## API Endpoints

### HTTP (port 8000)
- `POST /analyze` - Submit payload for analysis
- `GET /schedules` - Get schedule status
- `POST /schedules/{name}/run` - Run specific schedule
- `GET /status` - Gateway status

### WebSocket (port 8001)
Real-time analysis updates and notifications.