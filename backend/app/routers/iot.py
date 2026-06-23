from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])

@router.get("")
async def iot_placeholder():
    return {"message": "IoT endpoint placeholder"}
