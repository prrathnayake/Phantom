"""Risk Scoring and Detection Enhancement.

Adds weighted risk scoring, trend analysis, and predictive alerting.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

import config
from src.core.storage import Storage
from src.utils.debug_log import debug_logger


@dataclass
class RiskScore:
    score: int
    level: str
    factors: List[str]
    timestamp: str


class RiskScorer:
    """Calculates risk scores based on detections and assets."""
    
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self._lock = Lock()
        
        self.asset_criticality = self._default_asset_criticality()
        
        self.detection_weights = {
            "process_count": 10,
            "open_ports": 15,
            "file_changes": 20,
            "established_connections": 15,
            "external_ips": 20,
            "memory_percent": 10,
            "swap_percent": 10,
            "disk_percent": 10,
            "failed_logins": 25,
            "privilege_escalation": 40,
            "brute_force": 35,
            "lateral_movement": 50,
            "data_exfiltration": 45,
            "malware": 50,
            "dns_tunneling": 30,
        }
        
        self._baseline: Dict[str, List[float]] = {}
        self._max_baseline_entries = 100
        
        debug_logger.info("RiskScorer initialized")
    
    def _default_asset_criticality(self) -> Dict[str, int]:
        return {
            "domain_controller": 10,
            "file_server": 8,
            "database_server": 9,
            "web_server": 7,
            "workstation": 5,
            "router": 9,
            "firewall": 10,
            "default": 5
        }
    
    def update_baseline(
        self,
        sensor: str,
        value: float
    ) -> None:
        """Update baseline for sensor.
        
        Args:
            sensor: Sensor name
            value: Current value
        """
        with self._lock:
            if sensor not in self._baseline:
                self._baseline[sensor] = []
            
            self._baseline[sensor].append(value)
            
            if len(self._baseline[sensor]) > self._max_baseline_entries:
                self._baseline[sensor] = self._baseline[sensor][-self._max_baseline_entries:]
    
    def get_baseline_stats(
        self,
        sensor: str,
        window: int = 10
    ) -> Dict[str, float]:
        """Get baseline statistics for a sensor.
        
        Args:
            sensor: Sensor name
            window: Number of recent values
            
        Returns:
            Dictionary with mean, std, min, max
        """
        with self._lock:
            values = self._baseline.get(sensor, [])[-window:]
        
        if not values:
            return {"mean": 0, "std": 0, "min": 0, "max": 0}
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        
        return {
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
    
    def is_anomalous(
        self,
        sensor: str,
        value: float,
        threshold: float = 2.0
    ) -> bool:
        """Check if value is anomalous based on baseline.
        
        Args:
            sensor: Sensor name
            value: Current value
            threshold: Z-score threshold
            
        Returns:
            True if anomalous
        """
        stats = self.get_baseline_stats(sensor, window=20)
        
        if stats["std"] == 0:
            return abs(value - stats["mean"]) > 0
        
        z_score = abs(value - stats["mean"]) / stats["std"]
        
        return z_score > threshold
    
    def calculate_detection_risk(
        self,
        rule: str,
        details: Dict[str, Any]
    ) -> int:
        """Calculate risk score for a detection.
        
        Args:
            rule: Detection rule
            details: Detection details
            
        Returns:
            Risk score (0-100)
        """
        base_weight = self.detection_weights.get(rule, 10)
        
        severity_multiplier = 1.0
        
        if "critical" in str(details).lower():
            severity_multiplier = 1.5
        elif "high" in str(details).lower():
            severity_multiplier = 1.25
        
        count_value = details.get("count", details.get("failed_count", 1))
        if count_value > 10:
            severity_multiplier += 0.25
        elif count_value > 5:
            severity_multiplier += 0.1
        
        score = int(base_weight * severity_multiplier)
        
        return min(score, 100)
    
    def calculate_correlation_risk(
        self,
        correlation_event: Dict[str, Any]
    ) -> int:
        """Calculate risk score for a correlation event.
        
        Args:
            correlation_event: Correlation event data
            
        Returns:
            Risk score (0-100)
        """
        severity = correlation_event.get("severity", "medium")
        
        severity_scores = {
            "critical": 80,
            "high": 60,
            "medium": 40,
            "low": 20
        }
        
        base_score = severity_scores.get(severity, 40)
        
        confidence = correlation_event.get("confidence", 0.5)
        if confidence > 0.8:
            base_score += 10
        elif confidence > 0.6:
            base_score += 5
        
        if correlation_event.get("correlation_id"):
            base_score += 10
        
        return min(base_score, 100)
    
    def calculate_combined_risk(
        self,
        detections: List[Dict[str, Any]],
        correlations: List[Dict[str, Any]]
    ) -> RiskScore:
        """Calculate combined risk from detections and correlations.
        
        Args:
            detections: List of detection events
            correlations: List of correlation events
            
        Returns:
            Combined risk score
        """
        total_score = 0
        factors = []
        
        for detection in detections:
            rule = detection.get("rule", "unknown")
            details = detection.get("details", {})
            score = self.calculate_detection_risk(rule, details)
            total_score += score
            factors.append(f"Detection: {rule}")
        
        for correlation in correlations:
            score = self.calculate_correlation_risk(correlation)
            total_score += score
            factors.append(f"Correlation: {correlation.get('pattern', 'unknown')}")
        
        total_score = min(total_score, 100)
        
        level = self._score_to_level(total_score)
        
        return RiskScore(
            score=total_score,
            level=level,
            factors=factors,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _score_to_level(self, score: int) -> str:
        if score >= 76:
            return "CRITICAL"
        elif score >= 51:
            return "HIGH"
        elif score >= 26:
            return "MEDIUM"
        else:
            return "LOW"
    
    def should_escalate(self, risk_score: int) -> bool:
        """Determine if risk score requires escalation.
        
        Args:
            risk_score: Calculated risk score
            
        Returns:
            True if should escalate
        """
        return risk_score >= 51
    
    def should_auto_escalate(self, risk_score: int) -> bool:
        """Determine if should auto-escalate for critical risks.
        
        Args:
            risk_score: Calculated risk score
            
        Returns:
            True if auto-escalation required
        """
        return risk_score >= 76
    
    def get_risk_trend(
        self,
        metrics: List[float],
        window: int = 5
    ) -> Dict[str, Any]:
        """Analyze trend in metric values.
        
        Args:
            metrics: Historical values
            window: Window size
            
        Returns:
            Trend analysis
        """
        if len(metrics) < window:
            return {"trend": "insufficient_data", "direction": "stable"}
        
        recent = metrics[-window:]
        older = metrics[-window*2:-window] if len(metrics) >= window * 2 else metrics[:-window]
        
        if not older:
            older = recent
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        change = recent_avg - older_avg
        change_percent = (change / older_avg * 100) if older_avg > 0 else 0
        
        if change_percent > 20:
            direction = "rising"
        elif change_percent < -20:
            direction = "falling"
        else:
            direction = "stable"
        
        return {
            "trend": direction,
            "change_percent": round(change_percent, 2),
            "recent_avg": round(recent_avg, 2),
            "older_avg": round(older_avg, 2)
        }


class TrendAnalyzer:
    """Analyzes trends in sensor data."""
    
    def __init__(self):
        self._sensor_history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = Lock()
        
        self.min_history_for_trend = 5
        
        debug_logger.info("TrendAnalyzer initialized")
    
    def record_value(
        self,
        sensor: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a sensor value.
        
        Args:
            sensor: Sensor name
            value: Current value
            metadata: Additional metadata
        """
        with self._lock:
            if sensor not in self._sensor_history:
                self._sensor_history[sensor] = []
            
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": value,
                "metadata": metadata or {}
            }
            
            self._sensor_history[sensor].append(entry)
            
            if len(self._sensor_history[sensor]) > 100:
                self._sensor_history[sensor] = self._sensor_history[sensor][-100:]
    
    def analyze_trend(
        self,
        sensor: str,
        window: int = 10
    ) -> Dict[str, Any]:
        """Analyze trend for a sensor.
        
        Args:
            sensor: Sensor name
            window: Analysis window
            
        Returns:
            Trend analysis
        """
        with self._lock:
            history = list(self._sensor_history.get(sensor, []))
        
        if len(history) < self.min_history_for_trend:
            return {
                "sensor": sensor,
                "status": "insufficient_data",
                "data_points": len(history)
            }
        
        values = [h["value"] for h in history[-window:]]
        
        mean = sum(values) / len(values)
        
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_change = sum(diffs) / len(diffs) if diffs else 0
        
        if avg_change > 0.1:
            trend = "rising"
        elif avg_change < -0.1:
            trend = "falling"
        else:
            trend = "stable"
        
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        
        return {
            "sensor": sensor,
            "status": "analyzed",
            "trend": trend,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "avg_change": round(avg_change, 4),
            "data_points": len(values)
        }
    
    def predict_next_value(
        self,
        sensor: str,
        window: int = 10
    ) -> Optional[float]:
        """Predict next value for a sensor.
        
        Args:
            sensor: Sensor name
            window: Window for prediction
            
        Returns:
            Predicted value or None
        """
        with self._lock:
            history = list(self._sensor_history.get(sensor, []))
        
        if len(history) < window:
            return None
        
        values = [h["value"] for h in history[-window:]]
        
        mean = sum(values) / len(values)
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            return values[-1] + avg_diff
        
        return mean
    
    def is_predictive_anomaly(
        self,
        sensor: str,
        current_value: float,
        window: int = 10
    ) -> bool:
        """Check if current value deviates from predicted.
        
        Args:
            sensor: Sensor name
            current_value: Current value
            window: Window for prediction
            
        Returns:
            True if anomalous
        """
        predicted = self.predict_next_value(sensor, window)
        
        if predicted is None:
            return False
        
        diff = abs(current_value - predicted)
        threshold = abs(predicted) * 0.5 if predicted != 0 else 5
        
        return diff > threshold


def create_risk_scorer() -> RiskScorer:
    """Create RiskScorer with default settings.
    
    Returns:
        Configured RiskScorer
    """
    return RiskScorer()


def create_trend_analyzer() -> TrendAnalyzer:
    """Create TrendAnalyzer with default settings.
    
    Returns:
        Configured TrendAnalyzer
    """
    return TrendAnalyzer()
