from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from genegarden_api.db import Base
from genegarden_api.db.session import get_db_session
from genegarden_api.main import app
from genegarden_api.models import BiologicalEntity, EntityType, KnowledgeGraphSnapshot, SourceName
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository


@pytest.mark.asyncio
async def test_knowledge_api_returns_typed_snapshot_and_stable_404() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    session = factory()
    entity = BiologicalEntity(
        canonical_id="ensembl:ENSG00000141510",
        entity_type=EntityType.GENE,
        label="Fixture gene",
        source=SourceName.OPEN_TARGETS,
        source_identifier="ENSG00000141510",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await KnowledgeRepository(session).persist_snapshot(
        KnowledgeGraphSnapshot(entities=(entity,), relationships=())
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/knowledge/graph/ensembl:ENSG00000141510")
            missing = await client.get("/api/v1/knowledge/entities/efo:EFO_9999999")
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await engine.dispose()

    assert response.status_code == 200
    assert response.json()["entities"][0]["canonical_id"] == entity.canonical_id
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "entity_not_found"


@pytest.mark.asyncio
async def test_knowledge_api_returns_stable_error_when_neighborhood_exceeds_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exceed_limit(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise GraphSnapshotLimitError("The graph exceeded the safe entity limit.")

    monkeypatch.setattr(KnowledgeRepository, "get_bounded_subgraph", exceed_limit)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/knowledge/graph/ensembl:ENSG00000141510")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "knowledge_graph_limit"
