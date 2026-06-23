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