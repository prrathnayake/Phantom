"""Cross-Sensor Correlation Engine.

Analyzes patterns across multiple sensors to detect complex attack patterns.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional
import json

import config
from src.core.storage import Storage
from src.utils.debug_log import debug_logger


class CorrelationSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AttackPattern(Enum):
    BRUTE_FORCE = "brute_force"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MALWARE = "malware"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DNS_TUNNELING = "dns_tunneling"
    SUSPICIOUS_PROCESS = "suspicious_process"
    CREDENTIAL_THEFT = "credential_theft"


@dataclass
class CorrelationEvent:
    pattern: str
    severity: str
    description: str
    correlated_sensors: List[str]
    detected_at: str
    confidence: float
    details: Dict[str, Any]
    correlation_id: str


class CorrelationRule:
    def __init__(
        self,
        pattern: AttackPattern,
        required_sensors: List[str],
        conditions: Dict[str, Any],
        severity: str = "medium",
        description: str = ""
    ):
        self.pattern = pattern
        self.required_sensors = required_sensors
        self.conditions = conditions
        self.severity = severity
        self.description = description or pattern.value


class CorrelationEngine:
    """Analyzes correlations between sensor data."""
    
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self._lock = Lock()
        
        self._sensor_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._correlation_window = timedelta(minutes=5)
        
        self._rules = self._build_correlation_rules()
        
        self.max_cache_entries = 100
        
        debug_logger.info("CorrelationEngine initialized")
    
    def _build_correlation_rules(self) -> List[CorrelationRule]:
        return [
            CorrelationRule(
                pattern=AttackPattern.BRUTE_FORCE,
                required_sensors=["auth_sensor", "network_sensor"],
                conditions={
                    "auth_sensor": {"failed_logins": {"gt": 5}},
                    "network_sensor": {"established_count": {"gt": 10}}
                },
                severity="high",
                description="Multiple failed logins with high network activity"
            ),
            CorrelationRule(
                pattern=AttackPattern.LATERAL_MOVEMENT,
                required_sensors=["network_sensor", "port_sensor", "process_sensor"],
                conditions={
                    "network_sensor": {"external_ips": {"gt": 5}},
                    "port_sensor": {"unusual_ports": {"gt": 0}},
                    "process_sensor": {"new_processes": {"gt": 0}}
                },
                severity="critical",
                description="Unusual network patterns + port scanning + new processes"
            ),
            CorrelationRule(
                pattern=AttackPattern.DATA_EXFILTRATION,
                required_sensors=["network_sensor", "disk_io_sensor"],
                conditions={
                    "network_sensor": {"external_ips": {"gt": 3}, "bytes_sent": {"gt": 1000000}},
                    "disk_io_sensor": {"write_rate": {"gt": 100}}
                },
                severity="critical"
            ),
            CorrelationRule(
                pattern=AttackPattern.PRIVILEGE_ESCALATION,
                required_sensors=["auth_sensor", "process_sensor"],
                conditions={
                    "auth_sensor": {"privilege_escalations": {"gt": 0}},
                    "process_sensor": {"elevated_processes": {"gt": 0}}
                },
                severity="critical"
            ),
            CorrelationRule(
                pattern=AttackPattern.MALWARE,
                required_sensors=["process_sensor", "network_sensor"],
                conditions={
                    "process_sensor": {"suspicious_processes": {"gt": 0}},
                    "network_sensor": {"known_malicious_ips": {"gt": 0}}
                },
                severity="critical"
            ),
            CorrelationRule(
                pattern=AttackPattern.RESOURCE_EXHAUSTION,
                required_sensors=["memory_sensor", "process_sensor"],
                conditions={
                    "memory_sensor": {"percent_used": {"gt": 90}},
                    "process_sensor": {"count": {"gt": 300}}
                },
                severity="medium"
            ),
            CorrelationRule(
                pattern=AttackPattern.DNS_TUNNELING,
                required_sensors=["dns_sensor", "network_sensor"],
                conditions={
                    "dns_sensor": {"suspicious_domains": {"gt": 0}},
                    "network_sensor": {"external_ips": {"gt": 5}}
                },
                severity="high"
            ),
        ]
    
    def update_sensor_data(
        self,
        sensor_name: str,
        data: Dict[str, Any]
    ) -> None:
        """Update sensor data cache.
        
        Args:
            sensor_name: Name of the sensor
            data: Sensor data
        """
        with self._lock:
            if sensor_name not in self._sensor_cache:
                self._sensor_cache[sensor_name] = []
            
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            
            self._sensor_cache[sensor_name].append(entry)
            
            if len(self._sensor_cache[sensor_name]) > self.max_cache_entries:
                self._sensor_cache[sensor_name] = self._sensor_cache[sensor_name][-self.max_cache_entries:]
    
    def analyze(self) -> List[CorrelationEvent]:
        """Analyze current sensor data for correlations.
        
        Returns:
            List of detected correlation events
        """
        events = []
        now = datetime.utcnow()
        window_start = now - self._correlation_window
        
        for rule in self._rules:
            if self._check_rule(rule, window_start):
                event = self._create_correlation_event(rule)
                if event:
                    events.append(event)
                    
                    self.storage.log_detection(
                        rule.pattern.value,
                        event.description,
                        event.details
                    )
                    
                    debug_logger.info("Correlation detected", {
                        "pattern": rule.pattern.value,
                        "severity": rule.severity,
                        "confidence": event.confidence
                    })
        
        return events
    
    def _check_rule(
        self,
        rule: CorrelationRule,
        window_start: datetime
    ) -> bool:
        for sensor in rule.required_sensors:
            if sensor not in self._sensor_cache:
                return False
            
            sensor_data = self._sensor_cache[sensor]
            recent_data = [
                entry for entry in sensor_data
                if datetime.fromisoformat(entry["timestamp"]) > window_start
            ]
            
            if not recent_data:
                return False
            
            data = recent_data[-1]["data"]
            conditions = rule.conditions.get(sensor, {})
            
            if not self._check_conditions(data, conditions):
                return False
        
        return True
    
    def _check_conditions(
        self,
        data: Dict[str, Any],
        conditions: Dict[str, Any]
    ) -> bool:
        for field_name, condition in conditions.items():
            value = data.get(field_name)
            
            if value is None:
                value = 0
            
            if isinstance(condition, dict):
                if "gt" in condition and not value > condition["gt"]:
                    return False
                if "gte" in condition and not value >= condition["gte"]:
                    return False
                if "lt" in condition and not value < condition["lt"]:
                    return False
                if "lte" in condition and not value <= condition["lte"]:
                    return False
                if "eq" in condition and not value == condition["eq"]:
                    return False
                if "ne" in condition and not value != condition["ne"]:
                    return False
        
        return True
    
    def _create_correlation_event(
        self,
        rule: CorrelationRule
    ) -> Optional[CorrelationEvent]:
        now = datetime.utcnow()
        correlation_id = f"{rule.pattern.value}-{now.strftime('%Y%m%d%H%M%S')}"
        
        details = {}
        for sensor in rule.required_sensors:
            if sensor in self._sensor_cache and self._sensor_cache[sensor]:
                details[sensor] = self._sensor_cache[sensor][-1]["data"]
        
        confidence = self._calculate_confidence(rule, details)
        
        return CorrelationEvent(
            pattern=rule.pattern.value,
            severity=rule.severity,
            description=rule.description,
            correlated_sensors=rule.required_sensors,
            detected_at=now.isoformat(),
            confidence=confidence,
            details=details,
            correlation_id=correlation_id
        )
    
    def _calculate_confidence(
        self,
        rule: CorrelationRule,
        details: Dict[str, Dict[str, Any]]
    ) -> float:
        base_confidence = 0.5
        
        sensors_matched = 0
        for sensor in rule.required_sensors:
            if sensor in details:
                sensors_matched += 1
        
        if sensors_matched == len(rule.required_sensors):
            base_confidence += 0.3
        
        return min(base_confidence, 1.0)
    
    def detect_patterns_from_payload(
        self,
        payload: Dict[str, Any]
    ) -> List[CorrelationEvent]:
        """Detect patterns from a single payload.
        
        Args:
            payload: Diagnostic payload
            
        Returns:
            List of potential correlations
        """
        source = payload.get("source", "unknown")
        
        if source in self._sensor_cache:
            self._sensor_cache[source].append({
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            })
        else:
            self._sensor_cache[source] = [{
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            }]
        
        return self.analyze()
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """Get summary of correlation engine state.
        
        Returns:
            Summary dictionary
        """
        with self._lock:
            sensors_with_data = list(self._sensor_cache.keys())
        
        return {
            "correlation_window_minutes": self._correlation_window.total_seconds() / 60,
            "sensors_tracked": sensors_with_data,
            "rules_count": len(self._rules),
            "patterns": [r.pattern.value for r in self._rules]
        }
    
    def clear_cache(self) -> None:
        """Clear sensor data cache."""
        with self._lock:
            self._sensor_cache.clear()
        
        debug_logger.info("Correlation cache cleared")


def create_correlation_engine() -> CorrelationEngine:
    """Create CorrelationEngine with default settings.
    
    Returns:
        Configured CorrelationEngine
    """
    return CorrelationEngine()
