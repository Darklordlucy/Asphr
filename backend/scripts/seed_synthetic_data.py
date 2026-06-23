"""
Asphr Synthetic Data Generator
===============================
Generates realistic, road-aligned synthetic data for the Mumbai metropolitan 
road network and inserts it into the Supabase PostgreSQL database.

Data is generated on actual graph nodes/edges — not random lat/lon coordinates.
Traffic patterns, hazard clusters, and weather cells are modeled after real 
Mumbai conditions (monsoon rain zones, congestion hotspots, pothole corridors).
"""

import sys
import os
import math
import random
import asyncio
import datetime
from typing import List, Tuple

# Add backend to path
sys.path.insert(0, "D:\\Asphr\\backend")

import networkx as nx
from shapely.geometry import Point, Polygon, LineString
from geoalchemy2.shape import from_shape
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AsyncSessionLocal
from app.models.db_models import (
    RoadSegment, SegmentHazard, IoTReading, TrafficCondition,
    WeatherGrid, PopularPlace, VehicleProfile
)
from app.algorithms.graph_builder import GraphManager

# ---------------------------------------------------------------------------
# Mumbai geographic knowledge base (real-world reference points)
# ---------------------------------------------------------------------------

# Major congestion hotspots (lat, lon, name, severity 0-1)
CONGESTION_HOTSPOTS = [
    (18.9398, 72.8355, "CSMT Station Area", 0.85),
    (19.0178, 72.8478, "Dadar Junction", 0.90),
    (19.0760, 72.8777, "Sion-Kurla", 0.80),
    (19.0990, 72.9080, "Ghatkopar Junction", 0.75),
    (19.1860, 72.9756, "Thane Station", 0.82),
    (19.2403, 73.1305, "Kalyan Junction", 0.78),
    (19.3919, 72.8397, "Virar Station", 0.70),
    (19.0544, 72.8402, "Mahim Causeway", 0.88),
    (19.1197, 72.9052, "Powai-Andheri Link", 0.72),
    (19.0330, 72.8442, "Parel-Lower Parel", 0.80),
    (19.1370, 72.9170, "Kanjurmarg Junction", 0.65),
    (19.2100, 72.8500, "Borivali Station", 0.73),
    (18.9220, 72.8347, "Colaba-Navy Nagar", 0.55),
    (19.0030, 72.8270, "Worli Sea Link Area", 0.68),
    (19.1640, 72.8550, "Goregaon-Malad", 0.70),
]

# Pothole / hazard corridors (lat, lon, radius_meters, severity)
HAZARD_CORRIDORS = [
    (19.0544, 72.8402, 800, 0.75, "pothole"),       # Mahim Causeway
    (19.0178, 72.8478, 500, 0.65, "pothole"),        # Dadar
    (19.0760, 72.8777, 600, 0.70, "wet_road"),       # Sion-Kurla
    (19.1860, 72.9756, 700, 0.60, "pothole"),        # Thane
    (18.9550, 72.8320, 400, 0.55, "accident_prone"), # Marine Drive curves
    (19.1197, 72.9052, 500, 0.50, "pothole"),        # Powai
    (19.0990, 72.9080, 450, 0.58, "wet_road"),       # Ghatkopar
    (19.2403, 73.1305, 600, 0.62, "pothole"),        # Kalyan
    (19.0330, 72.8442, 350, 0.48, "accident_prone"), # Lower Parel
    (19.2100, 72.8500, 400, 0.52, "pothole"),        # Borivali
]

# Real Mumbai landmarks for popular places
POPULAR_PLACES = [
    ("Gateway of India", "landmark", 18.9220, 72.8347, 0.95),
    ("Marine Drive", "landmark", 18.9438, 72.8234, 0.92),
    ("Juhu Beach", "tourist", 19.0984, 72.8264, 0.88),
    ("Siddhivinayak Temple", "landmark", 19.0169, 72.8310, 0.90),
    ("Haji Ali Dargah", "landmark", 18.9828, 72.8089, 0.85),
    ("Chhatrapati Shivaji Maharaj Vastu Sangrahalaya", "landmark", 18.9268, 72.8326, 0.80),
    ("Bandra-Worli Sea Link", "landmark", 19.0302, 72.8153, 0.87),
    ("Crawford Market", "food", 18.9472, 72.8338, 0.78),
    ("Phoenix Palladium Mall", "food", 19.0100, 72.8310, 0.82),
    ("Film City Goregaon", "tourist", 19.1640, 72.8550, 0.75),
    ("IIT Bombay Campus", "landmark", 19.1334, 72.9133, 0.70),
    ("Powai Lake", "tourist", 19.1270, 72.9060, 0.72),
    ("Sanjay Gandhi National Park", "tourist", 19.2147, 72.9100, 0.83),
    ("Elephanta Caves Ferry Terminal", "tourist", 18.9100, 72.8780, 0.77),
    ("Worli Fort", "landmark", 19.0005, 72.8152, 0.65),
    ("Girgaon Chowpatty", "food", 18.9556, 72.8146, 0.80),
    ("Dharavi", "landmark", 19.0424, 72.8546, 0.55),
    ("Dadar Flower Market", "food", 19.0178, 72.8435, 0.73),
    ("Upvan Lake Thane", "tourist", 19.2120, 72.9650, 0.68),
    ("Kalyan Fort", "landmark", 19.2350, 73.1250, 0.60),
    ("Versova Beach", "tourist", 19.1310, 72.8120, 0.65),
    ("Linking Road Shopping", "food", 19.0660, 72.8340, 0.76),
    ("BKC Business District", "landmark", 19.0650, 72.8680, 0.70),
    ("Thane Creek Flamingo Point", "tourist", 19.1900, 72.9900, 0.72),
    ("Tikuji-ni-Wadi", "tourist", 19.2600, 73.0800, 0.58),
]

# Vehicle profiles
VEHICLE_PROFILES = [
    ("bike", None, None, None, False, True, False),
    ("car", 1.9, 1.6, 2.5, False, True, False),
    ("truck", 2.5, 3.5, 3.5, True, False, True),
    ("supercar", 2.0, 1.3, 3.0, True, True, True),
]


def haversine_dist(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


async def seed_vehicle_profiles(db: AsyncSession):
    """Insert standard vehicle profiles."""
    print("\n[1/6] Seeding vehicle profiles...")
    # Check if profiles already exist
    result = await db.execute(select(func.count(VehicleProfile.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  Vehicle profiles already exist ({count} rows). Skipping.")
        return

    for vtype, width, height, min_road, avoid_bump, narrow, highway in VEHICLE_PROFILES:
        profile = VehicleProfile(
            vehicle_type=vtype,
            max_width_m=width,
            max_height_m=height,
            min_road_width_m=min_road,
            avoid_speed_bumps=avoid_bump,
            allow_narrow_roads=narrow,
            prefer_highways=highway
        )
        db.add(profile)
    await db.commit()
    print(f"  Inserted {len(VEHICLE_PROFILES)} vehicle profiles.")


async def seed_popular_places(db: AsyncSession):
    """Insert real Mumbai landmarks as popular places."""
    print("\n[2/6] Seeding popular places (real Mumbai landmarks)...")
    result = await db.execute(select(func.count(PopularPlace.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  Popular places already exist ({count} rows). Skipping.")
        return

    for name, category, lat, lon, score in POPULAR_PLACES:
        place = PopularPlace(
            name=name,
            category=category,
            geometry=from_shape(Point(lon, lat), srid=4326),
            popularity_score=score,
            city="Mumbai"
        )
        db.add(place)
    await db.commit()
    print(f"  Inserted {len(POPULAR_PLACES)} popular places.")


async def seed_weather_grid(db: AsyncSession):
    """Create weather grid cells covering Mumbai with realistic monsoon patterns."""
    print("\n[3/6] Seeding weather grid (Mumbai monsoon simulation)...")
    result = await db.execute(select(func.count(WeatherGrid.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  Weather grid already exists ({count} cells). Skipping.")
        return

    # Divide Mumbai into ~0.05 degree grid cells (~5.5km each)
    min_lat, max_lat = 18.90, 19.50
    min_lon, max_lon = 72.75, 73.20
    cell_size = 0.05

    # Western coastal cells get more rain (Arabian Sea effect)
    cells_inserted = 0
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            # Build polygon for this cell
            cell_poly = Polygon([
                (lon, lat),
                (lon + cell_size, lat),
                (lon + cell_size, lat + cell_size),
                (lon, lat + cell_size),
                (lon, lat)
            ])

            # Coastal proximity factor (more rain near the sea / western coast)
            coastal_factor = max(0, 1.0 - (lon - 72.75) / (73.20 - 72.75))

            # Randomize but bias towards monsoon conditions
            is_rainy = random.random() < (0.4 + 0.3 * coastal_factor)

            if is_rainy:
                precip = round(random.uniform(2.0, 15.0) * (1 + coastal_factor), 1)
                condition = random.choice(["rain", "heavy rain", "thunderstorm"])
                visibility = round(random.uniform(1.0, 5.0), 1)
            else:
                precip = round(random.uniform(0.0, 1.5), 1)
                condition = random.choice(["clear", "cloudy", "mist"])
                visibility = round(random.uniform(5.0, 15.0), 1)

            cell = WeatherGrid(
                cell_geometry=from_shape(cell_poly, srid=4326),
                temperature=round(random.uniform(26.0, 34.0), 1),
                humidity=round(random.uniform(65.0, 95.0), 1),
                visibility_km=visibility,
                precipitation_mm=precip,
                wind_speed_kmh=round(random.uniform(5.0, 35.0), 1),
                weather_condition=condition
            )
            db.add(cell)
            cells_inserted += 1

            lon += cell_size
        lat += cell_size

    await db.commit()
    print(f"  Inserted {cells_inserted} weather grid cells.")


async def seed_segment_hazards(db: AsyncSession):
    """Generate hazard scores for road segments near known pothole/hazard corridors."""
    print("\n[4/6] Seeding segment hazards (pothole corridors & accident zones)...")
    result = await db.execute(select(func.count(SegmentHazard.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  Segment hazards already exist ({count} rows). Skipping.")
        return

    # Fetch all road segments with their geometry centroids
    segments_result = await db.execute(
        text("""
            SELECT id, source_node, target_node, 
                   ST_Y(ST_Centroid(geometry)) as lat,
                   ST_X(ST_Centroid(geometry)) as lon,
                   road_type
            FROM road_segments
        """)
    )
    segments = segments_result.fetchall()
    
    if not segments:
        print("  No road segments found in database. Run graph sync first!")
        return

    print(f"  Found {len(segments)} road segments. Calculating hazard proximity...")

    hazards_inserted = 0
    batch = []

    for seg_id, src, tgt, seg_lat, seg_lon, road_type in segments:
        # Check proximity to hazard corridors
        max_hazard = 0.0
        hazard_type = None
        hazard_source = "ml_model"

        for h_lat, h_lon, h_radius, h_severity, h_type in HAZARD_CORRIDORS:
            dist = haversine_dist(seg_lat, seg_lon, h_lat, h_lon)
            if dist <= h_radius:
                # Decay hazard score with distance from corridor center
                proximity_factor = 1.0 - (dist / h_radius)
                score = h_severity * proximity_factor
                # Add road-type bias (residential roads are rougher)
                if road_type in ("residential", "unclassified", "living_street"):
                    score = min(1.0, score * 1.3)
                elif road_type in ("motorway", "trunk", "primary"):
                    score *= 0.7  # better-maintained roads
                
                if score > max_hazard:
                    max_hazard = score
                    hazard_type = h_type

        # Also add a small baseline hazard for all residential roads
        if max_hazard == 0 and road_type in ("residential", "unclassified"):
            if random.random() < 0.15:  # 15% of residential roads have minor issues
                max_hazard = round(random.uniform(0.05, 0.25), 3)
                hazard_type = random.choice(["pothole", "wet_road"])

        if max_hazard > 0.01:
            # Add slight randomization to prevent perfectly deterministic data
            max_hazard = min(1.0, max_hazard * random.uniform(0.85, 1.15))
            
            hazard = SegmentHazard(
                segment_id=seg_id,
                hazard_score=round(max_hazard, 3),
                hazard_type=hazard_type,
                confidence=round(random.uniform(0.7, 0.98), 2),
                source=random.choice(["ml_model", "iot", "weather_api"]),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=random.randint(6, 48))
            )
            batch.append(hazard)
            hazards_inserted += 1

            if len(batch) >= 500:
                db.add_all(batch)
                await db.commit()
                batch = []
                print(f"  ... inserted {hazards_inserted} hazards so far")

    if batch:
        db.add_all(batch)
        await db.commit()

    print(f"  Inserted {hazards_inserted} segment hazard records.")


async def seed_traffic_conditions(db: AsyncSession):
    """Generate traffic speed data based on proximity to congestion hotspots."""
    print("\n[5/6] Seeding traffic conditions (congestion hotspot simulation)...")
    result = await db.execute(select(func.count(TrafficCondition.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  Traffic conditions already exist ({count} rows). Skipping.")
        return

    # Fetch segments with centroid lat/lon and road type
    segments_result = await db.execute(
        text("""
            SELECT id, 
                   ST_Y(ST_Centroid(geometry)) as lat,
                   ST_X(ST_Centroid(geometry)) as lon,
                   road_type, max_speed
            FROM road_segments
        """)
    )
    segments = segments_result.fetchall()

    if not segments:
        print("  No road segments found. Run graph sync first!")
        return

    print(f"  Found {len(segments)} segments. Calculating traffic conditions...")

    # Default free-flow speeds by road type
    default_speeds = {
        'motorway': 80, 'trunk': 70, 'primary': 60,
        'secondary': 50, 'tertiary': 40, 'residential': 30,
        'living_street': 15, 'unclassified': 30
    }

    traffic_inserted = 0
    batch = []

    for seg_id, seg_lat, seg_lon, road_type, db_max_speed in segments:
        free_flow = db_max_speed or default_speeds.get(road_type, 30)

        # Calculate congestion reduction factor based on proximity to hotspots
        max_congestion_factor = 0.0
        for h_lat, h_lon, h_name, h_severity in CONGESTION_HOTSPOTS:
            dist = haversine_dist(seg_lat, seg_lon, h_lat, h_lon)
            influence_radius = 1500  # meters
            if dist <= influence_radius:
                proximity = 1.0 - (dist / influence_radius)
                congestion = h_severity * proximity
                max_congestion_factor = max(max_congestion_factor, congestion)

        # Apply congestion: reduce speed proportionally
        # At max congestion (1.0), speed drops to ~15-20% of free flow
        speed_reduction = 1.0 - (max_congestion_factor * 0.8)
        current_speed = max(5.0, free_flow * speed_reduction * random.uniform(0.85, 1.15))

        # Determine congestion level (0=free, 1=light, 2=moderate, 3=heavy, 4=standstill)
        speed_ratio = current_speed / free_flow
        if speed_ratio > 0.8:
            congestion_level = 0
        elif speed_ratio > 0.6:
            congestion_level = 1
        elif speed_ratio > 0.4:
            congestion_level = 2
        elif speed_ratio > 0.2:
            congestion_level = 3
        else:
            congestion_level = 4

        traffic = TrafficCondition(
            segment_id=seg_id,
            speed_kmh=round(current_speed, 1),
            congestion_level=congestion_level,
            traffic_volume=random.randint(50, 800) if congestion_level >= 2 else random.randint(5, 200)
        )
        batch.append(traffic)
        traffic_inserted += 1

        if len(batch) >= 500:
            db.add_all(batch)
            await db.commit()
            batch = []
            print(f"  ... inserted {traffic_inserted} traffic records so far")

    if batch:
        db.add_all(batch)
        await db.commit()

    print(f"  Inserted {traffic_inserted} traffic condition records.")


async def seed_iot_readings(db: AsyncSession):
    """Generate IoT sensor readings on actual road segment coordinates."""
    print("\n[6/6] Seeding IoT readings (simulated sensor fleet)...")
    result = await db.execute(select(func.count(IoTReading.id)))
    count = result.scalar()
    if count and count > 0:
        print(f"  IoT readings already exist ({count} rows). Skipping.")
        return

    # Fetch a sample of road segments with their start/end coordinates
    segments_result = await db.execute(
        text("""
            SELECT id, source_node, target_node,
                   ST_Y(ST_StartPoint(geometry)) as start_lat,
                   ST_X(ST_StartPoint(geometry)) as start_lon,
                   ST_Y(ST_EndPoint(geometry)) as end_lat,
                   ST_X(ST_EndPoint(geometry)) as end_lon,
                   road_type
            FROM road_segments
            ORDER BY RANDOM()
            LIMIT 3000
        """)
    )
    segments = segments_result.fetchall()

    if not segments:
        print("  No road segments found. Run graph sync first!")
        return

    print(f"  Generating IoT readings on {len(segments)} randomly sampled road segments...")

    device_ids = [f"bike_{i:02d}" for i in range(1, 11)] + \
                 [f"car_{i:02d}" for i in range(1, 6)] + \
                 [f"truck_{i:02d}" for i in range(1, 4)]

    iot_inserted = 0
    batch = []

    for seg_id, src, tgt, s_lat, s_lon, e_lat, e_lon, road_type in segments:
        # Generate 1-3 readings per segment (simulating devices traversing the road)
        num_readings = random.randint(1, 3)
        
        for _ in range(num_readings):
            # Interpolate a point along the segment
            t = random.uniform(0.1, 0.9)
            lat = s_lat + t * (e_lat - s_lat)
            lon = s_lon + t * (e_lon - s_lon)

            # Check if this segment is near a hazard corridor for realistic vibration
            near_hazard = False
            for h_lat, h_lon, h_radius, h_severity, _ in HAZARD_CORRIDORS:
                if haversine_dist(lat, lon, h_lat, h_lon) <= h_radius:
                    near_hazard = True
                    base_vibration = h_severity * random.uniform(1.5, 4.0)
                    break

            if not near_hazard:
                # Normal road vibration
                if road_type in ("residential", "unclassified"):
                    base_vibration = random.uniform(0.2, 1.2)
                elif road_type in ("motorway", "trunk", "primary"):
                    base_vibration = random.uniform(0.05, 0.4)
                else:
                    base_vibration = random.uniform(0.1, 0.8)

            # Decompose vibration into accelerometer axes (realistic 3-axis sensor)
            accel_x = round(random.gauss(0, base_vibration * 0.3), 3)
            accel_y = round(random.gauss(0, base_vibration * 0.3), 3)
            accel_z = round(9.81 + random.gauss(0, base_vibration * 0.5), 3)
            
            vibration = round(math.sqrt(accel_x**2 + accel_y**2 + (accel_z - 9.81)**2), 3)

            # Classify road condition
            if vibration < 0.5:
                condition = "smooth"
            elif vibration < 1.5:
                condition = "moderate"
            elif vibration < 3.0:
                condition = "rough"
            else:
                condition = "severe"

            # Gyroscope data (slight tilt/rotation noise)
            gyro_x = round(random.gauss(0, 0.05), 4)
            gyro_y = round(random.gauss(0, 0.05), 4)
            gyro_z = round(random.gauss(0, 0.02), 4)

            reading = IoTReading(
                device_id=random.choice(device_ids),
                segment_id=seg_id,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                accel_x=accel_x,
                accel_y=accel_y,
                accel_z=accel_z,
                gyro_x=gyro_x,
                gyro_y=gyro_y,
                gyro_z=gyro_z,
                vibration_level=vibration,
                road_condition=condition,
                timestamp=datetime.datetime.utcnow() - datetime.timedelta(
                    minutes=random.randint(0, 1440)  # last 24 hours
                )
            )
            batch.append(reading)
            iot_inserted += 1

            if len(batch) >= 500:
                db.add_all(batch)
                await db.commit()
                batch = []
                print(f"  ... inserted {iot_inserted} IoT readings so far")

    if batch:
        db.add_all(batch)
        await db.commit()

    print(f"  Inserted {iot_inserted} IoT reading records.")


async def main():
    print("=" * 60)
    print("  Asphr Synthetic Data Generator")
    print("  Mumbai Metropolitan Road Network")
    print("=" * 60)

    # First check if road_segments exist in the DB
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count(RoadSegment.id)))
        seg_count = result.scalar()
        print(f"\nRoad segments in database: {seg_count}")

        if not seg_count or seg_count == 0:
            print("\nERROR: No road segments found in database!")
            print("Please run the FastAPI server first to sync the graph to the database.")
            print("The graph_builder will populate road_segments on startup.")
            return

        print(f"\nProceeding with {seg_count} road segments as base data...\n")

        # Seed all tables in order
        await seed_vehicle_profiles(db)
        await seed_popular_places(db)
        await seed_weather_grid(db)
        await seed_segment_hazards(db)
        await seed_traffic_conditions(db)
        await seed_iot_readings(db)

    print("\n" + "=" * 60)
    print("  Synthetic data generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart the FastAPI server to re-enrich graph weights with new data")
    print("  2. Test routes — safest/popular/fastest should now differ")
    print("  3. Check Supabase dashboard to verify inserted rows")


if __name__ == "__main__":
    asyncio.run(main())
