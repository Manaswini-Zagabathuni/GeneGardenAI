from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, Field

from genegarden_api.models.discovery import CandidatePath
from genegarden_api.models.domain import (
    BiologicalEntity,
    BiomedicalRelationship,
    DomainModel,
    EvidenceRecord,
    Publication,
)


class ClaimScope(StrEnum):
    DIRECT_RELATIONSHIP = "direct_relationship"
    INFERRED_PATH = "inferred_path"


class ConflictStatus(StrEnum):
    NONE_REPORTED = "none_reported"
    CONFLICTING = "conflicting"
    NOT_ASSESSED = "not_assessed"


class PublicationReference(DomainModel):
    citation_id: str
    source_identifier: str
    title: str
    web_url: AnyHttpUrl
    author_string: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    is_open_access: bool | None = None
    verified_from: Literal["persisted_europe_pmc", "live_europe_pmc"]


class EvidenceItemView(DomainModel):
    evidence_id: str
    record: EvidenceRecord
    publications: tuple[PublicationReference, ...] = ()
    missing_publication_ids: tuple[str, ...] = ()
    interpretation: str


class RelationshipEvidenceView(DomainModel):
    claim_id: str
    claim_scope: Literal[ClaimScope.DIRECT_RELATIONSHIP] = ClaimScope.DIRECT_RELATIONSHIP
    source_entity: BiologicalEntity
    target_entity: BiologicalEntity
    traversed_from: str
    traversed_to: str
    direction: Literal["forward", "reverse"]
    relationship: BiomedicalRelationship
    evidence_items: tuple[EvidenceItemView, ...]
    conflict_status: ConflictStatus
    uncertainty: tuple[str, ...]


class PathEvidenceView(DomainModel):
    path_id: str
    claim_scope: ClaimScope
    path: CandidatePath
    relationships: tuple[RelationshipEvidenceView, ...]
    publications: tuple[PublicationReference, ...]
    missing_evidence: bool
    conflict_status: ConflictStatus
    uncertainty: tuple[str, ...]


class AssistantEvidenceBundle(DomainModel):
    scope_entity: BiologicalEntity | None = None
    path: PathEvidenceView | None = None
    relationships: tuple[RelationshipEvidenceView, ...] = ()
    publications: tuple[PublicationReference, ...] = ()
    limitations: tuple[str, ...] = ()


class AssistantClaimCategory(StrEnum):
    REPORTED_FINDING = "reported_finding"
    HYPOTHESIS = "hypothesis"
    MODEL_INTERPRETATION = "model_interpretation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AssistantClaim(DomainModel):
    text: str = Field(min_length=1, max_length=2000)
    category: AssistantClaimCategory
    citation_ids: tuple[str, ...] = ()


class AssistantAnswer(DomainModel):
    question: str
    mode: Literal["evidence_summary", "llm_grounded"]
    provider_available: bool
    claims: tuple[AssistantClaim, ...]
    references: tuple[PublicationReference, ...]
    unsupported_claims: tuple[str, ...] = ()
    limitations: tuple[str, ...]
    evidence_bundle: AssistantEvidenceBundle


def publication_reference(
    publication: Publication, *, verified_from: Literal["persisted_europe_pmc", "live_europe_pmc"]
) -> PublicationReference | None:
    parts = publication.source_identifier.split(":", 1)
    if len(parts) != 2 or not parts[0].isalnum() or not _safe_publication_id(parts[1]):
        return None
    source, identifier = parts[0].upper(), parts[1]
    return PublicationReference(
        citation_id=f"publication:{publication.source_identifier}",
        source_identifier=publication.source_identifier,
        title=publication.title,
        web_url=f"https://europepmc.org/article/{source}/{identifier}",
        author_string=publication.author_string,
        journal=publication.journal,
        publication_year=publication.publication_year,
        abstract=publication.abstract,
        doi=publication.doi,
        pmid=publication.pmid,
        pmcid=publication.pmcid,
        is_open_access=publication.is_open_access,
        verified_from=verified_from,
    )


def _safe_publication_id(value: str) -> bool:
    return (
        bool(value)
        and len(value) <= 128
        and all(character.isalnum() or character in "._-" for character in value)
    )
