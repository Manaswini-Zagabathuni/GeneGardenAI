import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from genegarden_api import __version__
from genegarden_api.api.router import api_router
from genegarden_api.core.config import get_settings
from genegarden_api.core.errors import register_exception_handlers
from genegarden_api.core.logging import configure_logging
from genegarden_api.db.session import close_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.api_log_level)
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Research API for evidence-grounded exploration of biomedical relationships. "
            "Not for diagnostic or clinical use."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )
    register_exception_handlers(application)

    @application.middleware("http")
    async def log_request(request: Request, call_next) -> Response:
        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000
        logging.getLogger("genegarden_api.requests").info(
            "request_completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
