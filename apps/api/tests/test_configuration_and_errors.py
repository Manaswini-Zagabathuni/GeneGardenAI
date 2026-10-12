from datetime import datetime

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from genegarden_api.core.config import Settings
from genegarden_api.main import app
from genegarden_api.models import BiologicalEntity, EntityType, SourceName


def test_settings_parse_safe_configuration_and_reject_invalid_limits() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        api_port=9000,
        api_cors_origins=["https://portfolio.example"],
        external_request_max_attempts=5,
    )

    assert settings.app_env == "test"
    assert settings.api_port == 9000
    assert str(settings.cors_origins[0]).rstrip("/") == "https://portfolio.example"
    assert settings.assistant_llm_provider == "none"

    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_port=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, external_request_max_attempts=6)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, assistant_llm_provider="unconfigured-provider")


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://genegarden:genegarden@localhost:5432/genegarden",
        ("postgresql+asyncpg://genegarden:test-only-password@localhost:5432/genegarden_test"),
    ],
)
def test_production_configuration_rejects_development_and_test_credentials(
    database_url: str,
) -> None:
    with pytest.raises(ValidationError, match="development or test database credentials"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url=database_url,
            api_cors_origins=["https://example.com"],
        )


def test_production_configuration_validates_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://genegarden:test-only-password@localhost:5432/genegarden_test",
    )

    with pytest.raises(ValidationError, match="development or test database credentials"):
        Settings(_env_file=None, app_env="production", api_cors_origins=["https://example.com"])


def test_production_configuration_rejects_http_cors_and_accepts_safe_values() -> None:
    safe_database_url = "postgresql+asyncpg://app:strong-password@db:5432/genegarden"

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url=safe_database_url,
            api_cors_origins=["http://example.com"],
        )

    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url=safe_database_url,
        api_cors_origins=["https://example.com"],
    )
    assert settings.app_env == "production"


def test_local_development_configuration_keeps_documented_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None, app_env="development")

    assert settings.app_env == "development"
    assert settings.database_url.hosts()[0]["host"] == "localhost"


def test_neon_database_url_is_normalized_for_asyncpg_without_losing_tls() -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql://portfolio_user:example-password@"
            "ep-example.us-east-2.aws.neon.tech/neondb"
            "?sslmode=require&channel_binding=require"
        ),
    )

    normalized = make_url(str(settings.database_url))
    assert normalized.drivername == "postgresql+asyncpg"
    assert normalized.query["ssl"] == "require"
    assert "sslmode" not in normalized.query
    assert "channel_binding" not in normalized.query


def test_neon_database_url_requires_tls_and_database_driver_must_be_supported() -> None:
    with pytest.raises(ValidationError, match="must require TLS") as validation_error:
        Settings(
            _env_file=None,
            database_url=(
                "postgresql://portfolio_user:example-password@"
                "ep-example.us-east-2.aws.neon.tech/neondb"
            ),
        )
    assert "example-password" not in str(validation_error.value)

    with pytest.raises(ValidationError, match="PostgreSQL with the asyncpg driver"):
        Settings(_env_file=None, database_url="sqlite:///local.db")


def test_domain_schema_rejects_naive_timestamp_and_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        BiologicalEntity(
            canonical_id="ensembl:ENSG00000141510",
            entity_type=EntityType.GENE,
            label="Fixture gene",
            source=SourceName.OPEN_TARGETS,
            source_identifier="ENSG00000141510",
            retrieved_at=datetime(2026, 1, 1),
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        BiologicalEntity(
            canonical_id="ensembl:ENSG00000141510",
            entity_type=EntityType.GENE,
            label="Fixture gene",
            source=SourceName.OPEN_TARGETS,
            source_identifier="ENSG00000141510",
            invented_claim="not allowed",
        )


@pytest.mark.asyncio
async def test_validation_errors_use_stable_envelope() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/discovery/paths",
            json={"source_id": "not-canonical", "max_path_length": 99},
        )
        invalid_path_identifier = await client.get("/api/v1/knowledge/entities/not-canonical")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert isinstance(response.json()["error"]["details"], list)
    assert invalid_path_identifier.status_code == 422
    assert invalid_path_identifier.json()["error"]["code"] == "validation_error"
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
