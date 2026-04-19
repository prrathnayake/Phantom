# ML-Based Anomaly Detection

## Overview

This document provides guidance on implementing machine learning-based anomaly detection for the Suraksha monitoring agent.

---

## Current Implementation

The system currently uses **statistical methods** for anomaly detection:

- **Z-Score Detection**: Identifies values that deviate significantly from the mean
- **Moving Average**: Establishes baselines with rolling window calculations
- **Rate of Change**: Detects sudden spikes or drops in metrics

See `analysis/statistical_anomaly.py` for the current implementation.

---

## Future ML Integration Options

### Option 1: Scikit-learn (Recommended for Production)

#### Isolation Forest
```python
from sklearn.ensemble import IsolationForest
import numpy as np

class IsolationForestDetector:
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(contamination=contamination)
    
    def fit(self, X_train):
        self.model.fit(X_train)
    
    def predict(self, X):
        return self.model.predict(X)
    
    def score(self, X):
        return self.model.score_samples(X)
```

**Pros**: Unsupervised, handles high-dimensional data, fast training
**Cons**: May flag normal anomalies as outliers

#### One-Class SVM
```python
from sklearn.svm import OneClassSVM

class OneClassSVMDetector:
    def __init__(self, nu=0.1):
        self.model = OneClassSVM(nu=nu)
    
    def fit(self, X_train):
        self.model.fit(X_train)
    
    def predict(self, X):
        return self.model.predict(X)
```

#### LSTM for Time-Series
```python
# Pseudocode for LSTM-based anomaly detection
class LSTMSequenceDetector:
    def __init__(self, sequence_length=10):
        self.sequence_length = sequence_length
        self.model = self._build_lstm()
    
    def _build_lstm(self):
        # Keras/TensorFlow model
        model = Sequential([
            LSTM(64, input_shape=(self.sequence_length, 1)),
            RepeatVector(self.sequence_length),
            LSTM(64, return_sequences=True),
            TimeDistributed(Dense(1)),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def fit(self, X_train):
        # Train autoencoder to reconstruct normal sequences
        self.model.fit(X_train, X_train, epochs=50)
    
    def detect_anomaly(self, X_test):
        # High reconstruction error = anomaly
        reconstructed = self.model.predict(X_test)
        error = np.mean(np.square(X_test - reconstructed))
        return error > self.threshold
```

### Option 2: TensorFlow/PyTorch

#### Autoencoder for Normal Behavior Modeling
```python
import torch
import torch.nn as nn

class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def detect_anomaly(self, x, threshold):
        with torch.no_grad():
            reconstructed = self.forward(x)
            error = torch.mean((x - reconstructed) ** 2)
        return error > threshold
```

#### Transformer-Based Sequence Prediction
```python
# For detecting anomalous sequences in system logs
class TransformerDetector(nn.Module):
    def __init__(self, vocab_size, d_model=64, nhead=4, num_layers=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model, nhead),
            num_layers
        )
        self.fc = nn.Linear(d_model, vocab_size)
    
    def forward(self, x):
        x = self.embedding(x)
        x = self.transformer(x)
        return self.fc(x)
```

---

## Training Data Requirements

### Data Collection
1. **Baseline Period**: Collect 7-30 days of normal operation data
2. **Feature Engineering**: 
   - Process counts, CPU, memory, network over time
   - Authentication patterns (times, sources, users)
   - File access patterns
   - Network connection patterns

### Data Storage
```
data/
  ml_training/
    process_baseline.csv
    network_baseline.csv
    auth_baseline.csv
    labels/
      anomaly_labels.csv
```

### Data Format
```csv
timestamp,process_count,cpu_percent,memory_percent,network_connections,is_anomaly
2026-04-01T10:00:00,150,45.2,62.1,45,0
2026-04-01T10:01:00,320,89.5,78.3,120,1
```

---

## Model Deployment

### Versioning with MLflow
```python
import mlflow

with mlflow.start_run():
    mlflow.sklearn.log_model(model, "anomaly_detector")
    mlflow.log_param("contamination", 0.1)
    mlflow.log_metric("f1_score", 0.95)
```

### A/B Testing
1. Deploy new model alongside current model
2. Route small percentage of traffic to new model
3. Compare detection rates and false positives
4. Gradually increase traffic if performance is better

### Performance Monitoring
- Track detection latency
- Monitor false positive rate
- Alert on model drift

---

## Integration with Suraksha

### Step 1: Model Training Pipeline
```python
# train_model.py
from sklearn.ensemble import IsolationForest
import pandas as pd
import joblib

def train_model(data_path):
    df = pd.read_csv(data_path)
    X = df.drop(['timestamp', 'is_anomaly'], axis=1)
    
    model = IsolationForest(contamination=0.1)
    model.fit(X)
    
    joblib.dump(model, 'models/anomaly_detector.pkl')
```

### Step 2: Inference Integration
```python
# In analysis/ml_anomaly.py
import joblib
import numpy as np

class MLAnomalyDetector:
    def __init__(self, model_path='models/anomaly_detector.pkl'):
        self.model = joblib.load(model_path)
    
    def detect(self, sensor_data: dict) -> dict:
        features = self._extract_features(sensor_data)
        score = self.model.score_samples([features])[0]
        
        return {
            'is_anomaly': score < -0.5,
            'anomaly_score': abs(score),
            'confidence': self._calculate_confidence(score)
        }
```

### Step 3: Hybrid Approach
Combine statistical + ML for better results:
```python
class HybridDetector:
    def __init__(self):
        self.statistical = StatisticalAnomalyDetector()
        self.ml = MLAnomalyDetector()
    
    def detect(self, data):
        stat_result = self.statistical.detect(data)
        ml_result = self.ml.detect(data)
        
        # Either method can flag an anomaly
        is_anomaly = stat_result['is_anomaly'] or ml_result['is_anomaly']
        
        return {
            'is_anomaly': is_anomaly,
            'methods': [stat_result, ml_result],
            'confidence': max(stat_result.get('score', 0), ml_result.get('confidence', 0))
        }
```

---

## Recommended Implementation Path

1. **Phase 1**: Use statistical methods (current implementation)
2. **Phase 2**: Collect labeled training data during operations
3. **Phase 3**: Train sklearn Isolation Forest on baseline
4. **Phase 4**: A/B test statistical vs ML detection
5. **Phase 5**: Deploy LSTM for time-series if needed

---

## Demo Mode

The current `analysis/ml_anomaly.py` includes:
- Synthetic data generation for testing
- Placeholder class structure for ML integration
- Clear comments on where to add real ML code

Run in demo mode:
```bash
python -c "from analysis.statistical_anomaly import StatisticalAnomalyDetector; d = StatisticalAnomalyDetector(); d.run_demo()"
```

---

## References

- [Isolation Forest Paper](https://doi.org/10.1109/ICDM.2008.17)
- [LSTM Anomaly Detection](https://arxiv.org/abs/1802.03903)
- [Scikit-learn Documentation](https://scikit-learn.org/stable/)
- [PyTorch Documentation](https://pytorch.org/docs/)

---

*Document Version: 1.0*
*Created: 2026-04-19*
*Project: Suraksha - Secure Monitoring Agent*