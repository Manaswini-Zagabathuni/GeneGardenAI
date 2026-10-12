import hashlib
from collections.abc import Awaitable, Callable

from genegarden_api.models import (
    CandidatePath,
    ClaimScope,
    ConflictStatus,
    EvidenceItemView,
    EvidenceType,
    KnowledgeGraphSnapshot,
    PathEvidenceView,
    Publication,
    PublicationReference,
    RelationshipEvidenceView,
)
from genegarden_api.models.evidence import publication_reference

PublicationResolver = Callable[[str], Awaitable[Publication | None]]


class EvidenceExplorerService:
    """Projects persisted provenance into a claim-oriented, read-only evidence view."""

    def __init__(self, publication_resolver: PublicationResolver | None = None) -> None:
        self._publication_resolver = publication_resolver

    async def explore_path(
        self, path: CandidatePath, snapshot: KnowledgeGraphSnapshot
    ) -> PathEvidenceView:
        entity_by_id = {entity.canonical_id: entity for entity in snapshot.entities}
        publication_by_id = {
            publication.source_identifier: publication for publication in snapshot.publications
        }
        requested_ids = {
            publication_id
            for edge in path.edges
            for relationship in edge.relationships
            for evidence in relationship.evidence
            for publication_id in evidence.publication_ids
        }
        live_ids: set[str] = set()
        if self._publication_resolver:
            for publication_id in sorted(requested_ids - publication_by_id.keys())[:10]:
                publication = await self._publication_resolver(publication_id)
                if publication is not None:
                    publication_by_id[publication_id] = publication
                    live_ids.add(publication_id)

        relationships: list[RelationshipEvidenceView] = []
        for edge in path.edges:
            for relationship in edge.relationships:
                source = entity_by_id[relationship.source_entity_id]
                target = entity_by_id[relationship.target_entity_id]
                evidence_items: list[EvidenceItemView] = []
                for evidence in relationship.evidence:
                    references: list[PublicationReference] = []
                    invalid_ids: list[str] = []
                    for publication_id in evidence.publication_ids:
                        publication = publication_by_id.get(publication_id)
                        reference = (
                            publication_reference(
                                publication,
                                verified_from=(
                                    "live_europe_pmc"
                                    if publication_id in live_ids
                                    else "persisted_europe_pmc"
                                ),
                            )
                            if publication
                            else None
                        )
                        if reference is None:
                            invalid_ids.append(publication_id)
                        else:
                            references.append(reference)
                    evidence_items.append(
                        EvidenceItemView(
                            evidence_id=_evidence_id(
                                relationship.canonical_key, evidence.source_record_id
                            ),
                            record=evidence,
                            publications=tuple(references),
                            missing_publication_ids=tuple(invalid_ids),
                            interpretation=_evidence_interpretation(evidence.evidence_type),
                        )
                    )
                conflict = _conflict_status(relationship.evidence)
                uncertainty = _relationship_uncertainty(
                    has_evidence=bool(relationship.evidence),
                    has_missing_publications=any(
                        item.missing_publication_ids for item in evidence_items
                    ),
                    conflict=conflict,
                )
                relationships.append(
                    RelationshipEvidenceView(
                        claim_id=f"relationship:{relationship.canonical_key}",
                        source_entity=source,
                        target_entity=target,
                        traversed_from=edge.traversed_from,
                        traversed_to=edge.traversed_to,
                        direction=edge.direction,
                        relationship=relationship,
                        evidence_items=tuple(evidence_items),
                        conflict_status=conflict,
                        uncertainty=uncertainty,
                    )
                )

        references_by_id = {
            reference.citation_id: reference
            for relationship in relationships
            for item in relationship.evidence_items
            for reference in item.publications
        }
        relationship_conflicts = {item.conflict_status for item in relationships}
        if ConflictStatus.CONFLICTING in relationship_conflicts:
            overall_conflict = ConflictStatus.CONFLICTING
        elif ConflictStatus.NOT_ASSESSED in relationship_conflicts:
            overall_conflict = ConflictStatus.NOT_ASSESSED
        else:
            overall_conflict = ConflictStatus.NONE_REPORTED
        scope = ClaimScope.DIRECT_RELATIONSHIP if len(path.edges) == 1 else ClaimScope.INFERRED_PATH
        uncertainty = list(path.limitations)
        if scope == ClaimScope.INFERRED_PATH:
            uncertainty.append(
                "This is an inferred multi-step graph path; it is not a directly reported finding "
                "and does not establish causality."
            )
        if not references_by_id:
            uncertainty.append(
                "No verified publication metadata is linked to this path's evidence records."
            )
        return PathEvidenceView(
            path_id=path.path_id,
            claim_scope=scope,
            path=path,
            relationships=tuple(relationships),
            publications=tuple(references_by_id.values()),
            missing_evidence=any(not item.evidence_items for item in relationships),
            conflict_status=overall_conflict,
            uncertainty=tuple(dict.fromkeys(uncertainty)),
        )


def _evidence_id(relationship_key: str, source_record_id: str) -> str:
    digest = hashlib.sha256(f"{relationship_key}|{source_record_id}".encode()).hexdigest()[:16]
    return f"evidence:{digest}"


def _evidence_interpretation(evidence_type: EvidenceType) -> str:
    if evidence_type == EvidenceType.LITERATURE_CONTEXT:
        return (
            "Literature metadata retrieved in the relationship context; presence alone does not "
            "verify the biological claim or causality."
        )
    if evidence_type == EvidenceType.ASSOCIATION_DATASOURCE_SCORE:
        return (
            "An Open Targets datasource aggregation score, preserved in its source-specific "
            "meaning; it is not a probability."
        )
    return (
        "An Open Targets overall association score, preserved as a ranking signal; it is not a "
        "probability or a paper-level claim."
    )


def _conflict_status(evidence_records: tuple) -> ConflictStatus:
    stances = {
        str(record.attributes.get("stance", "")).lower()
        for record in evidence_records
        if record.attributes.get("stance")
    }
    if {"support", "refute"}.issubset(stances):
        return ConflictStatus.CONFLICTING
    if stances:
        return ConflictStatus.NONE_REPORTED
    return ConflictStatus.NOT_ASSESSED


def _relationship_uncertainty(
    *, has_evidence: bool, has_missing_publications: bool, conflict: ConflictStatus
) -> tuple[str, ...]:
    notes: list[str] = []
    if not has_evidence:
        notes.append("No evidence records are attached to this relationship.")
    if has_missing_publications:
        notes.append("One or more referenced publication identifiers could not be resolved.")
    if conflict == ConflictStatus.NOT_ASSESSED:
        notes.append(
            "Conflict was not assessed because the stored sources do not provide a normalized "
            "support/refute stance."
        )
    elif conflict == ConflictStatus.CONFLICTING:
        notes.append("Stored evidence contains both explicit support and refute stances.")
    return tuple(notes)
