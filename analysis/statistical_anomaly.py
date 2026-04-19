"""Statistical Anomaly Detection.

Uses statistical methods (moving average, Z-score) for anomaly detection.
Includes demo mode with synthetic data generation.
"""
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
import random
import math

from utils.debug_log import debug_logger


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    threshold: float
    confidence: float
    method: str
    details: Dict[str, Any]


class StatisticalAnomalyDetector:
    """Statistical anomaly detection using Z-score and moving average."""
    
    def __init__(self, window_size: int = 20, threshold: float = 2.5):
        self.window_size = window_size
        self.threshold = threshold
        
        self._history: Dict[str, List[float]] = {}
        self._lock = Lock()
        
        self.demo_mode = False
        
        debug_logger.info("StatisticalAnomalyDetector initialized", {
            "window_size": window_size,
            "threshold": threshold
        })
    
    def record_value(
        self,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a value for baseline calculation.
        
        Args:
            metric_name: Name of the metric
            value: Current value
            metadata: Optional additional data
        """
        with self._lock:
            if metric_name not in self._history:
                self._history[metric_name] = []
            
            self._history[metric_name].append(value)
            
            if len(self._history[metric_name]) > self.window_size * 2:
                self._history[metric_name] = self._history[metric_name][-self.window_size * 2:]
    
    def _calculate_stats(
        self,
        values: List[float]
    ) -> Dict[str, float]:
        """Calculate basic statistics.
        
        Args:
            values: List of values
            
        Returns:
            Dictionary with mean, std, min, max
        """
        if not values:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "count": 0}
        
        count = len(values)
        mean = sum(values) / count
        
        if count < 2:
            return {"mean": mean, "std": 0, "min": min(values), "max": max(values), "count": count}
        
        variance = sum((x - mean) ** 2 for x in values) / count
        std = math.sqrt(variance)
        
        return {
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "count": count
        }
    
    def _calculate_z_score(
        self,
        value: float,
        mean: float,
        std: float
    ) -> float:
        """Calculate Z-score.
        
        Args:
            value: Current value
            mean: Baseline mean
            std: Standard deviation
            
        Returns:
            Z-score
        """
        if std == 0:
            return abs(value - mean)
        
        return abs(value - mean) / std
    
    def detect(
        self,
        metric_name: str,
        value: float
    ) -> AnomalyResult:
        """Detect if value is anomalous.
        
        Args:
            metric_name: Metric name
            value: Current value
            
        Returns:
            AnomalyResult
        """
        with self._lock:
            values = list(self._history.get(metric_name, []))
        
        if len(values) < self.window_size:
            return AnomalyResult(
                is_anomaly=False,
                score=0,
                threshold=self.threshold,
                confidence=0,
                method="insufficient_data",
                details={"samples_needed": self.window_size - len(values)}
            )
        
        recent_values = values[-self.window_size:]
        
        stats = self._calculate_stats(recent_values)
        z_score = self._calculate_z_score(value, stats["mean"], stats["std"])
        
        is_anomaly = z_score > self.threshold
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=z_score,
            threshold=self.threshold,
            confidence=min(z_score / self.threshold, 1.0),
            method="z_score",
            details={
                "mean": stats["mean"],
                "std": stats["std"],
                "value": value
            }
        )
    
    def detect_multiple(
        self,
        data: Dict[str, float]
    ) -> Dict[str, AnomalyResult]:
        """Detect anomalies in multiple metrics.
        
        Args:
            data: Dictionary of metric_name -> value
            
        Returns:
            Dictionary of metric_name -> AnomalyResult
        """
        results = {}
        
        for metric_name, value in data.items():
            self.record_value(metric_name, value)
            results[metric_name] = self.detect(metric_name, value)
        
        return results
    
    def get_baseline_stats(
        self,
        metric_name: str
    ) -> Dict[str, float]:
        """Get baseline statistics for a metric.
        
        Args:
            metric_name: Metric name
            
        Returns:
            Statistics dictionary
        """
        with self._lock:
            values = list(self._history.get(metric_name, []))[-self.window_size:]
        
        return self._calculate_stats(values)
    
    def run_demo(self) -> None:
        """Run demo with synthetic data."""
        self.demo_mode = True
        
        debug_logger.info("Running statistical anomaly demo")
        
        metrics = ["cpu_percent", "memory_percent", "network_connections"]
        
        for i in range(self.window_size):
            for metric in metrics:
                base_value = {
                    "cpu_percent": 50,
                    "memory_percent": 60,
                    "network_connections": 30
                }[metric]
                
                noise = random.gauss(0, 10)
                value = base_value + noise
                
                self.record_value(metric, max(0, value))
        
        for metric in metrics:
            base = {"cpu_percent": 50, "memory_percent": 60, "network_connections": 30}[metric]
            
            normal_value = base + random.gauss(0, 5)
            result = self.detect(metric, normal_value)
            debug_logger.info(f"Normal value test: {metric}", {
                "value": normal_value,
                "is_anomaly": result.is_anomaly,
                "z_score": result.score
            })
            
            anomalous_value = base * 2
            result = self.detect(metric, anomalous_value)
            debug_logger.info(f"Anomalous value test: {metric}", {
                "value": anomalous_value,
                "is_anomaly": result.is_anomaly,
                "z_score": result.score
            })
        
        self.demo_mode = False
        debug_logger.info("Demo complete")
    
    def generate_synthetic_data(
        self,
        metric_name: str,
        count: int = 100,
        anomaly_rate: float = 0.05
    ) -> List[float]:
        """Generate synthetic data with anomalies.
        
        Args:
            metric_name: Metric name
            count: Number of data points
            anomaly_rate: Percentage of anomalies
            
        Returns:
            List of synthetic values
        """
        base_value = 50
        data = []
        
        for i in range(count):
            if random.random() < anomaly_rate:
                value = base_value * random.uniform(1.5, 2.5)
            else:
                value = base_value + random.gauss(0, 10)
            
            data.append(max(0, value))
        
        return data
    
    def clear_history(self) -> None:
        """Clear all historical data."""
        with self._lock:
            self._history.clear()
        
        debug_logger.info("Statistical anomaly history cleared")


def create_statistical_detector(
    window_size: int = 20,
    threshold: float = 2.5
) -> StatisticalAnomalyDetector:
    """Create StatisticalAnomalyDetector.
    
    Args:
        window_size: Window size for baseline
        threshold: Z-score threshold
        
    Returns:
        Configured detector
    """
    return StatisticalAnomalyDetector(window_size, threshold)