"""
Asphr Hazard Prediction Model — Training Pipeline
===================================================
Aggregates per-segment features from the Supabase database:
  - IoT vibration statistics (mean, std, max, count)
  - Weather conditions (precipitation, visibility, condition one-hot)
  - Traffic conditions (speed, congestion, volume)
  - Road metadata (road_type one-hot, lanes, length, has_speed_bump)
  - Temporal features (hour_of_day, is_night)

Computes a continuous hazard_score label via the sigmoid formula and trains a
Stacking ensemble: HistGradientBoostingRegressor + ExtraTreesRegressor +
RandomForestRegressor -> HuberRegressor meta-learner.  Exports:
  - ml-training/models/hazard_model.pkl   (trained model)
  - ml-training/models/feature_columns.json (ordered feature names)

Usage:
    python ml-training/train_hazard_model.py
"""

import sys
import os
import json
import math
import asyncio
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    ExtraTreesRegressor,
    RandomForestRegressor,
    StackingRegressor,
)
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# ---------------------------------------------------------------------------
# Path setup — allow running from project root or ml-training/
# ---------------------------------------------------------------------------
BACKEND_DIR = str(Path(__file__).resolve().parent.parent / "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import AsyncSessionLocal
from sqlalchemy import text

warnings.filterwarnings("ignore", category=FutureWarning)

# Output directory
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS_DIR / "hazard_model.pkl"
COLUMNS_PATH = MODELS_DIR / "feature_columns.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sigmoid(x: float) -> float:
    """Standard sigmoid, clamped input to avoid overflow."""
    x = max(-10.0, min(10.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# Known road types for one-hot encoding
ROAD_TYPES = [
    "motorway", "trunk", "primary", "secondary",
    "tertiary", "residential", "living_street", "unclassified",
]

# Known weather conditions for one-hot encoding
WEATHER_CONDITIONS = ["clear", "cloudy", "mist", "fog", "rain", "heavy rain", "thunderstorm", "snow"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

async def fetch_training_data() -> pd.DataFrame:
    """
    Fetch and join IoT readings, traffic, weather, and road segment metadata
    per segment_id.  Returns a flat DataFrame ready for feature engineering.
    """
    async with AsyncSessionLocal() as db:
        # ---- 1. IoT vibration aggregates per segment ----
        iot_query = text("""
            SELECT
                segment_id,
                AVG(vibration_level)  AS mean_vibration,
                STDDEV(vibration_level) AS std_vibration,
                MAX(vibration_level)  AS max_vibration,
                COUNT(*)              AS reading_count,
                AVG(EXTRACT(HOUR FROM timestamp)) AS avg_hour
            FROM iot_readings
            WHERE segment_id IS NOT NULL
            GROUP BY segment_id
        """)
        iot_result = await db.execute(iot_query)
        iot_rows = iot_result.fetchall()
        iot_df = pd.DataFrame(
            iot_rows,
            columns=["segment_id", "mean_vibration", "std_vibration",
                      "max_vibration", "reading_count", "avg_hour"]
        )
        print(f"  IoT aggregates: {len(iot_df)} segments with readings")

        # ---- 2. Traffic conditions (latest per segment) ----
        traffic_query = text("""
            SELECT DISTINCT ON (segment_id)
                segment_id,
                speed_kmh,
                congestion_level,
                traffic_volume
            FROM traffic_conditions
            WHERE segment_id IS NOT NULL
            ORDER BY segment_id, recorded_at DESC
        """)
        traffic_result = await db.execute(traffic_query)
        traffic_rows = traffic_result.fetchall()
        traffic_df = pd.DataFrame(
            traffic_rows,
            columns=["segment_id", "speed_kmh", "congestion_level", "traffic_volume"]
        )
        print(f"  Traffic conditions: {len(traffic_df)} segments")

        # ---- 3. Road segment metadata ----
        road_query = text("""
            SELECT
                id AS segment_id,
                road_type,
                lanes,
                length_meters,
                has_speed_bump,
                ST_Y(ST_Centroid(geometry)) AS centroid_lat,
                ST_X(ST_Centroid(geometry)) AS centroid_lon
            FROM road_segments
        """)
        road_result = await db.execute(road_query)
        road_rows = road_result.fetchall()
        road_df = pd.DataFrame(
            road_rows,
            columns=["segment_id", "road_type", "lanes", "length_meters",
                      "has_speed_bump", "centroid_lat", "centroid_lon"]
        )
        print(f"  Road segments: {len(road_df)} total")

        # ---- 4. Weather grid (fetch all cells for spatial join) ----
        weather_query = text("""
            SELECT
                ST_Y(ST_Centroid(cell_geometry)) AS cell_lat,
                ST_X(ST_Centroid(cell_geometry)) AS cell_lon,
                precipitation_mm,
                visibility_km,
                weather_condition
            FROM weather_grid
        """)
        weather_result = await db.execute(weather_query)
        weather_rows = weather_result.fetchall()
        weather_df = pd.DataFrame(
            weather_rows,
            columns=["cell_lat", "cell_lon", "precipitation_mm",
                      "visibility_km", "weather_condition"]
        )
        print(f"  Weather cells: {len(weather_df)}")

        # ---- 5. Existing hazard scores (as ground-truth reference) ----
        hazard_query = text("""
            SELECT segment_id, hazard_score
            FROM segment_hazards
            WHERE segment_id IS NOT NULL
        """)
        hazard_result = await db.execute(hazard_query)
        hazard_rows = hazard_result.fetchall()
        hazard_df = pd.DataFrame(hazard_rows, columns=["segment_id", "db_hazard_score"])
        print(f"  Existing hazard scores: {len(hazard_df)} segments")

    # ---- Merge everything on segment_id ----
    # Start from road segments (the base table — every segment gets a row)
    df = road_df.copy()

    # IoT — left join (not all segments have IoT data)
    df = df.merge(iot_df, on="segment_id", how="left")

    # Traffic — left join
    df = df.merge(traffic_df, on="segment_id", how="left")

    # Existing hazard scores — left join
    df = df.merge(hazard_df, on="segment_id", how="left")

    # Weather — nearest-cell join (find closest weather cell to each segment centroid)
    if len(weather_df) > 0 and len(df) > 0:
        weather_lats = weather_df["cell_lat"].values
        weather_lons = weather_df["cell_lon"].values

        best_precip = []
        best_visibility = []
        best_condition = []

        for _, row in df.iterrows():
            dists = np.sqrt(
                (weather_lats - row["centroid_lat"])**2 +
                (weather_lons - row["centroid_lon"])**2
            )
            idx = np.argmin(dists)
            best_precip.append(weather_df.iloc[idx]["precipitation_mm"])
            best_visibility.append(weather_df.iloc[idx]["visibility_km"])
            best_condition.append(weather_df.iloc[idx]["weather_condition"])

        df["precipitation_mm"] = best_precip
        df["visibility_km"] = best_visibility
        df["weather_condition"] = best_condition
    else:
        df["precipitation_mm"] = 0.0
        df["visibility_km"] = 10.0
        df["weather_condition"] = "clear"

    return df


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Build the final feature matrix and compute the target label.

    Returns (features_df, feature_column_names).
    """
    # ---- Fill NaN values with sensible defaults ----
    df["mean_vibration"] = df["mean_vibration"].fillna(0.0)
    df["std_vibration"] = df["std_vibration"].fillna(0.0)
    df["max_vibration"] = df["max_vibration"].fillna(0.0)
    df["reading_count"] = df["reading_count"].fillna(0)
    df["avg_hour"] = df["avg_hour"].fillna(12.0)
    df["speed_kmh"] = df["speed_kmh"].fillna(30.0)
    df["congestion_level"] = df["congestion_level"].fillna(0)
    df["traffic_volume"] = df["traffic_volume"].fillna(50)
    df["lanes"] = df["lanes"].fillna(2)
    df["length_meters"] = df["length_meters"].fillna(100.0)
    df["has_speed_bump"] = df["has_speed_bump"].fillna(False).astype(int)
    df["precipitation_mm"] = df["precipitation_mm"].fillna(0.0)
    df["visibility_km"] = df["visibility_km"].fillna(10.0)
    df["weather_condition"] = df["weather_condition"].fillna("clear")
    df["db_hazard_score"] = df["db_hazard_score"].fillna(0.0)

    # ---- Temporal features ----
    df["hour_of_day"] = df["avg_hour"].astype(float)
    df["is_night"] = ((df["hour_of_day"] >= 20) | (df["hour_of_day"] <= 6)).astype(int)

    # ---- Road type one-hot ----
    for rt in ROAD_TYPES:
        df[f"road_{rt}"] = (df["road_type"] == rt).astype(int)

    # ---- Weather condition one-hot ----
    df["weather_condition"] = df["weather_condition"].str.lower().str.strip()
    for wc in WEATHER_CONDITIONS:
        df[f"weather_{wc.replace(' ', '_')}"] = (df["weather_condition"] == wc).astype(int)

    # ---- Derived features ----
    df["vibration_normalized"] = df["mean_vibration"] / 5.0  # cap at 5.0
    df["vibration_normalized"] = df["vibration_normalized"].clip(0, 1)

    # ---- Compute target label: hazard_score = sigmoid(vib_norm + weather_pen + traffic_pen) ----
    weather_penalty = df["weather_condition"].map({
        "heavy rain": 0.4, "thunderstorm": 0.4, "snow": 0.4,
        "rain": 0.3,
        "fog": 0.2, "mist": 0.2,
        "cloudy": 0.05,
        "clear": 0.0,
    }).fillna(0.0)

    traffic_penalty = df["congestion_level"].astype(float) * 0.1

    raw_score = df["vibration_normalized"] + weather_penalty + traffic_penalty
    df["hazard_label"] = raw_score.apply(sigmoid)

    # Where we have existing DB hazard scores > 0, blend them (trust DB data)
    has_db_score = df["db_hazard_score"] > 0.01
    df.loc[has_db_score, "hazard_label"] = (
        0.6 * df.loc[has_db_score, "hazard_label"] +
        0.4 * df.loc[has_db_score, "db_hazard_score"]
    )

    # ---- Assemble feature columns ----
    feature_cols = [
        # Vibration
        "mean_vibration", "std_vibration", "max_vibration", "reading_count",
        "vibration_normalized",
        # Traffic
        "speed_kmh", "congestion_level", "traffic_volume",
        # Road metadata
        "lanes", "length_meters", "has_speed_bump",
        # Weather numeric
        "precipitation_mm", "visibility_km",
        # Temporal
        "hour_of_day", "is_night",
    ]
    # Road type one-hot
    feature_cols += [f"road_{rt}" for rt in ROAD_TYPES]
    # Weather condition one-hot
    feature_cols += [f"weather_{wc.replace(' ', '_')}" for wc in WEATHER_CONDITIONS]

    X = df[feature_cols].copy()
    y = df["hazard_label"].copy()

    # Sanity: force numeric and fill any remaining NaN
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = y.fillna(0.5)

    return X, y, feature_cols


# ---------------------------------------------------------------------------
# Training  (ARCHITECTURE CHANGE — everything above this line is unchanged)
# ---------------------------------------------------------------------------

def train_model(X: pd.DataFrame, y: pd.Series, feature_cols: list[str]):
    """
    Stacking ensemble:
      Base layer  — HistGradientBoostingRegressor  (histogram-based, fast, handles large N)
                  — ExtraTreesRegressor            (high-variance complement, parallel)
                  — RandomForestRegressor          (stable bagging anchor)
      Meta layer  — HuberRegressor                 (robust to the label compression artefact)

    passthrough=True feeds the original 31 features alongside the 3 base
    predictions into the meta-learner, giving it full context to correct
    systematic errors from each base model.
    """
    print(f"\n  Training on {len(X)} samples with {len(feature_cols)} features...")

    # Stratified-ish split: bin hazard scores and stratify
    y_bins = pd.cut(y, bins=5, labels=False)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y_bins
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    # ------------------------------------------------------------------
    # Base estimator 1 — HistGradientBoostingRegressor
    #   Histogram-based splits = ~10-50x faster than sklearn GBM on 187k rows.
    #   early_stopping + validation_fraction lets it find the optimal n_iter
    #   without manual tuning.  l2_regularization prevents leaf over-reliance
    #   on the dominant weather features.
    # ------------------------------------------------------------------
    hgbr = HistGradientBoostingRegressor(
        max_iter=800,
        max_depth=10,
        learning_rate=0.02,
        l2_regularization=0.15,
        min_samples_leaf=20,
        max_bins=255,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=30,
        random_state=42,
    )

    # ------------------------------------------------------------------
    # Base estimator 2 — ExtraTreesRegressor
    #   Randomised splits introduce high variance, maximising diversity
    #   vs the gradient-based learners.  n_jobs=-1 parallelises across
    #   all cores — critical at 187k samples.
    # ------------------------------------------------------------------
    et = ExtraTreesRegressor(
        n_estimators=400,
        max_depth=None,           # grow full trees; min_samples_leaf controls size
        min_samples_leaf=8,
        max_features=0.6,         # subsample features per split for diversity
        n_jobs=-1,
        random_state=42,
    )

    # ------------------------------------------------------------------
    # Base estimator 3 — RandomForestRegressor
    #   Bagging anchor — lower variance than ET, different bias profile
    #   to HGBR.  Together the three cover bias-variance space well.
    # ------------------------------------------------------------------
    rf = RandomForestRegressor(
        n_estimators=400,
        max_depth=18,
        min_samples_leaf=8,
        max_features=0.5,
        n_jobs=-1,
        random_state=42,
    )

    # ------------------------------------------------------------------
    # Meta-learner — Pipeline(StandardScaler -> HuberRegressor)
    #   passthrough=True means the meta-learner sees [hgbr_pred, et_pred,
    #   rf_pred, X] — 34 inputs total.  Raw features have wildly different
    #   scales (traffic_volume 5-800 vs base predictions 0-1), so we MUST
    #   scale before feeding into the linear HuberRegressor.
    #   max_iter=1000 gives lbfgs enough room to converge.
    # ------------------------------------------------------------------
    meta = Pipeline([
        ("scaler", StandardScaler()),
        ("huber", HuberRegressor(
            epsilon=1.15,
            alpha=0.001,
            max_iter=1000,
        )),
    ])

    # ------------------------------------------------------------------
    # Stacking ensemble
    #   cv=3 keeps wall-clock reasonable on 187k rows while still giving
    #   the meta-learner out-of-fold predictions for all training samples.
    # ------------------------------------------------------------------
    model = StackingRegressor(
        estimators=[
            ("hgbr", hgbr),
            ("et",   et),
            ("rf",   rf),
        ],
        final_estimator=meta,
        cv=3,
        n_jobs=-1,
        passthrough=True,
    )

    print("  Fitting stacking ensemble (3-fold CV for meta-features)...")
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0.0, 1.0)

    mae  = mean_absolute_error(y_test, y_pred)
    rmse = math.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)

    print(f"\n  --- Evaluation (hold-out 20%) ---")
    print(f"  MAE  : {mae:.4f}")
    print(f"  RMSE : {rmse:.4f}")
    print(f"  R2   : {r2:.4f}")

    # Per-base-model feature importances
    print(f"\n  --- Top 10 Feature Importances (HistGBR) ---")
    hgbr_fitted = model.named_estimators_["hgbr"]
    try:
        importances = np.array(hgbr_fitted.feature_importances_)
        if importances.sum() > 0:
            idx = np.argsort(importances)[::-1][:10]
            for i in idx:
                print(f"    {feature_cols[i]:30s} {importances[i]:.4f}")
    except Exception:
        print("    (not available for HistGBR)")

    print(f"\n  --- Top 10 Feature Importances (ExtraTrees) ---")
    et_fitted = model.named_estimators_["et"]
    importances_et = et_fitted.feature_importances_
    idx_et = np.argsort(importances_et)[::-1][:10]
    for i in idx_et:
        print(f"    {feature_cols[i]:30s} {importances_et[i]:.4f}")

    return model


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_model(model, feature_cols: list[str]):
    """Save trained model and feature column ordering."""
    joblib.dump(model, MODEL_PATH)
    print(f"\n  Model saved -> {MODEL_PATH}")

    with open(COLUMNS_PATH, "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"  Feature columns saved -> {COLUMNS_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("  Asphr Hazard Prediction Model -- Training Pipeline")
    print("=" * 60)

    print("\n[1/4] Fetching training data from Supabase...")
    df = await fetch_training_data()

    if len(df) == 0:
        print("\nERROR: No road segments found. Run the FastAPI server and seed script first.")
        return

    print(f"\n[2/4] Engineering features...")
    X, y, feature_cols = engineer_features(df)
    print(f"  Feature matrix shape: {X.shape}")
    print(f"  Label distribution: min={y.min():.3f}, mean={y.mean():.3f}, max={y.max():.3f}")

    print(f"\n[3/4] Training Stacking Ensemble (HistGBR + ExtraTrees + RF -> Huber)...")
    model = train_model(X, y, feature_cols)

    print(f"\n[4/4] Exporting model artifacts...")
    export_model(model, feature_cols)

    print("\n" + "=" * 60)
    print("  Training complete!")
    print("=" * 60)
    print("\nNext: Restart the FastAPI server -- the model will be loaded at startup.")


if __name__ == "__main__":
    asyncio.run(main())