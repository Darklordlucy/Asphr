from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/geocode", tags=["Geocoding"])

@router.get("")
async def geocode_placeholder():
    return {"message": "Geocoding endpoint placeholder"}
