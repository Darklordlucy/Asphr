from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import Point, LineString
from geoalchemy2.shape import from_shape

from app.config import get_db, AsyncSessionLocal
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
            vehicle_type=request.vehicle_type,
            avoid_tolls=request.avoid_tolls
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

@router.get("/hazards")
async def get_hazards_heatmap(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all road segments and their hazard scores within a bounding box.
    Returns GeoJSON LineString coordinates and the associated hazard score/type for heatmap rendering.
    """
    try:
        # Bbox geometry as string (Polygon)
        bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
        
        # Spatial query to fetch road segments intersecting with the bounding box, joined with their latest hazards
        query = text("""
            SELECT 
                rs.id AS segment_id,
                ST_AsText(rs.geometry) AS geom_wkt,
                sh.hazard_score,
                sh.hazard_type
            FROM road_segments rs
            LEFT JOIN LATERAL (
                SELECT hazard_score, hazard_type
                FROM segment_hazards
                WHERE segment_id = rs.id
                ORDER BY recorded_at DESC
                LIMIT 1
            ) sh ON TRUE
            WHERE ST_Intersects(rs.geometry, ST_GeomFromText(:bbox, 4326))
            LIMIT 5000
        """)
        
        result = await db.execute(query, {"bbox": bbox_wkt})
        rows = result.fetchall()
        
        hazards_list = []
        for segment_id, geom_wkt, hazard_score, hazard_type in rows:
            if not geom_wkt:
                continue
                
            # Parse WKT coordinates
            coords_str = geom_wkt.replace("LINESTRING", "").replace("(", "").replace(")", "").strip()
            coordinates = []
            for pt in coords_str.split(","):
                parts = pt.strip().split(" ")
                if len(parts) >= 2:
                    coordinates.append([float(parts[0]), float(parts[1])])
                    
            hazards_list.append({
                "segment_id": segment_id,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "hazard_score": float(hazard_score or 0.0),
                "hazard_type": hazard_type or "unknown"
            })
            
        return {"hazards": hazards_list}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve hazard heatmap: {str(e)}"
        )

async def save_feedback_in_background(request: FeedbackRequest):
    """Saves route feedback coordinates and details in the background."""
    async with AsyncSessionLocal() as db:
        try:
            start_geom = from_shape(Point(request.start_point.lon, request.start_point.lat), srid=4326)
            end_geom = from_shape(Point(request.end_point.lon, request.end_point.lat), srid=4326)
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
            print(f"[FeedbackBackgroundTask] Successfully saved feedback for user {request.user_id}")
        except Exception as e:
            await db.rollback()
            print(f"[FeedbackBackgroundTask] Error saving feedback: {e}")

@router.post("/feedback")
async def log_route_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks
):
    """Submit RLHF routing feedback and coordinates directly to database."""
    background_tasks.add_task(save_feedback_in_background, request)
    return {"status": "success", "message": "Feedback submitted successfully."}
