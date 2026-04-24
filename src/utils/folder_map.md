# Directory: src/utils

Shared utilities supporting the agent, dashboard, and gateway.

| File | Purpose |
| --- | --- |
| `debug_log.py` | DebugLogger - singleton structured debug logger writing to `.logs/debug.log`. Categories: INFO, ERROR, WARNING, SENSOR, TASK, DETECTION |
| `threadpool.py` | ThreadPool - singleton worker pool with mutex-protected state, exception capture, and graceful shutdown |
| `agent_state.py` | AgentState - thread-safe sensor snapshot manager with risk calculation (0-2 LOW, 3-5 MEDIUM, 6+ HIGH) |
| `event_cache.py` | EventCache - in-memory TTL cache of recent events and detections for fast dashboard queries |
| `log_counter.py` | MultiLogCounter - tracks line counts of multiple log files for dashboard statistics |
| `timeline.py` | Timeline - ordered event history with severity levels and threat counting |
| `memory.py` | AgentMemory - lightweight in-memory key-value store for dashboard/agent communication |
| `tool_executor.py` | ToolLogger - logs tool executions with timestamps and status for dashboard display |
| `system_scanner.py` | System scanner for dashboard chat commands (`scan`, `status`) |
| `datetime_utils.py` | UTC timestamp helpers |
| `installer.py` | Environment setup and dependency installer |

## Key Concepts

- **ThreadPool Singleton**: `ThreadPool.get_instance()` uses double-checked locking. Workers are non-daemon threads that process tasks from a bounded queue.
- **Debug Logger**: Controlled by `config.DEBUG_MODE`. Writes ISO timestamps + category + message + optional JSON data.
- **Risk Scoring**: AgentState calculates risk from process count, open ports, and file changes against configurable thresholds.
- **Event Cache**: Reduces disk I/O for dashboard refreshes by keeping the last N events/detections in memory with a TTL.
