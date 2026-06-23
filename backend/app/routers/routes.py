from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import Point, LineString
from geoalchemy2.shape import from_shape

from app.config import get_db
from app.schemas.route_schemas import RouteRequest, FeedbackRequest
from app.services.route_service import RouteService
from app.models.db_models import RouteFeedback

router = APIRouter(prefix="/api/v1/routes", tags=["Routes"])
route_service = RouteService()

@router.get("/types")
async def get_route_types():
    """Retrieve all supported routing objective weight functions."""
    return {
        "types": [
            {"id": "fastest", "name": "Fastest Route", "description": "Minimizes driving time using traffic metrics.", "icon": "Zap"},
            {"id": "safest", "name": "Safest Route", "description": "Avoids segment hazards and storm weather.", "icon": "Shield"},
            {"id": "straightest", "name": "Straightest Route", "description": "Minimizes turns and angular bearing shifts.", "icon": "ArrowRight"},
            {"id": "popular", "name": "Popular Route", "description": "Scenic routing traversing points of interest.", "icon": "Star"}
        ]
    }

@router.post("/compute")
async def compute_route(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Snaps origin/destination and runs the dynamic route optimization engine."""
    try:
        result = await route_service.compute_route_service(
            db=db,
            origin={"lat": request.origin.lat, "lon": request.origin.lon},
            destination={"lat": request.destination.lat, "lon": request.destination.lon},
            route_type=request.route_type,
            vehicle_type=request.vehicle_type
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Routing failure: {str(e)}"
        )

@router.post("/feedback")
async def log_route_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit RLHF routing feedback and coordinates directly to database."""
    try:
        # Convert Pydantic points to GeoAlchemy2 geometries
        start_geom = from_shape(Point(request.start_point.lon, request.start_point.lat), srid=4326)
        end_geom = from_shape(Point(request.end_point.lon, request.end_point.lat), srid=4326)
        
        # LineString expects list of tuples or coordinate points
        route_geom = from_shape(LineString([tuple(coord) for coord in request.route_geometry]), srid=4326)
        
        feedback_entry = RouteFeedback(
            user_id=request.user_id,
            start_point=start_geom,
            end_point=end_geom,
            route_geometry=route_geom,
            route_type=request.route_type,
            rating=request.rating,
            feedback_text=request.feedback_text
        )
        
        db.add(feedback_entry)
        await db.commit()
        
        return {"status": "success", "message": "Feedback submitted successfully."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
