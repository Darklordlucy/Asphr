from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, DateTime, CheckConstraint, ForeignKey
from geoalchemy2 import Geometry
from app.config import Base
import datetime

class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(Integer, primary_key=True, index=True)
    osm_way_id = Column(BigInteger)
    source_node = Column(BigInteger, nullable=False, index=True)
    target_node = Column(BigInteger, nullable=False, index=True)
    geometry = Column(Geometry("LineString", srid=4326), nullable=False)
    length_meters = Column(Float, nullable=False)
    road_type = Column(String(50))
    max_speed = Column(Integer)
    lanes = Column(Integer)
    has_speed_bump = Column(Boolean, default=False)
    is_toll = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SegmentHazard(Base):
    __tablename__ = "segment_hazards"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("road_segments.id", ondelete="CASCADE"), index=True)
    hazard_score = Column(Float, nullable=False)
    hazard_type = Column(String(50))
    confidence = Column(Float)
    source = Column(String(20))
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    expires_at = Column(DateTime)

    __table_args__ = (
        CheckConstraint("hazard_score BETWEEN 0 AND 1", name="chk_hazard_score"),
    )

class IoTReading(Base):
    __tablename__ = "iot_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("road_segments.id"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accel_x = Column(Float)
    accel_y = Column(Float)
    accel_z = Column(Float)
    gyro_x = Column(Float)
    gyro_y = Column(Float)
    gyro_z = Column(Float)
    vibration_level = Column(Float)
    road_condition = Column(String(20))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class TrafficCondition(Base):
    __tablename__ = "traffic_conditions"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("road_segments.id"), index=True)
    speed_kmh = Column(Float)
    congestion_level = Column(Integer, index=True)
    traffic_volume = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("congestion_level BETWEEN 0 AND 4", name="chk_congestion_level"),
    )

class WeatherGrid(Base):
    __tablename__ = "weather_grid"

    id = Column(Integer, primary_key=True, index=True)
    cell_geometry = Column(Geometry("Polygon", srid=4326), nullable=False)
    temperature = Column(Float)
    humidity = Column(Float)
    visibility_km = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    weather_condition = Column(String(50))
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

class PopularPlace(Base):
    __tablename__ = "popular_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50))
    geometry = Column(Geometry("Point", srid=4326), nullable=False)
    popularity_score = Column(Float)
    city = Column(String(100), index=True)

class VehicleProfile(Base):
    __tablename__ = "vehicle_profiles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_type = Column(String(50), nullable=False)
    max_width_m = Column(Float)
    max_height_m = Column(Float)
    min_road_width_m = Column(Float)
    avoid_speed_bumps = Column(Boolean)
    allow_narrow_roads = Column(Boolean)
    prefer_highways = Column(Boolean)

class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved = Column(Boolean, default=False)
    hospital_notified = Column(Boolean, default=False)

class RouteFeedback(Base):
    __tablename__ = "route_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100))
    start_point = Column(Geometry("Point", srid=4326))
    end_point = Column(Geometry("Point", srid=4326))
    route_geometry = Column(Geometry("LineString", srid=4326))
    route_type = Column(String(20))
    rating = Column(Integer)
    feedback_text = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_rating"),
    )
