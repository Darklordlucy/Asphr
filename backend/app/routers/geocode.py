from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_db
from app.services.geocoding_service import GeocodingService

router = APIRouter(prefix="/api/v1/geocode", tags=["Geocoding"])
geocoding_service = GeocodingService()

@router.get("/forward")
async def forward_geocode(
    query: str,
    db: AsyncSession = Depends(get_db)
):
    """Geocode a text query to [longitude, latitude] coordinates."""
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'query' cannot be empty."
        )
    
    result = await geocoding_service.forward_geocode(query, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coordinates not found for query: '{query}'"
        )
        
    lon, lat = result
    return {
        "query": query,
        "longitude": lon,
        "latitude": lat
    }

@router.get("/reverse")
async def reverse_geocode(
    lat: float,
    lon: float,
    db: AsyncSession = Depends(get_db)
):
    """Reverse geocode [latitude, longitude] coordinates to a text address."""
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be between -90 and 90, and longitude between -180 and 180."
        )
        
    result = await geocoding_service.reverse_geocode(lat, lon, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address not found for coordinates: [{lat}, {lon}]"
        )
        
    return result
