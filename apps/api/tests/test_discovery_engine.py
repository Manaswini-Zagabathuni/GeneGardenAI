from datetime import UTC, datetime

import pytest

from genegarden_api.graph.discovery import (
    BiomedicalDiscoveryEngine,
    DiscoveryLimitError,
    IncompatibleRelationshipError,
)
from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    DiscoveryOptions,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    RelationshipType,
    SourceName,
)

NOW = datetime(2026, 10, 11, tzinfo=UTC)


def entity(identifier: str, entity_type: EntityType, label: str) -> BiologicalEntity:
    return BiologicalEntity(
        canonical_id=identifier,
        entity_type=entity_type,
        label=label,
        source=SourceName.OPEN_TARGETS,
        source_identifier=identifier.split(":", 1)[1],
        retrieved_at=NOW,
    )


def relationship(
    key: str,
    source_id: str,
    target_id: str,
    *,
    score: float | None = 0.8,
    datasource: str | None = "eva",
    duplicate_evidence: bool = False,
) -> BiomedicalRelationship:
    evidence: tuple[EvidenceRecord, ...] = ()
    if datasource:
        record = EvidenceRecord(
            source=SourceName.OPEN_TARGETS,
            source_record_id=f"{key}:{datasource}",
            evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
            score=score,
            attributes={"datasource_id": datasource},
            retrieved_at=NOW,
        )
        evidence = (record, record) if duplicate_evidence else (record,)
    return BiomedicalRelationship(
        canonical_key=key,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier=key,
        score=score,
        evidence=evidence,
        retrieved_at=NOW,
    )


def cycle_snapshot() -> KnowledgeGraphSnapshot:
    gene_a = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene A")
    gene_b = entity("ensembl:ENSG00000000002", EntityType.GENE, "Gene B")
    disease_a = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease A")
    disease_b = entity("mondo:MONDO_0000002", EntityType.DISEASE, "Disease B")
    disconnected = entity("mondo:MONDO_0000003", EntityType.DISEASE, "Disconnected")
    relationships = (
        relationship("rel1", gene_a.canonical_id, disease_a.canonical_id, score=0.9),
        relationship("rel2", gene_b.canonical_id, disease_a.canonical_id, score=0.8),
        relationship("rel3", gene_b.canonical_id, disease_b.canonical_id, score=0.7),
        relationship("rel4", gene_a.canonical_id, disease_b.canonical_id, score=0.6),
    )
    return KnowledgeGraphSnapshot(
        entities=(gene_a, gene_b, disease_a, disease_b, disconnected),
        relationships=relationships,
    )


def test_bounded_search_prevents_cycles_and_filters_endpoint_type() -> None:
    result = BiomedicalDiscoveryEngine().search(
        cycle_snapshot(),
        DiscoveryOptions(
            source_id="ensembl:ENSG00000000001",
            target_entity_types=frozenset({EntityType.DISEASE}),
            max_path_length=4,
            result_count=25,
        ),
    )

    assert result.paths
    assert all(
        len(path.nodes) == len(set(node.canonical_id for node in path.nodes))
        for path in result.paths
    )
    assert all(path.nodes[-1].entity_type == EntityType.DISEASE for path in result.paths)
    assert all(len(path.edges) <= 4 for path in result.paths)
    assert not any(path.nodes[-1].label == "Disconnected" for path in result.paths)


def test_parallel_duplicate_edges_produce_one_path_and_keep_provenance() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene")
    disease = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease")
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease),
        relationships=(
            relationship(
                "duplicate-a",
                gene.canonical_id,
                disease.canonical_id,
                duplicate_evidence=True,
            ),
            relationship("duplicate-b", gene.canonical_id, disease.canonical_id),
        ),
    )
    result = BiomedicalDiscoveryEngine().search(
        snapshot,
        DiscoveryOptions(source_id=gene.canonical_id, max_path_length=1),
    )

    assert len(result.paths) == 1
    edge = result.paths[0].edges[0]
    assert len(edge.relationships) == 2
    assert len(edge.relationships[0].evidence) == 1


def test_missing_evidence_is_disclosed_and_not_fabricated() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene")
    disease = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease")
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease),
        relationships=(
            relationship(
                "missing", gene.canonical_id, disease.canonical_id, score=None, datasource=None
            ),
        ),
    )
    result = BiomedicalDiscoveryEngine().search(
        snapshot, DiscoveryOptions(source_id=gene.canonical_id)
    )
    path = result.paths[0]
    strength = next(
        item for item in path.score.components if item.name == "comparable_evidence_strength"
    )

    assert strength.raw_value is None
    assert strength.contribution == 0
    assert any("lacked a comparable" in limitation for limitation in path.limitations)
    assert "not a probability" in path.score.interpretation


def test_disconnected_target_and_empty_graph_return_empty_results() -> None:
    snapshot = cycle_snapshot()
    disconnected = BiomedicalDiscoveryEngine().search(
        snapshot,
        DiscoveryOptions(
            source_id="ensembl:ENSG00000000001",
            target_id="mondo:MONDO_0000003",
        ),
    )
    missing_source = BiomedicalDiscoveryEngine().search(
        snapshot,
        DiscoveryOptions(source_id="ensembl:ENSG00000000009"),
    )

    assert disconnected.paths == ()
    assert missing_source.paths == ()


def test_enumeration_budget_stops_path_explosion() -> None:
    with pytest.raises(DiscoveryLimitError, match="work budget"):
        BiomedicalDiscoveryEngine().search(
            cycle_snapshot(),
            DiscoveryOptions(
                source_id="ensembl:ENSG00000000001",
                max_path_length=4,
                result_count=25,
                max_enumerated_paths=1,
            ),
        )

    with pytest.raises(DiscoveryLimitError, match="Path expansion"):
        BiomedicalDiscoveryEngine().search(
            cycle_snapshot(),
            DiscoveryOptions(
                source_id="ensembl:ENSG00000000001",
                target_entity_types=frozenset({EntityType.PROTEIN}),
                max_path_length=4,
                max_path_expansions=1,
            ),
        )


def test_self_loop_and_dangling_relationships_do_not_create_candidate_paths() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene")
    disease = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease")
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease),
        relationships=(
            relationship("self-loop", gene.canonical_id, gene.canonical_id),
            relationship("dangling", gene.canonical_id, "mondo:MONDO_9999999"),
        ),
    )

    result = BiomedicalDiscoveryEngine().search(
        snapshot,
        DiscoveryOptions(source_id=gene.canonical_id, max_path_length=4),
    )

    assert result.paths == ()
    assert result.enumerated_path_count == 0


def test_reverse_traversal_preserves_stored_direction() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene")
    disease = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease")
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease),
        relationships=(relationship("directed", gene.canonical_id, disease.canonical_id),),
    )

    result = BiomedicalDiscoveryEngine().search(
        snapshot,
        DiscoveryOptions(
            source_id=disease.canonical_id,
            target_id=gene.canonical_id,
            max_path_length=1,
        ),
    )

    assert result.paths[0].edges[0].direction == "reverse"
    assert result.paths[0].edges[0].relationships[0].source_entity_id == gene.canonical_id
    assert any("traversed in reverse" in item for item in result.paths[0].limitations)


def test_inverted_relationship_semantics_are_rejected_instead_of_mislabeled() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE, "Gene")
    disease = entity("mondo:MONDO_0000001", EntityType.DISEASE, "Disease")
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease),
        relationships=(relationship("inverted", disease.canonical_id, gene.canonical_id),),
    )

    with pytest.raises(IncompatibleRelationshipError, match="gene-to-disease direction"):
        BiomedicalDiscoveryEngine().search(
            snapshot, DiscoveryOptions(source_id=gene.canonical_id, max_path_length=1)
        )
