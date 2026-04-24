# Directory: src/core

Framework foundation. Storage layer, LLM client, and tool framework.

| File / Folder | Purpose |
| --- | --- |
| `storage.py` | Storage class - append-only JSONL files for `events.log` and `detections.log`. Provides `log_event`, `log_detection`, `get_recent_events`, `get_recent_detections` |
| `openrouter_client.py` | OpenRouterClient - HTTP wrapper for OpenRouter chat completion API. Handles timeouts, auth errors, rate limits, and health reporting |
| `tools/` | Tool framework: shell, file, process, diagnostic tools with safety checks and execution registry |

## Key Concepts

- **JSONL Storage**: Each line is a standalone JSON object. Safe to read with `jq`, `pandas`, or simple line iteration.
- **Silent Failures**: Storage write failures are caught and logged but never crash the agent.
- **OpenRouter Health**: `get_health()` returns sanitized status (`missing_api_key`, `failed`, `reachable`, `configured`) without exposing the API key.
- **Error Categories**: OpenRouter errors are categorized as `missing_api_key`, `timeout`, `auth_error`, `rate_limited`, `http_error`, `request_error`, `invalid_response`.
