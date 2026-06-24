"""
Traffic Forecaster — ML Inference Module
=========================================
Singleton class loaded during FastAPI startup. Provides:
  - predict_future_speed(current_speed, weather_cond_str, hour_of_day, day_of_week) -> float
  - predict_batch(feature_dicts) -> list[float]

Graceful fallback: if the model file is missing or corrupt, predictions
return None, and graph weight enrichment falls back to current speeds.
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class TrafficLSTM(nn.Module):
    def __init__(self, input_dim=4, hidden_dim=32, num_layers=2, output_dim=1):
        super(TrafficLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=False)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        # x shape: (seq_len, batch_size, input_dim)
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[-1])
        return out

class TrafficForecaster:
    """Singleton ML traffic speed forecaster loaded once at application startup."""

    _instance: Optional["TrafficForecaster"] = None

    def __init__(self):
        self.model: Optional[TrafficLSTM] = None
        self.seq_len = 4
        self.future_offset = 2
        self.weather_conditions = ["clear", "cloudy", "mist", "fog", "rain", "heavy rain", "thunderstorm", "snow"]
        self.weather_map = {cond: float(i) for i, cond in enumerate(self.weather_conditions)}
        self._ready = False

    @classmethod
    def get_instance(cls) -> "TrafficForecaster":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self, model_path: str) -> bool:
        """
        Load a trained PyTorch model.
        """
        model_file = Path(model_path)
        if not model_file.exists():
            logger.warning(f"Traffic forecaster model file not found: {model_file}. ML predictions disabled.")
            return False

        try:
            # Load checkpoint (map to CPU)
            checkpoint = torch.load(model_file, map_location=torch.device('cpu'))
            
            # Reconstruct architecture parameters from checkpoint metadata
            input_dim = checkpoint.get('input_dim', 4)
            hidden_dim = checkpoint.get('hidden_dim', 32)
            num_layers = checkpoint.get('num_layers', 2)
            self.seq_len = checkpoint.get('seq_len', 4)
            self.future_offset = checkpoint.get('future_offset', 2)
            self.weather_conditions = checkpoint.get('weather_conditions', self.weather_conditions)
            self.weather_map = {cond: float(i) for i, cond in enumerate(self.weather_conditions)}

            # Initialize model and load state dict
            self.model = TrafficLSTM(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                output_dim=1
            )
            self.model.load_state_dict(checkpoint['state_dict'])
            self.model.eval() # evaluation mode
            
            self._ready = True
            logger.info(f"Traffic forecaster model loaded successfully from {model_file}.")
            print(f"[TrafficForecaster] Model loaded successfully ({input_dim} features, TrafficLSTM)")
            return True
        except Exception as e:
            logger.error(f"Failed to load traffic forecaster model: {e}")
            print(f"[TrafficForecaster] ERROR loading model: {e}")
            self.model = None
            self._ready = False
            return False

    @property
    def is_ready(self) -> bool:
        return self._ready and self.model is not None

    def _build_sequence(self, current_speed: float, weather_cond_str: str, hour_of_day: float, day_of_week: int) -> torch.Tensor:
        """
        Builds a historical input sequence of length seq_len (e.g. 4 steps)
        from a single snapshot of data by back-populating prior steps.
        
        Returns a PyTorch tensor of shape (seq_len, 1, input_dim) ready for the LSTM.
        """
        weather_str = (weather_cond_str or "clear").lower().strip()
        weather_encoded = self.weather_map.get(weather_str, 0.0)

        seq_data = []
        # Construct seq_len historical steps (e.g., t-45m, t-30m, t-15m, t)
        for i in range(self.seq_len - 1, -1, -1):
            # Back-calculate time (15 mins = 0.25 hours per step)
            step_hour = (hour_of_day - i * 0.25) % 24
            # Keep it simple: day of week
            step_day = float(day_of_week)
            
            # Simple assumption: historical speeds were close to current speed
            step_speed = current_speed
            
            # Scale features
            h_scaled = step_hour / 24.0
            d_scaled = step_day / 7.0
            s_scaled = step_speed / 100.0
            w_scaled = weather_encoded / 7.0
            
            seq_data.append([h_scaled, d_scaled, s_scaled, w_scaled])

        # Convert to tensor: shape (seq_len, input_dim) -> reshape to (seq_len, 1, input_dim)
        tensor = torch.tensor(seq_data, dtype=torch.float32).unsqueeze(1)
        return tensor

    def predict_future_speed(
        self,
        current_speed: float,
        weather_cond_str: str,
        hour_of_day: float,
        day_of_week: int
    ) -> Optional[float]:
        """
        Predict future speed (30 minutes ahead) for a single segment.
        """
        if not self.is_ready:
            return None

        try:
            with torch.no_grad():
                X = self._build_sequence(current_speed, weather_cond_str, hour_of_day, day_of_week)
                # X shape: (seq_len, 1, input_dim)
                pred_scaled = self.model(X).item()
                # Rescale speed from [0, 1] to original scale
                predicted_speed = pred_scaled * 100.0
                return max(5.0, min(predicted_speed, 120.0))
        except Exception as e:
            logger.error(f"TrafficForecaster prediction error: {e}")
            return None

    def predict_batch(self, feature_dicts: List[Dict[str, Any]]) -> Optional[List[float]]:
        """
        Predict future speeds for a batch of segments.
        
        Each feature dict in feature_dicts must contain:
          - "speed_kmh": current speed
          - "weather_condition": weather condition string
          - "hour_of_day": current hour
          - "day_of_week": current day of week (0-6)
        """
        if not self.is_ready:
            return None

        if not feature_dicts:
            return []

        try:
            batch_size = len(feature_dicts)
            # Pre-allocate numpy array: (seq_len, batch_size, input_dim)
            arr = np.zeros((self.seq_len, batch_size, 4), dtype=np.float32)
            
            for idx, fd in enumerate(feature_dicts):
                curr_sp = float(fd.get("speed_kmh", 30.0))
                weather_str = fd.get("weather_condition", "clear")
                weather_encoded = self.weather_map.get(weather_str.lower().strip(), 0.0)
                hour = float(fd.get("hour_of_day", 12.0))
                day = float(fd.get("day_of_week", 0.0))
                
                for i in range(self.seq_len - 1, -1, -1):
                    step_hour = (hour - i * 0.25) % 24
                    step_day = day
                    step_speed = curr_sp
                    
                    # Scale features
                    arr[self.seq_len - 1 - i, idx, 0] = step_hour / 24.0
                    arr[self.seq_len - 1 - i, idx, 1] = step_day / 7.0
                    arr[self.seq_len - 1 - i, idx, 2] = step_speed / 100.0
                    arr[self.seq_len - 1 - i, idx, 3] = weather_encoded / 7.0
            
            X = torch.from_numpy(arr)
            
            with torch.no_grad():
                preds_scaled = self.model(X) # output shape (batch_size, 1)
                preds = preds_scaled.squeeze(-1).tolist()
                
            return [max(5.0, min(p * 100.0, 120.0)) for p in preds]
        except Exception as e:
            logger.error(f"TrafficForecaster batch prediction error: {e}")
            return None
