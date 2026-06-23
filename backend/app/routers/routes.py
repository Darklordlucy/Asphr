from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/routes", tags=["Routes"])

@router.get("")
async def routes_placeholder():
    return {"message": "Routes endpoint placeholder"}
