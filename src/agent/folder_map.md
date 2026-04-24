# Directory: src/agent

The intelligence layer of Phantom. Manages LLM analysis, session context, memory, skills, and report generation.

| File / Folder | Purpose |
| --- | --- |
| `agent.py` | Core Agent class with analysis loop, skill/tool execution, LLM prompting, report generation, and memory updates |
| `context.py` | SessionContext and ContextManager - manages per-session payload history, findings, and TTL-based cleanup |
| `memory.py` | SessionMemory and SessionMemoryEntry - key-value memory with TTL, tags, search, and optional JSON persistence |
| `reports_storage.py` | ReportStorage - saves/retrieves Markdown reports with metadata to `reports/YYYY-MM-DD/` |
| `system_prompt.md` | Single system prompt used when calling the LLM for security analysis |
| `skills/` | Skill implementations (network, process, memory, port, log, security, system diagnostics) |
| `reports/` | Runtime generated reports organized by date (`YYYY-MM-DD/`) |

## Key Concepts

- **Session**: An analysis cycle identified by UUID. Holds all payloads, findings, and metadata.
- **ContextManager**: Thread-safe session registry with automatic eviction when max_sessions (100) or timeout (3600s) exceeded.
- **SessionMemory**: Key-value store with TTL, tag-based search, and optional file persistence. Max 500 entries.
- **Agent.analyze()**: The main 8-step flow: receive payload → update context → fetch memory → execute skills → execute tools → build prompt → call LLM → generate report → update memory.
- **Redaction**: `_redact_value()` recursively scrubs sensitive keys (password, token, api_key, etc.) before persisting payloads.
