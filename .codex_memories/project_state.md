# Project State & Active Context

Stable facts and active threads for this project.

## STABLE FACTS
project_name: "SMA - Secure Monitoring Agent"
project_focus: "System Monitoring Agent - local security and telemetry collection"
architecture: "Python-based agent with sensors (process, port, file), detection engine, TUI dashboard"

## ACTIVE CONTEXT
active_threads: {
  "threadpool": "created, singleton with 8 threads, available for parallel task execution",
  "soc_dashboard": "Full SOC TUI: Top Bar, Left (Process/Ports/Files/Timeline/Risk), Center (Detections/Incidents/Activity), Right (Chat/Tools/Memory/Actions)",
  "agent_core": "working, sensors collect and write to local logs folder",
  "logs_folder": "using ./logs/ instead of C:\\Users\\cybor\\agent_logs",
  "timeline": "attack flow visualization with persistence",
  "memory": "agent knowledge storage with TTL",
  "tool_executor": "tool execution logging with persistence"
}

## NOTES
- Uses Textual for TUI dashboard
- Logs stored in `agents/001_monitoring/logs/`
- Sensors: process_sensor, port_sensor, file_sensor
- Detection rules: process_count, open_ports, file_changes
- Skills: risk_assessment, vulnerability_check (LLM-powered)
