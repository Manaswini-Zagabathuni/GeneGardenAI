from datetime import UTC, datetime

import pytest

from genegarden_api.graph import KnowledgeGraphBuilder
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
from genegarden_api.services.normalization import (
    IdentifierNormalizationError,
    deduplicate_entities,
    normalize_disease_id,
    normalize_ensembl_gene_id,
    relationship_key,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def entities() -> tuple[BiologicalEntity, BiologicalEntity]:
    return (
        BiologicalEntity(
            canonical_id="ensembl:ENSG00000141510",
            entity_type=EntityType.GENE,
            label="Fixture gene",
            source=SourceName.OPEN_TARGETS,
            source_identifier="ENSG00000141510",
            retrieved_at=NOW,
        ),
        BiologicalEntity(
            canonical_id="efo:EFO_0000001",
            entity_type=EntityType.DISEASE,
            label="Fixture disease",
            source=SourceName.OPEN_TARGETS,
            source_identifier="EFO_0000001",
            retrieved_at=NOW,
        ),
    )


def test_identifier_normalization_and_deduplication() -> None:
    assert normalize_ensembl_gene_id("ensg00000141510.7") == "ensembl:ENSG00000141510"
    assert normalize_disease_id("efo:0000001") == "efo:EFO_0000001"
    with pytest.raises(IdentifierNormalizationError):
        normalize_ensembl_gene_id("not-an-ensembl-id")

    gene = entities()[0]
    duplicate = gene.model_copy(update={"aliases": ("Fixture alias",)})
    merged = deduplicate_entities((gene, duplicate))
    assert len(merged) == 1
    assert merged[0].aliases == ("Fixture alias",)


def test_networkx_builder_preserves_provenance_and_ranking_weight() -> None:
    gene, disease = entities()
    relationship = BiomedicalRelationship(
        canonical_key=relationship_key(
            SourceName.OPEN_TARGETS,
            RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
            gene.canonical_id,
            disease.canonical_id,
        ),
        source_entity_id=gene.canonical_id,
        target_entity_id=disease.canonical_id,
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier="fixture-pair",
        score=0.75,
        evidence=(
            EvidenceRecord(
                source=SourceName.OPEN_TARGETS,
                source_record_id="fixture-evidence",
                evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
                retrieved_at=NOW,
            ),
        ),
        retrieved_at=NOW,
    )
    graph = KnowledgeGraphBuilder().build(
        KnowledgeGraphSnapshot(entities=(gene, disease), relationships=(relationship,))
    )
    edge = graph.edges[gene.canonical_id, disease.canonical_id, relationship.canonical_key]
    assert edge["source"] == "open_targets"
    assert edge["weight"] == 0.25
    assert edge["evidence_records"][0].source_record_id == "fixture-evidence"


def test_networkx_builder_rejects_dangling_relationships() -> None:
    gene = entities()[0]
    relationship = BiomedicalRelationship(
        canonical_key="fixture|dangling",
        source_entity_id=gene.canonical_id,
        target_entity_id="efo:EFO_9999999",
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier="fixture-pair",
        retrieved_at=NOW,
    )
    with pytest.raises(ValueError, match="unknown target"):
        KnowledgeGraphBuilder().build(
            KnowledgeGraphSnapshot(entities=(gene,), relationships=(relationship,))
        )
