# Project State & Active Context

Stable facts and active threads for this project.

## STABLE FACTS
project_name: "Suraksha - Secure Monitoring Agent"
project_focus: "Centralized security monitoring with Gateway + Central Agent architecture"
architecture: "Gateway (Input Interfaces + Schedule Manager) + Central Agent (LLM Analysis) + Diagnostics"

## ACTIVE CONTEXT
active_threads: {
  "gateway": "working, input interfaces (HTTP/CLI/Queue/File/WS) + autonomous schedule manager",
  "central_agent": "working, LLM analysis loop with context/memory management",
  "diagnostics": "working, process/port/file sensors",
  "reports": "stored in central_agent/reports/YYYY-MM-DD/",
  "tests": "123 tests passing"
}

## ARCHITECTURE COMPONENTS
- Gateway: Input interfaces + Schedule Manager
- Central Agent: Single LLM analysis loop + Context Manager + Session Memory + Reports
- Diagnostics: process_sensor, port_sensor, file_sensor
- Detection: rules in analysis/detection.py
- Skills: risk_assessment, vulnerability_check (LLM-powered)

## DIRECTORIES
- central_agent/ - Central intelligence
- gateway/ - Input interfaces + scheduler
- diagnostics/ - Diagnostic collectors
- analysis/ - Detection engine
- skills/ - Agent skills
- core/ - Storage + OpenRouterClient
- utils/ - Utilities