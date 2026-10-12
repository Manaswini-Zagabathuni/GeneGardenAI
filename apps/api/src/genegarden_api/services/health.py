from genegarden_api import __version__
from genegarden_api.schemas.health import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        return HealthResponse(status="ok", service="genegarden-api", version=__version__)
