from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from genegarden_api.db import Base
from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    Publication,
    RelationshipType,
    SourceName,
)
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_repository_round_trips_snapshot_and_deduplicates_upserts() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    publication = Publication(
        source_identifier="MED:fixture",
        title="Fixture publication",
        pmid="fixture",
        retrieved_at=NOW,
    )
    gene = BiologicalEntity(
        canonical_id="ensembl:ENSG00000141510",
        entity_type=EntityType.GENE,
        label="Fixture gene",
        source=SourceName.OPEN_TARGETS,
        source_identifier="ENSG00000141510",
        retrieved_at=NOW,
    )
    disease = BiologicalEntity(
        canonical_id="efo:EFO_0000001",
        entity_type=EntityType.DISEASE,
        label="Fixture disease",
        source=SourceName.OPEN_TARGETS,
        source_identifier="EFO_0000001",
        retrieved_at=NOW,
    )
    evidence = EvidenceRecord(
        source=SourceName.EUROPE_PMC,
        source_record_id="fixture-search",
        evidence_type=EvidenceType.LITERATURE_CONTEXT,
        publication_ids=(publication.source_identifier,),
        retrieved_at=NOW,
    )
    relationship = BiomedicalRelationship(
        canonical_key="open_targets|gene_associated_with_disease|fixture",
        source_entity_id=gene.canonical_id,
        target_entity_id=disease.canonical_id,
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier="fixture-pair",
        score=0.4,
        evidence=(evidence,),
        retrieved_at=NOW,
    )
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease), relationships=(relationship,), publications=(publication,)
    )

    async with factory() as session:
        repository = KnowledgeRepository(session)
        await repository.persist_snapshot(snapshot)
        await repository.persist_snapshot(snapshot)
        loaded = await repository.get_neighborhood(gene.canonical_id)
        entity = await repository.get_entity(gene.canonical_id)
        with pytest.raises(GraphSnapshotLimitError, match="entity limit"):
            await repository.get_bounded_subgraph(gene.canonical_id, max_depth=2, max_nodes=1)

    await engine.dispose()
    assert entity is not None and entity.label == "Fixture gene"
    assert loaded is not None
    assert len(loaded.entities) == 2
    assert len(loaded.relationships) == 1
    assert loaded.relationships[0].evidence[0].publication_ids == ("MED:fixture",)
