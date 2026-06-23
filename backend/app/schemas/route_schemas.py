from pydantic import BaseModel, Field
from typing import List, Optional

class Coordinate(BaseModel):
    lat: float
    lon: float

class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    route_type: str = Field(default="fastest", description="One of: fastest, safest, straightest, popular")
    vehicle_type: str = Field(default="car", description="One of: bike, car, truck, supercar")

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = None
    start_point: Coordinate
    end_point: Coordinate
    route_geometry: List[List[float]] = Field(description="Coordinates list of LineString [[lon, lat], ...]")
    route_type: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None
