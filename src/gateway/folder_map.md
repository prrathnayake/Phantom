# Directory: src/gateway

Input gateway and scheduler. Receives data from multiple interfaces and autonomously runs diagnostic schedules.

| File / Folder | Purpose |
| --- | --- |
| `server.py` | Main gateway server entry point - binds HTTP and WebSocket handlers |
| `schedule_manager.py` | ScheduleManager - autonomous cron-like scheduler that imports sensor `collect()` functions and runs them at configured intervals |
| `payload_sender.py` | PayloadSender - transmits diagnostic payloads to the Agent endpoint with retry logic, batching, and async support |
| `interfaces/` | Input interface handlers (HTTP, WebSocket, CLI, Queue, File) |
| `triggers/` | Additional trigger implementations for event-driven execution |

## Key Concepts

- **Schedule**: A dataclass holding `name`, `interval`, `script_module`, `func`, `next_run`, `enabled`, and `last_result`. Determines if it should run via `should_run()`.
- **Autonomous Loop**: `run_autonomous()` sleeps in 1-second increments and calls `run_all_due()` to execute any schedules whose `next_run` has passed.
- **Notification System**: `SCHEDULE_NOTIFICATIONS` callback registry allows external components (e.g., dashboard) to receive run results via `on_schedule_run()`.
- **Dynamic Import**: `add_schedule()` dynamically imports `src.diagnostics.{script_module}` and binds its `collect()` function.
- **Thread Safety**: All schedule mutations use a `threading.Lock`.
