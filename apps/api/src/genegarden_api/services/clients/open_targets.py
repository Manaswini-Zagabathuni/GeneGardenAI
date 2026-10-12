import hashlib
import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from genegarden_api.services.cache import TTLMemoryCache
from genegarden_api.services.clients.base import (
    ExternalResponseError,
    ResilientJsonClient,
    SleepCallable,
)

TARGET_ASSOCIATIONS_QUERY = """
query GeneGardenTargetAssociations($ensemblId: String!, $pageSize: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    associatedDiseases(page: {index: 0, size: $pageSize}) {
      count
      rows {
        disease {
          id
          name
          description
        }
        score
        datatypeScores { id score }
        datasourceScores { id score }
      }
    }
  }
}
""".strip()


class OpenTargetsModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class OpenTargetsScore(OpenTargetsModel):
    id: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)


class OpenTargetsDisease(OpenTargetsModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None


class OpenTargetsAssociation(OpenTargetsModel):
    disease: OpenTargetsDisease
    score: float = Field(ge=0, le=1)
    datatype_scores: tuple[OpenTargetsScore, ...] = Field(default=(), alias="datatypeScores")
    datasource_scores: tuple[OpenTargetsScore, ...] = Field(default=(), alias="datasourceScores")


class OpenTargetsAssociationPage(OpenTargetsModel):
    count: int = Field(ge=0)
    rows: tuple[OpenTargetsAssociation, ...]


class OpenTargetsTarget(OpenTargetsModel):
    id: str = Field(min_length=1)
    approved_symbol: str = Field(min_length=1, alias="approvedSymbol")
    approved_name: str = Field(min_length=1, alias="approvedName")
    biotype: str | None = None
    associated_diseases: OpenTargetsAssociationPage = Field(alias="associatedDiseases")


class _OpenTargetsData(OpenTargetsModel):
    target: OpenTargetsTarget | None


class _GraphQlError(OpenTargetsModel):
    message: str


class _GraphQlEnvelope(OpenTargetsModel):
    data: dict[str, Any] | None = None
    errors: tuple[_GraphQlError, ...] = ()


class OpenTargetsClient(ResilientJsonClient):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        max_attempts: int,
        backoff_seconds: float,
        user_agent: str,
        cache: TTLMemoryCache[dict[str, Any]],
        client: httpx.AsyncClient | None = None,
        sleep: SleepCallable | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if sleep is not None:
            kwargs["sleep"] = sleep
        super().__init__(
            service_name="open_targets",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            user_agent=user_agent,
            cache=cache,
            client=client,
            **kwargs,
        )

    async def fetch_target_associations(
        self, ensembl_id: str, *, page_size: int = 5
    ) -> OpenTargetsTarget:
        if not 1 <= page_size <= 25:
            raise ValueError("Open Targets page_size must be between 1 and 25")
        variables = {"ensemblId": ensembl_id, "pageSize": page_size}
        body = {"query": TARGET_ASSOCIATIONS_QUERY, "variables": variables}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        payload = await self._request_json(
            "POST", "", cache_key=f"open-targets:{digest}", json_body=body
        )
        try:
            envelope = _GraphQlEnvelope.model_validate(payload)
            if envelope.errors:
                raise ExternalResponseError(
                    "open_targets",
                    "Open Targets rejected the GraphQL query.",
                )
            data = _OpenTargetsData.model_validate(envelope.data)
        except ValidationError as exc:
            raise ExternalResponseError(
                "open_targets",
                "Open Targets returned data that did not match the documented schema.",
            ) from exc
        if data.target is None:
            raise ExternalResponseError(
                "open_targets",
                f"Open Targets did not return target {ensembl_id!r}.",
            )
        return data.target
