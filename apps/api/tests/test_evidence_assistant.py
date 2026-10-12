from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from genegarden_api.api.routes.evidence import router as evidence_router
from genegarden_api.core.errors import register_exception_handlers
from genegarden_api.db.session import get_db_session
from genegarden_api.graph.discovery import BiomedicalDiscoveryEngine
from genegarden_api.models import (
    AssistantClaim,
    AssistantClaimCategory,
    AssistantEvidenceBundle,
    BiologicalEntity,
    BiomedicalRelationship,
    ClaimScope,
    DiscoveryOptions,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    Publication,
    RelationshipType,
    SourceName,
)
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository
from genegarden_api.services.assistant import (
    GroundedGenerationRequest,
    GroundedGenerationResult,
    ResearchAssistantService,
)
from genegarden_api.services.evidence import EvidenceExplorerService

NOW = datetime(2026, 10, 11, tzinfo=UTC)


def entity(identifier: str, kind: EntityType) -> BiologicalEntity:
    return BiologicalEntity(
        canonical_id=identifier,
        entity_type=kind,
        label=identifier.rsplit(":", 1)[1],
        source=SourceName.OPEN_TARGETS,
        source_identifier=identifier.rsplit(":", 1)[1],
        retrieved_at=NOW,
    )


def relationship(
    source: BiologicalEntity,
    target: BiologicalEntity,
    *,
    publication_ids: tuple[str, ...] = (),
    stances: tuple[str, ...] = (),
) -> BiomedicalRelationship:
    evidence = [
        EvidenceRecord(
            source=SourceName.EUROPE_PMC,
            source_record_id=f"context:{source.canonical_id}:{target.canonical_id}",
            evidence_type=EvidenceType.LITERATURE_CONTEXT,
            publication_ids=publication_ids,
            retrieved_at=NOW,
        )
    ]
    evidence.extend(
        EvidenceRecord(
            source=SourceName.OPEN_TARGETS,
            source_record_id=f"stance:{stance}",
            evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
            attributes={"stance": stance},
            retrieved_at=NOW,
        )
        for stance in stances
    )
    return BiomedicalRelationship(
        canonical_key=f"{source.canonical_id}|association|{target.canonical_id}",
        source_entity_id=source.canonical_id,
        target_entity_id=target.canonical_id,
        relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
        source=SourceName.OPEN_TARGETS,
        source_identifier=f"{source.source_identifier}:{target.source_identifier}",
        evidence=tuple(evidence),
        retrieved_at=NOW,
    )


@pytest.mark.asyncio
async def test_evidence_explorer_links_only_exact_verified_publications() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE)
    disease = entity("efo:EFO_0000001", EntityType.DISEASE)
    edge = relationship(gene, disease, publication_ids=("MED:12345", "unsafe/id"))
    publication = Publication(
        source_identifier="MED:12345",
        title="Verified fixture publication",
        abstract="Fixture abstract used only to test the API contract.",
        retrieved_at=NOW,
    )
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene, disease), relationships=(edge,), publications=(publication,)
    )
    path = (
        BiomedicalDiscoveryEngine()
        .search(
            snapshot,
            DiscoveryOptions(source_id=gene.canonical_id, max_path_length=1),
        )
        .paths[0]
    )

    view = await EvidenceExplorerService().explore_path(path, snapshot)

    assert view.claim_scope == ClaimScope.DIRECT_RELATIONSHIP
    assert view.publications[0].source_identifier == "MED:12345"
    assert str(view.publications[0].web_url) == "https://europepmc.org/article/MED/12345"
    assert view.relationships[0].evidence_items[0].missing_publication_ids == ("unsafe/id",)
    assert "could not be resolved" in view.relationships[0].uncertainty[0]


@pytest.mark.asyncio
async def test_evidence_explorer_labels_inferred_path_and_conflicting_stances() -> None:
    gene_a = entity("ensembl:ENSG00000000001", EntityType.GENE)
    disease = entity("efo:EFO_0000001", EntityType.DISEASE)
    gene_b = entity("ensembl:ENSG00000000002", EntityType.GENE)
    snapshot = KnowledgeGraphSnapshot(
        entities=(gene_a, disease, gene_b),
        relationships=(
            relationship(gene_a, disease, stances=("support", "refute")),
            relationship(gene_b, disease),
        ),
    )
    path = (
        BiomedicalDiscoveryEngine()
        .search(
            snapshot,
            DiscoveryOptions(
                source_id=gene_a.canonical_id,
                target_id=gene_b.canonical_id,
                max_path_length=2,
            ),
        )
        .paths[0]
    )

    view = await EvidenceExplorerService().explore_path(path, snapshot)

    assert view.claim_scope == ClaimScope.INFERRED_PATH
    assert view.conflict_status == "conflicting"
    assert any("does not establish causality" in note for note in view.uncertainty)


class UnsupportedProvider:
    async def generate(self, request: GroundedGenerationRequest) -> GroundedGenerationResult:
        del request
        return GroundedGenerationResult(
            claims=(
                AssistantClaim(
                    text="An unsupported biomedical mechanism.",
                    category=AssistantClaimCategory.REPORTED_FINDING,
                    citation_ids=("publication:MED:does-not-exist",),
                ),
            )
        )


@pytest.mark.asyncio
async def test_assistant_withholds_unsupported_provider_claims() -> None:
    bundle = AssistantEvidenceBundle(limitations=("No records were retrieved.",))

    answer = await ResearchAssistantService(UnsupportedProvider()).answer(
        question="What mechanism is supported?", evidence=bundle, use_llm=True
    )

    assert answer.mode == "evidence_summary"
    assert answer.claims[0].category == AssistantClaimCategory.INSUFFICIENT_EVIDENCE
    assert answer.unsupported_claims == ("An unsupported biomedical mechanism.",)
    assert any("withheld" in limitation for limitation in answer.limitations)


@pytest.mark.asyncio
async def test_assistant_needs_no_llm_credentials() -> None:
    answer = await ResearchAssistantService().answer(
        question="What is known?",
        evidence=AssistantEvidenceBundle(),
        use_llm=True,
    )

    assert answer.provider_available is False
    assert answer.mode == "evidence_summary"
    assert any("No LLM provider" in limitation for limitation in answer.limitations)


@pytest.mark.asyncio
async def test_entity_assistant_returns_stable_error_when_graph_exceeds_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exceed_limit(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise GraphSnapshotLimitError("The graph exceeded the assistant entity limit.")

    async def fake_session():
        yield object()

    monkeypatch.setattr(KnowledgeRepository, "get_bounded_subgraph", exceed_limit)
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(evidence_router, prefix="/api/v1")
    test_app.dependency_overrides[get_db_session] = fake_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assistant/answer",
            json={
                "question": "What does the evidence show?",
                "entity_id": "ensembl:ENSG00000141510",
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "assistant_query_limit"


@pytest.mark.asyncio
async def test_path_conflict_summary_reports_none_when_all_stances_are_one_sided() -> None:
    gene = entity("ensembl:ENSG00000000001", EntityType.GENE)
    disease = entity("efo:EFO_0000001", EntityType.DISEASE)
    edge = relationship(gene, disease, stances=("support",))
    snapshot = KnowledgeGraphSnapshot(entities=(gene, disease), relationships=(edge,))
    path = (
        BiomedicalDiscoveryEngine()
        .search(snapshot, DiscoveryOptions(source_id=gene.canonical_id, max_path_length=1))
        .paths[0]
    )

    view = await EvidenceExplorerService().explore_path(path, snapshot)

    assert view.relationships[0].conflict_status == "none_reported"
    assert view.conflict_status == "none_reported"
