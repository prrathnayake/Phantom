# Project Architecture

_(This file is for the coding agent. It contains the architecture of the actual project being built.)_

## Application Stack
- Frontend: Textual TUI (terminal-based)
- Backend: Python (scheduled tasks, sensors, detection)
- Database: JSON file storage (events.log, detections.log)

## Structural Logic

```
                    ┌─────────────┐
                    │   main.py   │
                    │ (scheduler) │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
    │sensors │       │analysis │      │ skills  │
    │-process│       │-detect  │      │-risk    │
    │-port   │       │-summarise│      │-vuln    │
    │-file   │       └──────────┘      └─────────┘
    └────┬────┘
         │
    ┌────▼────┐
    │ storage │
    │ (logs)  │
    └────┬────┘
         │
    ┌────▼────┐
    │dashboard│ (separate process, reads logs)
    │ (TUI)   │
    └─────────┘
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point, wires scheduler, registers tasks |
| `core/scheduler.py` | Runs tasks at configured intervals |
| `core/storage.py` | Writes JSON events/detections to log files |
| `core/openrouter_client.py` | LLM API wrapper |
| `sensors/` | Collect system telemetry |
| `analysis/detection.py` | Rule-based anomaly detection |
| `skills/` | High-level tasks (risk assessment, vulnerability check) |
| `dashboard.py` | TUI application displaying real-time data |
