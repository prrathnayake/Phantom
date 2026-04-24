# Directory: src/analysis

Detection engine. Transforms raw sensor data into security events via rule-based, statistical, ML-based, and correlation methods.

| File | Purpose |
| --- | --- |
| `detection.py` | Rule-based detection engine. Evaluates thresholds (process count, ports, file changes, memory, disk, auth) against the latest sensor payloads |
| `statistical_anomaly.py` | Rolling statistics anomaly detection (mean ± 2.5 std dev, Z-score, rate of change) |
| `ml_anomaly.py` | Placeholder and demo for ML-based anomaly detection (Isolation Forest, LSTM, Autoencoder) |
| `correlation.py` | Cross-sensor correlation engine. Detects multi-step attack patterns (brute force, lateral movement, exfiltration, etc.) |
| `trends.py` | Trend analysis: moving averages, baselines, predictive alerting |
| `summariser.py` | Report summarizer that condenses analysis output into executive summaries |
| `alert_manager.py` | Alert priority queue, multi-channel dispatch (SIEM, Slack, Teams, PagerDuty), deduplication, throttling |
| `approval_manager.py` | Interactive approval workflow for high-risk auto-response actions |
| `response_actions.py` | Automated response definitions (BLOCK_IP, KILL_PROCESS, DISABLE_USER, QUARANTINE_FILE) |

## Key Concepts

- **Thresholds**: All numeric thresholds are defined in `config.DETECTION_THRESHOLDS` and overridable via environment variables.
- **Correlation Rules**: `CorrelationRule` defines `AttackPattern`, `required_sensors`, `conditions` (gt/gte/lt/lte/eq/ne), and `severity`.
- **Confidence Scoring**: Correlation confidence starts at 0.5 and increases by 0.3 when all required sensors match.
- **Time Window**: Correlation engine only considers sensor data from the last 5 minutes (`config.CORRELATION_WINDOW_MINUTES`).
