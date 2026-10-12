from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

_POSTGRES_DRIVERS = {"postgres", "postgresql", "postgresql+asyncpg"}
_TLS_SSL_MODES = {"require", "verify-ca", "verify-full"}
_INSECURE_PRODUCTION_DATABASE_PASSWORDS = frozenset({"genegarden", "test-only-password"})


def normalize_async_database_url(value: object) -> str:
    """Convert a standard PostgreSQL URL into SQLAlchemy's asyncpg form.

    Hosted providers such as Neon publish libpq-style URLs. SQLAlchemy passes URL query
    parameters as keyword arguments to asyncpg, whose keyword is ``ssl`` rather than
    ``sslmode`` and which does not accept ``channel_binding``. This conversion happens in
    memory only; the credential-bearing URL is never logged.
    """

    raw_url = str(value)
    try:
        url = make_url(raw_url)
    except ArgumentError as exc:
        raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from exc

    if url.drivername not in _POSTGRES_DRIVERS:
        raise ValueError("DATABASE_URL must use PostgreSQL with the asyncpg driver")

    query = dict(url.query)
    ssl_mode = query.pop("sslmode", None)
    asyncpg_ssl = query.get("ssl")
    if ssl_mode is not None and asyncpg_ssl is not None and ssl_mode != asyncpg_ssl:
        raise ValueError("DATABASE_URL cannot specify conflicting sslmode and ssl values")
    if ssl_mode is not None:
        query["ssl"] = ssl_mode

    # Neon may append this libpq option. asyncpg does not implement a matching argument;
    # TLS remains explicitly controlled by the normalized `ssl` query parameter.
    query.pop("channel_binding", None)

    hostname = (url.host or "").lower()
    if hostname.endswith(".neon.tech") and query.get("ssl") not in _TLS_SSL_MODES:
        raise ValueError(
            "Neon DATABASE_URL values must require TLS with sslmode=require or stronger"
        )

    normalized = url.set(drivername="postgresql+asyncpg", query=query)
    return normalized.render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    app_name: str = "GeneGarden AI API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:5173")]
    )
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://genegarden:genegarden@localhost:5432/genegarden"
    )
    database_readiness_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    open_targets_graphql_url: AnyHttpUrl = AnyHttpUrl(
        "https://api.platform.opentargets.org/api/v4/graphql"
    )
    europe_pmc_api_url: AnyHttpUrl = AnyHttpUrl("https://www.ebi.ac.uk/europepmc/webservices/rest")
    external_request_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    external_request_max_attempts: int = Field(default=3, ge=1, le=5)
    external_request_backoff_seconds: float = Field(default=0.25, ge=0, le=5)
    external_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    europe_pmc_email: str | None = None
    external_user_agent: str = "GeneGardenAI/0.1 (research and educational use)"
    assistant_llm_provider: Literal["none"] = "none"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        return normalize_async_database_url(value)

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
        if self.app_env != "production":
            return self
        if any(
            host.get("password") in _INSECURE_PRODUCTION_DATABASE_PASSWORDS
            for host in self.database_url.hosts()
        ):
            raise ValueError(
                "Production must not use documented development or test database credentials"
            )
        if any(origin.scheme != "https" for origin in self.api_cors_origins):
            raise ValueError("Production CORS origins must use HTTPS")
        return self

    @property
    def cors_origins(self) -> list[AnyHttpUrl]:
        return self.api_cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
