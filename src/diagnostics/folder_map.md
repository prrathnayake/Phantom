# Directory: src/diagnostics

Sensor collectors that gather system metrics and security-relevant data. Each sensor exposes a `collect(context)` function used by the ScheduleManager.

| File | Purpose |
| --- | --- |
| `process_sensor.py` | Running processes, CPU/memory usage per process. Prefers `psutil`; falls back to `ps` (Unix) or `tasklist` (Windows) |
| `port_sensor.py` | Listening TCP/UDP ports, connection states |
| `file_sensor.py` | File system changes in the watched directory (added, modified, removed) |
| `network_sensor.py` | Network connections, external IPs, bytes sent/received |
| `memory_sensor.py` | RAM and swap usage percentages |
| `disk_io_sensor.py` | Disk usage per mount point, read/write rates |
| `auth_sensor.py` | Failed logins, privilege escalations, authentication events |
| `service_sensor.py` | Critical system services (Windows services / systemd) |
| `registry_sensor.py` | Windows registry changes + Linux auditd events |
| `dns_sensor.py` | DNS queries, cache state, suspicious domain lookups |
| `driver_sensor.py` | Kernel modules (Linux) / installed drivers (Windows) |
| `certificate_sensor.py` | TLS certificate expiry, weak cipher detection |
| `hardware_sensor.py` | USB device insertions, hardware changes |

## Key Concepts

- **Unified Interface**: Every sensor implements `collect(context: Dict[str, Any]) -> Dict[str, Any]`.
- **Graceful Degradation**: Sensors prefer `psutil` but fall back to shell commands when unavailable.
- **Debug Logging**: All sensors call `debug_logger.sensor()` for observability.
- **Context**: The shared `context` dict allows sensors to store snapshots (e.g., `_snapshot`) for delta comparisons across runs.
