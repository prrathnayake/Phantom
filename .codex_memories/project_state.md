# Project State & Active Context

Stable facts and active threads for this project.

## STABLE FACTS
project_name: "Phantom - AI Agentic Harness System"
project_focus: "Centralized security monitoring with Gateway + Central Agent architecture"
architecture: "Gateway (Input Interfaces + Schedule Manager) + Central Agent (LLM Analysis) + Diagnostics"

## ACTIVE CONTEXT
active_threads: {
  "gateway": "working, input interfaces (HTTP/CLI/Queue/File/WS) + autonomous schedule manager",
  "central_agent": "working, LLM analysis loop with context/memory management",
  "diagnostics": "working, process/port/file sensors",
  "reports": "stored in central_agent/reports/YYYY-MM-DD/",
  "tests": "135 tests passing"
}

## ARCHITECTURE COMPONENTS
- Gateway: Input interfaces + Schedule Manager
- Central Agent: Single LLM analysis loop + Context Manager + Session Memory + Reports
- Diagnostics: process_sensor, port_sensor, file_sensor
- Detection: rules in analysis/detection.py
- Skills: risk_assessment, vulnerability_check (LLM-powered)

## DIRECTORIES
- src/central_agent/ - Central intelligence
- src/gateway/ - Input interfaces + scheduler
- src/diagnostics/ - Diagnostic collectors
- src/analysis/ - Detection engine
- src/skills/ - Agent skills
- src/core/ - Storage + OpenRouterClient
- src/integrations/ - External service clients
- src/utils/ - Utilities
- central_agent/reports/ - Runtime reports (root level)
- apps/web/ - Flask dashboard
- cli/ - CLI tools