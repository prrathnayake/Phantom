"""ML-Based Anomaly Detection.

This module provides a placeholder framework for ML-based anomaly detection.
The current implementation uses statistical methods.

For full ML integration, see docs/ML_ANOMALY_DETECTION.md for guidance on:
- Scikit-learn Isolation Forest
- TensorFlow/PyTorch Autoencoders
- LSTM for time-series

This placeholder allows easy integration of trained ML models.
"""
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
import random

from src.utils.debug_log import debug_logger


@dataclass
class MLAnomalyResult:
    """Result from ML anomaly detection."""
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    model_version: str
    details: Dict[str, Any]


class MLAnomalyDetector:
    """Placeholder for ML-based anomaly detection.
    
    Current implementation uses simple threshold-based detection.
    To integrate ML:
    1. Train a model (see sklearn/tensorflow)
    2. Save the model to models/anomaly_detector.pkl
    3. Load and use in the detect() method
    
    Example Integration (future):
    ```
    from sklearn.ensemble import IsolationForest
    import joblib
    
    class MLAnomalyDetector:
        def __init__(self):
            self.model = joblib.load('models/anomaly_detector.pkl')
        
        def detect(self, features):
            score = self.model.score_samples([features])[0]
            return MLAnomalyResult(
                is_anomaly=score < -0.5,
                anomaly_score=abs(score),
                confidence=min(abs(score), 1.0),
                model_version="1.0.0"
            )
    ```
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/anomaly_detector.pkl"
        self._lock = Lock()
        
        self._feature_history: Dict[str, List[Dict[str, float]]] = {}
        
        self.model_loaded = False
        self.model_version = "0.0.0-placeholder"
        
        self._try_load_model()
        
        debug_logger.info("MLAnomalyDetector initialized", {
            "model_path": self.model_path,
            "model_loaded": self.model_loaded
        })
    
    def _try_load_model(self) -> None:
        """Attempt to load a trained model.
        
        Placeholder: In production, load trained model from disk.
        """
        try:
            import os
            if os.path.exists(self.model_path):
                import joblib
                self.model = joblib.load(self.model_path)
                self.model_loaded = True
                self.model_version = "1.0.0"
                debug_logger.info("ML model loaded", {"version": self.model_version})
        except ImportError:
            debug_logger.debug("joblib not available, using placeholder")
        except Exception as e:
            debug_logger.debug("Model load failed", {"error": str(e)})
    
    def _extract_features(
        self,
        sensor_data: Dict[str, Any]
    ) -> List[float]:
        """Extract features from sensor data for ML model.
        
        Args:
            sensor_data: Dictionary of sensor data
            
        Returns:
            List of numeric features
        """
        features = []
        
        numeric_fields = [
            "count", "percent_used", "established_count",
            "external_ips", "failed_count", "memory_mb"
        ]
        
        for field in numeric_fields:
            value = sensor_data.get(field, 0)
            if isinstance(value, (int, float)):
                features.append(float(value))
            else:
                features.append(0.0)
        
        if not features:
            features = [0.0] * 6
        
        return features[:6]
    
    def train_baseline(
        self,
        sensor_name: str,
        normal_data: List[Dict[str, Any]]
    ) -> bool:
        """Train baseline from normal operational data.
        
        In production, this would train an ML model.
        Current placeholder stores data for statistical baseline.
        
        Args:
            sensor_name: Name of the sensor
            normal_data: List of normal sensor data samples
            
        Returns:
            True if training successful
        """
        with self._lock:
            if sensor_name not in self._feature_history:
                self._feature_history[sensor_name] = []
            
            for data in normal_data:
                features = self._extract_features(data)
                self._feature_history[sensor_name].append(features)
            
            debug_logger.info("Baseline trained", {
                "sensor": sensor_name,
                "samples": len(normal_data)
            })
        
        return True
    
    def detect(
        self,
        sensor_name: str,
        sensor_data: Dict[str, Any]
    ) -> MLAnomalyResult:
        """Detect anomalies using ML model.
        
        Args:
            sensor_name: Name of the sensor
            sensor_data: Current sensor data
            
        Returns:
            MLAnomalyResult
        """
        features = self._extract_features(sensor_data)
        
        if not self.model_loaded:
            return self._placeholder_detect(sensor_name, features)
        
        try:
            scores = self.model.score_samples([features])
            anomaly_score = abs(scores[0])
            is_anomaly = anomaly_score > 0.5
            confidence = min(anomaly_score, 1.0)
            
            return MLAnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                confidence=confidence,
                model_version=self.model_version,
                details={"features": features}
            )
        except Exception as e:
            debug_logger.error("ML detection failed", {"error": str(e)})
            return self._placeholder_detect(sensor_name, features)
    
    def _placeholder_detect(
        self,
        sensor_name: str,
        features: List[float]
    ) -> MLAnomalyResult:
        """Placeholder detection using simple thresholds.
        
        Replace this with actual ML inference in production.
        
        Args:
            sensor_name: Sensor name
            features: Extracted features
            
        Returns:
            MLAnomalyResult
        """
        if not features:
            return MLAnomalyResult(
                is_anomaly=False,
                anomaly_score=0,
                confidence=0,
                model_version=self.model_version,
                details={"reason": "no_features"}
            )
        
        anomaly_score = features[0] / 100.0
        
        if features[0] > 80:
            anomaly_score = 0.8
        elif features[0] > 60:
            anomaly_score = 0.5
        elif features[0] > 40:
            anomaly_score = 0.3
        else:
            anomaly_score = 0.1
        
        return MLAnomalyResult(
            is_anomaly=anomaly_score > 0.5,
            anomaly_score=anomaly_score,
            confidence=0.5,
            model_version=self.model_version,
            details={"method": "placeholder", "features": features[:3]}
        )
    
    def detect_batch(
        self,
        sensor_name: str,
        data_samples: List[Dict[str, Any]]
    ) -> List[MLAnomalyResult]:
        """Detect anomalies in batch of samples.
        
        Args:
            sensor_name: Sensor name
            data_samples: List of sensor data samples
            
        Returns:
            List of MLAnomalyResults
        """
        results = []
        
        for data in data_samples:
            result = self.detect(sensor_name, data)
            results.append(result)
            
            self._record_for_baseline(sensor_name, data)
        
        return results
    
    def _record_for_baseline(
        self,
        sensor_name: str,
        sensor_data: Dict[str, Any]
    ) -> None:
        """Record data for baseline training.
        
        Args:
            sensor_name: Sensor name
            sensor_data: Sensor data
        """
        with self._lock:
            if sensor_name not in self._feature_history:
                self._feature_history[sensor_name] = []
            
            features = self._extract_features(sensor_data)
            self._feature_history[sensor_name].append(features)
            
            if len(self._feature_history[sensor_name]) > 1000:
                self._feature_history[sensor_name] = self._feature_history[sensor_name][-1000:]
    
    def generate_demo_data(
        self,
        sensor_name: str,
        count: int = 100
    ):
        """Generate demo training and test data.
        
        Args:
            sensor_name: Sensor name
            count: Number of samples
            
        Returns:
            Tuple of (normal_samples, anomaly_samples)
        """
        normal_samples = []
        anomaly_samples = []
        
        for i in range(count):
            sample = {
                "count": random.randint(50, 150),
                "percent_used": random.randint(30, 70),
                "established_count": random.randint(10, 50),
                "external_ips": random.randint(0, 5),
                "failed_count": random.randint(0, 3),
                "memory_mb": random.randint(1000, 4000)
            }
            
            if random.random() < 0.05:
                sample["count"] = random.randint(200, 300)
                sample["percent_used"] = random.randint(85, 99)
                anomaly_samples.append(sample)
            else:
                normal_samples.append(sample)
        
        return normal_samples, anomaly_samples
    
    def run_demo(self) -> None:
        """Run demonstration of ML anomaly detection."""
        debug_logger.info("Running ML anomaly detection demo")
        
        sensor_name = "demo_sensor"
        
        normal_data, anomaly_data = self.generate_demo_data(sensor_name, 50)
        
        self.train_baseline(sensor_name, normal_data)
        
        debug_logger.info("Testing normal samples")
        for data in normal_data[:5]:
            result = self.detect(sensor_name, data)
            debug_logger.info("Normal detection", {
                "is_anomaly": result.is_anomaly,
                "score": result.anomaly_score,
                "confidence": result.confidence
            })
        
        debug_logger.info("Testing anomalous samples")
        for data in anomaly_data[:5]:
            result = self.detect(sensor_name, data)
            debug_logger.info("Anomaly detection", {
                "is_anomaly": result.is_anomaly,
                "score": result.anomaly_score,
                "confidence": result.confidence
            })
        
        debug_logger.info("Demo complete")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information.
        
        Returns:
            Dictionary with model info
        """
        return {
            "model_path": self.model_path,
            "model_loaded": self.model_loaded,
            "model_version": self.model_version,
            "sensors_tracked": list(self._feature_history.keys())
        }


def create_ml_detector(
    model_path: Optional[str] = None
) -> MLAnomalyDetector:
    """Create ML anomaly detector.
    
    Args:
        model_path: Optional path to trained model
        
    Returns:
        Configured MLAnomalyDetector
    """
    return MLAnomalyDetector(model_path)
