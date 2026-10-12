from fastapi import APIRouter

from genegarden_api.core.errors import ApplicationError
from genegarden_api.db.session import DatabaseReadinessError, check_database_connection
from genegarden_api.schemas.health import HealthResponse, ReadinessResponse
from genegarden_api.services.health import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check whether the API process is healthy",
)
async def health_check() -> HealthResponse:
    return HealthService().check()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"description": "The configured PostgreSQL database is unavailable"}},
    summary="Check whether PostgreSQL can serve a query",
)
async def readiness_check() -> ReadinessResponse:
    try:
        await check_database_connection()
    except DatabaseReadinessError as exc:
        raise ApplicationError(
            code="database_unavailable",
            message="The PostgreSQL database is unavailable.",
            status_code=503,
        ) from exc
    return ReadinessResponse(
        status="ready",
        service="genegarden-api",
        database="reachable",
    )
