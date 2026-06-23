# Asphr Navigation Ecosystem — Strategic Build Guide
*A Scale.ai-style execution playbook for hackathon dominance*

---

## Executive Summary (Alexander's Lens)

Your hardware is a **data moat** — the IoT sensors create proprietary ground-truth that no Google Maps competitor can replicate. The software challenge is **orchestration**: turning raw sensor streams into differentiable routing intelligence without LLM APIs. 

**Core thesis**: Build a *multi-objective graph optimization engine* where edge weights are dynamically recomputed by ensemble ML models fed by your IoT fleet + public APIs. The "safest vs fastest vs straightest" is not three apps — it's one engine with tunable objective functions.

**Hackathon constraint**: Ship a working vertical slice (one city, 3 route types, live IoT plotting) rather than a perfect horizontal platform.

---

## Phase 0: Project Repository Architecture

Create a monorepo with clear separation of concerns for Railway + Vercel deployability.

```
asphr-navigation/
├── backend/                          # Python/FastAPI → Railway
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Environment variables
│   │   ├── models/                   # ML model definitions (PyTorch)
│   │   │   ├── __init__.py
│   │   │   ├── hazard_predictor.py   # Predicts road hazard scores
│   │   │   ├── route_optimizer.py    # Multi-objective pathfinding
│   │   │   └── traffic_forecaster.py # LSTM for traffic prediction
│   │   ├── algorithms/               # Core graph algorithms
│   │   │   ├── __init__.py
│   │   │   ├── graph_builder.py      # OSM → NetworkX graph
│   │   │   ├── dijkstra_variant.py   # Weighted shortest path
│   │   │   └── a_star_custom.py      # A* with dynamic heuristics
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── route_service.py      # Route computation orchestrator
│   │   │   ├── geocoding_service.py  # Forward/reverse geocoding
│   │   │   ├── iot_service.py        # Hardware data ingestion
│   │   │   └── weather_service.py    # Weather API aggregation
│   │   ├── routers/                  # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── routes.py             # /api/v1/routes/*
│   │   │   ├── geocode.py            # /api/v1/geocode/*
│   │   │   ├── iot.py                # /api/v1/iot/*
│   │   │   └── health.py             # /health
│   │   ├── schemas/                  # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── route_schemas.py
│   │   │   └── iot_schemas.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── geo_utils.py          # Haversine, coordinate transforms
│   ├── alembic/                      # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile                    # For Railway deployment
│   └── railway.toml                  # Railway config
│
├── frontend/                         # React/JavaScript → Vercel
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/                  # Mapbox GL JS wrapper
│   │   │   ├── RoutePanel/           # Route selection UI
│   │   │   ├── RouteTypes/           # Fastest/Safest/Straightest/Popular
│   │   │   ├── VehicleSelector/      # Bike/Car/Truck/Supercar
│   │   │   ├── IoTOverlay/           # Real-time sensor heatmap
│   │   │   └── SearchBar/            # Location search
│   │   ├── pages/
│   │   │   ├── Home.jsx              # Main map + routing interface
│   │   │   ├── RouteDetail.jsx       # Turn-by-turn + elevation/weather
│   │   │   └── Analytics.jsx         # IoT data dashboard (bonus)
│   │   ├── hooks/
│   │   │   ├── useMapbox.js
│   │   │   └── useRoutes.js          # React Query for backend calls
│   │   ├── services/
│   │   │   └── api.js                # Axios instance to FastAPI
│   │   ├── store/                    # Zustand state management
│   │   ├── App.jsx
│   │   └── index.js
│   ├── package.json
│   ├── vercel.json
│   └── .env.example
│
├── ml-training/                      # Jupyter notebooks (local only)
│   ├── notebooks/
│   ├── datasets/
│   └── models/                       # Exported .pt / .pkl files
│
├── infra/
│   └── supabase/
│       └── migrations/               # SQL table definitions
│
└── README.md
```

---

## Phase 1: Database Schema (Supabase/PostgreSQL + PostGIS)

**Step 1.1**: Enable PostGIS extension in Supabase dashboard (Database → Extensions → PostGIS).

**Step 1.2**: Execute these table creation queries in Supabase SQL Editor:

```sql
-- Core road network graph (extracted from OpenStreetMap)
CREATE TABLE road_segments (
    id SERIAL PRIMARY KEY,
    osm_way_id BIGINT,
    source_node BIGINT NOT NULL,
    target_node BIGINT NOT NULL,
    geometry GEOMETRY(LineString, 4326) NOT NULL,
    length_meters FLOAT NOT NULL,
    road_type VARCHAR(50),              -- motorway, residential, etc.
    max_speed INT,
    lanes INT,
    has_speed_bump BOOLEAN DEFAULT FALSE,
    is_toll BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_road_segments_geom ON road_segments USING GIST(geometry);
CREATE INDEX idx_road_segments_source ON road_segments(source_node);
CREATE INDEX idx_road_segments_target ON road_segments(target_node);

-- Dynamic hazard scores (updated by ML model + IoT)
CREATE TABLE segment_hazards (
    id SERIAL PRIMARY KEY,
    segment_id INT REFERENCES road_segments(id) ON DELETE CASCADE,
    hazard_score FLOAT NOT NULL CHECK (hazard_score BETWEEN 0 AND 1),
    hazard_type VARCHAR(50),            -- pothole, wet_road, accident_prone
    confidence FLOAT,
    source VARCHAR(20),                 -- 'iot', 'weather_api', 'ml_model'
    recorded_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP                -- TTL for transient hazards
);

CREATE INDEX idx_hazards_segment ON segment_hazards(segment_id);
CREATE INDEX idx_hazards_time ON segment_hazards(recorded_at);

-- IoT sensor readings from hardware fleet
CREATE TABLE iot_readings (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    segment_id INT REFERENCES road_segments(id),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    accel_x FLOAT,
    accel_y FLOAT,
    accel_z FLOAT,
    gyro_x FLOAT,
    gyro_y FLOAT,
    gyro_z FLOAT,
    vibration_level FLOAT,              -- derived: magnitude of accel
    road_condition VARCHAR(20),         -- smooth, moderate, rough, severe
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_iot_device ON iot_readings(device_id);
CREATE INDEX idx_iot_location ON iot_readings USING GIST(
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);
CREATE INDEX idx_iot_time ON iot_readings(timestamp);

-- Traffic conditions (from APIs + historical)
CREATE TABLE traffic_conditions (
    id SERIAL PRIMARY KEY,
    segment_id INT REFERENCES road_segments(id),
    speed_kmh FLOAT,
    congestion_level INT CHECK (congestion_level BETWEEN 0 AND 4),
    traffic_volume INT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_traffic_segment ON traffic_conditions(segment_id);
CREATE INDEX idx_traffic_time ON traffic_conditions(recorded_at);

-- Weather conditions per geographic grid cell
CREATE TABLE weather_grid (
    id SERIAL PRIMARY KEY,
    cell_geometry GEOMETRY(Polygon, 4326) NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    visibility_km FLOAT,
    precipitation_mm FLOAT,
    wind_speed_kmh FLOAT,
    weather_condition VARCHAR(50),      -- clear, rain, fog, snow
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_weather_geom ON weather_grid USING GIST(cell_geometry);

-- Popular places for "Popular Route" feature
CREATE TABLE popular_places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),               -- tourist, food, landmark
    geometry GEOMETRY(Point, 4326) NOT NULL,
    popularity_score FLOAT,
    city VARCHAR(100)
);

CREATE INDEX idx_places_geom ON popular_places USING GIST(geometry);
CREATE INDEX idx_places_city ON popular_places(city);

-- Vehicle profiles for routing constraints
CREATE TABLE vehicle_profiles (
    id SERIAL PRIMARY KEY,
    vehicle_type VARCHAR(50) NOT NULL,    -- bike, car, truck, supercar
    max_width_m FLOAT,
    max_height_m FLOAT,
    min_road_width_m FLOAT,
    avoid_speed_bumps BOOLEAN,
    allow_narrow_roads BOOLEAN,
    prefer_highways BOOLEAN
);

-- SOS alerts from hardware
CREATE TABLE sos_alerts (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    triggered_at TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    hospital_notified BOOLEAN DEFAULT FALSE
);

-- Route history for RLHF data collection
CREATE TABLE route_feedback (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    start_point GEOMETRY(Point, 4326),
    end_point GEOMETRY(Point, 4326),
    route_geometry GEOMETRY(LineString, 4326),
    route_type VARCHAR(20),             -- fastest, safest, etc.
    rating INT CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Phase 2: Free APIs & Data Sources

| Requirement | API | Endpoint Pattern | Rate Limit | Key Data |
|-------------|-----|------------------|------------|----------|
| **Base Maps & Geocoding** | Mapbox | `api.mapbox.com/geocoding/v5/mapbox.places/` | 50k/month free | Forward/reverse geocoding, directions |
| **OSM Road Data** | Overpass API | `overpass-api.de/api/interpreter` | Fair use | Raw road network for graph building |
| **Real-time Traffic** | TomTom Traffic API | `api.tomtom.com/traffic/services/4/flowSegmentData/` | 2.5k/day free | Speed, congestion per road segment |
| **Weather** | OpenWeatherMap | `api.openweathermap.org/data/2.5/weather` | 60 calls/min free | Temp, visibility, precipitation |
| **Weather (alt)** | Open-Meteo | `api.open-meteo.com/v1/forecast` | Unlimited | No API key needed |
| **Elevation** | Open-Elevation | `api.open-elevation.com/api/v1/lookup` | Fair use | Slope calculation for hazard scoring |
| **Popular Places** | Overpass API (OSM) | Query `tourism=attraction`, `amenity=restaurant` | Fair use | POI data for popular routes |

**API Orchestration Strategy**: Build a `DataAggregator` service that hits these APIs every 5 minutes, normalizes responses, and writes to your Supabase tables. Cache aggressively with Redis (or in-memory for hackathon).

---

## Phase 3: Backend Build — Step-by-Step

### Step 3.1: Environment Setup
1. Create Python virtual environment: `python -m venv venv`
2. `pip install fastapi uvicorn sqlalchemy psycopg2-binary geoalchemy2 shapely networkx osmnx scikit-learn torch pandas numpy httpx pydantic-settings`
3. Create `.env` file with Supabase connection string, Mapbox token, API keys.

### Step 3.2: FastAPI Skeleton (`app/main.py`)
1. Initialize FastAPI app with CORS middleware (allow Vercel domain).
2. Create lifespan context manager for startup/shutdown events.
3. Mount routers from `routers/` directory.
4. Health check endpoint at `/health` returning DB connection status.

### Step 3.3: Database Connection (`app/config.py`)
1. Use SQLAlchemy async engine (`create_async_engine`) with Supabase connection pool.
2. Define `get_db()` dependency for FastAPI route injection.
3. Create `Base` declarative base for ORM models.

### Step 3.4: Graph Construction Algorithm (`app/algorithms/graph_builder.py`)

**Purpose**: Convert OSM data into a traversable NetworkX graph with ML-enriched edge weights.

1. **Fetch OSM Data**: Use `osmnx.graph_from_place()` or Overpass API to download road network for target city.
2. **Simplify Graph**: `osmnx.simplify_graph()` to remove intermediate nodes.
3. **Enrich Edges**: For each edge, query:
   - `segment_hazards` → aggregate hazard score
   - `traffic_conditions` → current speed / congestion
   - `weather_grid` → weather impact factor
   - `iot_readings` → real-time vibration/condition
4. **Compute Composite Weights**:
   - **Fastest**: `weight = distance / (current_speed + ε)`
   - **Safest**: `weight = distance × (1 + hazard_score) × (1 + weather_penalty)`
   - **Straightest**: `weight = distance × (1 + angular_deviation_from_bearing)`
   - **Popular**: `weight = distance / (1 + nearby_popularity_density)`
5. **Store Graph**: Save as NetworkX pickle or adjacency list in memory (refresh every 5 min).

### Step 3.5: Multi-Objective Route Optimizer (`app/models/route_optimizer.py`)

**Core Algorithm**: Modified Dijkstra with dynamic edge weight recomputation.

1. **Input**: `start_lat, start_lon, end_lat, end_lon, route_type, vehicle_type`
2. **Snap to Graph**: Find nearest graph nodes using KD-tree or Ball tree.
3. **Vehicle Filtering**: Pre-filter edges based on `vehicle_profiles` (width constraints, speed bump avoidance).
4. **Weight Selection**: Choose weight function based on `route_type` parameter.
5. **Pathfinding**:
   - **Fastest/Safest**: Use `networkx.shortest_path()` with custom weight attribute.
   - **Straightest**: Implement A* where heuristic = great-circle distance to destination, but edge cost includes angular penalty.
   - **Popular**: Use bidirectional Dijkstra with edge cost reduced by proximity to `popular_places`.
6. **Output**: Ordered list of coordinates, segment IDs, total distance, estimated time, hazard summary.

### Step 3.6: Hazard Prediction Model (`app/models/hazard_predictor.py`)

**Architecture**: Gradient Boosting (XGBoost/LightGBM) or small Neural Net.

**Features**:
- Historical IoT vibration levels per segment
- Weather conditions (precipitation, visibility)
- Road type (residential roads more hazardous)
- Time of day (night driving risk)
- Recent accident density

**Training Pipeline** (run locally in `ml-training/`):
1. Aggregate `iot_readings` by segment, compute mean vibration, std dev.
2. Join with `weather_grid` and `traffic_conditions`.
3. Label: `hazard_score = sigmoid(vibration_normalized + weather_penalty + traffic_penalty)`.
4. Train model, export as `.pkl` (sklearn) or `.pt` (PyTorch if using NN).
5. Load model in FastAPI startup, predict on-the-fly for route requests.

### Step 3.7: Traffic Forecaster (`app/models/traffic_forecaster.py`)

**Architecture**: LSTM or Temporal Fusion Transformer (simpler: LSTM).

**Purpose**: Predict traffic 15-30 min ahead for proactive routing.

1. **Data**: Time-series of `traffic_conditions` per segment.
2. **Model**: `torch.nn.LSTM` with input shape `(seq_len, batch, features)` where features = [hour_of_day, day_of_week, historical_speed, weather_condition_encoded].
3. **Inference**: For requested route, predict future speeds at estimated arrival times per segment.
4. **Integration**: Add predicted congestion penalty to fastest route weights.

### Step 3.8: Geocoding Service (`app/services/geocoding_service.py`)

1. **Forward Geocode**: Call Mapbox Geocoding API with query string → return `[lon, lat]`.
2. **Reverse Geocode**: Call Mapbox with `[lon, lat]` → return address components.
3. **Cache**: Store results in Supabase `popular_places` or in-memory dict to reduce API calls.
4. **Fallback**: If Mapbox limit reached, use Nominatim (OpenStreetMap) with 1-second rate limiting.

### Step 3.9: IoT Data Ingestion Service (`app/services/iot_service.py`)

1. **POST Endpoint**: `/api/v1/iot/ingest` — hardware sends JSON payload.
2. **Validation**: Pydantic schema checks required fields (device_id, lat, lon, accelerometer).
3. **Processing**:
   - Compute `vibration_level = sqrt(accel_x² + accel_y² + accel_z²)`.
   - Classify: `smooth < 0.5 < moderate < 1.5 < rough < 3.0 < severe`.
   - Map lat/lon to nearest `road_segments` using PostGIS `ST_DWithin` query.
4. **Write**: Insert into `iot_readings` table.
5. **Trigger**: If `vibration_level > THRESHOLD` and `gyro` indicates crash pattern (sudden stop + tilt), insert into `sos_alerts` and trigger notification logic.

### Step 3.10: Route API Endpoints (`app/routers/routes.py`)

Implement these endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/routes/compute` | Main routing engine |
| GET | `/api/v1/routes/types` | List available route types |
| GET | `/api/v1/routes/hazards` | Get hazard heatmap for bounding box |
| POST | `/api/v1/routes/feedback` | RLHF data collection |

**`/api/v1/routes/compute` Request Body**:
```json
{
  "origin": {"lat": 12.9716, "lon": 77.5946},
  "destination": {"lat": 12.9352, "lon": 77.6245},
  "route_type": "safest",
  "vehicle_type": "bike",
  "avoid_tolls": false
}
```

**Response**:
```json
{
  "route_id": "uuid",
  "geometry": {"type": "LineString", "coordinates": [...]},
  "distance_km": 8.4,
  "duration_min": 24,
  "hazard_score_avg": 0.23,
  "segments": [{"id": 1, "hazard": 0.1, "traffic": "moderate"}],
  "weather_alerts": ["Light rain expected in 15 min"]
}
```

### Step 3.11: Background Tasks & Scheduling
1. Use `fastapi.BackgroundTasks` for non-critical operations (feedback logging).
2. Use `APScheduler` or `celery` (overkill for hackathon) for:
   - Refreshing weather data every 10 minutes.
   - Recomputing graph edge weights every 5 minutes.
   - Expiring old `segment_hazards` records.

---

## Phase 4: Frontend Build — Step-by-Step

### Step 4.1: React + Mapbox Setup
1. `npx create-react-app frontend` (or Vite for faster builds).
2. `npm install mapbox-gl axios react-query zustand react-router-dom lucide-react tailwindcss`.
3. Configure Mapbox GL JS with your token in `.env`.

### Step 4.2: Page Structure

| Page | Route | Features |
|------|-------|----------|
| **Home** | `/` | Full-screen Mapbox map, search bars (origin/destination), route type selector, vehicle selector, "Navigate" button |
| **Route Detail** | `/route/:routeId` | Turn-by-turn list, elevation profile, weather overlay, hazard warnings, "Start Navigation" simulation |
| **Analytics** | `/analytics` | (Bonus) IoT heatmap, sensor density, recent SOS alerts |

### Step 4.3: Component Architecture

**Home Page Layout**:
1. **Map Component** (`components/Map/MapboxMap.jsx`):
   - Initialize Mapbox with `mapboxgl.Map`.
   - Add sources: `routes` (line layer), `hazards` (heatmap/circle layer), `iot` (real-time dots).
   - Fit bounds to route geometry when computed.

2. **Search Bar** (`components/SearchBar/SearchBar.jsx`):
   - Two inputs: Origin, Destination.
   - Debounced Mapbox Geocoding API calls (300ms).
   - Dropdown suggestions with place names.

3. **Route Type Selector** (`components/RouteTypes/RouteTypeSelector.jsx`):
   - Four cards: Fastest (Zap icon), Safest (Shield icon), Straightest (ArrowRight icon), Popular (Star icon).
   - Active state highlights selected type.
   - On change, re-fetches route if origin/destination exist.

4. **Vehicle Selector** (`components/VehicleSelector/VehicleSelector.jsx`):
   - Horizontal scroll: Bike, Car, Truck, Supercar.
   - Icons change route constraints (bike → narrow roads OK, supercar → avoid speed bumps).

5. **Route Panel** (`components/RoutePanel/RoutePanel.jsx`):
   - Shows computed route summary: distance, time, safety score.
   - "Start" button simulates navigation (pulsing dot along route).

### Step 4.4: State Management (Zustand)

Create `store/navigationStore.js`:
- `origin`, `destination` (lat/lon objects)
- `routeType`, `vehicleType`
- `currentRoute` (geometry + metadata from backend)
- `hazards` (array for map overlay)
- `iotReadings` (real-time updates via polling)

### Step 4.5: API Integration

Create `services/api.js`:
- Axios instance with base URL pointing to Railway backend.
- Functions: `computeRoute(payload)`, `geocode(query)`, `reverseGeocode(lon,lat)`, `getHazards(bbox)`.
- React Query hooks for caching and background refetching.

### Step 4.6: Real-Time IoT Visualization
1. Poll `/api/v1/iot/readings?bbox=minLon,minLat,maxLon,maxLat` every 5 seconds.
2. Update Mapbox source `iot` with new GeoJSON points.
3. Color-code by `road_condition`: green (smooth) → yellow (moderate) → red (severe).

### Step 4.7: RLHF Feedback UI
1. After route completion (or on Route Detail page), show 5-star rating.
2. Text input: "What was wrong with this route?"
3. POST to `/api/v1/routes/feedback` with route geometry and rating.

---

## Phase 5: Deployment Guide

### Step 5.1: Backend → Railway

1. **Prepare Repository**:
   - Ensure `backend/` is a git repo (or use Railway CLI).
   - `requirements.txt` must include all dependencies.
   - `Dockerfile`:
     ```dockerfile
     FROM python:3.11-slim
     WORKDIR /app
     COPY requirements.txt .
     RUN pip install --no-cache-dir -r requirements.txt
     COPY app/ ./app/
     CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
     ```

2. **Railway Setup**:
   - Login to railway.app, create new project.
   - Connect GitHub repo, select `backend/` as root directory.
   - Add environment variables in Railway dashboard:
     - `DATABASE_URL` (from Supabase → Connection string → URI)
     - `MAPBOX_TOKEN`
     - `OPENWEATHER_API_KEY`
     - `TOMTOM_API_KEY`
   - Deploy. Railway auto-detects Dockerfile.

3. **Verify**:
   - Visit `https://your-project.railway.app/health`.
   - Should return `{"status": "ok", "db": "connected"}`.

### Step 5.2: Database → Supabase

1. Create project at supabase.com.
2. In SQL Editor, run all table creation queries from Phase 1.
3. Enable Row Level Security (RLS) later; for hackathon, keep open.
4. Copy connection string from Settings → Database → Connection Pooling → URI.
5. Test connection from local backend before deploying.

### Step 5.3: Frontend → Vercel

1. **Build Configuration**:
   - `vercel.json`:
     ```json
     {
       "buildCommand": "npm run build",
       "outputDirectory": "build",
       "framework": "create-react-app"
     }
     ```

2. **Environment Variables** in Vercel dashboard:
   - `REACT_APP_MAPBOX_TOKEN`
   - `REACT_APP_API_URL=https://your-project.railway.app`

3. **Deploy**:
   - Connect GitHub repo to Vercel.
   - Set root directory to `frontend/`.
   - Deploy. Vercel provides HTTPS URL instantly.

### Step 5.4: Hardware Integration

1. Configure IoT devices to POST to `https://your-project.railway.app/api/v1/iot/ingest`.
2. Ensure JSON payload matches `iot_schemas.py` Pydantic model.
3. Test with sample curl:
   ```bash
   curl -X POST https://your-project.railway.app/api/v1/iot/ingest \
     -H "Content-Type: application/json" \
     -d '{"device_id":"bike_01","latitude":12.97,"longitude":77.59,"accel_x":0.1,"accel_y":0.0,"accel_z":9.8}'
   ```

### Step 5.5: End-to-End Verification Checklist

- [ ] Mapbox map loads on Vercel frontend.
- [ ] Search bar returns geocoding suggestions.
- [ ] Compute route returns valid geometry for all 4 route types.
- [ ] IoT data appears as dots on map within 10 seconds of ingestion.
- [ ] SOS alert creates record in `sos_alerts` table.
- [ ] Weather conditions affect safest route path (test during rain).
- [ ] Vehicle selector changes route (bike through narrow road, truck avoids it).

---

## Phase 6: Hackathon Execution Strategy

**Day 1 Morning**: 
- Set up repo, Supabase tables, Railway + Vercel skeletons.
- Get one API working (Mapbox geocoding → route display).

**Day 1 Afternoon**: 
- Build graph from OSM for your demo city.
- Implement basic Dijkstra for fastest route.

**Day 2 Morning**: 
- Add hazard scoring from IoT data.
- Implement safest route variant.
- Add vehicle constraints.

**Day 2 Afternoon**: 
- Polish UI, add route type selector animations.
- Test end-to-end with live IoT data.
- Prepare demo narrative: "Our sensors see what Google can't."

**Pitch Angle**: *"While others use crowdsourced reports, we have ground-truth sensors. While others give you one route, we optimize for your priorities. While others call an ambulance after you crash, we call before you stop moving."*

---

## Algorithm & Model Summary

| Component | Algorithm/Model | Input | Output |
|-----------|----------------|-------|--------|
| Graph | NetworkX + OSMnx | OpenStreetMap data | Traversable road graph |
| Fastest Route | Dijkstra | Distance, speed | Min-time path |
| Safest Route | Dijkstra with hazard weights | IoT + weather + traffic | Min-risk path |
| Straightest Route | A* with bearing heuristic | Coordinates | Min-turn path |
| Popular Route | Dijkstra with POI density | Popular places | Scenic path |
| Hazard Prediction | XGBoost / LightGBM | Vibration, weather, road type | 0-1 hazard score |
| Traffic Forecast | LSTM | Historical speed, time | Future speed prediction |
| SOS Detection | Rule-based threshold | Gyro + accelerometer pattern | Accident alert |

---

**Final Strategic Note from Alexander**: In a hackathon, judges remember *demos*, not architecture diagrams. Build the "safest route for bikes with live pothole detection" vertical first. Make the map show red dots where your hardware detected bumps. That single visualization proves your entire thesis. Everything else is optimization.
