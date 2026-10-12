from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from genegarden_api.db import Base
from genegarden_api.db.session import get_db_session
from genegarden_api.main import app
from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    RelationshipType,
    SourceName,
)
from genegarden_api.repositories import KnowledgeRepository

NOW = datetime(2026, 10, 11, tzinfo=UTC)


@pytest.mark.asyncio
async def test_discovery_api_validates_and_returns_provenance() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    session = factory()
    gene = BiologicalEntity(
        canonical_id="ensembl:ENSG00000141510",
        entity_type=EntityType.GENE,
        label="Fixture gene",
        source=SourceName.OPEN_TARGETS,
        source_identifier="ENSG00000141510",
        retrieved_at=NOW,
    )
    disease = BiologicalEntity(
        canonical_id="mondo:MONDO_0000001",
        entity_type=EntityType.DISEASE,
        label="Fixture disease",
        source=SourceName.OPEN_TARGETS,
        source_identifier="MONDO_0000001",
        retrieved_at=NOW,
    )
    evidence = EvidenceRecord(
        source=SourceName.OPEN_TARGETS,
        source_record_id="fixture:eva",
        evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
        score=0.7,
        attributes={"datasource_id": "eva"},
        retrieved_at=NOW,
    )
    relationship = BiomedicalRelationship(
        canonical_key="fixture-relationship",
        source_entity_id=gene.canonical_id,
        target_entity_id=disease.canonical_id,
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier="fixture-pair",
        score=0.7,
        evidence=(evidence,),
        retrieved_at=NOW,
    )
    await KnowledgeRepository(session).persist_snapshot(
        KnowledgeGraphSnapshot(entities=(gene, disease), relationships=(relationship,))
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/discovery/paths",
                json={
                    "source_id": gene.canonical_id,
                    "target_entity_types": ["disease"],
                    "max_path_length": 2,
                    "result_count": 5,
                },
            )
            path_id = response.json()["paths"][0]["path_id"]
            evidence_response = await client.post(
                "/api/v1/evidence/paths",
                json={
                    "discovery": {
                        "source_id": gene.canonical_id,
                        "target_entity_types": ["disease"],
                        "max_path_length": 2,
                        "result_count": 5,
                    },
                    "path_id": path_id,
                },
            )
            assistant_response = await client.post(
                "/api/v1/assistant/answer",
                json={
                    "question": "What does the stored relationship show?",
                    "path": {
                        "discovery": {
                            "source_id": gene.canonical_id,
                            "target_entity_types": ["disease"],
                            "max_path_length": 2,
                            "result_count": 5,
                        },
                        "path_id": path_id,
                    },
                },
            )
            invalid_path = await client.post(
                "/api/v1/evidence/paths",
                json={
                    "discovery": {"source_id": gene.canonical_id},
                    "path_id": "not-a-real-path",
                },
            )
            empty = await client.post(
                "/api/v1/discovery/paths",
                json={
                    "source_id": gene.canonical_id,
                    "target_entity_types": ["protein"],
                },
            )
            invalid = await client.post("/api/v1/discovery/paths", json={"source_id": "TP53"})
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["paths"][0]["edges"][0]["relationships"][0]["evidence"][0]["source_record_id"]
        == "fixture:eva"
    )
    assert "not a probability" in payload["paths"][0]["score"]["interpretation"]
    assert evidence_response.status_code == 200
    assert evidence_response.json()["claim_scope"] == "direct_relationship"
    assert evidence_response.json()["relationships"][0]["source_entity"]["canonical_id"] == (
        gene.canonical_id
    )
    assert assistant_response.status_code == 200
    assert assistant_response.json()["mode"] == "evidence_summary"
    assert assistant_response.json()["provider_available"] is False
    assert invalid_path.status_code == 404
    assert empty.status_code == 200 and empty.json()["paths"] == []
    assert invalid.status_code == 422
