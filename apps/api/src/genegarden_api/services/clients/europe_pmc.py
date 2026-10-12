import hashlib
import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from genegarden_api.models import Publication, SourceName
from genegarden_api.services.cache import TTLMemoryCache
from genegarden_api.services.clients.base import (
    ExternalResponseError,
    ResilientJsonClient,
    SleepCallable,
)
from genegarden_api.services.normalization import normalize_doi


class EuropePmcModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class EuropePmcResult(EuropePmcModel):
    identifier: str = Field(min_length=1, alias="id")
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    author_string: str | None = Field(default=None, alias="authorString")
    journal: str | None = Field(default=None, alias="journalTitle")
    publication_year: int | None = Field(default=None, alias="pubYear")
    abstract: str | None = Field(default=None, alias="abstractText")
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    is_open_access: bool | None = Field(default=None, alias="isOpenAccess")

    @field_validator("publication_year", mode="before")
    @classmethod
    def parse_year(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    @field_validator("is_open_access", mode="before")
    @classmethod
    def parse_open_access(cls, value: Any) -> bool | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"y", "yes", "true", "1"}:
            return True
        if normalized in {"n", "no", "false", "0"}:
            return False
        raise ValueError("Unexpected Europe PMC open-access flag")

    def to_domain(self, *, retrieved_at: datetime) -> Publication:
        return Publication(
            source=SourceName.EUROPE_PMC,
            source_identifier=f"{self.source}:{self.identifier}",
            title=self.title,
            author_string=self.author_string,
            journal=self.journal,
            publication_year=self.publication_year,
            abstract=self.abstract,
            doi=normalize_doi(self.doi),
            pmid=self.pmid,
            pmcid=self.pmcid,
            is_open_access=self.is_open_access,
            attributes={"europe_pmc_source": self.source},
            retrieved_at=retrieved_at,
        )


class _EuropePmcResultList(EuropePmcModel):
    results: tuple[EuropePmcResult, ...] = Field(default=(), alias="result")


class _EuropePmcSearchResponse(EuropePmcModel):
    hit_count: int = Field(ge=0, alias="hitCount")
    result_list: _EuropePmcResultList = Field(alias="resultList")


class EuropePmcClient(ResilientJsonClient):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        max_attempts: int,
        backoff_seconds: float,
        user_agent: str,
        cache: TTLMemoryCache[dict[str, Any]],
        email: str | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: SleepCallable | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if sleep is not None:
            kwargs["sleep"] = sleep
        super().__init__(
            service_name="europe_pmc",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            user_agent=user_agent,
            cache=cache,
            client=client,
            **kwargs,
        )
        self._email = email

    async def search_publications(
        self, term_a: str, term_b: str, *, page_size: int = 3
    ) -> tuple[EuropePmcResult, ...]:
        if not 1 <= page_size <= 25:
            raise ValueError("Europe PMC page_size must be between 1 and 25")
        query = f'TITLE_ABS:"{self._clean_term(term_a)}" AND TITLE_ABS:"{self._clean_term(term_b)}"'
        params: dict[str, str | int] = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": page_size,
        }
        if self._email:
            params["email"] = self._email
        digest = hashlib.sha256(query.encode()).hexdigest()
        payload = await self._request_json(
            "GET", "search", cache_key=f"europe-pmc:{digest}:{page_size}", params=params
        )
        try:
            response = _EuropePmcSearchResponse.model_validate(payload)
        except ValidationError as exc:
            raise ExternalResponseError(
                "europe_pmc",
                "Europe PMC returned data that did not match the documented schema.",
            ) from exc
        return response.result_list.results

    async def fetch_publication(self, source_identifier: str) -> EuropePmcResult | None:
        """Fetch one exact Europe PMC record by its stable ``SOURCE:ID`` pair."""
        match = re.fullmatch(r"([A-Za-z0-9]{2,12}):([A-Za-z0-9._-]{1,128})", source_identifier)
        if match is None:
            raise ValueError("Europe PMC identifiers must use the safe SOURCE:ID format")
        source, identifier = match.group(1).upper(), match.group(2)
        params: dict[str, str | int] = {
            "query": f"EXT_ID:{identifier} AND SRC:{source}",
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }
        if self._email:
            params["email"] = self._email
        payload = await self._request_json(
            "GET",
            "search",
            cache_key=f"europe-pmc:publication:{source}:{identifier}",
            params=params,
        )
        try:
            response = _EuropePmcSearchResponse.model_validate(payload)
        except ValidationError as exc:
            raise ExternalResponseError(
                "europe_pmc",
                "Europe PMC returned data that did not match the documented schema.",
            ) from exc
        for result in response.result_list.results:
            if result.source.upper() == source and result.identifier == identifier:
                return result
        return None

    @staticmethod
    def _clean_term(value: str) -> str:
        cleaned = " ".join(value.replace('"', " ").split())
        if not cleaned:
            raise ValueError("Europe PMC search terms must not be empty")
        return cleaned[:200]
