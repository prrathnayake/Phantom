# Directory: apps/web

Flask web dashboard for the Phantom monitoring system.

| File / Folder | Purpose |
| --- | --- |
| `app.py` | Flask application factory (`create_app()`). Defines all page routes, API endpoints, chat system, and initialization logic |
| `templates/base.html` | Base layout template with sidebar navigation, chat widget, and responsive grid |
| `templates/index.html` | Main dashboard with agent workspace, info widgets, and reasoning panel |
| `templates/diagnostics.html` | Diagnostics runner page with sensor grid, manual execution, and schedule management |
| `templates/monitor.html` | Real-time activity monitor with timeline and sensor status |
| `templates/reports.html` | Paginated Markdown report browser with date filtering |
| `templates/alerts.html` | Alert management with severity filters, acknowledge, and resolve |
| `templates/approvals.html` | Approval queue with action preview and one-click approve/deny |
| `templates/settings.html` | Runtime settings configuration with masked sensitive values |
| `templates/logs.html` | System logs viewer and LLM activity monitor with filtering |
| `templates/docs.html` | Embedded API documentation page |

## Key Features

- **Chat Widget**: Persistent across all pages. File-backed session history stored in `.logs/chats/`. Provides specific LLM error messages (timeout, rate limit, auth error).
- **Report Pagination**: `/reports` supports `?limit=` and `?offset=` query params.
- **Manual Diagnostics**: `/diagnostics` can trigger any sensor on-demand via `/api/diagnostics/run`.
- **Schedule Management**: Create, remove, enable, disable, and edit intervals from the web UI.
- **Approval Workflow**: Approve/deny high-risk actions. Approved actions execute via `response_engine` and generate alerts.
- **Alert Lifecycle**: Alerts can be acknowledged and resolved via the UI.
- **Settings**: Runtime configuration via `SettingsManager` with immediate effect.
- **Logs Filtering**: View events, detections, or LLM calls. LLM stats show call counts and token usage over time.
- **Security**: Report paths validated against directory traversal. Settings API masks secrets. Chat sessions isolated by Flask session ID.

## Page Routes

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `index.html` | Main dashboard |
| `/diagnostics` | `diagnostics.html` | Sensor runner & schedules |
| `/monitor` | `monitor.html` | Activity monitor |
| `/reports` | `reports.html` | Report browser (paginated) |
| `/alerts` | `alerts.html` | Alert management |
| `/approvals` | `approvals.html` | Approval queue |
| `/settings` | `settings.html` | Settings configuration |
| `/logs` | `logs.html` | Logs & LLM monitor |
| `/docs` | `docs.html` | API docs |
| `/health` | - | Health check |
| `/shutdown` | - | Server shutdown (POST) |

## API Endpoints

See `docs/COMPLETE.md` → **API Reference** → **Web Dashboard API Endpoints** for the full list of 30+ REST endpoints.
