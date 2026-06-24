import sys
import os
import json
import random
import asyncio
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

# Path setup — allow running from project root or ml-training/
BACKEND_DIR = str(Path(__file__).resolve().parent.parent / "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import AsyncSessionLocal
from sqlalchemy import text

warnings.filterwarnings("ignore")

# Output directory
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODELS_DIR / "traffic_forecaster.pt"

# Known weather conditions mapping
WEATHER_CONDITIONS = ["clear", "cloudy", "mist", "fog", "rain", "heavy rain", "thunderstorm", "snow"]
WEATHER_MAP = {cond: float(i) for i, cond in enumerate(WEATHER_CONDITIONS)}

# Default free-flow speeds by road type
DEFAULT_SPEEDS = {
    'motorway': 80.0, 'trunk': 70.0, 'primary': 60.0,
    'secondary': 50.0, 'tertiary': 40.0, 'residential': 30.0,
    'living_street': 15.0, 'unclassified': 30.0
}

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
        # We take the output of the last time step
        # lstm_out[-1] shape: (batch_size, hidden_dim)
        out = self.fc(lstm_out[-1])
        return out


def simulate_segment_series(base_speed, road_type, max_speed, base_weather_encoded, num_steps=96, step_min=15):
    """Simulate a realistic sequence of speeds and weather conditions for a segment."""
    speeds = []
    weather_encs = []
    hours = []
    days = []
    
    current_speed = base_speed
    current_weather = base_weather_encoded
    day_of_week = random.randint(0, 6) # start on a random day
    
    for step in range(num_steps):
        time_min = step * step_min
        hour = (time_min / 60.0) % 24
        day = (day_of_week + int(time_min / 1440.0)) % 7
        
        # Rush hour penalty: morning (8-10 AM) and evening (5-7 PM)
        is_rush = (8.0 <= hour <= 10.0) or (17.0 <= hour <= 19.0)
        # Weekday vs weekend rush hour severity
        rush_severity = 0.35 if day < 5 else 0.10
        
        # Base factor based on rush hour
        factor = 1.0
        if is_rush:
            factor -= rush_severity
            
        # Night driving factor
        is_night = (hour >= 22.0 or hour <= 5.0)
        if is_night:
            factor -= 0.05
        
        # Weather simulation transitions
        if random.random() < 0.10:
            if random.random() < 0.70:
                current_weather = base_weather_encoded
            else:
                current_weather = random.randint(0, len(WEATHER_CONDITIONS) - 1)
                
        # Weather speed penalty
        weather_penalty = 0.0
        if current_weather in [4, 5, 6]:  # rain, heavy rain, thunderstorm
            weather_penalty = 0.25
        elif current_weather in [2, 3]:  # mist, fog
            weather_penalty = 0.15
            
        factor -= weather_penalty
        
        # Speed dynamics: auto-regressive speed with noise
        target_speed = max_speed * factor
        current_speed = 0.7 * current_speed + 0.3 * target_speed + random.normalvariate(0, 1.5)
        current_speed = max(5.0, min(current_speed, max_speed))
        
        speeds.append(current_speed)
        weather_encs.append(float(current_weather))
        hours.append(hour)
        days.append(float(day))
        
    return hours, days, speeds, weather_encs


async def fetch_segments_data():
    """Fetch road segments and their traffic speeds & weather."""
    print("Fetching segments and traffic conditions from database...")
    async with AsyncSessionLocal() as db:
        # Get count of segments first
        count_res = await db.execute(text("SELECT COUNT(*) FROM road_segments"))
        total_segments = count_res.scalar()
        print(f"Total road segments in DB: {total_segments}")
        
        # Query up to 5,000 segments to keep training fast
        query = text("""
            SELECT 
                rs.id AS segment_id,
                rs.road_type,
                rs.max_speed,
                tc.speed_kmh AS current_speed,
                wg.weather_condition
            FROM road_segments rs
            LEFT JOIN (
                SELECT DISTINCT ON (segment_id) segment_id, speed_kmh
                FROM traffic_conditions
                ORDER BY segment_id, recorded_at DESC
            ) tc ON rs.id = tc.segment_id
            CROSS JOIN LATERAL (
                SELECT weather_condition
                FROM weather_grid
                ORDER BY cell_geometry <-> ST_Centroid(rs.geometry)
                LIMIT 1
            ) wg
            ORDER BY rs.id
            LIMIT 5000
        """)
        
        result = await db.execute(query)
        rows = result.fetchall()
        print(f"Fetched {len(rows)} segments.")
        return rows


def generate_dataset(rows, seq_len=4, future_offset=2):
    X_list = []
    y_list = []
    
    print("Generating simulated time-series datasets...")
    for idx, (segment_id, road_type, max_speed, current_speed, weather_cond) in enumerate(rows):
        if idx > 0 and idx % 1000 == 0:
            print(f"  Processed {idx} segments...")
            
        max_sp = float(max_speed or DEFAULT_SPEEDS.get(road_type, 30.0))
        curr_sp = float(current_speed or max_sp)
        
        weather_str = (weather_cond or "clear").lower().strip()
        weather_encoded = WEATHER_MAP.get(weather_str, 0.0)
        
        # Simulate 96 steps (24 hours at 15-minute intervals)
        hours, days, speeds, weather_encs = simulate_segment_series(
            base_speed=curr_sp,
            road_type=road_type,
            max_speed=max_sp,
            base_weather_encoded=weather_encoded,
            num_steps=96,
            step_min=15
        )
        
        # Create sequences of seq_len steps of history to predict step t + future_offset
        for t in range(seq_len - 1, len(speeds) - future_offset):
            seq_x = []
            for i in range(seq_len - 1, -1, -1):
                idx_t = t - i
                h_scaled = hours[idx_t] / 24.0
                d_scaled = days[idx_t] / 7.0
                s_scaled = speeds[idx_t] / 100.0
                w_scaled = weather_encs[idx_t] / 7.0
                seq_x.append([h_scaled, d_scaled, s_scaled, w_scaled])
            
            X_list.append(seq_x)
            y_list.append([speeds[t + future_offset] / 100.0])
            
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)
    
    print(f"Dataset generated. X shape: {X.shape}, y shape: {y.shape}")
    return X, y


def train_model(X, y, epochs=10, batch_size=512, lr=0.001):
    num_samples = X.shape[0]
    indices = np.arange(num_samples)
    np.random.shuffle(indices)
    
    split = int(0.8 * num_samples)
    train_idx, val_idx = indices[:split], indices[split:]
    
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")
    
    model = TrafficLSTM(input_dim=4, hidden_dim=32, num_layers=2, output_dim=1).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            # Transpose shape: (batch_size, seq_len, features) -> (seq_len, batch_size, features)
            batch_x = batch_x.transpose(0, 1)
            
            optimizer.zero_grad()
            predictions = model(batch_x)
            loss = criterion(predictions, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_x.size(1)
            
        train_loss /= len(train_idx)
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_mae = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                batch_x = batch_x.transpose(0, 1)
                
                predictions = model(batch_x)
                loss = criterion(predictions, batch_y)
                val_loss += loss.item() * batch_x.size(1)
                
                # Compute MAE in actual speed km/h (target and pred scaled by 100)
                mae = torch.mean(torch.abs(predictions - batch_y)) * 100.0
                val_mae += mae.item() * batch_x.size(1)
                
        val_loss /= len(val_idx)
        val_mae /= len(val_idx)
        val_rmse = np.sqrt(val_loss) * 100.0
        
        print(f"Epoch {epoch+1:02d}/{epochs:02d} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f} | Val MAE: {val_mae:.2f} km/h | Val RMSE: {val_rmse:.2f} km/h")
        
        # Save model if validation loss improves
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint = {
                'state_dict': model.state_dict(),
                'input_dim': 4,
                'hidden_dim': 32,
                'num_layers': 2,
                'seq_len': 4,
                'future_offset': 2,
                'weather_conditions': WEATHER_CONDITIONS
            }
            torch.save(checkpoint, MODEL_PATH)
            
    print(f"Model successfully saved to: {MODEL_PATH}")


async def main():
    rows = await fetch_segments_data()
    if not rows:
        print("Error: No segments found in the database. Cannot train model.")
        return
        
    X, y = generate_dataset(rows, seq_len=4, future_offset=2)
    train_model(X, y, epochs=10, batch_size=512)


if __name__ == "__main__":
    asyncio.run(main())
