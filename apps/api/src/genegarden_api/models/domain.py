from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceName(StrEnum):
    OPEN_TARGETS = "open_targets"
    EUROPE_PMC = "europe_pmc"


class EntityType(StrEnum):
    GENE = "gene"
    PROTEIN = "protein"
    PATHWAY = "pathway"
    DISEASE = "disease"


class RelationshipType(StrEnum):
    GENE_ASSOCIATED_WITH_DISEASE = "gene_associated_with_disease"


class EvidenceType(StrEnum):
    ASSOCIATION_DATASOURCE_SCORE = "association_datasource_score"
    ASSOCIATION_OVERALL_SCORE = "association_overall_score"
    LITERATURE_CONTEXT = "literature_context"


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("retrieved_at", "generated_at", check_fields=False)
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class BiologicalEntity(DomainModel):
    canonical_id: str = Field(min_length=3, max_length=128)
    entity_type: EntityType
    label: str = Field(min_length=1, max_length=512)
    description: str | None = None
    source: SourceName
    source_identifier: str = Field(min_length=1, max_length=255)
    aliases: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)


class Publication(DomainModel):
    source: SourceName = SourceName.EUROPE_PMC
    source_identifier: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1)
    author_string: str | None = None
    journal: str | None = None
    publication_year: int | None = Field(default=None, ge=1500, le=2200)
    abstract: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    is_open_access: bool | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)


class EvidenceRecord(DomainModel):
    source: SourceName
    source_record_id: str = Field(min_length=1, max_length=512)
    evidence_type: EvidenceType
    score: float | None = Field(default=None, ge=0, le=1)
    summary: str | None = None
    publication_ids: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)


class BiomedicalRelationship(DomainModel):
    canonical_key: str = Field(min_length=3, max_length=768)
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    source: SourceName
    source_identifier: str
    score: float | None = Field(default=None, ge=0, le=1)
    score_interpretation: str | None = None
    evidence: tuple[EvidenceRecord, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)


class KnowledgeGraphSnapshot(DomainModel):
    entities: tuple[BiologicalEntity, ...]
    relationships: tuple[BiomedicalRelationship, ...]
    publications: tuple[Publication, ...] = ()
    generated_at: datetime = Field(default_factory=utc_now)
