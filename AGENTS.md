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

## Architecture & Entrypoints

The repo has multiple independent entrypoints. Do not confuse them:

- **`python main.py`** — Runs the full stack locally: Gateway (HTTP 8000, WS 8001) + Agent + auto-starts Flask web dashboard (port 5000) as a subprocess.
- **`python dashboard.py`** — Textual TUI dashboard (SOC console). Imports from `core.*` and `utils.*` directly (not `src.*`) because it adds repo root to `sys.path`.
- **`python -m flask --app apps.web.app:create_app run`** — Flask web dashboard standalone. Factory is `apps.web.app:create_app`.
- **`python -m cli`** — Application CLI (not the Docker helper).
- **`python -m main`** — Docker container entrypoint (used by `docker/Dockerfile`).

## Build, Setup, and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full stack locally (agent + gateway + web dashboard)
python main.py

# Run TUI dashboard standalone
python dashboard.py

# Run web dashboard standalone
python -m flask --app apps.web.app:create_app run --host 0.0.0.0 --port 5000

# Run application CLI
python -m cli

# Run tests
pytest tests/
# Run a specific test file
pytest tests/test_agent_unit.py
```

## Docker Management

Compose file is at `docker/docker-compose.yml`; Dockerfile is at `docker/Dockerfile`. Use the `./phantom` helper (not `docker compose` directly) for consistency:

```bash
./phantom start              # Start all containers
./phantom start --wait       # Start and block until healthy
./phantom stop               # Stop containers
./phantom status             # Show status
./phantom restart [service]  # Restart service (or all)
./phantom logs [service]     # View logs (default: agent)
./phantom follow [service]   # Follow logs
./phantom exec service cmd   # Execute in container
./phantom shell [service]    # Interactive shell (default: agent)
./phantom health             # Health check all services
./phantom clean              # Remove containers & volumes
```

## Configuration & Environment

- `config.py` loads `.env` via `python-dotenv` at import time. Any env var prefixed in `config.py` can override defaults.
- `OPENROUTER_API_KEY` is required for LLM features but the system degrades gracefully without it (local fallback summaries are used).
- `AGENT_LOG_DIR` defaults to `./.logs`; falls back to a temp dir if the path is read-only.

## Testing Quirks

- **No `pytest.ini`, `setup.cfg`, or `pyproject.toml`** — pytest discovers from `tests/` with default settings.
- **Import path inconsistency across tests**: Some test files import `from agent.context` (no `src` prefix) while others use `from src.agent.context`. `conftest.py` adds both the repo root and `src/` to `sys.path`, but individual test files also manipulate `sys.path`. If adding new tests, prefer `from src.agent...` to avoid ambiguity.
- `tests/conftest.py` provides `temp_dir`, `mock_context`, and `sample_snapshot` fixtures.
- 144 tests passing as of last project state. Run the full suite before claiming done.

## Project Structure & Boundaries

```
src/
  agent/           # Intelligence layer (LLM loop, context, memory, reports)
  gateway/         # I/O + scheduler; dynamically imports any `src/diagnostics/*.py` with `collect(context)`
  diagnostics/     # Sensor collectors (zero-registration: drop a file with `collect()` and the scheduler picks it up)
  analysis/        # Detection engine, alert/approval/response managers
  core/            # Storage, OpenRouterClient, tool registry/executor
  integrations/    # Slack, Teams, PagerDuty, SIEM, ELK, CloudWatch clients
  utils/           # ThreadPool, timeline, event cache, agent state
  skills/          # Legacy skills (risk_assessment, vulnerability_check)

apps/web/          # Flask dashboard templates + routes
cli/               # Application CLI (not the `./phantom` Docker helper)
tests/             # Test suite
```

## Code Conventions

- Preserve useful comments/docstrings; do not add noisy comments for obvious code.
- All storage, sensor, and external API calls fail silently and log to `debug.log` (see `src/utils/debug_log.py`). Do not introduce crash-on-failure behavior in those boundaries.
- When adding a new diagnostic sensor, expose `collect(context)` in `src/diagnostics/<name>_sensor.py`; no registry edit is required.
- Update `.codex_memories/project_state.md` when completing substantial work.

## Documentation Sync Expectations

- Update local docs when architecture or workflow changes.
- Keep docs aligned with meaningful code changes.
