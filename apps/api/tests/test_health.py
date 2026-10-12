import httpx
import pytest

from genegarden_api.api.routes import health as health_routes
from genegarden_api.db import session as database_session
from genegarden_api.db.session import DatabaseReadinessError
from genegarden_api.main import app


@pytest.mark.asyncio
async def test_health_check() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "genegarden-api",
        "version": "0.1.0",
    }


@pytest.mark.asyncio
async def test_unknown_route_returns_not_found() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_error", "message": "Not Found"}}


@pytest.mark.asyncio
async def test_readiness_check_reports_a_successful_database_round_trip(monkeypatch) -> None:
    async def database_is_ready() -> None:
        return None

    monkeypatch.setattr(health_routes, "check_database_connection", database_is_ready)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "genegarden-api",
        "database": "reachable",
    }


@pytest.mark.asyncio
async def test_readiness_check_returns_safe_error_when_database_is_unavailable(monkeypatch) -> None:
    async def database_is_unavailable() -> None:
        raise DatabaseReadinessError("sensitive driver details")

    monkeypatch.setattr(health_routes, "check_database_connection", database_is_unavailable)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "The PostgreSQL database is unavailable.",
        }
    }
    assert "sensitive" not in response.text


@pytest.mark.asyncio
async def test_database_readiness_executes_query(monkeypatch) -> None:
    executed_statements: list[str] = []

    class Connection:
        async def execute(self, statement) -> None:
            executed_statements.append(str(statement))

    class ConnectionContext:
        async def __aenter__(self) -> Connection:
            return Connection()

        async def __aexit__(self, *_args) -> None:
            return None

    class Engine:
        def connect(self) -> ConnectionContext:
            return ConnectionContext()

    monkeypatch.setattr(database_session, "_engine", Engine())
    await database_session.check_database_connection()

    assert executed_statements == ["SELECT 1"]


@pytest.mark.asyncio
async def test_database_readiness_wraps_connection_errors_without_credentials(
    monkeypatch, caplog
) -> None:
    class ConnectionContext:
        async def __aenter__(self):
            raise OSError("postgresql://user:do-not-log@database.example/db")

        async def __aexit__(self, *_args) -> None:
            return None

    class Engine:
        def connect(self) -> ConnectionContext:
            return ConnectionContext()

    monkeypatch.setattr(database_session, "_engine", Engine())
    with pytest.raises(DatabaseReadinessError, match="Database is unavailable"):
        await database_session.check_database_connection()

    assert "do-not-log" not in caplog.text
    assert "error_type=OSError" in caplog.text
