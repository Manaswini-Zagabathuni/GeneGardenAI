from fastapi import APIRouter

from genegarden_api.schemas.health import HealthResponse
from genegarden_api.services.health import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check whether the API process is healthy",
)
async def health_check() -> HealthResponse:
    return HealthService().check()
