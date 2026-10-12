from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
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

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
        if self.app_env != "production":
            return self
        if any(host.get("password") == "genegarden" for host in self.database_url.hosts()):
            raise ValueError("Production must not use the documented development database password")
        if any(origin.scheme != "https" for origin in self.api_cors_origins):
            raise ValueError("Production CORS origins must use HTTPS")
        return self

    @property
    def cors_origins(self) -> list[AnyHttpUrl]:
        return self.api_cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
