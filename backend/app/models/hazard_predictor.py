"""
Hazard Predictor — ML Inference Module
========================================
Singleton class loaded during FastAPI startup.  Provides:
  - predict_segment_hazard(features_dict) → float  (single segment)
  - predict_batch(feature_dicts)          → list[float] (bulk)

Graceful fallback: if the model file is missing or corrupt, predictions
return None and the graph enrichment code falls back to DB hazard scores.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import joblib

logger = logging.getLogger(__name__)


class HazardPredictor:
    """Singleton ML hazard predictor loaded once at application startup."""

    _instance: Optional["HazardPredictor"] = None

    def __init__(self):
        self.model = None
        self.feature_columns: list[str] = []
        self._ready = False

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "HazardPredictor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def load_model(self, model_path: str, columns_path: str) -> bool:
        """
        Load a trained sklearn model and its feature column ordering.

        Args:
            model_path:   Path to the .pkl model file.
            columns_path: Path to the feature_columns.json file.

        Returns:
            True if loaded successfully, False otherwise.
        """
        model_file = Path(model_path)
        columns_file = Path(columns_path)

        if not model_file.exists():
            logger.warning(f"Hazard model file not found: {model_file}. ML predictions disabled.")
            return False

        if not columns_file.exists():
            logger.warning(f"Feature columns file not found: {columns_file}. ML predictions disabled.")
            return False

        try:
            self.model = joblib.load(model_file)
            with open(columns_file) as f:
                self.feature_columns = json.load(f)
            self._ready = True
            logger.info(
                f"Hazard prediction model loaded — "
                f"{len(self.feature_columns)} features, model type: {type(self.model).__name__}"
            )
            print(
                f"[HazardPredictor] Model loaded successfully "
                f"({len(self.feature_columns)} features, {type(self.model).__name__})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load hazard model: {e}")
            print(f"[HazardPredictor] ERROR loading model: {e}")
            self.model = None
            self._ready = False
            return False

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True if the model is loaded and ready for predictions."""
        return self._ready and self.model is not None

    def _build_feature_vector(self, features: dict) -> np.ndarray:
        """
        Build a 1-D feature array from a dictionary of raw features,
        matching the order in self.feature_columns.

        Missing features default to 0.0.
        """
        return np.array(
            [float(features.get(col, 0.0)) for col in self.feature_columns],
            dtype=np.float64,
        )

    def predict_segment_hazard(self, features: dict) -> Optional[float]:
        """
        Predict hazard score for a single road segment.

        Args:
            features: Dict of feature_name → value.

        Returns:
            Float hazard score in [0.0, 1.0], or None if model not loaded.
        """
        if not self.is_ready:
            return None

        try:
            X = self._build_feature_vector(features).reshape(1, -1)
            pred = float(self.model.predict(X)[0])
            return max(0.0, min(1.0, pred))
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None

    def predict_batch(self, feature_dicts: list[dict]) -> Optional[list[float]]:
        """
        Predict hazard scores for multiple segments at once.

        Args:
            feature_dicts: List of dicts, one per segment.

        Returns:
            List of float hazard scores in [0.0, 1.0], or None if model not loaded.
        """
        if not self.is_ready:
            return None

        if not feature_dicts:
            return []

        try:
            X = np.array(
                [self._build_feature_vector(fd) for fd in feature_dicts],
                dtype=np.float64,
            )
            preds = self.model.predict(X)
            return [max(0.0, min(1.0, float(p))) for p in preds]
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            return None
