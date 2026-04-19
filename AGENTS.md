# Repository Guidelines

## Agent Memory Entrypoint

Before doing substantive work, always read these in order:

1. `.codex_memories/_agent_rules.md`
2. `.codex_memories/project_state.md`
3. `.codex_memories/system_prompt.md`
4. `.codex_memories/daily_summary.md`
5. `.codex_memories/YYYY-MM-DD/revival_summary.md`
6. `.codex_memories/YYYY-MM-DD/task_log.md`

Write all reusable session memory only under `.codex_memories/`.
Do not create or use any alternate memory root.

## Project Identity

**Project**: Suraksha - Secure Monitoring Agent
**Focus**: Centralized security monitoring with Gateway + Central Agent architecture

## Project Structure & Important Directories

```
central_agent/     # Central intelligence (LLM analysis loop)
  system_prompt.md  # Single system prompt
  context.py      # Session context manager
  memory.py       # Session memory with TTL
  agent.py        # Central Agent with LLM loop
  reports/        # Generated reports (YYYY-MM-DD/)

gateway/          # Input interfaces + schedule manager
  schedule_manager.py  # Autonomous diagnostic runs
  payload_sender.py   # Sends payloads to Central Agent
  interfaces/     # HTTP, CLI, Queue, File, WebSocket

diagnostics/      # Diagnostic collectors
```

## Build, Setup, and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python main.py

# Run tests
pytest tests/
```

## Testing Commands & Conventions

- Preferred test root: `tests/`
- Test Central Agent: `tests/test_central_agent.py`
- Test Gateway: `tests/test_gateway.py`
- Test Diagnostics: `tests/test_diagnostics.py`
- Test Integration: `tests/test_integration.py`
- Test Core: `tests/test_core.py`

## Comments & Docstrings

- Preserve useful comments/docstrings where they help future readers
- Do not add noisy comments for obvious code

## Documentation Sync Expectations

- Update local docs when architecture or workflow changes
- Keep docs aligned with meaningful code changes