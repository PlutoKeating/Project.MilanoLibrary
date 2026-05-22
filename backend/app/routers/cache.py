from fastapi import APIRouter
from app.models import CacheClearResponse
from app.services.cache import clear_all_cache

router = APIRouter(prefix="/api", tags=["cache"])


@router.delete("/cache", response_model=CacheClearResponse)
async def clear_cache():
    result = await clear_all_cache()
    return CacheClearResponse(**result)
