from pydantic import BaseModel, ConfigDict, Field, field_validator

from genegarden_api.models import (
    DiscoveryOptions,
    EntityType,
    RelationshipType,
)
from genegarden_api.services.normalization import validate_canonical_entity_id


class DiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str | None = None
    target_entity_types: list[EntityType] = Field(default_factory=list, max_length=4)
    intermediate_entity_types: list[EntityType] = Field(default_factory=list, max_length=4)
    relationship_types: list[RelationshipType] = Field(
        default_factory=lambda: [RelationshipType.GENE_ASSOCIATED_WITH_DISEASE],
        min_length=1,
        max_length=4,
    )
    max_path_length: int = Field(default=3, ge=1, le=4)
    result_count: int = Field(default=10, ge=1, le=25)

    @field_validator("source_id", "target_id")
    @classmethod
    def validate_identifier(cls, value: str | None) -> str | None:
        return validate_canonical_entity_id(value) if value is not None else None

    @field_validator("target_entity_types", "intermediate_entity_types", "relationship_types")
    @classmethod
    def reject_duplicate_filters(cls, values: list) -> list:
        if len(values) != len(set(values)):
            raise ValueError("Filter values must be unique")
        return values

    def to_options(self) -> DiscoveryOptions:
        return DiscoveryOptions(
            source_id=self.source_id,
            target_id=self.target_id,
            target_entity_types=frozenset(self.target_entity_types),
            intermediate_entity_types=frozenset(self.intermediate_entity_types),
            relationship_types=frozenset(self.relationship_types),
            max_path_length=self.max_path_length,
            result_count=self.result_count,
        )
