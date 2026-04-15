# Project State & Active Context

Stable facts and active threads for this project.

## STABLE FACTS
project_name: "SMA - Secure Monitoring Agent"
project_focus: "System Monitoring Agent - local security and telemetry collection"
architecture: "Python-based agent with sensors (process, port, file), detection engine, TUI dashboard"

## ACTIVE CONTEXT
active_threads: {
  "threadpool": "created, singleton with mutex, available for parallel task execution",
  "tui_dashboard": "working, displays sensor data and detections",
  "agent_core": "working, sensors collect and write to local logs folder",
  "logs_folder": "using ./logs/ instead of C:\\Users\\cybor\\agent_logs"
}

## NOTES
- Uses Textual for TUI dashboard
- Logs stored in `agents/001_monitoring/logs/`
- Sensors: process_sensor, port_sensor, file_sensor
- Detection rules: process_count, open_ports, file_changes
- Skills: risk_assessment, vulnerability_check (LLM-powered)
