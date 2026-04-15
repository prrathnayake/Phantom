# Daily Summary

Rolling state for the current working day.

## Active Tasks
- None currently

## Recent Completions
- Added BACKGROUND TASKS panel to TUI dashboard for monitoring active/pending threadpool tasks and debug logs
- Added debug logging throughout codebase (sensors, core, analysis, skills, utils)
- Fixed config: changed WATCH_DIRECTORY to project folder, added .logs/ to gitignore
- Created DebugLogger class (utils/debug_log.py) with sensor(), task(), detection() methods
- Major performance optimization: LogCounter, EventCache, AgentState, ThreadPool async refresh, OpenRouter chat, risk score
- Created singleton ThreadPool (utils/threadpool.py) with mutex-based error handling, worker queue, exception catching, graceful shutdown
- Created TUI dashboard (dashboard.py) using Textual library
- Fixed logs folder to use local ./logs/ instead of C:\Users\cybor\agent_logs
- Fixed Textual method naming conflict (refresh -> refresh_detections/refresh_events)
- Committed all changes to git

## Blockers
- None

## Notes
- Dashboard and agent both write to same local logs folder
- Press R to refresh dashboard, Q to quit
- Agent runs via: python -m main
- Dashboard runs via: python -m dashboard
