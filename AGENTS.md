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

**Project**: Phantom - AI Agentic Harness System
**Focus**: Centralized security monitoring with Gateway + Agent architecture

## Project Structure & Important Directories

```
src/
  central_agent/     # Central intelligence (LLM analysis loop)
    system_prompt.md  # Single system prompt
    context.py      # Session context manager
    memory.py       # Session memory with TTL
    agent.py        # Agent with LLM loop
    skills/         # Skill implementations
  gateway/          # Input interfaces + schedule manager
    schedule_manager.py  # Autonomous diagnostic runs
    payload_sender.py   # Sends payloads to Agent
    interfaces/     # HTTP, CLI, Queue, File, WebSocket
  diagnostics/      # Diagnostic collectors
  analysis/         # Detection engine
  core/             # Storage + OpenRouterClient + Tools
  integrations/     # External service clients
  utils/            # Utilities
  skills/           # Legacy agent skills

central_agent/      # Runtime data (kept at root)
  reports/          # Generated reports (YYYY-MM-DD/)

tests/              # Test suite
apps/web/           # Flask web dashboard
cli/                # CLI tools
```

## Build, Setup, and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent (local)
python main.py

# Run with Docker
./phantom start        # Start all containers
./phantom status     # Check status
./phantom stop       # Stop containers

# Run tests
pytest tests/
```

## Docker Management

Use `./phantom` CLI for container management:

```bash
./phantom start              # Start containers
./phantom stop               # Stop containers
./phantom status             # Show status
./phantom restart [service]  # Restart service
./phantom logs [service]     # View logs
./phantom logs-follow        # Follow logs
./phantom exec service cmd # Execute in container
./phantom clean              # Remove containers & volumes
```

## Testing Commands & Conventions

- Preferred test root: `tests/`
- Test Agent: `tests/test_central_agent.py`
- Test Gateway: `tests/test_gateway.py`
- Test Diagnostics: `tests/test_diagnostics.py`
- Test Integration: `tests/test_integration.py`
- Test Core: `tests/test_core.py`
- Test Analysis: `tests/test_analysis.py`
- Test ThreadPool: `tests/test_threadpool.py`
- Test Config: `tests/test_config.py`

## Comments & Docstrings

- Preserve useful comments/docstrings where they help future readers
- Do not add noisy comments for obvious code

## Documentation Sync Expectations

- Update local docs when architecture or workflow changes
- Keep docs aligned with meaningful code changes