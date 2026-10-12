import json
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from genegarden_api.models import KnowledgeGraphSnapshot
from genegarden_api.services.cache import TTLMemoryCache
from genegarden_api.services.clients.europe_pmc import EuropePmcClient
from genegarden_api.services.clients.open_targets import OpenTargetsClient
from genegarden_api.services.ingestion import BiomedicalIngestionService, IngestionManifest

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class MemoryRepository:
    def __init__(self) -> None:
        self.snapshot: KnowledgeGraphSnapshot | None = None
        self.finished: dict[str, object] = {}

    async def start_ingestion_run(self, *_args) -> UUID:
        return uuid4()

    async def persist_snapshot(self, snapshot: KnowledgeGraphSnapshot) -> None:
        self.snapshot = snapshot

    async def finish_ingestion_run(self, _run_id: UUID, **values) -> None:
        self.finished = values


@pytest.mark.asyncio
async def test_ingestion_builds_only_sourced_relationships() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "europepmc" in request.url.path:
            return httpx.Response(200, json=fixture("europe_pmc_search.json"))
        return httpx.Response(200, json=fixture("open_targets_target.json"))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    common = {
        "timeout_seconds": 1,
        "max_attempts": 1,
        "backoff_seconds": 0,
        "user_agent": "GeneGarden-test",
        "cache": TTLMemoryCache(ttl_seconds=60),
        "client": http_client,
    }
    repository = MemoryRepository()
    service = BiomedicalIngestionService(
        OpenTargetsClient(base_url="https://example.test/graphql", **common),
        EuropePmcClient(base_url="https://example.test/europepmc", **common),
        repository,
    )
    statistics = await service.ingest(
        IngestionManifest(
            domain_name="fixture-domain",
            target_ids=("ENSG00000141510",),
            max_associations_per_target=1,
            publications_per_association=1,
        )
    )
    await http_client.aclose()

    assert statistics.entities == 2
    assert statistics.relationships == 1
    assert repository.snapshot is not None
    relationship = repository.snapshot.relationships[0]
    assert relationship.source.value == "open_targets"
    assert relationship.relationship_type.value == "gene_associated_with_disease"
    assert relationship.evidence[-1].evidence_type.value == "literature_context"
    assert "not independently validated" in (relationship.evidence[-1].summary or "")
    assert repository.finished["status"] == "succeeded"


def test_manifest_rejects_duplicates_and_unbounded_requests() -> None:
    with pytest.raises(ValueError, match="unique"):
        IngestionManifest(
            domain_name="bad",
            target_ids=("ENSG00000141510", "ENSG00000141510"),
        )
    with pytest.raises(ValueError):
        IngestionManifest(
            domain_name="bad",
            target_ids=("ENSG00000141510",),
            max_associations_per_target=100,
        )
