import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from genegarden_api.services.cache import TTLMemoryCache
from genegarden_api.services.clients.base import ExternalResponseError
from genegarden_api.services.clients.europe_pmc import EuropePmcClient
from genegarden_api.services.clients.open_targets import OpenTargetsClient

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def client_arguments(transport: httpx.BaseTransport) -> dict:
    return {
        "timeout_seconds": 1,
        "max_attempts": 3,
        "backoff_seconds": 0,
        "user_agent": "GeneGarden-test",
        "cache": TTLMemoryCache(ttl_seconds=60),
        "client": httpx.AsyncClient(transport=transport),
    }


@pytest.mark.asyncio
async def test_open_targets_validates_and_caches_documented_shape() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        assert request.headers["user-agent"] == "GeneGarden-test"
        assert request.method == "POST"
        return httpx.Response(200, json=fixture("open_targets_target.json"))

    arguments = client_arguments(httpx.MockTransport(handler))
    client = OpenTargetsClient(base_url="https://example.test/graphql", **arguments)
    first = await client.fetch_target_associations("ENSG00000141510")
    second = await client.fetch_target_associations("ENSG00000141510")
    await arguments["client"].aclose()

    assert first.approved_symbol == "FIXTURE_GENE"
    assert second.associated_diseases.rows[0].score == 0.73
    assert requests == 1


@pytest.mark.asyncio
async def test_open_targets_rejects_graphql_errors() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"errors": [{"message": "bad query"}]})
    )
    arguments = client_arguments(transport)
    client = OpenTargetsClient(base_url="https://example.test/graphql", **arguments)
    with pytest.raises(ExternalResponseError, match="rejected"):
        await client.fetch_target_associations("ENSG00000141510")
    await arguments["client"].aclose()


@pytest.mark.asyncio
async def test_europe_pmc_parses_metadata_after_bounded_retry() -> None:
    requests = 0
    delays: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(503, headers={"Retry-After": "0"})
        return httpx.Response(200, json=fixture("europe_pmc_search.json"))

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    arguments = client_arguments(httpx.MockTransport(handler))
    client = EuropePmcClient(
        base_url="https://example.test/rest",
        email="researcher@example.test",
        sleep=record_sleep,
        **arguments,
    )
    results = await client.search_publications("FIXTURE_GENE", "Fixture disease")
    publication = results[0].to_domain(retrieved_at=datetime.now(UTC))
    await arguments["client"].aclose()

    assert requests == 2
    assert delays == [0]
    assert publication.doi == "10.0000/fixture"
    assert publication.is_open_access is True


@pytest.mark.asyncio
async def test_clients_enforce_small_page_limits() -> None:
    arguments = client_arguments(httpx.MockTransport(lambda _: httpx.Response(500)))
    open_targets = OpenTargetsClient(base_url="https://example.test", **arguments)
    europe_pmc = EuropePmcClient(base_url="https://example.test", **arguments)
    with pytest.raises(ValueError, match="between 1 and 25"):
        await open_targets.fetch_target_associations("ENSG00000141510", page_size=26)
    with pytest.raises(ValueError, match="between 1 and 25"):
        await europe_pmc.search_publications("gene", "disease", page_size=0)
    await arguments["client"].aclose()


@pytest.mark.asyncio
async def test_europe_pmc_fetches_only_an_exact_source_identifier() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["query"] == "EXT_ID:FIXTURE-1 AND SRC:MED"
        return httpx.Response(200, json=fixture("europe_pmc_search.json"))

    arguments = client_arguments(httpx.MockTransport(handler))
    client = EuropePmcClient(base_url="https://example.test/rest", **arguments)
    result = await client.fetch_publication("MED:FIXTURE-1")
    await arguments["client"].aclose()

    assert result is not None
    assert result.identifier == "FIXTURE-1"


@pytest.mark.asyncio
async def test_europe_pmc_rejects_invalid_identifier_and_reports_failure() -> None:
    arguments = client_arguments(httpx.MockTransport(lambda _: httpx.Response(503)))
    client = EuropePmcClient(base_url="https://example.test/rest", **arguments)
    with pytest.raises(ValueError, match="SOURCE:ID"):
        await client.fetch_publication("https://unsafe.example/path")
    with pytest.raises(Exception, match="bounded retries"):
        await client.fetch_publication("MED:12345")
    await arguments["client"].aclose()
