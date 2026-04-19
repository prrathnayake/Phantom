# Suraksha - Implementation Plan: Enhanced Proactiveness & Security Monitoring

## Overview

This document outlines the comprehensive implementation plan for enhancing the Suraksha monitoring agent with proactive security capabilities, cross-platform sensors, anomaly detection, and interactive approval workflows.

---

## Requirements Summary

- **Platform**: Cross-platform (Windows + Linux)
- **Approval System**: Interactive approval via UI/API before executing actions
- **External Services**: All integrations (SIEM, Slack/Teams, PagerDuty, ELK, CloudWatch)
- **Anomaly Detection**: Cross-sensor correlation + risk scoring
- **ML**: Simple statistical methods with demo code + documentation for ML integration

---

## Architecture Overview

### Current Flow
```
Sensors → Scheduled Checks → Detection Rules → Storage → (Manual review)
```

### Proposed Proactive Flow
```
Sensors → Detection Rules → Correlation Engine → Risk Scorer → 
  ├─ Low Risk: Store + Report
  ├─ Medium Risk: Alert + Store + Report
  ├─ High Risk: Create Approval Request → Human Approves → Execute + Alert
  └─ Critical: Immediate Approval Request + LLM Analysis + Auto-Response
```

---

## Phase 1: Alert Manager & External Integrations

### 1.1 Alert Manager Framework
**File**: `analysis/alert_manager.py`
- Alert priority queue (CRITICAL, HIGH, MEDIUM, LOW)
- Multi-channel dispatch: SIEM, Slack/Teams, PagerDuty, ELK, CloudWatch
- Alert deduplication and throttling
- Alert history tracking

### 1.2 Alert Data Model
```python
@dataclass
class Alert:
    alert_id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    source: str
    recommended_action: str
    affected_assets: List[str]
    timestamp: str
    status: Literal["PENDING", "APPROVED", "DENIED", "EXECUTED"]
```

### 1.3 External Service Integrations

#### SIEM Integration (`integrations/siem_client.py`)
- Splunk HTTP Event Collector (HEC)
- QRadar log forwarding
- Wazuh API integration
- Elastic Elasticsearch ingestion

#### Slack Integration (`integrations/slack_client.py`)
- Incoming webhooks
- Channel messaging
- Interactive message buttons for approvals

#### Teams Integration (`integrations/teams_client.py`)
- Incoming webhooks
- Adaptive Cards for rich formatting

#### PagerDuty Integration (`integrations/pagerduty_client.py`)
- Events API v2
- Incident creation
- Acknowledge/Resolve

#### ELK Integration (`integrations/elk_client.py`)
- Elasticsearch bulk API
- Logstash alternative

#### CloudWatch Integration (`integrations/cloudwatch_client.py`)
- CloudWatch PutMetricData API
- Custom metrics for alerts
- CloudWatch Logs ingestion

---

## Phase 2: Interactive Approval Workflow

### 2.1 Approval Request System
**File**: `analysis/approval_manager.py`
- Creates approval requests with action details
- Stores pending approvals in storage
- Provides API endpoints for approval/denial
- Implements timeout and escalation

### 2.2 API Endpoints
- `POST /api/approvals` - Create approval request
- `GET /api/approvals` - List pending approvals
- `POST /api/approvals/{id}/approve` - Approve action
- `POST /api/approvals/{id}/deny` - Deny action
- `GET /api/approvals/{id}` - Get approval status

### 2.3 Dashboard Integration
- Add approval request queue UI
- One-click approve/deny buttons
- Action preview panel
- Approval history

### 2.4 Notification on Pending Approvals
- Push notification to dashboard
- Slack/Teams message for urgent approvals

---

## Phase 3: Anomaly Detection Enhancement

### 3.1 Cross-Sensor Correlation Engine
**File**: `analysis/correlation.py`
- Time-windowed correlation (configurable, default 5 min)
- Pattern detection rules:
  - High network + failed logins = potential brute force
  - Process spike + file changes = possible malware
  - Memory pressure + disk I/O = resource exhaustion
  - DNS anomalies + network spikes = possible exfiltration
- Correlation chaining (detect multi-step attacks)

### 3.2 Risk Scoring Model
- Weighted scoring:
  - Asset criticality (user-defined)
  - Threat severity (CVSS-like)
  - Attack chain bonus (if multiple correlated)
- Risk levels: 0-25 LOW, 26-50 MEDIUM, 51-75 HIGH, 76-100 CRITICAL

### 3.3 Trend Analysis
**File**: `analysis/trends.py`
- Moving average for sensor baselines
- Rate of change detection
- Predictive alerting (alert before threshold hit)

---

## Phase 4: New Cross-Platform Sensors

| Sensor | File | Description |
|--------|------|-------------|
| **service_sensor** | `diagnostics/service_sensor.py` | Monitor critical services (Windows services / systemd) |
| **registry_sensor** | `diagnostics/registry_sensor.py` | Windows registry keys + Linux auditd |
| **dns_sensor** | `diagnostics/dns_sensor.py` | DNS queries, cache, suspicious domains |
| **driver_sensor** | `diagnostics/driver_sensor.py` | Kernel modules (Linux) / Drivers (Windows) |
| **certificate_sensor** | `diagnostics/certificate_sensor.py` | TLS cert expiry, weak ciphers |
| **hardware_sensor** | `diagnostics/hardware_sensor.py` | USB devices, hardware changes |

---

## Phase 5: ML-Based Anomaly Detection Demo

### 5.1 Statistical Anomaly Detection
**File**: `analysis/statistical_anomaly.py`
- Baseline calculation (moving average, std deviation)
- Z-score based anomaly detection
- Seasonal adjustment for time-series data
- Demo mode with synthetic data generation

### 5.2 ML Framework Placeholder
**File**: `analysis/ml_anomaly.py`
- Abstract class for ML-based detection
- Placeholder for sklearn/tensorflow integration
- Clear documentation comments for ML integration
- Demo data generation for testing

### 5.3 ML Documentation
See `docs/ML_ANOMALY_DETECTION.md` for detailed ML integration guide.

---

## Phase 6: Auto-Response with Approval

### 6.1 Response Action Definitions
**File**: `analysis/response_actions.py`
- Action types: `BLOCK_IP`, `KILL_PROCESS`, `DISABLE_USER`, `QUARANTINE_FILE`, `ALERT_ONLY`
- Parameter schemas for each action
- Dry-run capability

### 6.2 Example Response Workflow
```
1. Detection: High network to suspicious IP + port scan
2. Correlation: Flags as potential lateral movement
3. Risk Score: 78 (HIGH)
4. Action: BLOCK_IP + DISABLE_USER
5. Approval Request Created → Dashboard notification
6. User clicks "Approve"
7. Response Engine executes: 
   - BLOCK_IP: Add to firewall blocklist
   - DISABLE_USER: Deactivate compromised account
8. Alert sent to SIEM + Slack
```

---

## File Structure Changes

```
diagnostics/
  + service_sensor.py    (NEW)
  + registry_sensor.py   (NEW)
  + dns_sensor.py        (NEW)
  + driver_sensor.py     (NEW)
  + certificate_sensor.py (NEW)
  + hardware_sensor.py   (NEW)

analysis/
  + alert_manager.py     (NEW)
  + correlation.py       (NEW)
  + trends.py            (NEW)
  + statistical_anomaly.py (NEW)
  + ml_anomaly.py        (NEW)
  + approval_manager.py  (NEW)
  + response_actions.py  (NEW)
  ~ detection.py         (MODIFY - add risk scoring)
  ~ summariser.py        (MODIFY - integrate alerts)

integrations/
  + __init__.py
  + siem_client.py
  + slack_client.py
  + teams_client.py
  + pagerduty_client.py
  + elk_client.py
  + cloudwatch_client.py

gateway/interfaces/
  ~ http_handler.py      (MODIFY - add approval endpoints)
  
apps/web/
  ~ app.py               (MODIFY - add approval UI)

docs/
  + IMPLEMENTATION_PLAN.md (THIS FILE)
  + ML_ANOMALY_DETECTION.md (NEW)
```

---

## Configuration

### New Config Settings (config.py)
```python
# New sensor intervals
POLL_INTERVALS.update({
    "service_sensor": 60,
    "registry_sensor": 300,
    "dns_sensor": 30,
    "driver_sensor": 120,
    "certificate_sensor": 3600,
    "hardware_sensor": 60,
})

# Alert settings
ALERT_THROTTLE_SECONDS = 60
ALERT_TIMEOUT_MINUTES = 30

# Risk scoring
RISK_WEIGHTS = {...}

# External integrations
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")
PAGERDUTY_KEY = os.environ.get("PAGERDUTY_KEY")
ELASTIC_URL = os.environ.get("ELASTIC_URL")
SPLUNK_HEC_URL = os.environ.get("SPLUNK_HEC_URL")
CLOUDWATCH_REGION = os.environ.get("AWS_DEFAULT_REGION")
```

---

## Testing Strategy

1. **Unit Tests**: Each new component has dedicated unit tests
2. **Integration Tests**: Test sensor → detection → alert → approval flow
3. **E2E Tests**: Full workflow from detection to action execution
4. **Mock External Services**: Use responses for SIEM, Slack, etc.

---

## Implementation Status

| Phase | Status |
|-------|--------|
| Phase 1: Alert & Integrations | ⬜ Planned |
| Phase 2: Approval Workflow | ⬜ Planned |
| Phase 3: Anomaly Detection | ⬜ Planned |
| Phase 4: New Sensors | ⬜ Planned |
| Phase 5: ML Demo | ⬜ Planned |
| Phase 6: Auto-Response | ⬜ Planned |

---

*Document Version: 1.0*
*Created: 2026-04-19*
*Project: Suraksha - Secure Monitoring Agent*