# Directory: src/integrations

External service clients for alert dispatch and SIEM integration.

| File | Purpose |
| --- | --- |
| `siem_client.py` | SIEM integration: Splunk HEC, QRadar, Wazuh API |
| `slack_client.py` | Slack incoming webhooks and interactive message buttons |
| `teams_client.py` | Microsoft Teams incoming webhooks and Adaptive Cards |
| `pagerduty_client.py` | PagerDuty Events API v2 (incident creation, acknowledge, resolve) |
| `elk_client.py` | Elasticsearch bulk API ingestion and Logstash alternative |
| `cloudwatch_client.py` | AWS CloudWatch PutMetricData and CloudWatch Logs ingestion |

## Key Concepts

- **Webhook-Based**: Slack and Teams use simple HTTP POSTs to configured webhook URLs.
- **API Key Security**: All integration secrets are read from environment variables (never hardcoded).
- **Configurable**: Each client checks for required config (URL, API key) before attempting to send and fails gracefully if missing.
